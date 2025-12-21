"""
Reconciliation Engine
Matches bank transactions to invoices and handles settlement
"""
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from database.models import (
    BankTransaction, Invoice, Reconciliation, TransactionType, TransactionStatus,
    InvoiceType, InvoiceStatus, MatchType, ReconciliationStatus,
    JournalEntry, JournalEntryLine, JournalEntryType, Buyer, Vendor
)
from database.db import get_db
from core.company_manager import CompanyManager
from core.report_generator import regenerate_csvs


def reconcile_transactions(company_id: int = None) -> Dict:
    """
    Run automatic reconciliation of unmatched bank transactions with invoices
    
    Args:
        company_id: Company ID to reconcile for. If None, uses current company (fallback)
    
    Returns:
        Dictionary with reconciliation summary
    """
    db = next(get_db())
    try:
        # Use provided company_id, or fall back to current company
        if company_id is None:
            current_company = CompanyManager.get_current_company()
            if not current_company:
                raise ValueError("No current company set and no company_id provided")
            company_id = current_company.company_id
        else:
            # Verify company exists
            from database.models import Company
            company = db.query(Company).filter(Company.company_id == company_id).first()
            if not company:
                raise ValueError(f"Company with ID {company_id} not found")
        
        # Get unmatched transactions
        unmatched_txns = db.query(BankTransaction).filter(
            BankTransaction.company_id == company_id,
            BankTransaction.status == TransactionStatus.UNMATCHED
        ).all()
        
        # Get pending and partially paid invoices (both can receive payments)
        pending_invoices = db.query(Invoice).filter(
            Invoice.company_id == company_id,
            Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.PARTIALLY_PAID])
        ).all()
        
        # Log for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Reconciliation started for company_id={company_id}")
        logger.info(f"Found {len(unmatched_txns)} unmatched transactions")
        logger.info(f"Found {len(pending_invoices)} pending/partially paid invoices")
        
        matches = []
        exact_matches = 0
        fuzzy_matches = 0
        
        if not unmatched_txns:
            logger.warning("No unmatched transactions found. Nothing to reconcile.")
            return {
                "total_transactions": 0,
                "matches_found": 0,
                "exact_matches": 0,
                "fuzzy_matches": 0,
                "auto_settled": 0,
                "settled_existing": 0,
                "matches": [],
                "message": "No unmatched transactions found"
            }
        
        if not pending_invoices:
            logger.warning("No pending/partially paid invoices found. Nothing to match against.")
            return {
                "total_transactions": len(unmatched_txns),
                "matches_found": 0,
                "exact_matches": 0,
                "fuzzy_matches": 0,
                "auto_settled": 0,
                "settled_existing": 0,
                "matches": [],
                "message": "No pending invoices found to match against"
            }
        
        for txn in unmatched_txns:
            best_match = None
            best_confidence = 0.0
            match_type = None
            
            for invoice in pending_invoices:
                # Match credit transactions to sales invoices
                # Match debit transactions to purchase invoices
                if txn.type == TransactionType.CREDIT and invoice.invoice_type != InvoiceType.SALES:
                    continue
                if txn.type == TransactionType.DEBIT and invoice.invoice_type != InvoiceType.PURCHASE:
                    continue
                
                # Try exact match
                confidence, mtype = exact_match(txn, invoice)
                if confidence > best_confidence:
                    best_match = invoice
                    best_confidence = confidence
                    match_type = mtype
                
                # Try fuzzy match if exact didn't work
                if confidence < 0.95:
                    fuzzy_conf, fuzzy_mtype = fuzzy_match(txn, invoice)
                    if fuzzy_conf > best_confidence:
                        best_match = invoice
                        best_confidence = fuzzy_conf
                        match_type = fuzzy_mtype
                
                # Try partial payment match if other matches didn't work
                if best_confidence < 0.85:
                    partial_conf, partial_mtype = partial_payment_match(txn, invoice)
                    if partial_conf > best_confidence:
                        best_match = invoice
                        best_confidence = partial_conf
                        match_type = partial_mtype
            
            # Create reconciliation if confidence > 70% and match_type is valid
            if best_match and best_confidence >= 0.70 and match_type is not None:
                logger.info(f"Match found: Txn {txn.transaction_id} -> Invoice {best_match.invoice_id} "
                          f"(confidence={best_confidence:.2f}, type={match_type.value})")
                # Check if this is a partial payment
                is_partial_payment = (best_match.amount - txn.amount) > 0.01
                
                # Calculate total reconciled amount for this invoice
                existing_recons = db.query(Reconciliation).join(
                    BankTransaction, Reconciliation.transaction_id == BankTransaction.transaction_id
                ).filter(
                    Reconciliation.invoice_id == best_match.invoice_id,
                    Reconciliation.status == ReconciliationStatus.SETTLED
                ).all()
                
                total_reconciled = sum(
                    recon.transaction.amount for recon in existing_recons
                    if recon.transaction
                )
                total_reconciled += txn.amount
                
                # Auto-settle all matches (confidence >= 0.70 is good enough)
                should_auto_settle = True
                
                reconciliation = Reconciliation(
                    transaction_id=txn.transaction_id,
                    invoice_id=best_match.invoice_id,
                    match_type=match_type,
                    match_confidence=best_confidence,
                    status=ReconciliationStatus.SETTLED
                )
                db.add(reconciliation)
                
                # Update transaction status to SETTLED
                txn.status = TransactionStatus.SETTLED
                
                # Mark invoice as paid only if fully paid, otherwise mark as partially paid
                if total_reconciled >= best_match.amount - 0.01:  # Allow small rounding differences
                    best_match.status = InvoiceStatus.PAID
                elif is_partial_payment:
                    best_match.status = InvoiceStatus.PARTIALLY_PAID
                
                reconciliation.settled_at = datetime.now()
                
                # Create journal entry for payment/receipt
                try:
                    create_journal_entry_from_reconciliation(reconciliation, txn, best_match, db, is_partial_payment)
                except Exception as e:
                    print(f"Error creating journal entry for reconciliation {reconciliation.reconciliation_id}: {e}")
                    # Don't fail reconciliation if journal entry creation fails
                
                if match_type == MatchType.EXACT:
                    exact_matches += 1
                else:
                    fuzzy_matches += 1
                
                matches.append({
                    "transaction_id": txn.transaction_id,
                    "invoice_id": best_match.invoice_id,
                    "match_type": match_type.value,
                    "confidence": best_confidence,
                    "auto_settled": should_auto_settle
                })
        
        # Commit new reconciliations first
        db.commit()
        
        # Also settle any existing pending reconciliations (uses separate session)
        pending_recons = db.query(Reconciliation).join(
            BankTransaction, Reconciliation.transaction_id == BankTransaction.transaction_id
        ).filter(
            BankTransaction.company_id == company_id,
            Reconciliation.status == ReconciliationStatus.PENDING
        ).all()
        
        settled_existing = 0
        for recon in pending_recons:
            try:
                # settle_reconciliation creates its own session, so we need to refresh
                db.refresh(recon)
                settle_reconciliation(recon.reconciliation_id)
                settled_existing += 1
            except Exception as e:
                print(f"Error settling existing reconciliation {recon.reconciliation_id}: {e}")
        
        # Regenerate CSVs if any matches were found or existing ones were settled
        if matches or settled_existing > 0:
            regenerate_csvs(company_id=company_id)
        
        result = {
            "total_transactions": len(unmatched_txns),
            "matches_found": len(matches),
            "exact_matches": exact_matches,
            "fuzzy_matches": fuzzy_matches,
            "auto_settled": len(matches),  # All matches are now auto-settled
            "settled_existing": settled_existing,  # Count of existing pending reconciliations that were settled
            "matches": matches
        }
        
        logger.info(f"Reconciliation complete: {result}")
        return result
    finally:
        db.close()


def exact_match(txn: BankTransaction, invoice: Invoice) -> Tuple[float, Optional[MatchType]]:
    """Try exact match: amount + date + reference"""
    # Amount must match exactly
    if abs(txn.amount - invoice.amount) > 0.01:
        return 0.0, None
    
    # Date should be within 1 day
    if invoice.invoice_date:
        date_diff = abs((txn.date - invoice.invoice_date).days)
        if date_diff > 1:
            return 0.0, None
    
    # Reference match (if available)
    if txn.reference and invoice.invoice_number:
        if invoice.invoice_number.lower() in txn.reference.lower() or \
           txn.reference.lower() in invoice.invoice_number.lower():
            return 0.98, MatchType.EXACT
    
    # Amount + date match
    return 0.95, MatchType.EXACT


def fuzzy_match(txn: BankTransaction, invoice: Invoice) -> Tuple[float, Optional[MatchType]]:
    """Try fuzzy match: amount ±1%, date ±5 days"""
    # Amount within 1%
    amount_diff = abs(txn.amount - invoice.amount) / invoice.amount if invoice.amount > 0 else 1.0
    if amount_diff > 0.01:
        return 0.0, None
    
    # Date within 5 days
    if invoice.invoice_date:
        date_diff = abs((txn.date - invoice.invoice_date).days)
        if date_diff > 5:
            return 0.0, None
        
        # Confidence decreases with date difference
        date_confidence = max(0.0, 1.0 - (date_diff / 5.0) * 0.2)
    else:
        date_confidence = 0.5
    
    # Amount confidence
    amount_confidence = 1.0 - amount_diff * 10
    
    # Combined confidence
    confidence = (amount_confidence * 0.7 + date_confidence * 0.3) * 0.85
    
    return confidence, MatchType.FUZZY


def partial_payment_match(txn: BankTransaction, invoice: Invoice) -> Tuple[float, Optional[MatchType]]:
    """Try partial payment match: reference contains invoice number, amount < invoice amount"""
    # Check if reference contains invoice number (e.g., "241323" in "241323-P1")
    reference_match = False
    if txn.reference and invoice.invoice_number:
        # Extract base invoice number (remove any suffixes)
        base_invoice_num = invoice.invoice_number.split('-')[0].split('_')[0]
        txn_ref_lower = txn.reference.lower()
        invoice_num_lower = invoice.invoice_number.lower()
        base_invoice_lower = base_invoice_num.lower()
        
        # Check if invoice number appears in reference
        if (base_invoice_lower in txn_ref_lower or 
            invoice_num_lower in txn_ref_lower or
            txn_ref_lower in invoice_num_lower):
            reference_match = True
    
    # If no reference match, check description
    description_match = False
    if txn.description and invoice.invoice_number:
        base_invoice_num = invoice.invoice_number.split('-')[0].split('_')[0]
        desc_lower = txn.description.lower()
        invoice_num_lower = invoice.invoice_number.lower()
        base_invoice_lower = base_invoice_num.lower()
        
        if (base_invoice_lower in desc_lower or 
            invoice_num_lower in desc_lower):
            description_match = True
    
    # Must have either reference or description match
    if not (reference_match or description_match):
        return 0.0, None
    
    # Amount must be less than invoice amount (partial payment)
    if txn.amount >= invoice.amount:
        return 0.0, None
    
    # Payment date should be after invoice date (reasonable for payments)
    date_confidence = 1.0
    if invoice.invoice_date:
        days_diff = (txn.date - invoice.invoice_date).days
        if days_diff < 0:
            # Payment before invoice - less likely but possible (advance payment)
            date_confidence = 0.7
        elif days_diff > 90:
            # Payment more than 90 days after invoice - still valid but lower confidence
            date_confidence = max(0.5, 1.0 - (days_diff - 90) / 365.0 * 0.3)
    
    # Amount ratio confidence (partial payments are usually round percentages)
    amount_ratio = txn.amount / invoice.amount if invoice.amount > 0 else 0
    # Check if it's a common percentage (50%, 60%, 40%, 30%, 20%, etc.)
    common_ratios = [0.5, 0.6, 0.4, 0.3, 0.2, 0.7, 0.8, 0.25, 0.75, 0.33, 0.67]
    ratio_match = min([abs(amount_ratio - r) for r in common_ratios]) < 0.01
    
    if ratio_match:
        amount_confidence = 0.9
    else:
        # Still valid but less confident
        amount_confidence = 0.75
    
    # Reference/description match confidence
    ref_confidence = 0.95 if reference_match else (0.85 if description_match else 0.0)
    
    # Combined confidence for partial payment
    confidence = (ref_confidence * 0.5 + amount_confidence * 0.3 + date_confidence * 0.2) * 0.85
    
    return confidence, MatchType.FUZZY  # Use FUZZY for partial payments


def settle_reconciliation(reconciliation_id: int) -> Reconciliation:
    """
    Settle a reconciliation: mark invoice as paid and update balances
    
    Args:
        reconciliation_id: ID of the reconciliation to settle
        
    Returns:
        Updated Reconciliation object
    """
    db = next(get_db())
    try:
        reconciliation = db.query(Reconciliation).filter(
            Reconciliation.reconciliation_id == reconciliation_id
        ).first()
        
        if not reconciliation:
            raise ValueError(f"Reconciliation {reconciliation_id} not found")
        
        if reconciliation.status == ReconciliationStatus.SETTLED:
            return reconciliation  # Already settled
        
        invoice = reconciliation.invoice
        transaction = reconciliation.transaction
        
        # Calculate total reconciled amount
        existing_recons = db.query(Reconciliation).join(
            BankTransaction, Reconciliation.transaction_id == BankTransaction.transaction_id
        ).filter(
            Reconciliation.invoice_id == invoice.invoice_id,
            Reconciliation.status == ReconciliationStatus.SETTLED
        ).all()
        
        total_reconciled = sum(
            recon.transaction.amount for recon in existing_recons
            if recon.transaction
        )
        total_reconciled += transaction.amount
        
        # Mark invoice as paid only if fully paid, otherwise mark as partially paid
        is_partial = (invoice.amount - transaction.amount) > 0.01
        if total_reconciled >= invoice.amount - 0.01:  # Allow small rounding differences
            invoice.status = InvoiceStatus.PAID
        elif is_partial:
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        
        # Mark transaction as settled
        transaction.status = TransactionStatus.SETTLED
        
        # Update reconciliation
        reconciliation.status = ReconciliationStatus.SETTLED
        reconciliation.settled_at = datetime.now()
        
        # Create journal entry for payment/receipt if not already created
        # Check if journal entry already exists for this reconciliation
        existing_entry = db.query(JournalEntry).filter(
            JournalEntry.reference == f"{transaction.reference or transaction.transaction_id}",
            JournalEntry.company_id == invoice.company_id
        ).first()
        
        if not existing_entry:
            try:
                create_journal_entry_from_reconciliation(reconciliation, transaction, invoice, db, is_partial)
            except Exception as e:
                print(f"Error creating journal entry for reconciliation {reconciliation.reconciliation_id}: {e}")
        
        db.commit()
        
        # Regenerate CSVs (balances will be updated)
        # Use company_id from invoice or transaction
        company_id = invoice.company_id if invoice else transaction.company_id
        regenerate_csvs(company_id=company_id)
        
        db.refresh(reconciliation)
        return reconciliation
    finally:
        db.close()


def create_journal_entry_from_reconciliation(
    reconciliation: Reconciliation,
    transaction: BankTransaction,
    invoice: Invoice,
    db,
    is_partial_payment: bool = False
) -> JournalEntry:
    """
    Create journal entry for a payment/receipt from reconciliation
    
    For partial payments: Creates entry with 1 credit and 2 debit lines
    For full payments: Creates standard payment entry
    """
    # Get buyer/vendor names
    buyer_name = "Unknown"
    vendor_name = "Unknown"
    
    if invoice.buyer_id:
        buyer = db.query(Buyer).filter(Buyer.buyer_id == invoice.buyer_id).first()
        if buyer:
            buyer_name = buyer.name
    
    if invoice.vendor_id:
        vendor = db.query(Vendor).filter(Vendor.vendor_id == invoice.vendor_id).first()
        if vendor:
            vendor_name = vendor.name
    
    # Determine entry type
    if transaction.type == TransactionType.CREDIT:
        entry_type = JournalEntryType.RECEIPT  # Money received
    else:
        entry_type = JournalEntryType.PAYMENT  # Money paid
    
    # Calculate payment percentage for narration
    payment_percentage = (transaction.amount / invoice.amount * 100) if invoice.amount > 0 else 0
    
    # Create narration with bank details
    if is_partial_payment:
        narration = f"Being part payment ({payment_percentage:.0f}%) received from {buyer_name if transaction.type == TransactionType.CREDIT else vendor_name} against Invoice No. {invoice.invoice_number}"
    else:
        narration = f"Being payment received from {buyer_name if transaction.type == TransactionType.CREDIT else vendor_name} against Invoice No. {invoice.invoice_number}"
    
    # Add payment mode and reference
    if transaction.description:
        # Extract payment mode from description (RTGS, NEFT, UPI, etc.)
        desc_upper = transaction.description.upper()
        payment_modes = ['RTGS', 'NEFT', 'IMPS', 'UPI', 'CHEQUE', 'CASH', 'ECS', 'NACH']
        payment_mode = None
        for mode in payment_modes:
            if mode in desc_upper:
                payment_mode = mode
                break
        
        if payment_mode:
            narration += f" via {payment_mode}"
    
    if transaction.reference:
        narration += f" Ref: {transaction.reference}"
    
    journal_entry = JournalEntry(
        company_id=invoice.company_id,
        entry_type=entry_type,
        date=transaction.date,
        narration=narration,
        reference=transaction.reference or str(transaction.transaction_id),
        status="approved"
    )
    db.add(journal_entry)
    db.flush()  # Get entry_id
    
    lines = []
    
    # Extract bank account info from description or use default
    bank_account_name = "Bank Account"
    bank_account_number = ""
    
    # Try to extract bank account info from description
    if transaction.description:
        desc = transaction.description.upper()
        # Look for account number patterns (e.g., "4512XXXXXXX890", "A/C 1234567890")
        account_match = re.search(r'(\d{4,}X*\d{4,})|(A/C\s*:?\s*\d{4,})|(ACC\s*:?\s*\d{4,})', desc)
        if account_match:
            bank_account_number = account_match.group(0).replace('A/C', '').replace('ACC', '').replace(':', '').strip()
        
        # Look for bank name (HDFC, ICICI, SBI, etc.)
        bank_names = ['HDFC', 'ICICI', 'SBI', 'AXIS', 'KOTAK', 'PNB', 'BOI', 'BOB', 'CANARA', 'UNION']
        for bank in bank_names:
            if bank in desc:
                bank_account_name = f"{bank} Bank"
                break
    
    # Format bank account name with account number if available
    if bank_account_number:
        bank_account_display = f"{bank_account_name} ({bank_account_number})"
    else:
        bank_account_display = bank_account_name
    
    if transaction.type == TransactionType.CREDIT:
        # RECEIPT: Money received
        # Accounting: Debit Bank (asset increases), Credit Debtors (asset decreases)
        # For partial payments: 1 Debit (Bank) + 2 Credit structure (as per requirement)
        if is_partial_payment:
            # Partial payment: 1 Debit (Bank) + 2 Credit lines
            # Calculate the ratio of payment to invoice
            payment_ratio = transaction.amount / invoice.amount if invoice.amount > 0 else 1.0
            
            # Debit: Bank Account (money received - asset increases)
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="1100",
                account_name=bank_account_display,
                debit=transaction.amount,
                credit=0
            ))
            
            # Allocate payment proportionally: principal (taxable) and GST portions
            # Credit 1: Debtors Account - Principal portion (taxable value proportion)
            principal_amount = invoice.taxable_amount * payment_ratio
            
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="1200",
                account_name=f"Debtors – {buyer_name}",
                debit=0,
                credit=principal_amount
            ))
            
            # Credit 2: GST portion of the payment (combined GST accounts)
            # Calculate total GST portion proportionally
            total_gst = (invoice.cgst_amount or 0) + (invoice.sgst_amount or 0) + (invoice.igst_amount or 0)
            gst_portion = total_gst * payment_ratio
            remaining_amount = transaction.amount - principal_amount
            
            if remaining_amount > 0.01:  # Only if significant amount
                # For sales invoices, GST Output accounts are being reduced (settled)
                # Allocate to the appropriate GST Output account based on invoice
                if invoice.igst_amount and invoice.igst_amount > 0:
                    # Inter-state: Use IGST Output
                    lines.append(JournalEntryLine(
                        entry_id=journal_entry.entry_id,
                        account_code="2310",
                        account_name="IGST Output (Settlement)",
                        debit=0,
                        credit=remaining_amount
                    ))
                elif (invoice.cgst_amount or 0) > 0 or (invoice.sgst_amount or 0) > 0:
                    # Intra-state: Use CGST Output (we'll combine CGST+SGST into one line)
                    # This maintains the 1 debit + 2 credit structure
                    lines.append(JournalEntryLine(
                        entry_id=journal_entry.entry_id,
                        account_code="2320",
                        account_name="CGST/SGST Output (Settlement)",
                        debit=0,
                        credit=remaining_amount
                    ))
                else:
                    # No GST in invoice, allocate to Suspense for review
                    lines.append(JournalEntryLine(
                        entry_id=journal_entry.entry_id,
                        account_code="9999",
                        account_name="Suspense - Payment Allocation",
                        debit=0,
                        credit=remaining_amount
                    ))
        else:
            # Full payment: Standard entry (Debit Bank, Credit Debtors)
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="1100",
                account_name=bank_account_display,
                debit=transaction.amount,
                credit=0
            ))
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="1200",
                account_name=f"Debtors – {buyer_name}",
                debit=0,
                credit=transaction.amount
            ))
    else:
        # PAYMENT: Money paid
        # For partial payments: 1 Debit + 2 Credit structure (as per requirement)
        if is_partial_payment:
            # Partial payment: 1 Debit (Bank) + 2 Credit lines
            # Calculate payment ratio
            payment_ratio = transaction.amount / invoice.amount if invoice.amount > 0 else 1.0
            
            # Debit: Bank Account (money paid)
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="1100",
                account_name=bank_account_display,
                debit=transaction.amount,
                credit=0
            ))
            
            # Credit 1: Creditors Account - Principal portion (taxable value proportion)
            principal_amount = invoice.taxable_amount * payment_ratio
            
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="2100",
                account_name=f"Creditors – {vendor_name}",
                debit=0,
                credit=principal_amount
            ))
            
            # Credit 2: GST portion of the payment (combined GST accounts)
            remaining_amount = transaction.amount - principal_amount
            
            if remaining_amount > 0.01:
                # For purchase invoices, GST Input accounts are being reduced (settled)
                # Allocate to the appropriate GST Input account based on invoice
                if invoice.igst_amount and invoice.igst_amount > 0:
                    # Inter-state: Use IGST Input
                    lines.append(JournalEntryLine(
                        entry_id=journal_entry.entry_id,
                        account_code="2311",
                        account_name="IGST Input (Settlement)",
                        debit=0,
                        credit=remaining_amount
                    ))
                elif (invoice.cgst_amount or 0) > 0 or (invoice.sgst_amount or 0) > 0:
                    # Intra-state: Use CGST Input (we'll combine CGST+SGST into one line)
                    # This maintains the 1 debit + 2 credit structure
                    lines.append(JournalEntryLine(
                        entry_id=journal_entry.entry_id,
                        account_code="2321",
                        account_name="CGST/SGST Input (Settlement)",
                        debit=0,
                        credit=remaining_amount
                    ))
                else:
                    # No GST in invoice, allocate to Suspense for review
                    lines.append(JournalEntryLine(
                        entry_id=journal_entry.entry_id,
                        account_code="9999",
                        account_name="Suspense - Payment Allocation",
                        debit=0,
                        credit=remaining_amount
                    ))
        else:
            # Full payment: Standard entry (Debit Bank, Credit Creditors)
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="1100",
                account_name=bank_account_display,
                debit=transaction.amount,
                credit=0
            ))
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="2100",
                account_name=f"Creditors – {vendor_name}",
                debit=0,
                credit=transaction.amount
            ))
    
    # Add all lines
    for line in lines:
        db.add(line)
    
    return journal_entry


def manual_settle(transaction_id: int, invoice_id: int) -> Reconciliation:
    """
    Manually create a settlement between transaction and invoice
    
    Args:
        transaction_id: Bank transaction ID
        invoice_id: Invoice ID
        
    Returns:
        Created Reconciliation object
    """
    db = next(get_db())
    try:
        # Check if reconciliation already exists
        existing = db.query(Reconciliation).filter(
            Reconciliation.transaction_id == transaction_id,
            Reconciliation.invoice_id == invoice_id
        ).first()
        
        if existing:
            return settle_reconciliation(existing.reconciliation_id)
        
        # Create new reconciliation
        reconciliation = Reconciliation(
            transaction_id=transaction_id,
            invoice_id=invoice_id,
            match_type=MatchType.MANUAL,
            match_confidence=1.0,
            status=ReconciliationStatus.PENDING
        )
        db.add(reconciliation)
        db.commit()
        
        # Settle it
        return settle_reconciliation(reconciliation.reconciliation_id)
    finally:
        db.close()


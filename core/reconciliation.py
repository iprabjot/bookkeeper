"""
Reconciliation Engine
Matches bank transactions to invoices and handles settlement
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from database.models import (
    BankTransaction, Invoice, Reconciliation, TransactionType, TransactionStatus,
    InvoiceType, InvoiceStatus, MatchType, ReconciliationStatus
)
from database.db import get_db
from core.company_manager import CompanyManager
from core.report_generator import regenerate_csvs


def reconcile_transactions() -> Dict:
    """
    Run automatic reconciliation of unmatched bank transactions with invoices
    
    Returns:
        Dictionary with reconciliation summary
    """
    db = next(get_db())
    try:
        current_company = CompanyManager.get_current_company()
        if not current_company:
            raise ValueError("No current company set")
        
        # Get unmatched transactions
        unmatched_txns = db.query(BankTransaction).filter(
            BankTransaction.company_id == current_company.company_id,
            BankTransaction.status == TransactionStatus.UNMATCHED
        ).all()
        
        # Get pending invoices
        pending_invoices = db.query(Invoice).filter(
            Invoice.company_id == current_company.company_id,
            Invoice.status == InvoiceStatus.PENDING
        ).all()
        
        matches = []
        exact_matches = 0
        fuzzy_matches = 0
        
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
            
            # Create reconciliation if confidence > 70% and match_type is valid
            if best_match and best_confidence >= 0.70 and match_type is not None:
                # Auto-settle all matches (confidence >= 0.70 is good enough)
                # This ensures invoices are marked as PAID when transactions are matched
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
                
                # Mark invoice as paid
                best_match.status = InvoiceStatus.PAID
                reconciliation.settled_at = datetime.now()
                
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
            BankTransaction.company_id == current_company.company_id,
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
            regenerate_csvs(company_id=current_company.company_id)
        
        return {
            "total_transactions": len(unmatched_txns),
            "matches_found": len(matches),
            "exact_matches": exact_matches,
            "fuzzy_matches": fuzzy_matches,
            "auto_settled": len(matches),  # All matches are now auto-settled
            "settled_existing": settled_existing,  # Count of existing pending reconciliations that were settled
            "matches": matches
        }
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
        
        # Mark invoice as paid
        invoice.status = InvoiceStatus.PAID
        
        # Mark transaction as settled
        transaction.status = TransactionStatus.SETTLED
        
        # Update reconciliation
        reconciliation.status = ReconciliationStatus.SETTLED
        reconciliation.settled_at = datetime.now()
        
        db.commit()
        
        # Regenerate CSVs (balances will be updated)
        # Use company_id from invoice or transaction
        company_id = invoice.company_id if invoice else transaction.company_id
        regenerate_csvs(company_id=company_id)
        
        db.refresh(reconciliation)
        return reconciliation
    finally:
        db.close()


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


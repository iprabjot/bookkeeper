"""
Processing Engine
Processes invoices and creates appropriate journal entries
"""
from datetime import datetime
from typing import Dict, List
from sqlalchemy import func as sql_func
from database.models import (
    JournalEntry, JournalEntryLine, Invoice, InvoiceType, InvoiceStatus,
    JournalEntryType, Vendor, Buyer
)
from database.db import get_db
from core.company_manager import CompanyManager
from core.invoice_classifier import classify_invoice
from core.vendor_buyer_manager import VendorBuyerManager
from core.report_generator import regenerate_csvs


def _parse_date(date_str: str) -> datetime:
    """Parse date string in various formats"""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return None


def process_invoice(invoice_data: Dict, file_path: str) -> Invoice:
    """
    Process an invoice: classify, create vendor/buyer, create journal entry
    
    Args:
        invoice_data: Extracted invoice data from PDF
        file_path: Path to the invoice PDF file
        
    Returns:
        Created Invoice object
    """
    db = next(get_db())
    try:
        current_company = CompanyManager.get_current_company()
        if not current_company:
            raise ValueError("No current company set")
        
        # Classify invoice
        classification = classify_invoice(invoice_data)
        invoice_type_str = classification["type"]
        invoice_type = InvoiceType.SALES if invoice_type_str == "sales" else InvoiceType.PURCHASE
        
        # Get or create vendor/buyer
        vendor_id = None
        buyer_id = None
        
        if invoice_type == InvoiceType.PURCHASE:
            # Purchase invoice: vendor is the supplier
            vendor_name = invoice_data.get("vendor_name") or ""
            vendor_gstin = invoice_data.get("vendor_gstin")
            
            if not vendor_name.strip():
                raise ValueError("Vendor name is required for purchase invoices but could not be extracted from PDF")
            
            vendor = VendorBuyerManager.get_or_create_vendor(
                name=vendor_name.strip(),
                gstin=vendor_gstin.strip() if vendor_gstin else None,
                address=None,
                contact_info=None
            )
            vendor_id = vendor.vendor_id
        else:
            # Sales invoice: buyer is the customer
            customer_name = invoice_data.get("customer_name") or ""
            customer_gstin = invoice_data.get("customer_gstin")
            
            if not customer_name.strip():
                raise ValueError("Customer name is required for sales invoices but could not be extracted from PDF")
            
            buyer = VendorBuyerManager.get_or_create_buyer(
                name=customer_name.strip(),
                gstin=customer_gstin.strip() if customer_gstin else None,
                address=None,
                contact_info=None
            )
            buyer_id = buyer.buyer_id
        
        # Get invoice number - ensure it's not None or empty
        invoice_number = invoice_data.get("invoice_number")
        
        # Only use fallback if invoice_number is missing, None, empty, or "None" string
        if not invoice_number or invoice_number == "None" or (isinstance(invoice_number, str) and invoice_number.strip() == ""):
            # Try to extract from filename as fallback (e.g., "Tax Invoice_241323_12_01_25" -> "241323")
            from pathlib import Path
            filename = Path(file_path).stem
            import re
            match = re.search(r'_(\d+)_', filename)
            if match:
                invoice_number = match.group(1)
            else:
                # Last resort: generate timestamp-based invoice number
                invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Ensure invoice_number is a non-empty string
        invoice_number = str(invoice_number).strip() if invoice_number else f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if not invoice_number:
            invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Parse invoice date for duplicate checking
        invoice_date = _parse_date(invoice_data.get("invoice_date")) if invoice_data.get("invoice_date") else None
        invoice_amount = invoice_data.get("total_amount", 0)
        
        # Check for duplicate invoice
        # Duplicate criteria: same company, same invoice number, same date, and same amount
        duplicate_query = db.query(Invoice).filter(
            Invoice.company_id == current_company.company_id,
            Invoice.invoice_number == invoice_number
        )
        
        # If we have a date, also match by date
        if invoice_date:
            duplicate_query = duplicate_query.filter(Invoice.invoice_date == invoice_date)
        
        # If we have an amount, also match by amount (with small tolerance for rounding)
        if invoice_amount > 0:
            duplicate_query = duplicate_query.filter(
                sql_func.abs(Invoice.amount - invoice_amount) < 0.01  # Allow 1 paisa tolerance
            )
        
        existing_invoice = duplicate_query.first()
        
        if existing_invoice:
            # Check if it's the exact same file
            if existing_invoice.file_path == file_path:
                raise ValueError(
                    f"Duplicate invoice: This invoice file has already been uploaded. "
                    f"Invoice #{existing_invoice.invoice_number} (ID: {existing_invoice.invoice_id})"
                )
            else:
                # Same invoice number but different file - might be a duplicate upload
                raise ValueError(
                    f"Duplicate invoice: An invoice with number '{invoice_number}' "
                    f"already exists for this company. "
                    f"Existing invoice ID: {existing_invoice.invoice_id}, "
                    f"Date: {existing_invoice.invoice_date}, "
                    f"Amount: {existing_invoice.amount}. "
                    f"If this is a different invoice, please verify the invoice number."
                )
        
        # Create invoice record
        invoice = Invoice(
            company_id=current_company.company_id,
            vendor_id=vendor_id,
            buyer_id=buyer_id,
            invoice_type=invoice_type,
            file_path=file_path,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            amount=invoice_amount,
            taxable_amount=invoice_data.get("taxable_amount", 0),
            igst_amount=invoice_data.get("igst", 0),
            cgst_amount=invoice_data.get("cgst", 0),
            sgst_amount=invoice_data.get("sgst", 0),
            status=InvoiceStatus.PENDING
        )
        db.add(invoice)
        db.flush()  # Get invoice_id
        
        # Create journal entry (using same db session)
        journal_entry = create_journal_entry_from_invoice(invoice, invoice_data, db)
        db.add(journal_entry)
        db.commit()
        
        # Regenerate CSVs
        regenerate_csvs(company_id=current_company.company_id)
        
        db.refresh(invoice)
        return invoice
    finally:
        db.close()


def create_journal_entry_from_invoice(invoice: Invoice, invoice_data: Dict, db) -> JournalEntry:
    """Create journal entry from invoice"""
    # Get buyer/vendor names
    buyer_name = "Unknown"
    if invoice.buyer_id:
        buyer = db.query(Buyer).filter(Buyer.buyer_id == invoice.buyer_id).first()
        if buyer:
            buyer_name = buyer.name
    
    vendor_name = "Unknown"
    if invoice.vendor_id:
        vendor = db.query(Vendor).filter(Vendor.vendor_id == invoice.vendor_id).first()
        if vendor:
            vendor_name = vendor.name
    
    entry_type = JournalEntryType.SALES if invoice.invoice_type == InvoiceType.SALES else JournalEntryType.PURCHASE
    
    journal_entry = JournalEntry(
        company_id=invoice.company_id,
        entry_type=entry_type,
        date=invoice.invoice_date or datetime.now(),
        narration=f"{'Sales' if invoice.invoice_type == InvoiceType.SALES else 'Purchase'} invoice {invoice.invoice_number}",
        reference=invoice.invoice_number,
        status="approved"
    )
    db.add(journal_entry)
    db.flush()  # Get entry_id
    
    # Create journal entry lines
    lines = []
    
    if invoice.invoice_type == InvoiceType.SALES:
        # Sales Invoice: Debit Debtors, Credit Sales + GST Payable
        # Debit: Debtors
        lines.append(JournalEntryLine(
            entry_id=journal_entry.entry_id,
            account_code="1100",
            account_name=f"Debtors – {buyer_name}",
            debit=invoice.amount,
            credit=0
        ))
        
        # Credit: Sales
        lines.append(JournalEntryLine(
            entry_id=journal_entry.entry_id,
            account_code="4100",
            account_name="Sales A/c",
            debit=0,
            credit=invoice.taxable_amount
        ))
        
        # Credit: GST Payable
        if invoice.igst_amount > 0:
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="2310",
                account_name="IGST Payable A/c",
                debit=0,
                credit=invoice.igst_amount
            ))
        if invoice.cgst_amount > 0:
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="2320",
                account_name="CGST Payable A/c",
                debit=0,
                credit=invoice.cgst_amount
            ))
        if invoice.sgst_amount > 0:
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="2330",
                account_name="SGST Payable A/c",
                debit=0,
                credit=invoice.sgst_amount
            ))
    else:
        # Purchase Invoice: Debit Expenses + GST Input, Credit Creditors
        # Debit: Expenses (or Inventory)
        lines.append(JournalEntryLine(
            entry_id=journal_entry.entry_id,
            account_code="5100",
            account_name="Purchase Expenses",
            debit=invoice.taxable_amount,
            credit=0
        ))
        
        # Debit: GST Input
        if invoice.igst_amount > 0:
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="2311",
                account_name="IGST Input A/c",
                debit=invoice.igst_amount,
                credit=0
            ))
        if invoice.cgst_amount > 0:
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="2321",
                account_name="CGST Input A/c",
                debit=invoice.cgst_amount,
                credit=0
            ))
        if invoice.sgst_amount > 0:
            lines.append(JournalEntryLine(
                entry_id=journal_entry.entry_id,
                account_code="2331",
                account_name="SGST Input A/c",
                debit=invoice.sgst_amount,
                credit=0
            ))
        
        # Credit: Creditors
        lines.append(JournalEntryLine(
            entry_id=journal_entry.entry_id,
            account_code="2100",
            account_name=f"Creditors – {vendor_name}",
            debit=0,
            credit=invoice.amount
        ))
    
    # Add all lines
    for line in lines:
        db.add(line)
    
    return journal_entry


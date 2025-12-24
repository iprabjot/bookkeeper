"""
Bank Statement Parser
Parses CSV and PDF bank statements and extracts transactions with AI categorization
"""
import csv
import os
from datetime import datetime
from typing import List, Dict, Optional
from database.models import BankTransaction, TransactionType, Reconciliation
from database.db import get_db
from core.company_manager import CompanyManager
from core.bank_statement_pdf_parser import parse_bank_statement_pdf
from core.transaction_categorizer import categorize_transaction_with_ai, categorize_transaction_rule_based
import logging

logger = logging.getLogger(__name__)


def parse_bank_statement(file_path: str, company_id: int = None, categorize: bool = True) -> List[BankTransaction]:
    """
    Parse bank statement (CSV or PDF) and create bank transactions with categorization
    
    Supports:
    - CSV files: Date, Description, Debit, Credit, Balance
    - PDF files: HDFC, ICICI, SBI, and other Indian bank formats
    
    Args:
        file_path: Path to CSV or PDF file
        company_id: Company ID to associate transactions with
        categorize: If True, use AI to categorize transactions
    
    Returns:
        List of created BankTransaction objects with categories
    """
    # Determine file type
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.pdf':
        return parse_bank_statement_pdf_with_categorization(file_path, company_id, categorize)
    elif file_ext == '.csv':
        return parse_bank_statement_csv(file_path, company_id, categorize)
    else:
        raise ValueError(f"Unsupported file format: {file_ext}. Only CSV and PDF are supported.")


def parse_bank_statement_csv(file_path: str, company_id: int = None, categorize: bool = True) -> List[BankTransaction]:
    """
    Parse CSV bank statement and create bank transactions
    
    Supports common formats:
    - HDFC: Date, Description, Debit, Credit, Balance
    - ICICI: Date, Description, Amount, Type (Dr/Cr)
    - SBI: Date, Description, Withdrawal, Deposit, Balance
    - Generic: Date, Description, Amount, Type
    
    Args:
        file_path: Path to CSV file
        company_id: Company ID to associate transactions with. If None, uses current company (fallback)
    
    Returns:
        List of created BankTransaction objects
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
        
        transactions = []
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        rows = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    # Read all rows into memory while file is open
                    rows = list(reader)
                    if rows:  # Successfully read at least one row
                        break
            except Exception as e:
                continue
        
        if rows is None or len(rows) == 0:
            raise ValueError("Could not read CSV file with any encoding or file is empty")
        
        for row in rows:
            # Try to detect format and extract data
            transaction = parse_transaction_row(row, company_id)
            if transaction:
                # Check for duplicates before adding
                # Match on: company, date, amount, type, and reference (if available)
                query = db.query(BankTransaction).filter(
                    BankTransaction.company_id == company_id,
                    BankTransaction.date == transaction.date,
                    BankTransaction.amount == transaction.amount,
                    BankTransaction.type == transaction.type
                )
                
                # If reference exists, also match on reference
                if transaction.reference:
                    query = query.filter(BankTransaction.reference == transaction.reference)
                else:
                    # If no reference, also match on description to avoid duplicates
                    if transaction.description:
                        query = query.filter(BankTransaction.description == transaction.description)
                
                existing = query.first()
                
                if not existing:
                    db.add(transaction)
                    transactions.append(transaction)
                # else: skip duplicate (silently)
        
        db.commit()
        
        # Categorize transactions if requested
        if categorize and transactions:
            categorize_transactions(transactions, db)
        db.commit()
        
        # Refresh all transactions
        for txn in transactions:
            db.refresh(txn)
        
        return transactions
    finally:
        db.close()


def parse_transaction_row(row: Dict, company_id: int) -> BankTransaction:
    """Parse a single transaction row from CSV"""
    # Try different column name patterns
    date_str = None
    for col in ['Date', 'date', 'DATE', 'Transaction Date', 'Txn Date']:
        if col in row:
            date_str = row[col]
            break
    
    description = None
    for col in ['Description', 'description', 'DESCRIPTION', 'Narration', 'Particulars', 'Remarks']:
        if col in row:
            description = row[col]
            break
    
    reference = None
    for col in ['Reference', 'reference', 'REFERENCE', 'Ref No', 'Cheque No', 'UTR']:
        if col in row:
            reference = row[col]
            break
    
    # Parse date
    try:
        # Try common date formats
        for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%b-%Y']:
            try:
                date = datetime.strptime(date_str.strip(), fmt)
                break
            except:
                continue
        else:
            return None  # Could not parse date
    except:
        return None
    
    # Determine amount and type
    amount = 0.0
    txn_type = None
    
    # Check for separate Debit/Credit columns
    if 'Debit' in row or 'debit' in row or 'Withdrawal' in row:
        debit_col = next((c for c in ['Debit', 'debit', 'Withdrawal'] if c in row), None)
        debit_val = row[debit_col].replace(',', '').strip()
        if debit_val and float(debit_val) > 0:
            amount = float(debit_val)
            txn_type = TransactionType.DEBIT
    
    if 'Credit' in row or 'credit' in row or 'Deposit' in row:
        credit_col = next((c for c in ['Credit', 'credit', 'Deposit'] if c in row), None)
        credit_val = row[credit_col].replace(',', '').strip()
        if credit_val and float(credit_val) > 0:
            amount = float(credit_val)
            txn_type = TransactionType.CREDIT
    
    # Check for single Amount column with Type
    if not txn_type and 'Amount' in row:
        amount_val = row['Amount'].replace(',', '').strip()
        if amount_val:
            amount = abs(float(amount_val))
            # Check Type column
            if 'Type' in row:
                type_str = row['Type'].upper()
                if 'DR' in type_str or 'DEBIT' in type_str:
                    txn_type = TransactionType.DEBIT
                elif 'CR' in type_str or 'CREDIT' in type_str:
                    txn_type = TransactionType.CREDIT
            else:
                # Default: positive is credit, negative is debit
                txn_type = TransactionType.CREDIT if float(amount_val) > 0 else TransactionType.DEBIT
    
    if not txn_type or amount == 0:
        return None
    
    return BankTransaction(
        company_id=company_id,
        date=date,
        amount=amount,
        description=description,
        reference=reference,
        type=txn_type,
        status="unmatched",
        category=None  # Will be set during categorization
    )


def parse_bank_statement_pdf_with_categorization(file_path: str, company_id: int = None, categorize: bool = True) -> List[BankTransaction]:
    """
    Parse PDF bank statement and create bank transactions with categorization
    
    Args:
        file_path: Path to PDF file
        company_id: Company ID to associate transactions with
        categorize: If True, use AI to categorize transactions
    
    Returns:
        List of created BankTransaction objects
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
        
        # Parse PDF
        try:
            pdf_transactions = parse_bank_statement_pdf(file_path)
            logger.info(f"PDF parser extracted {len(pdf_transactions)} transactions")
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}", exc_info=True)
            raise ValueError(f"Failed to parse PDF bank statement: {str(e)}")
        
        if not pdf_transactions:
            raise ValueError("No transactions found in PDF. Please ensure the PDF contains a transaction table with Date, Narration, and Amount columns.")
        
        # Convert to BankTransaction objects
        bank_transactions = []
        for pdf_txn in pdf_transactions:
            # Determine amount and type
            amount = 0.0
            txn_type = None
            
            if pdf_txn.get("debit_amount"):
                amount = pdf_txn["debit_amount"]
                txn_type = TransactionType.DEBIT
            elif pdf_txn.get("credit_amount"):
                amount = pdf_txn["credit_amount"]
                txn_type = TransactionType.CREDIT
            
            if not txn_type or amount == 0:
                continue
            
            # Check for duplicates
            query = db.query(BankTransaction).filter(
                BankTransaction.company_id == company_id,
                BankTransaction.date == pdf_txn["date"],
                BankTransaction.amount == amount,
                BankTransaction.type == txn_type
            )
            
            if pdf_txn.get("reference"):
                query = query.filter(BankTransaction.reference == pdf_txn["reference"])
            elif pdf_txn.get("description"):
                query = query.filter(BankTransaction.description == pdf_txn["description"])
            
            existing = query.first()
            
            if not existing:
                # Final cleanup of description before creating transaction
                description = pdf_txn.get("description") or ""
                original_description = description
                reference = pdf_txn.get("reference")
                
                if description:
                    import re
                    # Remove trailing comma
                    description = description.rstrip(',').strip()
                    # If comma exists, take only the part before comma
                    if ',' in description:
                        description = description.split(',')[0].strip()
                    # Remove any remaining references, dates, amounts by splitting into words
                    words = description.split()
                    clean_words = []
                    for word in words:
                        # Check if word is a UPI handle (alphanumeric@provider)
                        is_upi_handle = re.match(r'^[A-Z0-9]{6,}@[A-Z]{2,}$', word.upper())
                        # Stop at first UPI handle, reference, date, or amount
                        if (is_upi_handle or
                            re.match(r'^[A-Z]{2,}\d{10,}$', word.upper()) or 
                            re.match(r'^\d{10,}$', word) or
                            re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', word) or
                            re.match(r'^-?\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?$', word)):
                            break
                        clean_words.append(word)
                    if clean_words:
                        description = ' '.join(clean_words).strip()
                    else:
                        # If all words were filtered, use first part before comma
                        if ',' in original_description:
                            description = original_description.split(',')[0].strip()
                
                # Extract reference from original description if not already found
                if not reference and original_description:
                    import re
                    # Pattern 1: UPI handle (e.g., Q045503691@YBL, merchant@paytm, etc.)
                    # UPI handles: alphanumeric@provider (provider: YBL, PAYTM, OKAXIS, etc.)
                    upi_handle_pattern = r'([A-Z0-9]{6,}@[A-Z]{2,})'
                    upi_match = re.search(upi_handle_pattern, original_description, re.IGNORECASE)
                    if upi_match:
                        reference = upi_match.group(1).upper()
                    
                    # Pattern 2: Transaction type with IFSC code (e.g., RTGSDR-UTIB0000041, NEFTDR-SBIN0050165)
                    if not reference:
                        ifsc_pattern = r'(?:RTGS|NEFT|IMPS|FT)[A-Z]*-([A-Z]{4}0[A-Z0-9]{6})'
                        ifsc_match = re.search(ifsc_pattern, original_description, re.IGNORECASE)
                        if ifsc_match:
                            reference = ifsc_match.group(1)
                    
                    # Pattern 3: Transaction type with reference number (e.g., FT-DR-50100106476458)
                    if not reference:
                        txn_ref_pattern = r'(?:RTGS|NEFT|IMPS|FT)[A-Z]*-[A-Z]*-(\d{10,})'
                        txn_ref_match = re.search(txn_ref_pattern, original_description, re.IGNORECASE)
                        if txn_ref_match:
                            reference = txn_ref_match.group(1)
                    
                    # Pattern 4: UTR number (12-16 digits/alphanumeric, often prefixed with "UTR")
                    if not reference:
                        utr_pattern = r'UTR[:\s]*([A-Z0-9]{12,16})'
                        utr_match = re.search(utr_pattern, original_description, re.IGNORECASE)
                        if utr_match:
                            reference = utr_match.group(1)
                    
                    # Pattern 5: IFSC code standalone (11 characters)
                    if not reference:
                        standalone_ifsc = r'\b([A-Z]{4}0[A-Z0-9]{6})\b'
                        ifsc_match = re.search(standalone_ifsc, original_description)
                        if ifsc_match:
                            reference = ifsc_match.group(1)
                    
                    # Pattern 6: Transaction type with reference (e.g., RTGSDR-UTIB0000041, NEFTDR-SBIN0050165)
                    if not reference:
                        txn_with_ref = r'(?:RTGS|NEFT|IMPS|FT|CHQ)[A-Z]*(?:DR|CR|PAID)?[-]?([A-Z0-9]{8,})'
                        txn_match = re.search(txn_with_ref, original_description, re.IGNORECASE)
                        if txn_match:
                            ref_candidate = txn_match.group(1)
                            # Only use if it looks like a valid reference (not just transaction type)
                            if len(ref_candidate) >= 8 and not re.match(r'^(DR|CR|PAID)$', ref_candidate, re.IGNORECASE):
                                reference = ref_candidate
                    
                    # Pattern 7: Long alphanumeric strings (10+ characters) that look like references
                    if not reference:
                        long_ref_pattern = r'\b([A-Z]{2,}\d{10,}|\d{10,})\b'
                        long_ref_match = re.search(long_ref_pattern, original_description)
                        if long_ref_match:
                            reference = long_ref_match.group(1)
                
                transaction = BankTransaction(
                    company_id=company_id,
                    date=pdf_txn["date"],
                    amount=amount,
                    description=description,
                    reference=reference,
                    type=txn_type,
                    status="unmatched",
                    category=None
                )
                db.add(transaction)
                bank_transactions.append(transaction)
        
        db.commit()
        
        # Categorize transactions if requested
        if categorize and bank_transactions:
            categorize_transactions(bank_transactions, db)
            db.commit()
        
        # Refresh all transactions
        for txn in bank_transactions:
            db.refresh(txn)
        
        return bank_transactions
    finally:
        db.close()


def categorize_transactions(transactions: List[BankTransaction], db) -> None:
    """
    Categorize bank transactions using AI with rate limiting
    
    Args:
        transactions: List of BankTransaction objects
        db: Database session
    """
    import time
    from database.models import Reconciliation
    
    if not transactions:
        return
    
    logger.info(f"Categorizing {len(transactions)} transactions with rate limiting")
    
    # For large batches, use rule-based categorization to avoid rate limits
    # Only use AI for smaller batches or when explicitly needed
    MAX_AI_CATEGORIZATIONS = 50  # Limit AI categorizations per batch
    
    if len(transactions) > MAX_AI_CATEGORIZATIONS:
        logger.info(f"Large batch ({len(transactions)} transactions). Using rule-based categorization for all to avoid rate limits.")
        # Use rule-based for all transactions in large batches
        for transaction in transactions:
            txn_data = {
                "transaction_id": str(transaction.transaction_id),
                "date": transaction.date.strftime("%Y-%m-%d"),
                "amount": transaction.amount if transaction.type == TransactionType.CREDIT else -transaction.amount,
                "bank_description": transaction.description or "",
                "is_reconciled": False,
                "reconciled_invoice": None,
            }
            result = categorize_transaction_rule_based(txn_data)
            if result:
                transaction.category = result.get("category_code")
        logger.info(f"Rule-based categorization complete for {len(transactions)} transactions")
        return
    
    # Use batch processing to avoid rate limits
    # Prepare transaction data for batch categorization
    from core.transaction_categorizer import categorize_transactions_batch
    
    txn_data_list = []
    transaction_map = {}  # Map transaction_id to BankTransaction object
    
    for transaction in transactions:
        # Check if transaction is reconciled
        reconciliation = db.query(Reconciliation).filter(
            Reconciliation.transaction_id == transaction.transaction_id
        ).first()
        
        is_reconciled = reconciliation is not None
        reconciled_invoice = None
        
        if is_reconciled and reconciliation.invoice:
            invoice = reconciliation.invoice
            reconciled_invoice = {
                "invoice_number": invoice.invoice_number,
                "invoice_description": None,
                "customer_vendor_name": None,
                "line_items": None,
            }
            
            if invoice.vendor:
                reconciled_invoice["customer_vendor_name"] = invoice.vendor.name
            elif invoice.buyer:
                reconciled_invoice["customer_vendor_name"] = invoice.buyer.name
        
        txn_id_str = str(transaction.transaction_id)
        txn_data = {
            "transaction_id": txn_id_str,
            "date": transaction.date.strftime("%Y-%m-%d"),
            "amount": transaction.amount if transaction.type == TransactionType.CREDIT else -transaction.amount,
            "bank_description": transaction.description or "",
            "is_reconciled": is_reconciled,
            "reconciled_invoice": reconciled_invoice if is_reconciled else None,
        }
        
        txn_data_list.append(txn_data)
        transaction_map[txn_id_str] = transaction
    
    # Categorize in batches (10 transactions per API call to avoid rate limits)
    try:
        batch_results = categorize_transactions_batch(txn_data_list, batch_size=10)
        
        # Apply categories to transactions
        categorized_count = 0
        for result in batch_results:
            if result and not result.get("error"):
                txn_id = result.get("transaction_id")
                if txn_id in transaction_map:
                    transaction_map[txn_id].category = result.get("category_code")
                    categorized_count += 1
        
        logger.info(f"Successfully categorized {categorized_count}/{len(transactions)} transactions")
        
    except Exception as e:
        logger.error(f"Batch categorization failed: {e}", exc_info=True)
        # Fallback to rule-based for all
        logger.info("Falling back to rule-based categorization")
        for transaction in transactions:
            txn_data = {
                "transaction_id": str(transaction.transaction_id),
                "date": transaction.date.strftime("%Y-%m-%d"),
                "amount": transaction.amount if transaction.type == TransactionType.CREDIT else -transaction.amount,
                "bank_description": transaction.description or "",
                "is_reconciled": False,
                "reconciled_invoice": None,
            }
            result = categorize_transaction_rule_based(txn_data)
            if result:
                transaction.category = result.get("category_code")


"""
Bank Statement Parser
Parses CSV bank statements and extracts transactions
"""
import csv
from datetime import datetime
from typing import List, Dict
from database.models import BankTransaction, TransactionType
from database.db import get_db
from core.company_manager import CompanyManager


def parse_bank_statement_csv(file_path: str, company_id: int = None) -> List[BankTransaction]:
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
        status="unmatched"
    )


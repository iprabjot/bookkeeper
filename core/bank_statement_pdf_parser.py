"""
PDF Bank Statement Parser
Extracts transactions from PDF bank statements using pdfplumber
Supports HDFC, ICICI, SBI, and other Indian bank formats
"""
import pdfplumber
import re
from datetime import datetime
from typing import List, Dict, Optional, Any


def parse_bank_statement_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Parse PDF bank statement and extract transactions
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        List of transaction dicts with:
        - date (datetime)
        - description (str)
        - reference (str or None)
        - debit_amount (float or None)
        - credit_amount (float or None)
        - balance (float or None)
    """
    import logging
    logger = logging.getLogger(__name__)
    transactions = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"Opened PDF with {len(pdf.pages)} pages")
            
            for page_num, page in enumerate(pdf.pages):
                logger.debug(f"Processing page {page_num + 1}")
                
                # Try to extract tables first (most reliable)
                # Use table_settings to improve extraction
                table_settings = {
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict",
                    "explicit_vertical_lines": [],
                    "explicit_horizontal_lines": [],
                    "snap_tolerance": 3,
                    "join_tolerance": 3,
                    "min_words_vertical": 1,
                    "min_words_horizontal": 1,
                }
                
                tables = page.extract_tables(table_settings)
                logger.debug(f"Found {len(tables)} tables on page {page_num + 1}")
                
                if tables:
                    for table_idx, table in enumerate(tables):
                        logger.debug(f"Processing table {table_idx + 1} with {len(table)} rows")
                        page_transactions = parse_transaction_table(table, page_num)
                        logger.debug(f"Extracted {len(page_transactions)} transactions from table {table_idx + 1}")
                        transactions.extend(page_transactions)
                
                # If no tables found or no transactions extracted, try text extraction
                if not tables or len(transactions) == 0:
                    logger.debug("No tables found or empty, trying text extraction")
                    text = page.extract_text()
                    if text:
                        logger.debug(f"Extracted {len(text)} characters of text")
                        page_transactions = parse_transaction_text(text, page_num)
                        logger.debug(f"Extracted {len(page_transactions)} transactions from text")
                        transactions.extend(page_transactions)
    
    except Exception as e:
        logger.error(f"Error parsing PDF with pdfplumber: {e}", exc_info=True)
        # Fallback to text extraction if pdfplumber fails
        try:
            from utils.invoice_extractor import extract_text_from_pdf
            text = extract_text_from_pdf(pdf_path, use_ocr=False)
            if text:
                logger.info("Using fallback text extraction")
                transactions = parse_transaction_text(text, 0)
            else:
                raise ValueError(f"Could not extract text from PDF: {e}")
        except ImportError:
            raise ValueError(f"Could not parse PDF: {e}")
    
    logger.info(f"Total transactions extracted: {len(transactions)}")
    return transactions


def parse_transaction_table(table: List[List], page_num: int = 0) -> List[Dict]:
    """
    Parse transaction data from a table structure
    
    Common table formats:
    - HDFC: Date | Narration | Chq/Ref | Value Dt | Withdrawal | Deposit | Balance
    - ICICI: Date | Description | Amount | Type | Balance
    - SBI: Date | Description | Withdrawal | Deposit | Balance
    """
    import logging
    logger = logging.getLogger(__name__)
    transactions = []
    
    if not table or len(table) < 2:
        logger.debug("Table is empty or has less than 2 rows")
        return transactions
    
    # Find header row - try multiple strategies
    header_row_idx = None
    
    # Strategy 1: Look for common header keywords
    for i, row in enumerate(table):
        if row and any(col and isinstance(col, str) for col in row):
            row_text = " ".join(str(col or "") for col in row).upper()
            if any(keyword in row_text for keyword in ["DATE", "NARRATION", "DESCRIPTION", "WITHDRAWAL", "DEPOSIT", "DEBIT", "CREDIT", "CHQ", "REF"]):
                header_row_idx = i
                logger.debug(f"Found header at row {i}: {row_text[:100]}")
                break
    
    # Strategy 2: If no header found, assume first row is header
    if header_row_idx is None:
        logger.debug("No header found with keywords, assuming first row is header")
        header_row_idx = 0
    
    if header_row_idx is None or header_row_idx >= len(table):
        logger.debug("Invalid header row index")
        return transactions
    
    headers = [str(col or "").strip().upper() if col else "" for col in table[header_row_idx]]
    
    # Find column indices - HDFC specific: Date | Narration | Chq./Ref.No. | Value Dt | Withdrawal Amt. | Deposit Amt. | Closing Balance
    date_col = find_column_index(headers, ["DATE", "TXN DATE", "VALUE DATE", "VALUE DT"])
    desc_col = find_column_index(headers, ["NARRATION", "DESCRIPTION", "PARTICULARS", "REMARKS"])
    ref_col = find_column_index(headers, ["REF", "REFERENCE", "CHQ", "CHEQUE", "UTR", "NEFT REF", "CHQ./REF", "CHQ/REF"])
    debit_col = find_column_index(headers, ["WITHDRAWAL", "DEBIT", "DR", "PAYMENT", "WITHDRAWAL AMT", "WITHDRAWAL AMT."])
    credit_col = find_column_index(headers, ["DEPOSIT", "CREDIT", "CR", "RECEIPT", "DEPOSIT AMT", "DEPOSIT AMT."])
    amount_col = find_column_index(headers, ["AMOUNT"])
    type_col = find_column_index(headers, ["TYPE", "DR/CR"])
    balance_col = find_column_index(headers, ["BALANCE", "CLOSING BALANCE", "CLOSING BAL"])
    
    logger.debug(f"Column indices - Date: {date_col}, Desc: {desc_col}, Ref: {ref_col}, Debit: {debit_col}, Credit: {credit_col}, Balance: {balance_col}")
    logger.debug(f"Headers: {headers}")
    
    # Parse data rows
    for row_idx in range(header_row_idx + 1, len(table)):
        row = table[row_idx]
        if not row or len(row) == 0:
            continue
        
        # Debug: log raw row data for first few rows
        if row_idx <= header_row_idx + 3:
            logger.debug(f"Row {row_idx} raw data: {[str(c)[:50] if c else '' for c in row]}")
        
        # Skip rows that are clearly not transactions (e.g., summary rows, empty rows)
        row_text = " ".join(str(col or "") for col in row).upper()
        if any(skip_word in row_text for skip_word in ["STATEMENT SUMMARY", "OPENING BALANCE", "CLOSING BALANCE", "DR COUNT", "CR COUNT", "GENERATED ON"]):
            continue
        
        # Extract date
        date_str = None
        if date_col is not None and date_col < len(row):
            date_str = str(row[date_col] or "").strip()
        
        # If no date in expected column, try first column (common in HDFC)
        if not date_str and len(row) > 0:
            first_col = str(row[0] or "").strip()
            # Check if first column looks like a date (DD/MM/YY or DD-MM-YY)
            if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', first_col):
                date_str = first_col
                date_col = 0  # Update date_col for this row
        
        if not date_str:
            continue
        
        # Parse date
        try:
            date = parse_date(date_str)
            if not date:
                logger.debug(f"Could not parse date: {date_str}")
                continue
        except Exception as e:
            logger.debug(f"Date parsing error for '{date_str}': {e}")
            continue
        
        # Extract description - clean it up to remove amounts, dates, and reference numbers
        description = None
        potential_refs = []  # Store potential reference numbers found in description
        
        if desc_col is not None and desc_col < len(row):
            description = str(row[desc_col] or "").strip()
            original_description = description  # Keep for debugging
            
            # Clean description: remove amounts, dates, and reference strings
            if description:
                # SIMPLE APPROACH: Extract description by taking words until we hit a reference/date/amount
                # This handles: "RTGSDR-UTIB0000041-MANGLASONS-NETBANK, HDFCR52025022493383444 24/02/25 261,865.60"
                words = description.split()
                clean_words = []
                
                for word in words:
                    # Check if word is a UPI handle (alphanumeric@provider)
                    is_upi_handle = re.match(r'^[A-Z0-9]{6,}@[A-Z]{2,}$', word.upper())
                    # Check if word is a reference (alphanumeric like HDFCR52025022493383444 or pure numeric 10+ digits)
                    is_ref = (re.match(r'^[A-Z]{2,}\d{10,}$', word.upper()) or 
                             re.match(r'^\d{10,}$', word))
                    # Check if word is a date
                    is_date = re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', word)
                    # Check if word is an amount (with or without negative sign, with commas)
                    is_amount = re.match(r'^-?\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?$', word)
                    
                    # Stop at first UPI handle, reference, date, or amount
                    if is_upi_handle or is_ref or is_date or is_amount:
                        break
                    
                    clean_words.append(word)
                
                if clean_words:
                    description = ' '.join(clean_words).strip()
                    # Extract potential references from original for later use
                    alphanumeric_ref_pattern = r'\b[A-Z]{2,}\d{10,}\b'
                    potential_refs.extend(re.findall(alphanumeric_ref_pattern, original_description, re.IGNORECASE))
                    numeric_ref_pattern = r'\b\d{10,}\b'
                    potential_refs.extend(re.findall(numeric_ref_pattern, original_description))
                    logger.debug(f"Cleaned description from '{original_description[:80]}' to '{description[:80]}'")
                else:
                    # Fallback: if no clean words, try first part before comma
                    if ',' in description:
                        first_part = description.split(',')[0].strip()
                        if first_part:
                            description = first_part
                            # Extract potential references from original for later use
                            alphanumeric_ref_pattern = r'\b[A-Z]{2,}\d{10,}\b'
                            potential_refs.extend(re.findall(alphanumeric_ref_pattern, original_description, re.IGNORECASE))
                            numeric_ref_pattern = r'\b\d{10,}\b'
                            potential_refs.extend(re.findall(numeric_ref_pattern, original_description))
                            logger.debug(f"Used first part before comma: '{description}'")
        
        # Extract reference
        reference = None
        if ref_col is not None and ref_col < len(row):
            reference = str(row[ref_col] or "").strip()
        
        # Extract reference from description if not found in ref column
        # Indian bank transaction patterns:
        # - RTGSDR-UTIB0000041 (RTGS Debit with IFSC code)
        # - NEFTDR-SBIN0050165 (NEFT Debit with IFSC code)
        # - CHQPAID (Cheque paid)
        # - FT-DR-50100106476458 (Fund Transfer Debit with reference)
        # - UPI-AGAMFILLINGSTATION-Q045503691@YBL (UPI with merchant and handle)
        # - UTR numbers (12-16 digits)
        # - IFSC codes (11 characters: 4 letters + 0 + 6 alphanumeric)
        if description and not reference:
            # Pattern 1: UPI handle (e.g., Q045503691@YBL, merchant@paytm, etc.)
            # UPI handles: alphanumeric@provider (provider: YBL, PAYTM, OKAXIS, etc.)
            upi_handle_pattern = r'([A-Z0-9]{6,}@[A-Z]{2,})'
            upi_match = re.search(upi_handle_pattern, description, re.IGNORECASE)
            if upi_match:
                reference = upi_match.group(1).upper()
                logger.debug(f"Extracted UPI handle reference: {reference}")
            
            # Pattern 2: Transaction type with IFSC code (e.g., RTGSDR-UTIB0000041, NEFTDR-SBIN0050165)
            if not reference:
                ifsc_pattern = r'(?:RTGS|NEFT|IMPS|FT)[A-Z]*-([A-Z]{4}0[A-Z0-9]{6})'
                ifsc_match = re.search(ifsc_pattern, description, re.IGNORECASE)
                if ifsc_match:
                    reference = ifsc_match.group(1)  # Extract IFSC code
                    logger.debug(f"Extracted IFSC code reference: {reference}")
            
            # Pattern 3: Transaction type with reference number (e.g., FT-DR-50100106476458)
            if not reference:
                txn_ref_pattern = r'(?:RTGS|NEFT|IMPS|FT)[A-Z]*-[A-Z]*-(\d{10,})'
                txn_ref_match = re.search(txn_ref_pattern, description, re.IGNORECASE)
                if txn_ref_match:
                    reference = txn_ref_match.group(1)
                    logger.debug(f"Extracted transaction reference: {reference}")
            
            # Pattern 4: UTR number (12-16 digits/alphanumeric, often prefixed with "UTR")
            if not reference:
                utr_pattern = r'UTR[:\s]*([A-Z0-9]{12,16})'
                utr_match = re.search(utr_pattern, description, re.IGNORECASE)
                if utr_match:
                    reference = utr_match.group(1)
                    logger.debug(f"Extracted UTR reference: {reference}")
            
            # Pattern 5: IFSC code standalone (11 characters: 4 letters + 0 + 6 alphanumeric)
            if not reference:
                standalone_ifsc = r'\b([A-Z]{4}0[A-Z0-9]{6})\b'
                ifsc_match = re.search(standalone_ifsc, description)
                if ifsc_match:
                    reference = ifsc_match.group(1)
                    logger.debug(f"Extracted standalone IFSC code: {reference}")
            
            # Pattern 6: Long numeric/alphanumeric strings (10+ digits) - fallback
            if not reference and potential_refs:
                # Use the longest numeric string as the reference
                longest_ref = max(potential_refs, key=len) if potential_refs else None
                if longest_ref and len(longest_ref) >= 10:
                    reference = longest_ref
                    logger.debug(f"Extracted numeric reference: {reference}")
            
            # Pattern 7: Transaction type codes (e.g., CHQPAID, RTGSDR, NEFTDR)
            # Extract the full transaction type code as reference if no other reference found
            if not reference:
                txn_type_pattern = r'\b(?:RTGS|NEFT|IMPS|FT|CHQ|POS|ATM|ECS|ACH|TDS)[A-Z]*(?:DR|CR|PAID)?\b'
                txn_type_match = re.search(txn_type_pattern, description, re.IGNORECASE)
                if txn_type_match:
                    # Try to extract reference number after the transaction type
                    txn_code = txn_type_match.group(0)
                    # Look for reference after transaction code (e.g., "RTGSDR-UTIB0000041")
                    after_txn = description[description.upper().find(txn_code.upper()) + len(txn_code):].strip()
                    if after_txn:
                        # Extract first alphanumeric sequence after transaction code
                        ref_after = re.search(r'[-]?([A-Z0-9]{8,})', after_txn, re.IGNORECASE)
                        if ref_after:
                            reference = ref_after.group(1)
                            logger.debug(f"Extracted reference after transaction type: {reference}")
                        else:
                            # Use transaction type code itself as reference
                            reference = txn_code
                            logger.debug(f"Using transaction type as reference: {reference}")
        
        # Extract amounts
        debit_amount = None
        credit_amount = None
        
        if debit_col is not None and debit_col < len(row):
            debit_val = str(row[debit_col] or "").strip().replace(",", "").replace(" ", "")
            if debit_val and debit_val not in ["-", "", "0", "0.00"]:
                try:
                    debit_amount = float(debit_val)
                except:
                    pass
        
        if credit_col is not None and credit_col < len(row):
            credit_val = str(row[credit_col] or "").strip().replace(",", "").replace(" ", "")
            if credit_val and credit_val not in ["-", "", "0", "0.00"]:
                try:
                    credit_amount = float(credit_val)
                except:
                    pass
        
        # Skip if no amounts found (likely not a transaction row)
        if not debit_amount and not credit_amount:
            logger.debug(f"Skipping row {row_idx} - no amounts found")
            continue
        
        # If single amount column, check type column
        if amount_col is not None and amount_col < len(row) and not debit_amount and not credit_amount:
            amount_val = str(row[amount_col] or "").strip().replace(",", "")
            if amount_val:
                try:
                    amount = float(amount_val)
                    if type_col is not None and type_col < len(row):
                        type_str = str(row[type_col] or "").upper()
                        if "DR" in type_str or "DEBIT" in type_str:
                            debit_amount = abs(amount)
                        elif "CR" in type_str or "CREDIT" in type_str:
                            credit_amount = abs(amount)
                    else:
                        # Default: positive is credit, negative is debit
                        if amount > 0:
                            credit_amount = amount
                        else:
                            debit_amount = abs(amount)
                except:
                    pass
        
        # Extract balance
        balance = None
        if balance_col is not None and balance_col < len(row):
            balance_val = str(row[balance_col] or "").strip().replace(",", "")
            if balance_val:
                try:
                    balance = float(balance_val)
                except:
                    pass
        
        # Final cleanup of description before adding transaction
        if description:
            # Remove trailing comma if present
            description = description.rstrip(',').strip()
            # One more pass to remove any remaining unwanted patterns
            # Remove anything after comma if comma exists
            if ',' in description:
                description = description.split(',')[0].strip()
            # Remove any remaining references, dates, amounts
            words = description.split()
            final_words = []
            for word in words:
                # Stop at first reference, date, or amount
                if (re.match(r'^[A-Z]{2,}\d{10,}$', word.upper()) or 
                    re.match(r'^\d{10,}$', word) or
                    re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', word) or
                    re.match(r'^-?\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?$', word)):
                    break
                final_words.append(word)
            if final_words:
                description = ' '.join(final_words).strip()
        
        # Only add if we have at least amount or description
        if debit_amount or credit_amount or description:
            transactions.append({
                "date": date,
                "description": description or "",
                "reference": reference,
                "debit_amount": debit_amount,
                "credit_amount": credit_amount,
                "balance": balance,
            })
    
    return transactions


def parse_transaction_text(text: str, page_num: int = 0) -> List[Dict]:
    """
    Parse transactions from plain text (fallback when tables not available)
    Handles HDFC format: Date | Narration | Ref | Value Dt | Withdrawal | Deposit | Balance
    """
    import logging
    logger = logging.getLogger(__name__)
    transactions = []
    
    # Look for transaction patterns in text
    lines = text.split("\n")
    
    # Find transaction section (usually after "Statement From" or table headers)
    start_idx = 0
    in_transaction_section = False
    
    for i, line in enumerate(lines):
        line_upper = line.upper()
        # Look for header row
        if any(keyword in line_upper for keyword in ["DATE", "NARRATION", "WITHDRAWAL", "DEPOSIT"]):
            start_idx = i + 1
            in_transaction_section = True
            logger.debug(f"Found transaction section starting at line {i}")
            break
        # Or look for "Statement From" which usually precedes transactions
        elif "STATEMENT FROM" in line_upper:
            start_idx = i + 5  # Skip a few lines after "Statement From"
            in_transaction_section = True
    
    if not in_transaction_section:
        logger.debug("Could not find transaction section in text")
        # Try to find any line with date pattern
        start_idx = 0
    
    # Parse lines that look like transactions
    # HDFC format: DD/MM/YY | Narration text | Ref | DD/MM/YY | Amount | Amount | Balance
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        if not line or len(line) < 10:
            continue
        
        # Skip summary/section headers
        if any(skip in line.upper() for skip in ["STATEMENT SUMMARY", "OPENING BALANCE", "CLOSING BALANCE", "GENERATED ON", "HDFC BANK"]):
            continue
        
        # Try to extract date from beginning of line (HDFC format: DD/MM/YY at start)
        date_match = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', line)
        if date_match:
            try:
                day, month, year = date_match.groups()
                if len(year) == 2:
                    year = "20" + year
                date = datetime(int(year), int(month), int(day))
                
                # Remove date from line
                remaining = line[date_match.end():].strip()
                
                # Try to find amounts in the line (HDFC has Withdrawal and Deposit columns)
                # Look for patterns like: "9,902.00" or "342,892.60"
                amount_pattern = r'([\d,]+\.\d{2})'
                amounts = re.findall(amount_pattern, remaining)
                
                debit_amount = None
                credit_amount = None
                reference = None
                description = ""
                
                # HDFC format typically has: Date | Narration | Ref | Value Dt | Withdrawal | Deposit | Balance
                # Try to split by common delimiters or extract fields
                parts = re.split(r'\s{2,}|\t', remaining)  # Split on multiple spaces or tabs
                
                if len(parts) >= 1:
                    # First part after date is usually narration/description
                    description = parts[0].strip()
                
                if len(parts) >= 2:
                    # Second part might be reference
                    ref_candidate = parts[1].strip()
                    if re.match(r'^[A-Z0-9]+$', ref_candidate) and len(ref_candidate) > 5:
                        reference = ref_candidate
                        if len(parts) >= 3:
                            description = parts[2].strip() if parts[2].strip() else description
                
                # Find amounts - look for numbers with commas and 2 decimal places
                # Usually withdrawal and deposit are in separate columns
                amount_values = []
                for amt_str in amounts:
                    try:
                        amt_val = float(amt_str.replace(",", ""))
                        if amt_val > 0:
                            amount_values.append(amt_val)
                    except:
                        pass
                
                # In HDFC format, if there are 2 amounts, first might be withdrawal (debit), second deposit (credit)
                # If there are 3 amounts, last is usually balance
                if len(amount_values) >= 2:
                    # Assume first is withdrawal (debit), second is deposit (credit)
                    debit_amount = amount_values[0] if amount_values[0] > 0 else None
                    credit_amount = amount_values[1] if amount_values[1] > 0 else None
                elif len(amount_values) == 1:
                    # Single amount - need to determine if debit or credit
                    # Check if line contains "DR" (debit) or "CR" (credit)
                    if " DR " in remaining.upper() or "DEBIT" in remaining.upper():
                        debit_amount = amount_values[0]
                    elif " CR " in remaining.upper() or "CREDIT" in remaining.upper():
                        credit_amount = amount_values[0]
                    else:
                        # Default: if description suggests payment, it's debit
                        if any(word in remaining.upper() for word in ["PAYMENT", "DR-", "NEFT DR", "RTGS DR"]):
                            debit_amount = amount_values[0]
                        else:
                            credit_amount = amount_values[0]
                
                # Only add if we have at least an amount
                if debit_amount or credit_amount:
                    transactions.append({
                        "date": date,
                        "description": description or remaining[:100],  # Use first 100 chars if no description extracted
                        "reference": reference,
                        "debit_amount": debit_amount,
                        "credit_amount": credit_amount,
                        "balance": None,
                    })
                    logger.debug(f"Extracted transaction: {date.strftime('%d/%m/%Y')} - {description[:50]} - Debit: {debit_amount}, Credit: {credit_amount}")
            except Exception as e:
                logger.debug(f"Error parsing line {i}: {e}")
                continue
    
    logger.info(f"Extracted {len(transactions)} transactions from text")
    return transactions


def find_column_index(headers: List[str], keywords: List[str]) -> Optional[int]:
    """Find column index by matching keywords in headers"""
    for i, header in enumerate(headers):
        if any(keyword in header for keyword in keywords):
            return i
    return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date from various formats"""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Common formats (HDFC uses DD/MM/YY)
    formats = [
        "%d/%m/%y",  # HDFC format: 02/04/24
        "%d-%m-%y",  # Alternative: 02-04-24
        "%d/%m/%Y",  # Full year: 02/04/2024
        "%d-%m-%Y",  # Full year: 02-04-2024
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d %b %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    
    # Try regex patterns
    match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', date_str)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = "20" + year
        try:
            return datetime(int(year), int(month), int(day))
        except:
            pass
    
    return None


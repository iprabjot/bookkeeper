"""
Invoice Extractor
Extracts structured data from PDF invoices using pdfplumber.
Handles Indian invoice formats including GST invoices, e-invoices, and tax invoices.
"""
import pdfplumber
import re
import json
from datetime import datetime
from pathlib import Path


def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return None
    return text


def parse_invoice_number(text):
    """Extract invoice number from text."""
    # Look for patterns like "Invoice 241389" or "INV-241389"
    patterns = [
        r'Invoice\s+(\d+)',
        r'INV[-\s]?(\d+)',
        r'Invoice\s+No[.:]?\s*(\d+)',
        r'#\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def parse_date(text):
    """Extract invoice date from text."""
    # Look for date patterns like "31-01-2025" or "31/01/2025"
    date_patterns = [
        r'(\d{2})[-/](\d{2})[-/](\d{4})',
        r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})',
    ]
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Try to find the most likely date (usually near "Date" or invoice number)
            for match in matches:
                try:
                    day, month, year = match
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                except:
                    continue
    return None


def parse_amounts(text):
    """Extract amounts from invoice text."""
    # Look for total amount patterns - be more specific
    patterns = [
        r'Total\s+₹\s*([\d,]+\.?\d*)',
        r'Invoice\s+Amount[:\s]+₹?\s*([\d,]+\.?\d*)',
        r'Amounts?\s+Sub\s+Total[:\s]+₹?\s*([\d,]+\.?\d*)',
        r'Total[:\s]+₹\s*([\d,]+\.?\d*)',
    ]
    
    amounts = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                amount = float(match.replace(',', ''))
                # Filter out unrealistic amounts (like HSN codes)
                if amount < 100000000:  # Less than 10 crore
                    amounts.append(amount)
            except:
                continue
    
    # Also look for amount in words pattern to find the total
    amount_words_pattern = r'(\w+\s+)*Lakh|(\w+\s+)*Thousand'
    if re.search(amount_words_pattern, text, re.IGNORECASE):
        # Find amounts near "Total" or "Amount"
        total_section = re.search(r'Total.*?₹\s*([\d,]+\.?\d*)', text, re.IGNORECASE | re.DOTALL)
        if total_section:
            try:
                amount = float(total_section.group(1).replace(',', ''))
                if amount < 100000000:
                    amounts.append(amount)
            except:
                pass
    
    # Return the largest reasonable amount as total
    if amounts:
        return max(amounts)
    return None


def parse_gst_details(text):
    """Extract GST information from invoice."""
    gst_info = {
        "gstin": None,
        "cgst": 0,
        "sgst": 0,
        "igst": 0,
        "taxable_amount": 0,
    }
    
    # Extract GSTIN
    gstin_pattern = r'GSTIN[:\s]+([A-Z0-9]{15})'
    gstin_match = re.search(gstin_pattern, text, re.IGNORECASE)
    if gstin_match:
        gst_info["gstin"] = gstin_match.group(1)
    
    # Extract IGST from table format (more reliable)
    # Look for IGST in a table row
    igst_table_pattern = r'IGST.*?(\d+)%.*?₹\s*([\d,]+\.?\d*)'
    igst_match = re.search(igst_table_pattern, text, re.IGNORECASE | re.DOTALL)
    if igst_match:
        gst_info["igst"] = float(igst_match.group(2).replace(',', ''))
    else:
        # Fallback to simpler pattern
        igst_patterns = [
            r'IGST[:\s]+₹?\s*([\d,]+\.?\d*)',
            r'IGST.*?Amount[:\s]+₹?\s*([\d,]+\.?\d*)',
        ]
        for pattern in igst_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                gst_info["igst"] = float(match.group(1).replace(',', ''))
                break
    
    # Extract CGST and SGST (for intra-state transactions)
    cgst_patterns = [
        r'CGST.*?(\d+)%.*?₹\s*([\d,]+\.?\d*)',
        r'CGST[:\s]+₹?\s*([\d,]+\.?\d*)',
    ]
    for pattern in cgst_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                gst_info["cgst"] = float(match.group(2).replace(',', ''))
            else:
                gst_info["cgst"] = float(match.group(1).replace(',', ''))
            break
    
    sgst_patterns = [
        r'SGST.*?(\d+)%.*?₹\s*([\d,]+\.?\d*)',
        r'SGST[:\s]+₹?\s*([\d,]+\.?\d*)',
    ]
    for pattern in sgst_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                gst_info["sgst"] = float(match.group(2).replace(',', ''))
            else:
                gst_info["sgst"] = float(match.group(1).replace(',', ''))
            break
    
    # Extract taxable amount from table
    taxable_patterns = [
        r'Taxable\s+amount[:\s]+₹?\s*([\d,]+\.?\d*)',
        r'HSN.*?Taxable\s+amount[:\s]+₹?\s*([\d,]+\.?\d*)',
    ]
    for pattern in taxable_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            gst_info["taxable_amount"] = float(match.group(1).replace(',', ''))
            break
    
    return gst_info


def parse_vendor_customer(text):
    """Extract vendor and customer information."""
    info = {
        "vendor_name": None,
        "vendor_gstin": None,
        "customer_name": None,
        "customer_gstin": None,
    }
    
    # Extract vendor name - look for company name at the start of document
    # Try multiple patterns
    vendor_patterns = [
        r'^([A-Z][A-Z\s&]+(?:CORP|PVT|LTD|ENTERPRISES|TRADERS|METAL|INDUSTRIES))',
        r'Tax\s+Invoice\s+([A-Z][A-Z\s&]+(?:CORP|PVT|LTD|ENTERPRISES|TRADERS|METAL|INDUSTRIES))',
    ]
    
    for pattern in vendor_patterns:
        vendor_match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if vendor_match:
            vendor_name = vendor_match.group(1).strip()
            # Clean up - remove extra spaces
            vendor_name = re.sub(r'\s+', ' ', vendor_name)
            # Remove common prefixes
            vendor_name = re.sub(r'^(TAX\s+INVOICE|INVOICE)\s+', '', vendor_name, flags=re.IGNORECASE)
            if len(vendor_name) > 3:  # Valid company name
                info["vendor_name"] = vendor_name
                break
    
    # If still not found, try to extract from first few lines
    if not info["vendor_name"]:
        lines = text.split('\n')[:5]
        for line in lines:
            line = line.strip()
            if line and len(line) > 5 and not line.startswith('Tax') and not line.startswith('Invoice'):
                # Check if it looks like a company name
                if any(word in line.upper() for word in ['CORP', 'PVT', 'LTD', 'ENTERPRISES', 'TRADERS', 'METAL']):
                    info["vendor_name"] = line
                    break
    
    # Extract customer name (usually after "Bill To")
    customer_match = re.search(r'Bill\s+To\s+([A-Z\s&]+(?:CORP|PVT|LTD|ENTERPRISES|TRADERS)?)', text, re.IGNORECASE | re.MULTILINE)
    if customer_match:
        customer_name = customer_match.group(1).strip()
        # Take first line (company name)
        customer_name = customer_name.split('\n')[0].strip()
        customer_name = re.sub(r'\s+', ' ', customer_name)
        if len(customer_name) > 3:
            info["customer_name"] = customer_name
    
    # Extract GSTINs - vendor GSTIN comes first, customer second
    gstin_pattern = r'GSTIN[:\s]+([A-Z0-9]{15})'
    gstin_matches = re.findall(gstin_pattern, text, re.IGNORECASE)
    if len(gstin_matches) >= 1:
        info["vendor_gstin"] = gstin_matches[0]
    if len(gstin_matches) >= 2:
        info["customer_gstin"] = gstin_matches[1]
    
    return info


def process_invoice_pdf(pdf_path):
    """Process a single PDF invoice and extract structured data."""
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return None
    
    invoice_data = {
        "invoice_number": parse_invoice_number(text),
        "invoice_date": parse_date(text),
        "total_amount": parse_amounts(text),
        "file_path": str(pdf_path),
    }
    
    # Parse GST details
    gst_info = parse_gst_details(text)
    invoice_data.update(gst_info)
    
    # Parse vendor/customer info
    vendor_customer = parse_vendor_customer(text)
    invoice_data.update(vendor_customer)
    
    # Calculate subtotal if not found
    if invoice_data["taxable_amount"] == 0 and invoice_data["total_amount"]:
        tax_amount = invoice_data.get("igst", 0) + invoice_data.get("cgst", 0) + invoice_data.get("sgst", 0)
        invoice_data["taxable_amount"] = invoice_data["total_amount"] - tax_amount
    
    # If invoice number not found, try to extract from filename
    if not invoice_data["invoice_number"]:
        filename = Path(pdf_path).stem
        # Extract number from filename like "Tax Invoice_241389_31_01_25"
        match = re.search(r'_(\d+)_', filename)
        if match:
            invoice_data["invoice_number"] = match.group(1)
    
    return invoice_data


def process_invoices_from_folder(folder_path):
    """Process all PDF invoices from a folder."""
    folder = Path(folder_path)
    pdf_files = list(folder.glob("*.pdf"))
    
    invoices = []
    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        invoice_data = process_invoice_pdf(pdf_file)
        if invoice_data:
            invoices.append(invoice_data)
        else:
            print(f"  Warning: Could not process {pdf_file.name}")
    
    return invoices


if __name__ == "__main__":
    # Test with sample invoice
    test_pdf = Path("data/Tax Invoice_241389_31_01_25.pdf")
    if test_pdf.exists():
        result = process_invoice_pdf(test_pdf)
        print(json.dumps(result, indent=2))


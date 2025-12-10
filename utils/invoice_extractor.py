"""
Invoice Extractor
Extracts structured data from PDF invoices using pdfplumber.
Handles Indian invoice formats including GST invoices, e-invoices, and tax invoices.
Supports OCR for image-based PDFs.
Supports AI-based extraction using LLM for better accuracy.
"""
import pdfplumber
import re
import json
import os
from datetime import datetime
from pathlib import Path

# Try to import OCR libraries (optional)
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Try to import LLM for AI-based extraction (optional)
AI_EXTRACTION_AVAILABLE = False
try:
    from dotenv import load_dotenv
    from crewai import LLM
    load_dotenv(".env")
    if os.getenv("OPENAI_API_KEY"):
        AI_EXTRACTION_AVAILABLE = True
except ImportError:
    pass


def extract_text_from_pdf(pdf_path, use_ocr=False):
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_path: Path to PDF file (local path or S3 URL)
        use_ocr: If True and text extraction fails, try OCR (requires pytesseract)
    
    Returns:
        Extracted text string, or None if extraction fails
    """
    # Handle S3 URLs - download temporarily if needed
    local_path = pdf_path
    temp_file = None
    
    if pdf_path.startswith("http"):
        # Download from S3 temporarily
        from core.storage import get_storage_service
        import tempfile
        
        storage = get_storage_service()
        if storage.enabled:
            # Extract object key from URL
            if "/" in pdf_path:
                parts = pdf_path.split("/")
                if storage.bucket_name in parts:
                    object_key = "/".join(parts[parts.index(storage.bucket_name) + 1:])
                else:
                    object_key = parts[-1]
            else:
                object_key = pdf_path.split("/")[-1]
            
            # Download to temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            local_path = temp_file.name
            temp_file.close()
            
            if not storage.download_file(object_key, local_path):
                return None
    
    text = ""
    try:
        with pdfplumber.open(local_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return None
    
    # If no text extracted and OCR is available, try OCR
    if not text.strip() and use_ocr and OCR_AVAILABLE:
        print(f"No text found in PDF, attempting OCR...")
        try:
            # Convert PDF pages to images
            images = convert_from_path(local_path, dpi=300)
            for img in images:
                ocr_text = pytesseract.image_to_string(img)
                text += ocr_text + "\n"
            print(f"OCR extracted {len(text)} characters")
        except Exception as e:
            error_msg = f"OCR failed: {e}"
            error_str = str(e).lower()
            
            if "poppler" in error_str or "unable to get page count" in error_str:
                error_msg += "\n\nNote: Poppler is required for PDF to image conversion. Install it:\n"
                error_msg += "  macOS: brew install poppler\n"
                error_msg += "  Ubuntu: sudo apt-get install poppler-utils\n"
                error_msg += "  Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases"
            elif "tesseract" in error_str or "not found" in error_str:
                error_msg += "\n\nNote: Tesseract OCR engine not found. Install it:\n"
                error_msg += "  macOS: brew install tesseract\n"
                error_msg += "  Ubuntu: sudo apt-get install tesseract-ocr\n"
                error_msg += "  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
            
            print(error_msg)
            return None
    
    finally:
        # Clean up temp file if we downloaded from S3
        if temp_file and os.path.exists(local_path):
            try:
                os.unlink(local_path)
            except:
                pass
    
    return text if text.strip() else None


def parse_invoice_number(text):
    """Extract invoice number from text."""
    # Look for patterns like "Invoice 241389" or "INV-241389"
    # Handle both same-line and next-line patterns
    patterns = [
        # Pattern 1: Invoice No. on same line as number
        r'Invoice\s+No[.:]\s*(\d+)',
        # Pattern 2: Invoice No. on one line, number on next line (with optional whitespace)
        r'Invoice\s+No[.:]\s*\n\s*(\d+)',
        # Pattern 3: Invoice No. followed by number within 50 chars (handles newlines)
        r'Invoice\s+No[.:].{0,50}?(\d{4,})',
        # Pattern 4: Simple "Invoice" followed by number
        r'Invoice\s+(\d+)',
        # Pattern 5: INV- prefix
        r'INV[-\s]?(\d+)',
        # Pattern 6: Hash prefix
        r'#\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            invoice_num = match.group(1)
            # Validate it's a reasonable invoice number (4-10 digits)
            if len(invoice_num) >= 4 and len(invoice_num) <= 10:
                return invoice_num
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
    """Extract vendor and customer information including addresses and contact details."""
    info = {
        "vendor_name": None,
        "vendor_gstin": None,
        "vendor_address": None,
        "vendor_contact": None,
        "customer_name": None,
        "customer_gstin": None,
        "customer_address": None,
        "customer_contact": None,
    }
    
    # Extract vendor name - look for company name at the start of document (header section)
    # Vendor is usually near "TAX INVOICE" or after PAN/GSTIN in header, BEFORE "buyer" section
    
    # Find where "buyer" section starts to limit vendor search to header
    buyer_section = re.search(r'(buyer|Bill\s+To|Billed\s+To)', text, re.IGNORECASE)
    header_text = text[:buyer_section.start()] if buyer_section else text[:500]
    
    # Pattern 1: After PAN (most reliable for vendor)
    vendor_patterns = [
        r'PAN\s*:\s*[A-Z0-9]+\s+([A-Z][A-Z\s\.\-&]+(?:UDYOG|ISPAT|CORP|PVT|LTD|ENTERPRISES|TRADERS|METAL|INDUSTRIES))',
        r'TAX\s+INVOICE.*?\n.*?([A-Z][A-Z\s\.\-&]+(?:UDYOG|ISPAT|CORP|PVT|LTD|ENTERPRISES|TRADERS|METAL|INDUSTRIES))',
    ]
    
    for pattern in vendor_patterns:
        vendor_match = re.search(pattern, header_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if vendor_match:
            vendor_name = vendor_match.group(1).strip()
            # Clean up - remove extra spaces and newlines
            vendor_name = re.sub(r'\s+', ' ', vendor_name)
            vendor_name = vendor_name.split('\n')[0].strip()
            # Remove common prefixes
            vendor_name = re.sub(r'^(TAX\s+INVOICE|INVOICE|ORIGINAL|FOR|RECIPIENT)\s+', '', vendor_name, flags=re.IGNORECASE)
            vendor_name = vendor_name.strip()
            if len(vendor_name) > 3:  # Valid company name
                info["vendor_name"] = vendor_name
                break
    
    # Pattern 2: If still not found, try to extract from header lines (before buyer section)
    if not info["vendor_name"]:
        lines = header_text.split('\n')[:10]
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:
                # Check if it looks like a company name (has company indicators or is substantial)
                if (any(word in line.upper() for word in ['UDYOG', 'ISPAT', 'CORP', 'PVT', 'LTD', 'ENTERPRISES', 'TRADERS', 'METAL', 'INDUSTRIES']) or
                    (line.isupper() and len(line.split()) >= 2 and len(line) > 8)):
                    # Skip if it's clearly not a company name
                    if not any(word in line.upper() for word in ['TAX', 'INVOICE', 'GSTIN', 'PAN', 'PHONE', 'EMAIL', 'ADDRESS', 'MSME', 'UDYAM']):
                        info["vendor_name"] = line
                        break
    
    # Extract customer name - try multiple patterns
    # Pattern 1: Look for company name after "buyer (Billed To)" - get the next substantial company name
    buyer_section_match = re.search(r'buyer\s*\([^)]+\)\s*:', text, re.IGNORECASE | re.MULTILINE)
    if buyer_section_match:
        # Get text after "buyer (Billed To):"
        text_after_buyer = text[buyer_section_match.end():]
        # Look for company name patterns in the next few lines
        company_pattern = r'\b([A-Z][A-Z\s\.\-&]{8,}(?:CORP|PVT|LTD|ENTERPRISES|TRADERS|METAL|UDYOG|ISPAT))\b'
        company_matches = re.findall(company_pattern, text_after_buyer[:500], re.IGNORECASE)
        if company_matches:
            # Take the first substantial match (longer than 10 chars, looks like a real company name)
            for match in company_matches:
                customer_name = match.strip()
                customer_name = re.sub(r'\s+', ' ', customer_name)
                # Filter out OCR noise (very short or contains numbers/random chars)
                if (len(customer_name) > 10 and 
                    customer_name != info.get("vendor_name", "") and
                    not re.search(r'^\d', customer_name) and
                    not re.search(r'[0-9]{4,}', customer_name)):  # No long number sequences
                    info["customer_name"] = customer_name
                    break
    
    # Pattern 2: "Bill To" or "Billed To" 
    if not info["customer_name"]:
        customer_patterns = [
            r'(?:Bill\s+To|Billed\s+To)\s*:?\s*([A-Z][A-Z\s\.\-&]{8,}(?:CORP|PVT|LTD|ENTERPRISES|TRADERS|METAL|UDYOG|ISPAT)?)',
        ]
        
        for pattern in customer_patterns:
            customer_match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if customer_match:
                customer_name = customer_match.group(1).strip()
                customer_name = customer_name.split('\n')[0].split(':')[0].strip()
                customer_name = re.sub(r'\s+', ' ', customer_name)
                # Remove OCR noise
                customer_name = re.sub(r'\s+(SEO|Es|Naeseests|Dota|s|36|32|2006|37|48|00|Acknowledgement|No\.).*$', '', customer_name, flags=re.IGNORECASE)
                customer_name = customer_name.strip()
                if len(customer_name) > 10 and customer_name != info.get("vendor_name", ""):
                    info["customer_name"] = customer_name
                    break
    
    # Pattern 2: "For [Company Name]" - usually at the bottom after total amount
    if not info["customer_name"]:
        # Look for "For" pattern, especially near the end of document
        for_patterns = [
            r'For\s+([A-Z][A-Z\s\.\-&]+(?:CORP|PVT|LTD|ENTERPRISES|TRADERS|METAL|UDYOG|ISPAT))',
            r'FOR\s+([A-Z][A-Z\s\.\-&]+(?:CORP|PVT|LTD|ENTERPRISES|TRADERS|METAL|UDYOG|ISPAT))',
        ]
        
        # Try from the end of text (where "For" usually appears)
        text_end = text[-500:] if len(text) > 500 else text
        
        for pattern in for_patterns:
            for_match = re.search(pattern, text_end, re.IGNORECASE | re.MULTILINE)
            if for_match:
                customer_name = for_match.group(1).strip()
                # Clean up - take first line, remove extra spaces
                customer_name = customer_name.split('\n')[0].strip()
                customer_name = re.sub(r'\s+', ' ', customer_name)
                # Make sure it's not the vendor name
                if len(customer_name) > 3 and customer_name != info.get("vendor_name", ""):
                    info["customer_name"] = customer_name
                    break
        
        # Also try searching entire text for "For" pattern
        if not info["customer_name"]:
            for pattern in for_patterns:
                for_match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if for_match:
                    customer_name = for_match.group(1).strip()
                    customer_name = customer_name.split('\n')[0].strip()
                    customer_name = re.sub(r'\s+', ' ', customer_name)
                    # Make sure it's not the vendor name
                    if len(customer_name) > 3 and customer_name != info.get("vendor_name", ""):
                        info["customer_name"] = customer_name
                        break
    
    # Pattern 3: Look for company names that appear multiple times (likely customer)
    if not info["customer_name"]:
        # Find all potential company names
        company_pattern = r'\b([A-Z][A-Z\s\.\-&]{5,}(?:CORP|PVT|LTD|ENTERPRISES|TRADERS|METAL|UDYOG|ISPAT))\b'
        companies = re.findall(company_pattern, text, re.IGNORECASE)
        # Count occurrences
        from collections import Counter
        company_counts = Counter([c.strip() for c in companies if len(c.strip()) > 5])
        # If there's a company that appears multiple times and isn't the vendor, it might be the customer
        if company_counts:
            most_common = company_counts.most_common(2)
            for company, count in most_common:
                if company != info.get("vendor_name", "") and count >= 2:
                    info["customer_name"] = company.strip()
                    break
    
    # Extract GSTINs - vendor GSTIN comes first, customer second
    gstin_pattern = r'GSTIN[:\s]+([A-Z0-9]{15})'
    gstin_matches = re.findall(gstin_pattern, text, re.IGNORECASE)
    if len(gstin_matches) >= 1:
        info["vendor_gstin"] = gstin_matches[0]
    if len(gstin_matches) >= 2:
        info["customer_gstin"] = gstin_matches[1]
    
    # Extract vendor address and contact
    if info["vendor_name"]:
        vendor_section = header_text
        # Look for address patterns after vendor name
        address_patterns = [
            r'(?:Address|ADDRESS)[:\s]*([^\n]{10,200})',
            r'(?:Add[:\s]*|Addr[:\s]*)([^\n]{10,200})',
        ]
        for pattern in address_patterns:
            addr_match = re.search(pattern, vendor_section, re.IGNORECASE)
            if addr_match:
                address = addr_match.group(1).strip()
                # Clean up address
                address = re.sub(r'\s+', ' ', address)
                address = address.split('\n')[0].strip()
                if len(address) > 10:
                    info["vendor_address"] = address
                    break
        
        # Extract contact info (phone, email)
        contact_patterns = [
            r'(?:Phone|Mobile|Mob|Tel)[:\s]*([+\d\s\-]{8,20})',
            r'(?:Email|E-mail|Mail)[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        ]
        contact_parts = []
        for pattern in contact_patterns:
            contact_match = re.search(pattern, vendor_section, re.IGNORECASE)
            if contact_match:
                contact_parts.append(contact_match.group(1).strip())
        if contact_parts:
            info["vendor_contact"] = ", ".join(contact_parts)
    
    # Extract customer address and contact
    if info["customer_name"]:
        # Find customer section (after "Bill To" or "Billed To")
        customer_section_start = re.search(r'(?:Bill\s+To|Billed\s+To|Buyer)', text, re.IGNORECASE)
        if customer_section_start:
            customer_section = text[customer_section_start.end():customer_section_start.end()+500]
            
            # Look for address patterns
            address_patterns = [
                r'(?:Address|ADDRESS)[:\s]*([^\n]{10,200})',
                r'(?:Add[:\s]*|Addr[:\s]*)([^\n]{10,200})',
            ]
            for pattern in address_patterns:
                addr_match = re.search(pattern, customer_section, re.IGNORECASE)
                if addr_match:
                    address = addr_match.group(1).strip()
                    address = re.sub(r'\s+', ' ', address)
                    address = address.split('\n')[0].strip()
                    if len(address) > 10:
                        info["customer_address"] = address
                        break
            
            # Extract contact info
            contact_patterns = [
                r'(?:Phone|Mobile|Mob|Tel)[:\s]*([+\d\s\-]{8,20})',
                r'(?:Email|E-mail|Mail)[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            ]
            contact_parts = []
            for pattern in contact_patterns:
                contact_match = re.search(pattern, customer_section, re.IGNORECASE)
                if contact_match:
                    contact_parts.append(contact_match.group(1).strip())
            if contact_parts:
                info["customer_contact"] = ", ".join(contact_parts)
    
    return info


def extract_with_ai(text: str) -> dict:
    """
    Use AI/LLM to extract structured invoice data from text.
    Falls back to None if AI extraction fails or is not available.
    """
    if not AI_EXTRACTION_AVAILABLE:
        return None
    
    try:
        llm = LLM(
            model=os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini"),
            base_url=os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.0
        )
        
        prompt = f"""Extract invoice information from the following invoice text and return ONLY valid JSON. 
Focus on Indian GST invoices. Extract all relevant fields accurately.

Invoice Text:
{text[:4000]}

Return a JSON object with these exact fields:
{{
    "invoice_number": "invoice number or null",
    "invoice_date": "date in YYYY-MM-DD format or null",
    "total_amount": number or null,
    "taxable_amount": number or null,
    "igst": number or null,
    "cgst": number or null,
    "sgst": number or null,
    "vendor_name": "company name issuing the invoice or null",
    "vendor_gstin": "15-character GSTIN or null",
    "vendor_address": "full address of vendor (street, city, state, pincode) or null",
    "vendor_contact": "contact details (phone, email) of vendor or null",
    "customer_name": "company name receiving the invoice (buyer/billed to) or null",
    "customer_gstin": "15-character GSTIN or null",
    "customer_address": "full address of customer (street, city, state, pincode) or null",
    "customer_contact": "contact details (phone, email) of customer or null"
}}

Rules:
- Extract invoice number from "Invoice No." or similar fields
- Extract date and convert to YYYY-MM-DD format
- Extract amounts as numbers (remove currency symbols, commas)
- Vendor is the company issuing the invoice (usually at top/header)
- Customer is the company receiving the invoice (usually "Bill To" or "Billed To" section)
- GSTINs are exactly 15 characters (alphanumeric)
- Extract full addresses including street, city, state, and pincode
- Extract contact information including phone numbers and email addresses
- Return null for missing fields, not empty strings
- Return ONLY the JSON object, no other text

JSON:"""

        response = llm.call(prompt)
        
        # Extract JSON from response (might have markdown code blocks)
        response_text = str(response)
        
        # Try to find JSON in the response
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            invoice_data = json.loads(json_str)
            
            # Validate and clean the data
            result = {
                "invoice_number": invoice_data.get("invoice_number") or None,
                "invoice_date": invoice_data.get("invoice_date") or None,
                "total_amount": float(invoice_data.get("total_amount", 0)) if invoice_data.get("total_amount") else None,
                "taxable_amount": float(invoice_data.get("taxable_amount", 0)) if invoice_data.get("taxable_amount") else None,
                "igst": float(invoice_data.get("igst", 0)) if invoice_data.get("igst") else None,
                "cgst": float(invoice_data.get("cgst", 0)) if invoice_data.get("cgst") else None,
                "sgst": float(invoice_data.get("sgst", 0)) if invoice_data.get("sgst") else None,
                "vendor_name": invoice_data.get("vendor_name") or None,
                "vendor_gstin": invoice_data.get("vendor_gstin") or None,
                "customer_name": invoice_data.get("customer_name") or None,
                "customer_gstin": invoice_data.get("customer_gstin") or None,
            }
            
            print(f"AI extraction successful")
            return result
        else:
            print("AI extraction: No valid JSON found in response")
            return None
            
    except Exception as e:
        print(f"AI extraction failed: {e}")
        return None


def process_invoice_pdf(pdf_path, use_ocr=False, use_ai=True):
    """
    Process a single PDF invoice and extract structured data.
    
    Args:
        pdf_path: Path to PDF file
        use_ocr: If True, use OCR for image-based PDFs (requires pytesseract)
    
    Returns:
        Dictionary with invoice data, or None if extraction fails
    """
    # First try without OCR
    text = extract_text_from_pdf(pdf_path, use_ocr=False)
    
    # If no text found and OCR is requested/available, try OCR
    if not text and (use_ocr or OCR_AVAILABLE):
        print("No text found in PDF, trying OCR...")
        text = extract_text_from_pdf(pdf_path, use_ocr=True)
    
    if not text:
        error_msg = "Could not extract text from PDF. "
        if not OCR_AVAILABLE:
            error_msg += "PDF appears to be image-based. Install OCR support: pip install pytesseract pdf2image"
        else:
            error_msg += "OCR also failed. Check error messages above for details."
            error_msg += "\nCommon issues:"
            error_msg += "\n  - Poppler not installed (needed for pdf2image): brew install poppler"
            error_msg += "\n  - Tesseract not installed (needed for OCR): brew install tesseract"
        print(error_msg)
        return None
    
    # Try AI-based extraction first if available and requested
    if use_ai and AI_EXTRACTION_AVAILABLE:
        print("Attempting AI-based extraction...")
        ai_result = extract_with_ai(text)
        if ai_result and (ai_result.get("invoice_number") or ai_result.get("total_amount") or ai_result.get("vendor_name")):
            # AI extraction successful, use it
            ai_result["file_path"] = str(pdf_path)
            print("Using AI-extracted data")
            return ai_result
        else:
            print("AI extraction incomplete, falling back to regex patterns...")
    
    # Fall back to regex-based extraction
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


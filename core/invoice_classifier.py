"""
Invoice Classifier
Determines if an invoice is a sales invoice or purchase invoice
based on letterhead and current company matching
"""
from typing import Dict, Any
from core.company_manager import CompanyManager


def classify_invoice(invoice_data: Dict, company_id: int = None) -> Dict[str, Any]:
    """
    Classify invoice as sales or purchase based on letterhead/company matching
    
    Args:
        invoice_data: Dictionary with vendor_name, vendor_gstin, customer_name, customer_gstin
        company_id: Company ID to compare against. If None, uses current company (fallback)
        
    Returns:
        Dictionary with type ('sales' or 'purchase') and confidence (0.0-1.0)
    """
    from database.models import Company
    from database.db import get_db
    
    db = next(get_db())
    try:
        if company_id is None:
            current_company = CompanyManager.get_current_company()
            if not current_company:
                raise ValueError("No current company set and no company_id provided")
            company_id = current_company.company_id
        
        current_company = db.query(Company).filter(Company.company_id == company_id).first()
        if not current_company:
            raise ValueError(f"Company with ID {company_id} not found")
    finally:
        db.close()
    
    # Handle None values - convert to empty string before calling string methods
    vendor_name = (invoice_data.get("vendor_name") or "").upper().strip()
    vendor_gstin = (invoice_data.get("vendor_gstin") or "").strip()
    customer_name = (invoice_data.get("customer_name") or "").upper().strip()
    customer_gstin = (invoice_data.get("customer_gstin") or "").strip()
    
    current_company_name = current_company.name.upper().strip()
    current_company_gstin = current_company.gstin.strip()
    
    confidence = 0.0
    invoice_type = None
    
    # Check GSTIN first (most reliable)
    if vendor_gstin and vendor_gstin == current_company_gstin:
        # Vendor GSTIN matches current company → Sales invoice
        invoice_type = "sales"
        confidence = 0.95
    elif customer_gstin and customer_gstin == current_company_gstin:
        # Customer GSTIN matches current company → Purchase invoice
        invoice_type = "purchase"
        confidence = 0.95
    elif vendor_name and current_company_name in vendor_name or vendor_name in current_company_name:
        # Vendor name matches current company → Sales invoice
        invoice_type = "sales"
        confidence = 0.80
    elif customer_name and current_company_name in customer_name or customer_name in current_company_name:
        # Customer name matches current company → Purchase invoice
        invoice_type = "purchase"
        confidence = 0.80
    elif vendor_name and vendor_name != current_company_name:
        # Vendor is different from current company → Purchase invoice
        invoice_type = "purchase"
        confidence = 0.70
    else:
        # Default to purchase if vendor is different
        invoice_type = "purchase"
        confidence = 0.60
    
    return {
        "type": invoice_type,
        "confidence": confidence
    }


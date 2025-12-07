"""
Invoice processing routes
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
from api.schemas import InvoiceResponse
from utils.invoice_extractor import process_invoice_pdf
from core.processing import process_invoice
from core.auth import get_current_user
from database.models import User
import tempfile
import os

router = APIRouter()


@router.post("/invoices", response_model=InvoiceResponse)
async def upload_invoice(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload and process an invoice PDF"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Extract invoice data (try AI first, then OCR if needed)
        invoice_data = process_invoice_pdf(tmp_path, use_ocr=True, use_ai=True)
        if not invoice_data:
            error_detail = (
                "Could not extract invoice data from PDF. "
                "The PDF appears to be image-based and text extraction failed. "
                "Check server logs for details.\n\n"
                "To enable OCR support, install:\n"
                "  macOS: brew install poppler tesseract\n"
                "  Ubuntu: sudo apt-get install poppler-utils tesseract-ocr\n"
                "Then restart the API server."
            )
            raise HTTPException(status_code=400, detail=error_detail)
        
        # Process invoice (create journal entry, etc.)
        invoice = process_invoice(invoice_data, tmp_path)
        
        return invoice
    except ValueError as e:
        # User errors (e.g., no current company)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log full error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Invoice processing error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process invoice. Please try again later or contact support."
        )
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(current_user: User = Depends(get_current_user)):
    """List all invoices for the authenticated user's company"""
    from database.models import Invoice
    from database.db import get_db
    
    db = next(get_db())
    try:
        invoices = db.query(Invoice).filter(
            Invoice.company_id == current_user.company_id
        ).order_by(Invoice.created_at.desc()).all()
        
        return invoices
    finally:
        db.close()


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: int, current_user: User = Depends(get_current_user)):
    """Get a specific invoice"""
    from database.models import Invoice
    from database.db import get_db
    
    db = next(get_db())
    try:
        invoice = db.query(Invoice).filter(
            Invoice.invoice_id == invoice_id,
            Invoice.company_id == current_user.company_id
        ).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    finally:
        db.close()


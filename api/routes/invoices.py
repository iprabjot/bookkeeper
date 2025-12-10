"""
Invoice processing routes
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from typing import List
from api.schemas import InvoiceResponse, BulkUploadResponse, FileUploadResponse
from utils.invoice_extractor import process_invoice_pdf
from core.processing import process_invoice
from core.file_processor import process_invoice_file
from core.storage import get_storage_service
from core.auth import get_current_user
from database.models import User, FileUpload, FileUploadStatus
from database.db import get_db
from sqlalchemy.orm import Session
import tempfile
import os
import uuid

router = APIRouter()


@router.post("/invoices", response_model=InvoiceResponse)
async def upload_invoice(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload and process an invoice PDF"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save uploaded file temporarily for processing
    import logging
    logger = logging.getLogger(__name__)
    
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
        
        # Save to persistent storage (S3 or local)
        storage = get_storage_service()
        object_key = storage.generate_object_key(
            file_type="invoice",
            company_id=current_user.company_id,
            filename=file.filename
        )
        persistent_path = storage.upload_file(
            tmp_path,
            object_key,
            content_type="application/pdf"
        )
        
        if not persistent_path:
            # Fallback to temp path if storage failed
            persistent_path = tmp_path
            logger.warning(f"Failed to save to persistent storage, using temp path: {tmp_path}")
        else:
            logger.info(f"Saved invoice to persistent storage: {persistent_path}")
        
        # Process invoice (create journal entry, etc.)
        invoice = process_invoice(invoice_data, persistent_path, company_id=current_user.company_id)
        
        return invoice
    except ValueError as e:
        # User errors (e.g., no current company)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log full error for debugging
        logger.error(f"Invoice processing error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process invoice. Please try again later or contact support."
        )
    finally:
        # Clean up temp file only if we successfully saved to persistent storage
        if 'persistent_path' in locals() and persistent_path != tmp_path:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                logger.debug(f"Cleaned up temp file after saving to persistent storage")


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


@router.get("/invoices/{invoice_id}/download")
async def download_invoice_pdf(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download invoice PDF file"""
    from database.models import Invoice
    from fastapi.responses import StreamingResponse
    from core.storage import get_storage_service
    
    invoice = db.query(Invoice).filter(
        Invoice.invoice_id == invoice_id,
        Invoice.company_id == current_user.company_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # If file is in S3, generate presigned URL or download
    if invoice.file_path.startswith("http"):
        storage = get_storage_service()
        if storage.enabled:
            # Extract object key from URL
            if "/" in invoice.file_path:
                parts = invoice.file_path.split("/")
                if storage.bucket_name in parts:
                    object_key = "/".join(parts[parts.index(storage.bucket_name) + 1:])
                else:
                    object_key = parts[-1]
            else:
                object_key = invoice.file_path.split("/")[-1]
            
            # Generate presigned URL for direct download
            presigned_url = storage.get_file_url(object_key, expires_in=3600)
            if presigned_url:
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=presigned_url)
            
            # Fallback: download and stream
            import tempfile
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            tmp_path = tmp_file.name
            tmp_file.close()
            
            if storage.download_file(object_key, tmp_path):
                def cleanup():
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                
                file_obj = open(tmp_path, 'rb')
                return StreamingResponse(
                    file_obj,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"'
                    }
                )
    
    # Local file
    if os.path.exists(invoice.file_path):
        def file_generator():
            with open(invoice.file_path, 'rb') as f:
                yield from f
        
        return StreamingResponse(
            file_generator(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"'
            }
        )
    
    raise HTTPException(status_code=404, detail="Invoice PDF file not found")


@router.post("/invoices/upload-multiple", response_model=BulkUploadResponse)
async def upload_multiple_invoices(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload multiple invoice PDFs for async processing
    Files are stored temporarily and processed in background
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(tempfile.gettempdir(), "bookkeeper_uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    upload_ids = []
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            continue  # Skip non-PDF files
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save file temporarily
        try:
            content = await file.read()
            with open(file_path, 'wb') as f:
                f.write(content)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save file {file.filename}: {e}", exc_info=True)
            continue
        
        # Create FileUpload record
        upload = FileUpload(
            company_id=current_user.company_id,
            user_id=current_user.user_id,
            filename=file.filename,
            file_path=file_path,
            file_type='invoice',
            status=FileUploadStatus.PENDING
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)
        
        upload_ids.append(upload.upload_id)
        
        # Schedule background processing
        def process_background(upload_id: int):
            """Background task wrapper"""
            db_session = next(get_db())
            try:
                process_invoice_file(upload_id, db_session)
            finally:
                db_session.close()
        
        background_tasks.add_task(process_background, upload.upload_id)
    
    if not upload_ids:
        raise HTTPException(status_code=400, detail="No valid PDF files provided")
    
    return BulkUploadResponse(
        upload_ids=upload_ids,
        message=f"Uploaded {len(upload_ids)} file(s). Processing in background."
    )


@router.get("/invoices/uploads", response_model=List[FileUploadResponse])
async def list_uploads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all file uploads for the current user's company"""
    uploads = db.query(FileUpload).filter(
        FileUpload.company_id == current_user.company_id
    ).order_by(FileUpload.created_at.desc()).limit(100).all()
    
    return uploads


@router.get("/invoices/uploads/{upload_id}", response_model=FileUploadResponse)
async def get_upload_status(
    upload_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get status of a specific file upload"""
    upload = db.query(FileUpload).filter(
        FileUpload.upload_id == upload_id,
        FileUpload.company_id == current_user.company_id
    ).first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    return upload


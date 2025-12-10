"""
Background file processing for invoices and bank statements
"""
import os
import logging
from sqlalchemy.orm import Session
from database.models import FileUpload, FileUploadStatus, Invoice
from utils.invoice_extractor import process_invoice_pdf
from core.processing import process_invoice
from datetime import datetime

logger = logging.getLogger(__name__)


def process_invoice_file(upload_id: int, db: Session):
    """
    Process a single invoice file in the background
    Updates FileUpload status and creates Invoice record
    """
    upload = db.query(FileUpload).filter(FileUpload.upload_id == upload_id).first()
    if not upload:
        logger.error(f"FileUpload {upload_id} not found")
        return
    
    try:
        # Update status to processing
        upload.status = FileUploadStatus.PROCESSING
        db.commit()
        
        # Check if file still exists
        if not os.path.exists(upload.file_path):
            raise FileNotFoundError(f"File not found: {upload.file_path}")
        
        # Extract invoice data
        invoice_data = process_invoice_pdf(upload.file_path, use_ocr=True, use_ai=True)
        if not invoice_data:
            raise ValueError(
                "Could not extract invoice data from PDF. "
                "The PDF appears to be image-based and text extraction failed."
            )
        
        # Process invoice (create journal entry, etc.)
        invoice = process_invoice(invoice_data, upload.file_path)
        
        # Update upload record with success
        upload.status = FileUploadStatus.COMPLETED
        upload.invoice_id = invoice.invoice_id
        upload.processed_at = datetime.utcnow()
        upload.error_message = None
        db.commit()
        
        logger.info(f"Successfully processed invoice file {upload.filename} (upload_id: {upload_id})")
        
    except Exception as e:
        # Update upload record with error
        upload.status = FileUploadStatus.FAILED
        upload.error_message = str(e)
        upload.processed_at = datetime.utcnow()
        db.commit()
        
        logger.error(f"Failed to process invoice file {upload.filename} (upload_id: {upload_id}): {e}", exc_info=True)
    
    finally:
        # Clean up temp file after processing
        try:
            if os.path.exists(upload.file_path):
                os.unlink(upload.file_path)
                logger.debug(f"Cleaned up temp file: {upload.file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp file {upload.file_path}: {e}")


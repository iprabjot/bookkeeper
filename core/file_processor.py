"""
Background file processing for invoices and bank statements
"""
import os
import logging
from sqlalchemy.orm import Session
from database.models import FileUpload, FileUploadStatus, Invoice
from utils.invoice_extractor import process_invoice_pdf
from core.processing import process_invoice
from core.storage import get_storage_service
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
        
        # Check if file exists (local file) or is S3 URL
        local_file_path = upload.file_path
        temp_downloaded = False
        
        if upload.file_path.startswith("http"):
            # File is already in S3, download temporarily for processing
            storage = get_storage_service()
            if storage.enabled:
                # Extract object key from URL
                # Format: https://endpoint/bucket/key or https://bucket.s3.region.amazonaws.com/key
                import tempfile
                tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                local_file_path = tmp_file.name
                tmp_file.close()
                temp_downloaded = True
                
                # Extract object key from URL
                if "/" in upload.file_path:
                    parts = upload.file_path.split("/")
                    if storage.bucket_name in parts:
                        object_key = "/".join(parts[parts.index(storage.bucket_name) + 1:])
                    else:
                        # Try to find the key after the last known part
                        object_key = parts[-1]
                else:
                    object_key = upload.file_path.split("/")[-1]
                
                if not storage.download_file(object_key, local_file_path):
                    raise FileNotFoundError(f"Could not download file from S3: {upload.file_path}")
            else:
                raise FileNotFoundError(f"File is in S3 but S3 storage is not enabled: {upload.file_path}")
        elif not os.path.exists(upload.file_path):
            raise FileNotFoundError(f"File not found: {upload.file_path}")
        
        # Extract invoice data
        invoice_data = process_invoice_pdf(local_file_path, use_ocr=True, use_ai=True)
        if not invoice_data:
            raise ValueError(
                "Could not extract invoice data from PDF. "
                "The PDF appears to be image-based and text extraction failed."
            )
        
        # Save file to persistent storage (S3 or local)
        storage = get_storage_service()
        persistent_path = None
        
        if upload.file_path.startswith("http"):
            # Already in S3, use the URL
            persistent_path = upload.file_path
        else:
            # Save to persistent storage
            object_key = storage.generate_object_key(
                file_type="invoice",
                company_id=upload.company_id,
                filename=upload.filename
            )
            persistent_path = storage.upload_file(
                local_file_path,
                object_key,
                content_type="application/pdf"
            )
            if persistent_path:
                logger.info(f"Saved invoice to persistent storage: {persistent_path}")
            else:
                # Fallback to original path if storage failed
                persistent_path = local_file_path
                logger.warning(f"Failed to save to persistent storage, using original path: {local_file_path}")
        
        # Process invoice (create journal entry, etc.)
        invoice = process_invoice(invoice_data, persistent_path, company_id=upload.company_id)
        
        # Update upload record with success
        upload.status = FileUploadStatus.COMPLETED
        upload.invoice_id = invoice.invoice_id
        upload.processed_at = datetime.utcnow()
        upload.error_message = None
        
        # Update file_path to persistent path
        upload.file_path = persistent_path
        
        db.commit()
        
        logger.info(f"Successfully processed invoice file {upload.filename} (upload_id: {upload_id})")
        
    except Exception as e:
        # Update upload record with error
        upload.status = FileUploadStatus.FAILED
        upload.error_message = str(e)
        upload.processed_at = datetime.utcnow()
        db.commit()
        
        logger.error(f"Failed to process invoice file {upload.filename} (upload_id: {upload_id}): {e}", exc_info=True)


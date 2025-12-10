"""
File Storage Service
Handles file uploads to S3-compatible storage (Railway Storage Buckets or AWS S3)
"""
import os
import logging
from typing import Optional, BinaryIO
from pathlib import Path
logger = logging.getLogger(__name__)

# Try to import boto3, fall back gracefully if not available
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not installed. Install with: pip install boto3")


class StorageService:
    """Service for handling file storage in S3-compatible storage or local filesystem"""
    
    def __init__(self):
        """Initialize storage service with credentials from environment"""
        self.bucket_name = os.getenv("S3_BUCKET_NAME")
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL")  # For Railway Storage Buckets
        self.region = os.getenv("S3_REGION", "us-east-1")
        self.access_key = os.getenv("S3_ACCESS_KEY_ID")
        self.secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
        
        # Local storage directory (persistent)
        # Default: storage/ in project root
        default_storage = os.path.join(os.getcwd(), "storage")
        self.local_storage_dir = os.getenv("LOCAL_STORAGE_DIR", default_storage)
        os.makedirs(self.local_storage_dir, exist_ok=True)
        logger.info(f"Local storage directory: {self.local_storage_dir}")
        
        self.s3_client = None
        self.enabled = False
        
        if not BOTO3_AVAILABLE:
            logger.info("boto3 not available. Using local filesystem storage.")
            logger.info(f"Local storage directory: {self.local_storage_dir}")
            return
        
        if not all([self.bucket_name, self.access_key, self.secret_key]):
            logger.info(
                "S3 credentials not configured. Using local filesystem storage. "
                f"Files stored in: {self.local_storage_dir}. "
                "Set S3_BUCKET_NAME, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY to enable S3 storage."
            )
            return
        
        try:
            # Initialize S3 client
            s3_config = {
                "aws_access_key_id": self.access_key,
                "aws_secret_access_key": self.secret_key,
                "region_name": self.region,
            }
            
            # Railway Storage Buckets use custom endpoint
            if self.endpoint_url:
                s3_config["endpoint_url"] = self.endpoint_url
            
            self.s3_client = boto3.client("s3", **s3_config)
            
            # Test connection
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.enabled = True
            logger.info(f"S3 storage enabled. Bucket: {self.bucket_name}")
            
        except NoCredentialsError:
            logger.error("S3 credentials invalid. Falling back to local storage.")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                logger.error(f"S3 bucket '{self.bucket_name}' not found. Falling back to local storage.")
            else:
                logger.error(f"S3 connection error: {e}. Falling back to local storage.")
        except Exception as e:
            logger.error(f"Failed to initialize S3 storage: {e}. Falling back to local storage.")
    
    def upload_file(
        self,
        file_path: str,
        object_key: str,
        content_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload a file to S3 storage or save to local filesystem
        
        Args:
            file_path: Local file path to upload
            object_key: S3 object key (path in bucket) or local relative path
            content_type: MIME type (e.g., 'application/pdf')
        
        Returns:
            S3 object URL or local file path if successful, None if failed
        """
        if not self.enabled or not self.s3_client:
            # Use local filesystem storage
            return self._save_to_local(file_path, object_key)
        
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args
            )
            
            # Generate URL
            if self.endpoint_url:
                # Railway Storage Buckets URL format
                url = f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
            else:
                # Standard S3 URL format
                url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_key}"
            
            logger.info(f"Uploaded file to S3: {object_key}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}", exc_info=True)
            return None
    
    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        object_key: str,
        content_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload a file-like object to S3 storage
        
        Args:
            file_obj: File-like object (e.g., BytesIO, file handle)
            object_key: S3 object key (path in bucket)
            content_type: MIME type
        
        Returns:
            S3 object URL if successful, None if failed
        """
        if not self.enabled or not self.s3_client:
            logger.debug(f"S3 not enabled, skipping upload: {object_key}")
            return None
        
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args
            )
            
            # Generate URL
            if self.endpoint_url:
                url = f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
            else:
                url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_key}"
            
            logger.info(f"Uploaded file to S3: {object_key}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}", exc_info=True)
            return None
    
    def download_file(self, object_key: str, local_path: str) -> bool:
        """
        Download a file from S3 storage
        
        Args:
            object_key: S3 object key
            local_path: Local path to save the file
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.s3_client:
            logger.debug(f"S3 not enabled, cannot download: {object_key}")
            return False
        
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3_client.download_file(self.bucket_name, object_key, local_path)
            logger.info(f"Downloaded file from S3: {object_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to download file from S3: {e}", exc_info=True)
            return False
    
    def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from S3 storage
        
        Args:
            object_key: S3 object key
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.s3_client:
            logger.debug(f"S3 not enabled, cannot delete: {object_key}")
            return False
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info(f"Deleted file from S3: {object_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file from S3: {e}", exc_info=True)
            return False
    
    def get_file_url(self, object_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for temporary access to a file
        
        Args:
            object_key: S3 object key
            expires_in: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Presigned URL if successful, None otherwise
        """
        if not self.enabled or not self.s3_client:
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}", exc_info=True)
            return None
    
    def generate_object_key(self, file_type: str, company_id: int, filename: str) -> str:
        """
        Generate a consistent S3 object key or local path for a file
        
        Args:
            file_type: Type of file ('invoice', 'report', 'bank_statement')
            company_id: Company ID
            filename: Original filename
        
        Returns:
            S3 object key or local relative path
        """
        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        
        # Format: {file_type}/company_{company_id}/{filename}
        object_key = f"{file_type}/company_{company_id}/{safe_filename}"
        return object_key
    
    def _save_to_local(self, source_path: str, relative_path: str) -> str:
        """
        Save file to local storage directory
        
        Args:
            source_path: Source file path
            relative_path: Relative path within storage directory
        
        Returns:
            Absolute path to saved file
        """
        try:
            # Create full destination path
            dest_path = os.path.join(self.local_storage_dir, relative_path)
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            
            # Copy file
            import shutil
            shutil.copy2(source_path, dest_path)
            
            logger.info(f"Saved file to local storage: {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Failed to save file to local storage: {e}", exc_info=True)
            return None


# Global storage service instance
_storage_service = None


def get_storage_service() -> StorageService:
    """Get or create the global storage service instance"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service


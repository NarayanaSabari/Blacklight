"""
File Storage Service
Handles file uploads, storage, and retrieval with support for:
- Google Cloud Storage (GCS) for production
- Local filesystem for development
"""
import os
import uuid
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import tempfile
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

try:
    from google.cloud import storage
    from google.oauth2 import service_account
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

from config.settings import settings  # Use global settings instance

logger = logging.getLogger(__name__)


class FileStorageService:
    """Service for handling file uploads and storage with GCS and local support"""
    
    # MIME type mappings
    MIME_TYPE_MAPPING = {
        # Documents
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'doc',
        # Images
        'image/jpeg': 'jpg',
        'image/jpg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'image/webp': 'webp',
        # Text
        'text/plain': 'txt',
    }
    
    # Reverse mapping: extension to MIME type
    EXTENSION_TO_MIME = {v: k for k, v in MIME_TYPE_MAPPING.items()}
    
    def __init__(self):
        """Initialize file storage service with configuration from settings"""
        self.storage_backend = settings.storage_backend
        self.local_path = Path(settings.storage_local_path)
        self.max_size_bytes = settings.max_file_size_mb * 1024 * 1024
        self.allowed_types = set(settings.allowed_document_types.split(','))
        
        # Initialize backend
        if self.storage_backend == 'gcs':
            self._init_gcs()
        else:
            self._init_local()
    
    def _init_local(self):
        """Initialize local filesystem storage"""
        self.local_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized local file storage at: {self.local_path}")
    
    def _init_gcs(self):
        """Initialize Google Cloud Storage"""
        if not GCS_AVAILABLE:
            logger.error("google-cloud-storage not installed. Install with: pip install google-cloud-storage")
            raise RuntimeError("GCS support not available. Install google-cloud-storage package.")
        
        if not settings.gcs_bucket_name:
            raise ValueError("GCS_BUCKET_NAME must be set when using GCS storage backend")
        
        self.bucket_name = settings.gcs_bucket_name
        
        # Initialize credentials
        credentials = None
        if settings.gcs_credentials_json:
            # Use inline JSON credentials
            try:
                creds_dict = json.loads(settings.gcs_credentials_json)
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid GCS_CREDENTIALS_JSON: {e}")
                raise ValueError("Invalid GCS credentials JSON")
        elif settings.gcs_credentials_path:
            # Use credentials file path
            if not os.path.exists(settings.gcs_credentials_path):
                raise FileNotFoundError(f"GCS credentials file not found: {settings.gcs_credentials_path}")
            credentials = service_account.Credentials.from_service_account_file(
                settings.gcs_credentials_path
            )
        
        # Initialize storage client
        if credentials:
            self.gcs_client = storage.Client(
                project=settings.gcs_project_id or None,
                credentials=credentials
            )
        else:
            # Use default credentials (e.g., from GOOGLE_APPLICATION_CREDENTIALS env var)
            self.gcs_client = storage.Client(project=settings.gcs_project_id or None)
        
        # Get bucket and verify connection
        try:
            self.bucket = self.gcs_client.bucket(self.bucket_name)
            
            # Verify bucket exists and is accessible
            if self.bucket.exists():
                logger.info(f"GCS connection successful - bucket '{self.bucket_name}' is accessible")
                logger.info({
                    "message": "GCS connection successful",
                    "bucket": self.bucket_name,
                    "project_id": settings.gcs_project_id or "default",
                    "storage_backend": "gcs"
                })
            else:
                logger.error(f"GCS connection failed - bucket '{self.bucket_name}' does not exist")
                logger.error({
                    "message": "GCS connection failed",
                    "reason": "Bucket does not exist",
                    "bucket": self.bucket_name
                })
                raise ValueError(f"GCS bucket '{self.bucket_name}' does not exist")
                
        except Exception as e:
            logger.error(f"GCS connection failed - unable to access bucket '{self.bucket_name}': {e}")
            logger.error({
                "message": "GCS connection failed",
                "reason": str(e),
                "bucket": self.bucket_name
            })
            raise
    
    def _get_file_key(
        self,
        tenant_id: int,
        document_type: str,
        filename: str,
        candidate_id: Optional[int] = None,
        invitation_id: Optional[int] = None
    ) -> str:
        """
        Generate storage key/path for a file.
        Format: tenants/{tenant_id}/candidates/{candidate_id}/{document_type}/{filename}
             or tenants/{tenant_id}/invitations/{invitation_id}/{document_type}/{filename}
        
        Args:
            tenant_id: Tenant ID for isolation
            document_type: Type of document (resume, id_proof, work_authorization, certificate, other)
            filename: Secure filename
            candidate_id: Optional candidate ID
            invitation_id: Optional invitation ID
        
        Returns:
            Storage key/path string
        """
        # Determine entity folder - candidate or invitation based
        if candidate_id:
            entity_path = f"candidates/{candidate_id}"
        elif invitation_id:
            entity_path = f"invitations/{invitation_id}"
        else:
            entity_path = "temp"
        
        # Build key: tenants/{tenant_id}/{entity_path}/{document_type}/{filename}
        return f"tenants/{tenant_id}/{entity_path}/{document_type}/{filename}"
    
    def _generate_secure_filename(self, original_filename: str) -> str:
        """Generate a secure, unique filename"""
        safe_filename = secure_filename(original_filename)
        name, ext = os.path.splitext(safe_filename)
        
        # Truncate long names
        if len(name) > 50:
            name = name[:50]
        
        # Add UUID and timestamp
        unique_id = uuid.uuid4().hex[:12]
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        return f"{name}_{timestamp}_{unique_id}{ext}"
    
    def _validate_file_type(self, filename: str) -> Tuple[bool, Optional[str]]:
        """Validate file type by extension"""
        if '.' not in filename:
            return False, "No file extension"
        
        extension = filename.rsplit('.', 1)[1].lower()
        if extension not in self.allowed_types:
            return False, f"File type '.{extension}' not allowed. Allowed: {', '.join(self.allowed_types)}"
        
        return True, None
    
    def _validate_file_size(self, file: FileStorage) -> Tuple[bool, Optional[str]]:
        """Validate file size"""
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        
        if size > self.max_size_bytes:
            max_mb = self.max_size_bytes / (1024 * 1024)
            return False, f"File too large ({size / (1024 * 1024):.2f}MB). Maximum: {max_mb}MB"
        
        if size == 0:
            return False, "File is empty"
        
        return True, None
    
    def _detect_mime_type(self, file_content: bytes, filename: str) -> str:
        """Detect MIME type from file content or fallback to extension"""
        if MAGIC_AVAILABLE:
            try:
                mime = magic.Magic(mime=True)
                return mime.from_buffer(file_content)
            except Exception as e:
                logger.warning(f"MIME detection failed: {e}")
        
        # Fallback: use extension
        extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        return self.EXTENSION_TO_MIME.get(extension, 'application/octet-stream')
    
    def validate_file(self, file: FileStorage) -> Dict[str, Any]:
        """
        Validate uploaded file.
        
        Args:
            file: FileStorage object from Flask request
        
        Returns:
            Dictionary with validation result:
            {
                "valid": bool,
                "error": Optional[str],
                "file_size": int,
                "extension": str
            }
        """
        if not file or not file.filename:
            return {"valid": False, "error": "No file provided"}
        
        # Validate file type
        valid_type, type_error = self._validate_file_type(file.filename)
        if not valid_type:
            return {"valid": False, "error": type_error}
        
        # Validate file size
        valid_size, size_error = self._validate_file_size(file)
        if not valid_size:
            return {"valid": False, "error": size_error}
        
        # Get file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        # Get extension
        extension = file.filename.rsplit('.', 1)[1].lower()
        
        return {
            "valid": True,
            "error": None,
            "file_size": file_size,
            "extension": extension
        }
    
    def upload_file(
        self,
        file: FileStorage,
        tenant_id: int,
        document_type: str,
        candidate_id: Optional[int] = None,
        invitation_id: Optional[int] = None,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload file to storage backend.
        
        Args:
            file: FileStorage object from Flask request
            tenant_id: Tenant ID for isolation
            document_type: Document type (resume, id_proof, certificate, etc.)
            candidate_id: Optional candidate ID
            invitation_id: Optional invitation ID
            content_type: Optional override for content type
        
        Returns:
            Dictionary with upload result:
            {
                "success": bool,
                "file_key": str,
                "file_name": str,
                "file_size": int,
                "mime_type": str,
                "storage_backend": str,
                "uploaded_at": str,
                "error": Optional[str]
            }
        """
        # Validate file
        validation = self.validate_file(file)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}
        
        try:
            # Read file content
            file_content = file.read()
            file.seek(0)
            
            # Generate secure filename
            secure_name = self._generate_secure_filename(file.filename)
            
            # Generate file key
            file_key = self._get_file_key(
                tenant_id=tenant_id,
                document_type=document_type,
                filename=secure_name,
                candidate_id=candidate_id,
                invitation_id=invitation_id
            )
            
            # Detect MIME type
            mime_type = content_type or self._detect_mime_type(file_content, file.filename)
            
            # Upload based on backend
            if self.storage_backend == 'gcs':
                upload_result = self._upload_to_gcs(file_key, file_content, mime_type)
            else:
                upload_result = self._upload_to_local(file_key, file_content)
            
            if not upload_result["success"]:
                return upload_result
            
            return {
                "success": True,
                "file_key": file_key,
                "file_name": secure_name,
                "file_size": len(file_content),
                "mime_type": mime_type,
                "storage_backend": self.storage_backend,
                "uploaded_at": datetime.utcnow().isoformat(),
                "error": None
            }
        
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return {"success": False, "error": f"Upload failed: {str(e)}"}
    
    def _upload_to_gcs(self, file_key: str, file_content: bytes, mime_type: str) -> Dict[str, Any]:
        """Upload file to Google Cloud Storage"""
        try:
            blob = self.bucket.blob(file_key)
            blob.upload_from_string(
                file_content,
                content_type=mime_type
            )
            
            # Set metadata
            blob.metadata = {
                'uploaded_at': datetime.utcnow().isoformat(),
                'original_size': str(len(file_content))
            }
            blob.patch()
            
            logger.info(f"Uploaded file to GCS: {file_key}")
            return {"success": True}
        
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            return {"success": False, "error": f"GCS upload failed: {str(e)}"}
    
    def _upload_to_local(self, file_key: str, file_content: bytes) -> Dict[str, Any]:
        """Upload file to local filesystem"""
        try:
            file_path = self.local_path / file_key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"Uploaded file to local storage: {file_path}")
            return {"success": True}
        
        except Exception as e:
            logger.error(f"Local upload failed: {e}")
            return {"success": False, "error": f"Local upload failed: {str(e)}"}
    
    def download_file(self, file_key: str) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        """
        Download file from storage.
        
        Args:
            file_key: Storage key/path
        
        Returns:
            Tuple of (file_content, content_type, error)
        """
        try:
            if self.storage_backend == 'gcs':
                return self._download_from_gcs(file_key)
            else:
                return self._download_from_local(file_key)
        
        except Exception as e:
            logger.error(f"File download failed: {e}")
            return None, None, f"Download failed: {str(e)}"

    def download_to_temp(self, file_key: str, suffix: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Download a storage object and write to a local temporary file.

        Returns:
            (local_path, error)
        """
        try:
            content, content_type, err = self.download_file(file_key)
            if err:
                return None, err

            # Determine suffix from file_key if not provided
            if not suffix and '.' in file_key:
                suffix = '.' + file_key.rsplit('.', 1)[1]

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix or '')
            tmp.write(content)
            tmp.flush()
            tmp.close()

            logger.info(f"Downloaded {file_key} to temp file: {tmp.name}")
            return tmp.name, None

        except Exception as e:
            logger.error(f"Failed to download_to_temp for {file_key}: {e}")
            return None, str(e)
    
    def _download_from_gcs(self, file_key: str) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        """Download file from GCS"""
        try:
            blob = self.bucket.blob(file_key)
            
            if not blob.exists():
                return None, None, "File not found"
            
            content = blob.download_as_bytes()
            content_type = blob.content_type or 'application/octet-stream'
            
            return content, content_type, None
        
        except Exception as e:
            logger.error(f"GCS download failed: {e}")
            return None, None, f"GCS download failed: {str(e)}"
    
    def _download_from_local(self, file_key: str) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        """Download file from local filesystem"""
        try:
            file_path = self.local_path / file_key
            
            if not file_path.exists():
                return None, None, "File not found"
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Detect content type
            extension = file_path.suffix.lstrip('.').lower()
            content_type = self.EXTENSION_TO_MIME.get(extension, 'application/octet-stream')
            
            return content, content_type, None
        
        except Exception as e:
            logger.error(f"Local download failed: {e}")
            return None, None, f"Local download failed: {str(e)}"
    
    def generate_signed_url(self, file_key: str, expiry_seconds: Optional[int] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate signed URL for temporary file access.
        
        Args:
            file_key: Storage key/path
            expiry_seconds: URL expiry time (default: from settings)
        
        Returns:
            Tuple of (signed_url, error)
        """
        if expiry_seconds is None:
            expiry_seconds = settings.signed_url_expiry_seconds
        
        try:
            if self.storage_backend == 'gcs':
                return self._generate_gcs_signed_url(file_key, expiry_seconds)
            else:
                # For local storage, return a path (not a signed URL)
                # In production, this should be served through a protected route
                return f"/api/documents/file/{file_key}", None
        
        except Exception as e:
            logger.error(f"Signed URL generation failed: {e}")
            return None, f"URL generation failed: {str(e)}"
    
    def _generate_gcs_signed_url(self, file_key: str, expiry_seconds: int) -> Tuple[Optional[str], Optional[str]]:
        """Generate signed URL for GCS file"""
        try:
            blob = self.bucket.blob(file_key)
            
            if not blob.exists():
                return None, "File not found"
            
            # Generate signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiry_seconds),
                method="GET"
            )
            
            return url, None
        
        except Exception as e:
            logger.error(f"GCS signed URL generation failed: {e}")
            return None, f"GCS signed URL generation failed: {str(e)}"
    
    def delete_file(self, file_key: str) -> Dict[str, Any]:
        """
        Delete file from storage.
        
        Args:
            file_key: Storage key/path
        
        Returns:
            Dictionary with deletion result
        """
        try:
            if self.storage_backend == 'gcs':
                return self._delete_from_gcs(file_key)
            else:
                return self._delete_from_local(file_key)
        
        except Exception as e:
            logger.error(f"File deletion failed: {e}")
            return {"success": False, "error": f"Deletion failed: {str(e)}"}
    
    def _delete_from_gcs(self, file_key: str) -> Dict[str, Any]:
        """Delete file from GCS"""
        try:
            blob = self.bucket.blob(file_key)
            
            if not blob.exists():
                return {"success": False, "error": "File not found"}
            
            blob.delete()
            logger.info(f"Deleted file from GCS: {file_key}")
            return {"success": True, "error": None}
        
        except Exception as e:
            logger.error(f"GCS deletion failed: {e}")
            return {"success": False, "error": f"GCS deletion failed: {str(e)}"}
    
    def _delete_from_local(self, file_key: str) -> Dict[str, Any]:
        """Delete file from local filesystem"""
        try:
            file_path = self.local_path / file_key
            
            if not file_path.exists():
                return {"success": False, "error": "File not found"}
            
            os.remove(file_path)
            logger.info(f"Deleted file from local storage: {file_path}")
            return {"success": True, "error": None}
        
        except Exception as e:
            logger.error(f"Local deletion failed: {e}")
            return {"success": False, "error": f"Local deletion failed: {str(e)}"}
    
    def file_exists(self, file_key: str) -> bool:
        """Check if file exists in storage"""
        try:
            if self.storage_backend == 'gcs':
                blob = self.bucket.blob(file_key)
                return blob.exists()
            else:
                file_path = self.local_path / file_key
                return file_path.exists()
        
        except Exception as e:
            logger.error(f"File existence check failed: {e}")
            return False
    
    def move_file(self, old_file_key: str, new_file_key: str) -> Dict[str, Any]:
        """
        Move/rename a file within storage (same bucket for GCS, same base path for local).
        
        Args:
            old_file_key: Current storage key/path
            new_file_key: New storage key/path
        
        Returns:
            Dictionary with move result:
            {
                "success": bool,
                "new_file_key": str,
                "error": Optional[str]
            }
        """
        try:
            if self.storage_backend == 'gcs':
                return self._move_in_gcs(old_file_key, new_file_key)
            else:
                return self._move_in_local(old_file_key, new_file_key)
        
        except Exception as e:
            logger.error(f"File move failed: {e}")
            return {"success": False, "error": f"Move failed: {str(e)}"}
    
    def _move_in_gcs(self, old_file_key: str, new_file_key: str) -> Dict[str, Any]:
        """Move file within GCS bucket (copy + delete)"""
        try:
            source_blob = self.bucket.blob(old_file_key)
            
            if not source_blob.exists():
                return {"success": False, "error": "Source file not found"}
            
            # Copy to new location
            new_blob = self.bucket.copy_blob(source_blob, self.bucket, new_file_key)
            
            # Delete original
            source_blob.delete()
            
            logger.info(f"Moved file in GCS: {old_file_key} -> {new_file_key}")
            return {"success": True, "new_file_key": new_file_key, "error": None}
        
        except Exception as e:
            logger.error(f"GCS move failed: {e}")
            return {"success": False, "error": f"GCS move failed: {str(e)}"}
    
    def _move_in_local(self, old_file_key: str, new_file_key: str) -> Dict[str, Any]:
        """Move file within local filesystem"""
        try:
            old_path = self.local_path / old_file_key
            new_path = self.local_path / new_file_key
            
            if not old_path.exists():
                return {"success": False, "error": "Source file not found"}
            
            # Create parent directories if needed
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            import shutil
            shutil.move(str(old_path), str(new_path))
            
            logger.info(f"Moved file in local storage: {old_path} -> {new_path}")
            return {"success": True, "new_file_key": new_file_key, "error": None}
        
        except Exception as e:
            logger.error(f"Local move failed: {e}")
            return {"success": False, "error": f"Local move failed: {str(e)}"}
    
    def generate_new_file_key_for_candidate(
        self,
        old_file_key: str,
        tenant_id: int,
        candidate_id: int,
        document_type: str
    ) -> str:
        """
        Generate a new file key for moving a file from invitation to candidate folder.
        
        Args:
            old_file_key: Current file key (e.g., tenants/1/invitations/100/resume/file.pdf)
            tenant_id: Tenant ID
            candidate_id: Target candidate ID
            document_type: Document type (resume, id_proof, etc.)
        
        Returns:
            New file key (e.g., tenants/1/candidates/42/resume/file.pdf)
        """
        # Extract filename from old key
        filename = old_file_key.rsplit('/', 1)[-1]
        
        # Build new key using candidate path
        return f"tenants/{tenant_id}/candidates/{candidate_id}/{document_type}/{filename}"

    def list_files(
        self,
        tenant_id: int,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all files and folders in storage for a tenant.
        
        Args:
            tenant_id: Tenant ID for isolation
            prefix: Optional path prefix to filter (relative to tenant folder)
            delimiter: Optional delimiter for folder-like listing (use '/' for folder view)
        
        Returns:
            Dictionary with listing result:
            {
                "success": bool,
                "files": List[Dict] - list of file objects,
                "prefixes": List[str] - list of "folder" prefixes (when using delimiter),
                "total_count": int,
                "total_size_bytes": int,
                "error": Optional[str]
            }
        """
        try:
            # Build the full prefix for this tenant
            base_prefix = f"tenants/{tenant_id}/"
            if prefix:
                # Ensure prefix doesn't have leading slash and ends with /
                clean_prefix = prefix.strip('/')
                if clean_prefix:
                    base_prefix = f"tenants/{tenant_id}/{clean_prefix}/"
            
            if self.storage_backend == 'gcs':
                return self._list_files_gcs(base_prefix, delimiter)
            else:
                return self._list_files_local(base_prefix, delimiter)
        
        except Exception as e:
            logger.error(f"File listing failed: {e}")
            return {"success": False, "error": f"Listing failed: {str(e)}", "files": [], "prefixes": []}

    def _list_files_gcs(self, prefix: str, delimiter: Optional[str] = None) -> Dict[str, Any]:
        """List files from GCS bucket"""
        try:
            files = []
            prefixes = []
            total_size = 0
            
            # List blobs with optional delimiter for folder-like behavior
            blobs = self.gcs_client.list_blobs(
                self.bucket_name,
                prefix=prefix,
                delimiter=delimiter
            )
            
            # Process blobs (files)
            for blob in blobs:
                # Skip the prefix itself if it's a "folder"
                if blob.name == prefix or blob.name.endswith('/'):
                    continue
                
                file_info = {
                    "name": blob.name.split('/')[-1],  # Just the filename
                    "full_path": blob.name,  # Full GCS path
                    "relative_path": blob.name.replace(f"tenants/", ""),  # Path without tenants/ prefix
                    "size": blob.size or 0,
                    "content_type": blob.content_type or "application/octet-stream",
                    "created_at": blob.time_created.isoformat() if blob.time_created else None,
                    "updated_at": blob.updated.isoformat() if blob.updated else None,
                    "is_file": True,
                    "storage_backend": "gcs"
                }
                files.append(file_info)
                total_size += blob.size or 0
            
            # Process prefixes (folders) - only available when using delimiter
            if delimiter and hasattr(blobs, 'prefixes'):
                for p in blobs.prefixes:
                    folder_name = p.rstrip('/').split('/')[-1]
                    prefixes.append({
                        "name": folder_name,
                        "full_path": p,
                        "relative_path": p.replace(f"tenants/", "").rstrip('/'),
                        "is_file": False
                    })
            
            return {
                "success": True,
                "files": files,
                "prefixes": prefixes,
                "total_count": len(files),
                "total_size_bytes": total_size,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"GCS listing failed: {e}")
            return {"success": False, "error": f"GCS listing failed: {str(e)}", "files": [], "prefixes": []}

    def _list_files_local(self, prefix: str, delimiter: Optional[str] = None) -> Dict[str, Any]:
        """List files from local filesystem"""
        try:
            files = []
            prefixes = []
            total_size = 0
            
            base_path = self.local_path / prefix.rstrip('/')
            
            if not base_path.exists():
                return {
                    "success": True,
                    "files": [],
                    "prefixes": [],
                    "total_count": 0,
                    "total_size_bytes": 0,
                    "error": None
                }
            
            if delimiter == '/':
                # Folder-like listing - only immediate children
                for item in base_path.iterdir():
                    relative_path = str(item.relative_to(self.local_path))
                    
                    if item.is_file():
                        stat = item.stat()
                        file_info = {
                            "name": item.name,
                            "full_path": relative_path,
                            "relative_path": relative_path.replace("tenants/", ""),
                            "size": stat.st_size,
                            "content_type": self.EXTENSION_TO_MIME.get(
                                item.suffix.lstrip('.').lower(), 
                                "application/octet-stream"
                            ),
                            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "is_file": True,
                            "storage_backend": "local"
                        }
                        files.append(file_info)
                        total_size += stat.st_size
                    elif item.is_dir():
                        prefixes.append({
                            "name": item.name,
                            "full_path": relative_path + '/',
                            "relative_path": relative_path.replace("tenants/", ""),
                            "is_file": False
                        })
            else:
                # Recursive listing - all files
                for item in base_path.rglob('*'):
                    if item.is_file():
                        relative_path = str(item.relative_to(self.local_path))
                        stat = item.stat()
                        file_info = {
                            "name": item.name,
                            "full_path": relative_path,
                            "relative_path": relative_path.replace("tenants/", ""),
                            "size": stat.st_size,
                            "content_type": self.EXTENSION_TO_MIME.get(
                                item.suffix.lstrip('.').lower(), 
                                "application/octet-stream"
                            ),
                            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "is_file": True,
                            "storage_backend": "local"
                        }
                        files.append(file_info)
                        total_size += stat.st_size
            
            return {
                "success": True,
                "files": files,
                "prefixes": prefixes,
                "total_count": len(files),
                "total_size_bytes": total_size,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"Local listing failed: {e}")
            return {"success": False, "error": f"Local listing failed: {str(e)}", "files": [], "prefixes": []}


# Legacy support for existing resume upload functionality
# LegacyResumeStorageService removed in Phase 3 cleanup. Use FileStorageService as the single storage abstraction.

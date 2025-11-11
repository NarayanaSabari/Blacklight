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

from config.settings import Settings

logger = logging.getLogger(__name__)
settings = Settings()


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
        
        # Get bucket
        try:
            self.bucket = self.gcs_client.bucket(self.bucket_name)
            if not self.bucket.exists():
                logger.warning(f"GCS bucket {self.bucket_name} does not exist")
        except Exception as e:
            logger.error(f"Failed to initialize GCS bucket: {e}")
            raise
        
        logger.info(f"Initialized GCS storage with bucket: {self.bucket_name}")
    
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
        Format: tenants/{tenant_id}/{document_type}/{entity_id}/{filename}
        
        Args:
            tenant_id: Tenant ID for isolation
            document_type: Type of document (resume, id_proof, etc.)
            filename: Secure filename
            candidate_id: Optional candidate ID
            invitation_id: Optional invitation ID
        
        Returns:
            Storage key/path string
        """
        # Determine entity folder
        if candidate_id:
            entity_folder = f"candidates/{candidate_id}"
        elif invitation_id:
            entity_folder = f"invitations/{invitation_id}"
        else:
            entity_folder = "temp"
        
        # Build key: tenants/{tenant_id}/{document_type}/{entity}/{filename}
        return f"tenants/{tenant_id}/{document_type}/{entity_folder}/{filename}"
    
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


# Legacy support for existing resume upload functionality
class LegacyResumeStorageService(FileStorageService):
    """
    Legacy wrapper for backward compatibility with existing resume upload code.
    Delegates to FileStorageService with appropriate document_type.
    """
    
    def upload_resume(
        self,
        file: FileStorage,
        tenant_id: int,
        candidate_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Legacy resume upload method"""
        result = self.upload_file(
            file=file,
            tenant_id=tenant_id,
            document_type='resume',
            candidate_id=candidate_id
        )
        
        if result["success"]:
            # Transform to legacy format
            return {
                "success": True,
                "file_path": result["file_key"],  # Use file_key as path
                "file_url": result.get("file_key"),  # Can generate URL separately
                "file_size": result["file_size"],
                "file_type": result["mime_type"],
                "extension": result["file_name"].rsplit('.', 1)[1] if '.' in result["file_name"] else '',
                "original_filename": file.filename,
                "uploaded_at": result["uploaded_at"],
                "error": None
            }
        
        return result
    
    def delete_resume(self, file_path: str) -> Dict[str, Any]:
        """Legacy resume deletion method"""
        return self.delete_file(file_path)
    
    def get_resume(self, file_path: str) -> Optional[str]:
        """Legacy resume getter"""
        if self.file_exists(file_path):
            return file_path
        return None


    """Service for handling file uploads and storage"""
    
    # Allowed MIME types for resumes
    ALLOWED_MIME_TYPES = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'doc'
    }
    
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}
    
    def __init__(self, storage_path: str = None, max_size_mb: int = 10):
        """
        Initialize file storage service
        
        Args:
            storage_path: Base path for file storage (default: uploads/resumes)
            max_size_mb: Maximum file size in MB (default: 10)
        """
        self.storage_path = storage_path or os.getenv('RESUME_STORAGE_PATH', 'uploads/resumes')
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self):
        """Create storage directory if it doesn't exist"""
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
    
    def _get_tenant_path(self, tenant_id: int) -> Path:
        """Get storage path for a specific tenant"""
        tenant_path = Path(self.storage_path) / str(tenant_id)
        tenant_path.mkdir(parents=True, exist_ok=True)
        return tenant_path
    
    def _get_candidate_path(self, tenant_id: int, candidate_id: Optional[int] = None) -> Path:
        """Get storage path for a specific candidate"""
        if candidate_id:
            candidate_path = self._get_tenant_path(tenant_id) / str(candidate_id)
            candidate_path.mkdir(parents=True, exist_ok=True)
            return candidate_path
        else:
            # For new candidates, use temp directory
            temp_path = self._get_tenant_path(tenant_id) / 'temp'
            temp_path.mkdir(parents=True, exist_ok=True)
            return temp_path
    
    def _validate_file_extension(self, filename: str) -> bool:
        """Validate file extension"""
        if '.' not in filename:
            return False
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in self.ALLOWED_EXTENSIONS
    
    def _validate_file_size(self, file: FileStorage) -> bool:
        """Validate file size"""
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)  # Reset file pointer
        return size <= self.max_size_bytes
    
    def _validate_mime_type(self, file_path: str) -> Optional[str]:
        """
        Validate file MIME type using python-magic (if available)
        Falls back to extension-based validation
        
        Returns:
            File extension if valid, None otherwise
        """
        if not MAGIC_AVAILABLE:
            # Fallback: validate by extension only
            extension = file_path.rsplit('.', 1)[1].lower() if '.' in file_path else None
            return extension if extension in self.ALLOWED_EXTENSIONS else None
        
        try:
            mime = magic.Magic(mime=True)
            mime_type = mime.from_file(file_path)
            return self.ALLOWED_MIME_TYPES.get(mime_type)
        except Exception as e:
            print(f"Error detecting MIME type: {e}")
            # Fallback to extension
            extension = file_path.rsplit('.', 1)[1].lower() if '.' in file_path else None
            return extension if extension in self.ALLOWED_EXTENSIONS else None
    
    def _generate_secure_filename(self, original_filename: str) -> str:
        """Generate a secure, unique filename"""
        # Secure the filename
        safe_filename = secure_filename(original_filename)
        
        # Add UUID to prevent conflicts
        name, ext = os.path.splitext(safe_filename)
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        return f"{name}_{timestamp}_{unique_id}{ext}"
    
    def validate_file(self, file: FileStorage) -> Dict[str, Any]:
        """
        Validate uploaded file
        
        Returns:
            Dictionary with validation result:
            {
                "valid": bool,
                "error": Optional[str],
                "file_type": Optional[str]
            }
        """
        # Check if file exists
        if not file or not file.filename:
            return {"valid": False, "error": "No file provided"}
        
        # Validate extension
        if not self._validate_file_extension(file.filename):
            return {
                "valid": False,
                "error": f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}"
            }
        
        # Validate size
        if not self._validate_file_size(file):
            max_size_mb = self.max_size_bytes / (1024 * 1024)
            return {
                "valid": False,
                "error": f"File too large. Maximum size: {max_size_mb}MB"
            }
        
        return {"valid": True, "error": None}
    
    def upload_resume(
        self,
        file: FileStorage,
        tenant_id: int,
        candidate_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Upload resume file
        
        Args:
            file: FileStorage object from Flask request
            tenant_id: Tenant ID for isolation
            candidate_id: Candidate ID (optional, for new candidates)
        
        Returns:
            Dictionary with upload result:
            {
                "success": bool,
                "file_path": str,
                "file_url": str,
                "file_size": int,
                "file_type": str,
                "original_filename": str,
                "uploaded_at": str,
                "error": Optional[str]
            }
        """
        # Validate file
        validation = self.validate_file(file)
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["error"]
            }
        
        try:
            # Generate secure filename
            secure_name = self._generate_secure_filename(file.filename)
            
            # Get storage path
            storage_dir = self._get_candidate_path(tenant_id, candidate_id)
            file_path = storage_dir / secure_name
            
            # Save file
            file.save(str(file_path))
            
            # Validate MIME type after saving
            file_type = self._validate_mime_type(str(file_path))
            if not file_type:
                # Delete invalid file
                os.remove(str(file_path))
                return {
                    "success": False,
                    "error": "Invalid file type detected"
                }
            
            # Get file size
            file_size = os.path.getsize(str(file_path))
            
            # Extract extension from filename
            extension = os.path.splitext(secure_name)[1].lstrip('.').lower()
            
            # Generate file URL (relative path for now, can be S3 URL in production)
            file_url = f"/{self.storage_path}/{tenant_id}/{candidate_id or 'temp'}/{secure_name}"
            
            return {
                "success": True,
                "file_path": str(file_path),
                "file_url": file_url,
                "file_size": file_size,
                "file_type": file_type,
                "extension": extension,  # Added for parser
                "original_filename": file.filename,
                "uploaded_at": datetime.utcnow().isoformat(),
                "error": None
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Upload failed: {str(e)}"
            }
    
    def delete_resume(self, file_path: str) -> Dict[str, Any]:
        """
        Delete resume file
        
        Args:
            file_path: Absolute path to file
        
        Returns:
            Dictionary with deletion result
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return {"success": True, "error": None}
            else:
                return {"success": False, "error": "File not found"}
        except Exception as e:
            return {"success": False, "error": f"Deletion failed: {str(e)}"}
    
    def get_resume(self, file_path: str) -> Optional[str]:
        """
        Get resume file path if it exists
        
        Args:
            file_path: Absolute path to file
        
        Returns:
            File path if exists, None otherwise
        """
        if os.path.exists(file_path):
            return file_path
        return None
    
    def move_temp_resume(
        self,
        temp_file_path: str,
        tenant_id: int,
        candidate_id: int
    ) -> Dict[str, Any]:
        """
        Move resume from temp directory to candidate directory
        
        Args:
            temp_file_path: Current file path in temp directory
            tenant_id: Tenant ID
            candidate_id: New candidate ID
        
        Returns:
            Dictionary with new file paths
        """
        try:
            if not os.path.exists(temp_file_path):
                return {"success": False, "error": "File not found"}
            
            # Get new path
            filename = os.path.basename(temp_file_path)
            new_dir = self._get_candidate_path(tenant_id, candidate_id)
            new_path = new_dir / filename
            
            # Move file
            os.rename(temp_file_path, str(new_path))
            
            # Generate new URL
            new_url = f"/{self.storage_path}/{tenant_id}/{candidate_id}/{filename}"
            
            return {
                "success": True,
                "file_path": str(new_path),
                "file_url": new_url,
                "error": None
            }
        
        except Exception as e:
            return {"success": False, "error": f"Move failed: {str(e)}"}

"""
File Storage Service
Handles resume file uploads, storage, and retrieval
"""
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False


class FileStorageService:
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

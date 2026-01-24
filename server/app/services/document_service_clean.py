"""
Document Service
Business logic for managing candidate documents with GCS/local storage support
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from werkzeug.datastructures import FileStorage
from sqlalchemy import select, and_

from app import db
from app.models.candidate_document import CandidateDocument
from app.models.candidate import Candidate
from app.models.candidate_invitation import CandidateInvitation
from app.services.file_storage import FileStorageService

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for managing candidate documents with cloud storage"""
    
    @staticmethod
    def upload_document(
        tenant_id: int,
        file: FileStorage,
        document_type: str,
        uploaded_by_id: Optional[int] = None,
        candidate_id: Optional[int] = None,
        invitation_id: Optional[int] = None
    ) -> Tuple[Optional[CandidateDocument], Optional[str]]:
        """
        Upload a document for a candidate or invitation.
        
        Args:
            tenant_id: Tenant ID for isolation
            file: FileStorage object from Flask request
            document_type: Type of document (resume, id_proof, etc.)
            uploaded_by_id: ID of portal user uploading (optional for public uploads)
            candidate_id: Optional candidate ID (post-approval)
            invitation_id: Optional invitation ID (during onboarding)
            
        Returns:
            Tuple of (CandidateDocument, error_message)
            Returns (None, error) if upload fails
        """
        # Validate inputs
        if not candidate_id and not invitation_id:
            return None, "Either candidate_id or invitation_id must be provided"
        
        if not file or not file.filename:
            return None, "No file provided"
        
        try:
            # Initialize storage service
            storage = FileStorageService()
            
            # Upload file to storage backend
            upload_result = storage.upload_file(
                file=file,
                tenant_id=tenant_id,
                document_type=document_type,
                candidate_id=candidate_id,
                invitation_id=invitation_id
            )
            
            if not upload_result['success']:
                return None, upload_result['error']
            
            # Create document record
            document = CandidateDocument(
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                invitation_id=invitation_id,
                document_type=document_type,
                file_name=upload_result['file_name'],
                file_key=upload_result['file_key'],
                file_size=upload_result['file_size'],
                mime_type=upload_result['mime_type'],
                storage_backend=upload_result['storage_backend'],
                uploaded_by_id=uploaded_by_id,
                uploaded_at=datetime.utcnow()
            )
            
            db.session.add(document)
            db.session.commit()
            
            logger.info(f"Created document {document.id} ({document_type}) for tenant {tenant_id}")
            return document, None
        
        except Exception as e:
            logger.error(f"Document upload failed: {e}")
            return None, f"Upload failed: {str(e)}"
    
    @staticmethod
    def get_document(document_id: int, tenant_id: Optional[int] = None) -> Optional[CandidateDocument]:
        """
        Get document by ID with optional tenant isolation check.
        
        Args:
            document_id: Document ID
            tenant_id: Optional tenant ID for security check
            
        Returns:
            CandidateDocument or None
        """
        document = db.session.get(CandidateDocument, document_id)
        
        # Enforce tenant isolation
        if document and tenant_id and document.tenant_id != tenant_id:
            logger.warning(f"Tenant {tenant_id} attempted to access document {document_id} from tenant {document.tenant_id}")
            return None
        
        return document
    
    @staticmethod
    def get_document_by_id(document_id: int, tenant_id: int) -> Tuple[Optional[CandidateDocument], Optional[str]]:
        """
        Get document by ID with tenant isolation (returns tuple for consistent error handling).
        
        Args:
            document_id: Document ID
            tenant_id: Tenant ID for security check
            
        Returns:
            Tuple of (CandidateDocument, error_message)
            Returns (None, error) if not found or access denied
        """
        document = db.session.get(CandidateDocument, document_id)
        
        if not document:
            return None, f"Document with ID {document_id} not found"
        
        # Enforce tenant isolation
        if document.tenant_id != tenant_id:
            logger.warning(f"Tenant {tenant_id} attempted to access document {document_id} from tenant {document.tenant_id}")
            return None, "Document not found"  # Don't reveal it exists in another tenant
        
        return document, None
    
    @staticmethod
    def list_documents(
        tenant_id: int,
        filters: Optional[Dict] = None,
        pagination: Optional[Dict] = None
    ) -> Tuple[List[CandidateDocument], int]:
        """
        List documents with filtering and pagination.
        
        Args:
            tenant_id: Tenant ID for isolation
            filters: Dict with optional keys: candidate_id, invitation_id, document_type, is_verified
            pagination: Dict with optional keys: page (default 1), per_page (default 20)
            
        Returns:
            Tuple of (documents list, total count)
        """
        filters = filters or {}
        pagination = pagination or {}
        
        candidate_id = filters.get('candidate_id')
        invitation_id = filters.get('invitation_id')
        document_type = filters.get('document_type')
        is_verified = filters.get('is_verified')
        page = pagination.get('page', 1)
        per_page = pagination.get('per_page', 20)
        
        query = select(CandidateDocument).where(CandidateDocument.tenant_id == tenant_id)
        
        if candidate_id:
            query = query.where(CandidateDocument.candidate_id == candidate_id)
        
        if invitation_id:
            query = query.where(CandidateDocument.invitation_id == invitation_id)
        
        if document_type:
            query = query.where(CandidateDocument.document_type == document_type)
        
        if is_verified is not None:
            query = query.where(CandidateDocument.is_verified == is_verified)
        
        # Get total count
        count_query = select(db.func.count()).select_from(query.subquery())
        total = db.session.execute(count_query).scalar()
        
        # Order by most recent first
        query = query.order_by(CandidateDocument.uploaded_at.desc())
        
        # Paginate
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        documents = db.session.execute(query).scalars().all()
        
        return list(documents), total
    
    @staticmethod
    def download_document(document_id: int, tenant_id: int) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        """
        Download document file content.
        
        Args:
            document_id: Document ID
            tenant_id: Tenant ID for security check
            
        Returns:
            Tuple of (file_content, content_type, error)
        """
        # Get document with tenant check
        document = DocumentService.get_document(document_id, tenant_id)
        if not document:
            return None, None, "Document not found"
        
        # Download from storage
        storage = FileStorageService()
        content, content_type, error = storage.download_file(document.file_key)
        
        if error:
            logger.error(f"Failed to download document {document_id}: {error}")
            return None, None, error
        
        return content, content_type, None
    
    @staticmethod
    def get_document_url(
        document_id: int,
        tenant_id: int,
        expiry_seconds: int = 3600
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate signed URL for document access.
        
        Args:
            document_id: Document ID
            tenant_id: Tenant ID for security check
            expiry_seconds: URL expiry time in seconds (default: 1 hour)
            
        Returns:
            Tuple of (signed_url, error)
        """
        # Get document with tenant check
        document = DocumentService.get_document(document_id, tenant_id)
        if not document:
            return None, "Document not found"
        
        # Generate signed URL
        storage = FileStorageService()
        url, error = storage.generate_signed_url(document.file_key, expiry_seconds)
        
        if error:
            logger.error(f"Failed to generate signed URL for document {document_id}: {error}")
            return None, error
        
        return url, None
    
    @staticmethod
    def delete_document(document_id: int, tenant_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a document (both file and database record).
        
        Args:
            document_id: Document ID
            tenant_id: Tenant ID for security check
            
        Returns:
            Tuple of (success, error_message)
        """
        # Get document with tenant check
        document = DocumentService.get_document(document_id, tenant_id)
        if not document:
            return False, "Document not found"
        
        try:
            # Delete file from storage
            storage = FileStorageService()
            delete_result = storage.delete_file(document.file_key)
            
            if not delete_result['success']:
                logger.warning(f"Failed to delete file for document {document_id}: {delete_result['error']}")
                # Continue with DB deletion even if file deletion fails
            
            # Delete database record
            db.session.delete(document)
            db.session.commit()
            db.session.expire_all()
            
            logger.info(f"Deleted document {document_id}")
            return True, None
        
        except Exception as e:
            logger.error(f"Document deletion failed: {e}")
            db.session.rollback()
            return False, f"Deletion failed: {str(e)}"
    
    @staticmethod
    def verify_document(
        document_id: int,
        tenant_id: int,
        verified_by_id: int,
        notes: Optional[str] = None
    ) -> Tuple[Optional[CandidateDocument], Optional[str]]:
        """
        Mark a document as verified by HR.
        
        Args:
            document_id: Document ID
            tenant_id: Tenant ID for security check
            verified_by_id: ID of portal user verifying
            notes: Optional verification notes
            
        Returns:
            Tuple of (updated_document, error_message)
        """
        document = DocumentService.get_document(document_id, tenant_id)
        if not document:
            return None, "Document not found"
        
        try:
            document.is_verified = True
            document.verified_by_id = verified_by_id
            document.verified_at = datetime.utcnow()
            document.verification_notes = notes
            document.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Verified document {document_id} by user {verified_by_id}")
            return document, None
        
        except Exception as e:
            logger.error(f"Document verification failed: {e}")
            db.session.rollback()
            return None, f"Verification failed: {str(e)}"
    
    @staticmethod
    def move_documents_to_candidate(invitation_id: int, candidate_id: int, tenant_id: int) -> Tuple[int, Optional[str]]:
        """
        Move documents from invitation to candidate (after approval).
        Updates document records to link to candidate.
        Files remain in same location (tenant isolation maintained).
        
        Args:
            invitation_id: Source invitation ID
            candidate_id: Target candidate ID
            tenant_id: Tenant ID for security check
            
        Returns:
            Tuple of (number_of_documents_moved, error_message)
        """
        try:
            # Get all documents for this invitation
            documents, _ = DocumentService.list_documents(
                tenant_id=tenant_id,
                filters={'invitation_id': invitation_id}
            )
            
            if not documents:
                return 0, None
            
            moved_count = 0
            for document in documents:
                # Update database record to link to candidate
                document.candidate_id = candidate_id
                # Keep invitation_id for audit trail
                document.updated_at = datetime.utcnow()
                moved_count += 1
            
            db.session.commit()
            
            logger.info(f"Moved {moved_count} documents from invitation {invitation_id} to candidate {candidate_id}")
            return moved_count, None
        
        except Exception as e:
            logger.error(f"Failed to move documents: {e}")
            db.session.rollback()
            return 0, f"Move failed: {str(e)}"
    
    @staticmethod
    def get_document_stats(tenant_id: int) -> Dict[str, int]:
        """
        Get document statistics for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Dictionary with statistics
        """
        try:
            # Total documents
            total_query = select(db.func.count()).select_from(CandidateDocument).where(
                CandidateDocument.tenant_id == tenant_id
            )
            total = db.session.execute(total_query).scalar()
            
            # Documents by type
            type_query = select(
                CandidateDocument.document_type,
                db.func.count(CandidateDocument.id)
            ).where(
                CandidateDocument.tenant_id == tenant_id
            ).group_by(CandidateDocument.document_type)
            
            by_type = dict(db.session.execute(type_query).all())
            
            # Verified documents
            verified_query = select(db.func.count()).select_from(CandidateDocument).where(
                and_(
                    CandidateDocument.tenant_id == tenant_id,
                    CandidateDocument.is_verified == True
                )
            )
            verified = db.session.execute(verified_query).scalar()
            
            # Total storage size (in bytes)
            size_query = select(db.func.sum(CandidateDocument.file_size)).where(
                CandidateDocument.tenant_id == tenant_id
            )
            total_size = db.session.execute(size_query).scalar() or 0
            
            return {
                "total_documents": total,
                "by_type": by_type,
                "verified_documents": verified,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
        
        except Exception as e:
            logger.error(f"Failed to get document stats: {e}")
            return {
                "total_documents": 0,
                "by_type": {},
                "verified_documents": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0
            }
    
    @staticmethod
    def get_document_types_config(tenant_id: int) -> List[Dict]:
        """
        Get document types configuration for a tenant.
        Reads from tenant.settings.document_types if configured,
        otherwise returns default types.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            List of document type configurations
        """
        from app.models.tenant import Tenant
        
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return DocumentService._get_default_document_types()
        
        # Check if tenant has custom document types in settings
        if tenant.settings and 'document_types' in tenant.settings:
            return tenant.settings['document_types']
        
        return DocumentService._get_default_document_types()
    
    @staticmethod
    def _get_default_document_types() -> List[Dict]:
        """Get default document types configuration"""
        return [
            {
                'id': 'resume',
                'name': 'Resume/CV',
                'description': 'Upload your latest resume or CV',
                'mandatory': True,
                'allowed_types': ['pdf', 'doc', 'docx'],
                'max_size_mb': 10,
                'order': 0
            },
            {
                'id': 'id_proof',
                'name': 'ID Proof',
                'description': 'Government-issued ID (Passport, Driver\'s License, etc.)',
                'mandatory': True,
                'allowed_types': ['pdf', 'jpg', 'jpeg', 'png'],
                'max_size_mb': 5,
                'order': 1
            },
            {
                'id': 'work_authorization',
                'name': 'Work Authorization',
                'description': 'Work visa or permit if applicable',
                'mandatory': False,
                'allowed_types': ['pdf', 'jpg', 'jpeg', 'png'],
                'max_size_mb': 5,
                'order': 2
            },
            {
                'id': 'certificate',
                'name': 'Certificates',
                'description': 'Professional certifications or degrees',
                'mandatory': False,
                'allowed_types': ['pdf', 'jpg', 'jpeg', 'png'],
                'max_size_mb': 5,
                'order': 3
            },
            {
                'id': 'other',
                'name': 'Other Documents',
                'description': 'Any other relevant documents',
                'mandatory': False,
                'allowed_types': ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'],
                'max_size_mb': 5,
                'order': 4
            }
        ]

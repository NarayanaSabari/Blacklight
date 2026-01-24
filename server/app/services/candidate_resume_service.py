"""
Candidate Resume Service
Manages multiple resumes per candidate with primary resume support
"""
from datetime import datetime
from typing import List, Optional, Tuple
import logging

from flask import current_app
from sqlalchemy import select, and_
from werkzeug.datastructures import FileStorage

from app import db
from app.models.candidate import Candidate
from app.models.candidate_resume import CandidateResume
from app.models.candidate_document import CandidateDocument
from app.services.file_storage import FileStorageService

logger = logging.getLogger(__name__)


class CandidateResumeService:
    """Service for managing candidate resumes"""
    
    @staticmethod
    def get_resume_by_id(resume_id: int, tenant_id: int) -> Optional[CandidateResume]:
        """
        Get a resume by ID.
        
        Args:
            resume_id: Resume ID
            tenant_id: Tenant ID for multi-tenant isolation
            
        Returns:
            CandidateResume or None
        """
        stmt = select(CandidateResume).where(
            and_(
                CandidateResume.id == resume_id,
                CandidateResume.tenant_id == tenant_id
            )
        )
        return db.session.scalar(stmt)
    
    @staticmethod
    def get_resumes_for_candidate(candidate_id: int, tenant_id: int) -> List[CandidateResume]:
        """
        Get all resumes for a candidate.
        
        Args:
            candidate_id: Candidate ID
            tenant_id: Tenant ID for multi-tenant isolation
            
        Returns:
            List of CandidateResume ordered by is_primary desc, created_at desc
        """
        stmt = select(CandidateResume).where(
            and_(
                CandidateResume.candidate_id == candidate_id,
                CandidateResume.tenant_id == tenant_id
            )
        ).order_by(
            CandidateResume.is_primary.desc(),
            CandidateResume.created_at.desc()
        )
        return list(db.session.scalars(stmt))
    
    @staticmethod
    def get_primary_resume(candidate_id: int, tenant_id: int) -> Optional[CandidateResume]:
        """
        Get the primary resume for a candidate.
        
        Args:
            candidate_id: Candidate ID
            tenant_id: Tenant ID for multi-tenant isolation
            
        Returns:
            Primary CandidateResume or None
        """
        stmt = select(CandidateResume).where(
            and_(
                CandidateResume.candidate_id == candidate_id,
                CandidateResume.tenant_id == tenant_id,
                CandidateResume.is_primary == True
            )
        )
        resume = db.session.scalar(stmt)
        
        # If no primary, return the most recent one
        if not resume:
            stmt = select(CandidateResume).where(
                and_(
                    CandidateResume.candidate_id == candidate_id,
                    CandidateResume.tenant_id == tenant_id
                )
            ).order_by(CandidateResume.created_at.desc()).limit(1)
            resume = db.session.scalar(stmt)
        
        return resume
    
    @staticmethod
    def create_resume(
        candidate_id: int,
        tenant_id: int,
        file_key: str,
        storage_backend: str,
        original_filename: str,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        is_primary: bool = False,
        uploaded_by_user_id: Optional[int] = None,
        uploaded_by_candidate: bool = False,
        parsed_resume_data: Optional[dict] = None,
    ) -> CandidateResume:
        """
        Create a new resume record.
        
        Args:
            candidate_id: Candidate ID
            tenant_id: Tenant ID
            file_key: Storage file key
            storage_backend: Storage backend ('local' or 'gcs')
            original_filename: Original uploaded filename
            file_size: File size in bytes
            mime_type: MIME type
            is_primary: Whether this is the primary resume
            uploaded_by_user_id: Portal user who uploaded (None if candidate)
            uploaded_by_candidate: True if uploaded by candidate
            parsed_resume_data: Pre-parsed resume data (optional)
            
        Returns:
            Created CandidateResume
        """
        # If setting as primary, unset other primaries first
        if is_primary:
            CandidateResumeService._unset_primary_for_candidate(candidate_id, tenant_id)
        
        # If this is the first resume for the candidate, make it primary
        existing_count = db.session.scalar(
            select(db.func.count(CandidateResume.id)).where(
                and_(
                    CandidateResume.candidate_id == candidate_id,
                    CandidateResume.tenant_id == tenant_id
                )
            )
        )
        if existing_count == 0:
            is_primary = True
        
        resume = CandidateResume(
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            file_key=file_key,
            storage_backend=storage_backend,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime_type,
            is_primary=is_primary,
            processing_status='pending' if not parsed_resume_data else 'completed',
            uploaded_by_user_id=uploaded_by_user_id,
            uploaded_by_candidate=uploaded_by_candidate,
            uploaded_at=datetime.utcnow(),
            parsed_resume_data=parsed_resume_data,
            processed_at=datetime.utcnow() if parsed_resume_data else None,
        )
        
        db.session.add(resume)
        db.session.flush()  # Flush to get ID but don't commit - let caller control transaction
        
        logger.info(f"Created resume {resume.id} for candidate {candidate_id}, is_primary={is_primary}")
        
        return resume
    
    @staticmethod
    def create_resume_with_document(
        candidate_id: int,
        tenant_id: int,
        file_key: str,
        storage_backend: str,
        original_filename: str,
        uploaded_by_user_id: int,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        is_primary: bool = False,
    ) -> Tuple[CandidateResume, CandidateDocument]:
        """
        Create both CandidateResume and CandidateDocument records and commit.
        Used for HR uploads to ensure resumes appear in document listings.
        
        Args:
            candidate_id: Candidate ID
            tenant_id: Tenant ID
            file_key: Storage file key
            storage_backend: Storage backend ('local' or 'gcs')
            original_filename: Original uploaded filename
            uploaded_by_user_id: Portal user who uploaded
            file_size: File size in bytes
            mime_type: MIME type
            is_primary: Whether this is the primary resume
            
        Returns:
            Tuple of (CandidateResume, CandidateDocument)
        """
        resume = CandidateResumeService.create_resume(
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            file_key=file_key,
            storage_backend=storage_backend,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime_type,
            is_primary=is_primary,
            uploaded_by_user_id=uploaded_by_user_id,
            uploaded_by_candidate=False,
        )
        
        resume_document = CandidateDocument(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            invitation_id=None,
            document_type='resume',
            file_name=original_filename,
            file_key=file_key,
            file_size=file_size or 0,
            mime_type=mime_type or 'application/pdf',
            storage_backend=storage_backend,
            uploaded_by_id=uploaded_by_user_id,
            is_verified=False,
        )
        db.session.add(resume_document)
        
        db.session.commit()
        db.session.refresh(resume)
        db.session.refresh(resume_document)
        
        logger.info(f"Created resume {resume.id} and document {resume_document.id} for candidate {candidate_id}")
        
        return resume, resume_document
    
    @staticmethod
    def upload_and_create_resume(
        candidate_id: int,
        tenant_id: int,
        file: FileStorage,
        is_primary: bool = False,
        uploaded_by_user_id: Optional[int] = None,
        uploaded_by_candidate: bool = False,
    ) -> Tuple[CandidateResume, str]:
        """
        Upload a resume file and create a resume record.
        
        Args:
            candidate_id: Candidate ID
            tenant_id: Tenant ID
            file: Uploaded file
            is_primary: Whether this is the primary resume
            uploaded_by_user_id: Portal user who uploaded (None if candidate)
            uploaded_by_candidate: True if uploaded by candidate
            
        Returns:
            Tuple of (CandidateResume, file_key)
        """
        # Get file info
        original_filename = file.filename or "resume"
        file.seek(0, 2)  # Seek to end to get size
        file_size = file.tell()
        file.seek(0)  # Reset for storage
        mime_type = file.content_type
        
        # Upload to storage using FileStorageService
        storage_service = FileStorageService()
        upload_result = storage_service.upload_file(
            file=file,
            tenant_id=tenant_id,
            document_type="resume",
            candidate_id=candidate_id,
            content_type=mime_type
        )
        
        if not upload_result.get("success"):
            raise ValueError(f"Failed to upload file: {upload_result.get('error', 'Unknown error')}")
        
        file_key = upload_result["file_key"]
        file_size = upload_result.get("file_size", file_size)
        storage_backend = upload_result.get("storage_backend", "gcs")
        
        # Create resume record
        resume = CandidateResumeService.create_resume(
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            file_key=file_key,
            storage_backend=storage_backend,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime_type,
            is_primary=is_primary,
            uploaded_by_user_id=uploaded_by_user_id,
            uploaded_by_candidate=uploaded_by_candidate,
        )
        
        return resume, file_key
    
    @staticmethod
    def set_primary(resume_id: int, tenant_id: int) -> CandidateResume:
        """
        Set a resume as primary for its candidate.
        
        Args:
            resume_id: Resume ID to set as primary
            tenant_id: Tenant ID for multi-tenant isolation
            
        Returns:
            Updated CandidateResume
            
        Raises:
            ValueError: If resume not found
        """
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        if not resume:
            raise ValueError(f"Resume {resume_id} not found")
        
        # Unset other primaries for this candidate
        CandidateResumeService._unset_primary_for_candidate(
            resume.candidate_id, tenant_id, exclude_id=resume_id
        )
        
        # Set this one as primary
        resume.is_primary = True
        db.session.commit()
        
        logger.info(f"Set resume {resume_id} as primary for candidate {resume.candidate_id}")
        
        return resume
    
    @staticmethod
    def _unset_primary_for_candidate(
        candidate_id: int, 
        tenant_id: int, 
        exclude_id: Optional[int] = None
    ) -> None:
        """
        Unset is_primary for all resumes of a candidate.
        
        Args:
            candidate_id: Candidate ID
            tenant_id: Tenant ID
            exclude_id: Resume ID to exclude from unsetting
        """
        stmt = select(CandidateResume).where(
            and_(
                CandidateResume.candidate_id == candidate_id,
                CandidateResume.tenant_id == tenant_id,
                CandidateResume.is_primary == True
            )
        )
        if exclude_id:
            stmt = stmt.where(CandidateResume.id != exclude_id)
        
        for resume in db.session.scalars(stmt):
            resume.is_primary = False
        
        db.session.flush()
    
    @staticmethod
    def update_processing_status(
        resume_id: int,
        status: str,
        error: Optional[str] = None,
        parsed_data: Optional[dict] = None,
        polished_data: Optional[dict] = None,
    ) -> Optional[CandidateResume]:
        """
        Update the processing status of a resume.
        
        Args:
            resume_id: Resume ID
            status: New status ('pending', 'processing', 'completed', 'failed')
            error: Error message if failed
            parsed_data: Parsed resume data
            polished_data: Polished resume data
            
        Returns:
            Updated CandidateResume or None if not found
        """
        resume = db.session.get(CandidateResume, resume_id)
        if not resume:
            return None
        
        resume.processing_status = status
        resume.processing_error = error
        
        if parsed_data is not None:
            resume.parsed_resume_data = parsed_data
        
        if polished_data is not None:
            resume.polished_resume_data = polished_data
        
        if status == 'completed':
            resume.processed_at = datetime.utcnow()
        
        db.session.commit()
        
        return resume
    
    @staticmethod
    def delete_resume(resume_id: int, tenant_id: int) -> bool:
        """
        Delete a resume and its corresponding CandidateDocument record.
        
        Args:
            resume_id: Resume ID
            tenant_id: Tenant ID for multi-tenant isolation
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If trying to delete the only resume or primary without replacement
        """
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        if not resume:
            return False
        
        candidate_id = resume.candidate_id
        was_primary = resume.is_primary
        file_key = resume.file_key
        
        # Check if this is the only resume
        count = db.session.scalar(
            select(db.func.count(CandidateResume.id)).where(
                and_(
                    CandidateResume.candidate_id == candidate_id,
                    CandidateResume.tenant_id == tenant_id
                )
            )
        )
        
        if count == 1:
            raise ValueError("Cannot delete the only resume for a candidate")
        
        # Delete the file from storage
        try:
            storage_service = FileStorageService()
            storage_service.delete_file(file_key)
        except Exception as e:
            logger.warning(f"Failed to delete resume file {file_key}: {e}")
        
        # Find and delete matching CandidateDocument record (linked by file_key)
        # This prevents orphan document records when resume is deleted
        doc_stmt = select(CandidateDocument).where(
            and_(
                CandidateDocument.file_key == file_key,
                CandidateDocument.tenant_id == tenant_id,
                CandidateDocument.candidate_id == candidate_id
            )
        )
        matching_doc = db.session.scalar(doc_stmt)
        if matching_doc:
            db.session.delete(matching_doc)
            logger.info(f"Deleted matching CandidateDocument {matching_doc.id} for resume {resume_id}")
        
        # Delete the resume record
        db.session.delete(resume)
        
        # If was primary, set another as primary before committing
        if was_primary:
            # Find the next most recent resume to set as primary
            next_primary_stmt = select(CandidateResume).where(
                and_(
                    CandidateResume.candidate_id == candidate_id,
                    CandidateResume.tenant_id == tenant_id,
                    CandidateResume.id != resume_id
                )
            ).order_by(CandidateResume.created_at.desc()).limit(1)
            other_resume = db.session.scalar(next_primary_stmt)
            if other_resume:
                other_resume.is_primary = True
                logger.info(f"Set resume {other_resume.id} as new primary after deletion")
        
        # Single commit for all changes (resume delete, document delete, primary update)
        db.session.commit()
        db.session.expire_all()
        
        logger.info(f"Deleted resume {resume_id} for candidate {candidate_id}")
        
        return True
    
    @staticmethod
    def get_resume_download_url(resume_id: int, tenant_id: int) -> Optional[str]:
        """
        Get a signed download URL for a resume.
        
        Args:
            resume_id: Resume ID
            tenant_id: Tenant ID for multi-tenant isolation
            
        Returns:
            Signed URL or None if not found
        """
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        if not resume:
            return None
        
        storage_service = FileStorageService()
        signed_url, error = storage_service.generate_signed_url(resume.file_key)
        
        if error:
            logger.warning(f"Failed to generate signed URL for resume {resume_id}: {error}")
            # Fallback to download endpoint
            return f"/api/portal/candidates/{resume.candidate_id}/resumes/{resume_id}/download"
        
        return signed_url
    
    @staticmethod
    def update_polished_resume(
        resume_id: int,
        candidate_id: int,
        tenant_id: int,
        markdown_content: str,
    ) -> CandidateResume:
        """
        Update the polished/formatted version of a resume.
        
        Args:
            resume_id: Resume ID
            candidate_id: Candidate ID (for validation)
            tenant_id: Tenant ID for multi-tenant isolation
            markdown_content: Updated markdown content
            
        Returns:
            Updated CandidateResume
            
        Raises:
            ValueError: If resume not found or doesn't belong to candidate
        """
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        
        if not resume or resume.candidate_id != candidate_id:
            raise ValueError("Resume not found")
        
        polished_data = resume.polished_resume_data or {}
        polished_data['markdown_content'] = markdown_content
        polished_data['manually_edited'] = True
        
        resume.set_polished_resume(markdown_content)
        db.session.commit()
        
        logger.info(f"Updated polished resume {resume_id} for candidate {candidate_id}")
        
        return resume
    
    @staticmethod
    def regenerate_polished_resume(
        resume_id: int,
        candidate_id: int,
        tenant_id: int,
        candidate_name: str,
    ) -> CandidateResume:
        """
        Regenerate polished resume using AI from parsed data.
        
        Args:
            resume_id: Resume ID
            candidate_id: Candidate ID (for validation)
            tenant_id: Tenant ID for multi-tenant isolation
            candidate_name: Candidate's full name for personalization
            
        Returns:
            Updated CandidateResume with new polished data
            
        Raises:
            ValueError: If resume not found or no parsed data available
        """
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        
        if not resume or resume.candidate_id != candidate_id:
            raise ValueError("Resume not found")
        
        if not resume.parsed_resume_data:
            raise ValueError("No parsed resume data available. Please upload and parse a resume first.")
        
        from app.services.resume_polishing_service import ResumePolishingService
        
        service = ResumePolishingService()
        polished_data = service.polish_resume(
            parsed_data=resume.parsed_resume_data,
            candidate_name=candidate_name
        )
        
        resume.polished_resume_data = polished_data
        db.session.commit()
        db.session.refresh(resume)
        
        logger.info(f"Regenerated polished resume {resume_id} for candidate {candidate_id}")
        
        return resume
    
    @staticmethod
    def upload_resume_with_document(
        candidate_id: int,
        tenant_id: int,
        file: FileStorage,
        is_primary: bool,
        uploaded_by_user_id: int,
    ) -> Tuple[CandidateResume, CandidateDocument]:
        """
        Upload resume and create both CandidateResume and CandidateDocument records.
        This commits the transaction for Inngest worker compatibility.
        
        Args:
            candidate_id: Candidate ID
            tenant_id: Tenant ID
            file: Uploaded file
            is_primary: Whether this is the primary resume
            uploaded_by_user_id: Portal user who uploaded
            
        Returns:
            Tuple of (CandidateResume, CandidateDocument)
        """
        resume, file_key = CandidateResumeService.upload_and_create_resume(
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            file=file,
            is_primary=is_primary,
            uploaded_by_user_id=uploaded_by_user_id,
            uploaded_by_candidate=False,
        )
        
        resume_document = CandidateDocument(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            invitation_id=None,
            document_type='resume',
            file_name=file.filename or 'resume',
            file_key=file_key,
            file_size=resume.file_size or 0,
            mime_type=resume.mime_type or 'application/pdf',
            storage_backend=resume.storage_backend or 'gcs',
            uploaded_by_id=uploaded_by_user_id,
            is_verified=False,
        )
        db.session.add(resume_document)
        db.session.commit()
        
        logger.info(f"Uploaded resume {resume.id} and document {resume_document.id} for candidate {candidate_id}")
        
        return resume, resume_document

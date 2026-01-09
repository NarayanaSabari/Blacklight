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
        db.session.commit()
        
        logger.info(f"Created resume {resume.id} for candidate {candidate_id}, is_primary={is_primary}")
        
        return resume
    
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
        file_content = file.read()
        file_size = len(file_content)
        mime_type = file.content_type
        file.seek(0)  # Reset for storage
        
        # Upload to storage
        storage_service = FileStorageService()
        file_key = storage_service.upload_file(
            file_content=file_content,
            filename=original_filename,
            folder=f"resumes/tenant-{tenant_id}",
            content_type=mime_type
        )
        
        storage_backend = current_app.config.get('STORAGE_BACKEND', 'gcs')
        
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
        Delete a resume.
        
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
            storage_service.delete_file(resume.file_key)
        except Exception as e:
            logger.warning(f"Failed to delete resume file {resume.file_key}: {e}")
        
        # Delete the resume record
        db.session.delete(resume)
        db.session.commit()
        
        # If was primary, set another as primary
        if was_primary:
            other_resume = CandidateResumeService.get_primary_resume(candidate_id, tenant_id)
            if other_resume:
                other_resume.is_primary = True
                db.session.commit()
                logger.info(f"Set resume {other_resume.id} as new primary after deletion")
        
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
        
        if resume.storage_backend == 'gcs':
            return storage_service.get_signed_url(resume.file_key)
        else:
            # Local storage - return a relative path or local URL
            return f"/api/portal/candidates/{resume.candidate_id}/resumes/{resume_id}/download"

"""
Candidate Resume Model
Manages multiple resumes per candidate with primary resume support
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app import db
from app.models import BaseModel


class CandidateResume(BaseModel):
    """
    Resume model for candidate files.
    Supports multiple resumes per candidate with one primary resume.
    Each resume has its own parsed data and polished content.
    """
    __tablename__ = 'candidate_resumes'
    
    # Tenant relationship
    tenant_id = db.Column(Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Link to candidate
    candidate_id = db.Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # File storage
    file_key = db.Column(String(1000), nullable=False)  # GCS/local storage key
    storage_backend = db.Column(String(50), default='gcs')  # 'local' or 'gcs'
    original_filename = db.Column(String(500), nullable=False)  # Original uploaded filename
    file_size = db.Column(Integer)  # File size in bytes
    mime_type = db.Column(String(100))  # e.g., 'application/pdf'
    
    # Resume status
    is_primary = db.Column(Boolean, default=False, nullable=False, index=True)  # Only one primary per candidate
    processing_status = db.Column(String(50), default='pending', nullable=False, index=True)
    # Status values: pending, processing, completed, failed
    processing_error = db.Column(Text)  # Error message if processing failed
    
    # Parsed data (same structure as previous candidate fields)
    parsed_resume_data = db.Column(JSONB)  # Raw parsed data from AI
    
    # AI-Polished Resume Data (formatted markdown with metadata)
    # Structure:
    # {
    #     "markdown_content": "# John Doe\n\n## Professional Summary\n...",
    #     "polished_at": "2026-01-02T10:30:00Z",
    #     "polished_by": "ai",  // "ai" | "recruiter"
    #     "ai_model": "gemini-2.5-flash",
    #     "version": 1,
    #     "last_edited_at": null,
    #     "last_edited_by_user_id": null
    # }
    polished_resume_data = db.Column(JSONB)
    
    # Upload metadata
    uploaded_by_user_id = db.Column(Integer, ForeignKey('portal_users.id'))  # NULL if uploaded by candidate
    uploaded_by_candidate = db.Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    uploaded_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = db.Column(DateTime)  # When parsing completed
    
    # Relationships
    tenant = relationship('Tenant', backref='candidate_resumes')
    candidate = relationship('Candidate', back_populates='resumes', foreign_keys=[candidate_id])
    uploaded_by = relationship('PortalUser', foreign_keys=[uploaded_by_user_id], backref='uploaded_resumes')
    
    def __repr__(self):
        return f'<CandidateResume {self.id} - {self.original_filename} (primary={self.is_primary})>'
    
    @property
    def polished_resume_markdown(self) -> str:
        """Get the polished resume markdown content."""
        if self.polished_resume_data:
            return self.polished_resume_data.get("markdown_content", "")
        return ""
    
    @property
    def has_polished_resume(self) -> bool:
        """Check if resume has been polished."""
        return bool(
            self.polished_resume_data
            and self.polished_resume_data.get("markdown_content")
        )
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0.0
    
    @property
    def file_extension(self) -> str:
        """Extract file extension from filename"""
        if self.original_filename and '.' in self.original_filename:
            return self.original_filename.rsplit('.', 1)[1].lower()
        return ''
    
    def set_polished_resume(
        self,
        markdown_content: str,
        polished_by: str = "ai",
        ai_model: str = None,
        user_id: int = None,
    ) -> None:
        """
        Set or update the polished resume data.

        Args:
            markdown_content: The polished markdown content
            polished_by: Who polished it ("ai" or "recruiter")
            ai_model: AI model used (if polished by AI)
            user_id: User ID (if edited by recruiter)
        """
        current_version = 1
        if self.polished_resume_data:
            current_version = self.polished_resume_data.get("version", 0) + 1

        now = datetime.utcnow().isoformat() + "Z"

        self.polished_resume_data = {
            "markdown_content": markdown_content,
            "polished_at": now if polished_by == "ai" else self.polished_resume_data.get("polished_at") if self.polished_resume_data else now,
            "polished_by": "ai" if polished_by == "ai" else self.polished_resume_data.get("polished_by", "ai") if self.polished_resume_data else polished_by,
            "ai_model": ai_model or (self.polished_resume_data.get("ai_model") if self.polished_resume_data else None),
            "version": current_version,
            "last_edited_at": now if polished_by == "recruiter" else None,
            "last_edited_by_user_id": user_id if polished_by == "recruiter" else None,
        }
    
    def to_dict(self, include_parsed_data: bool = False, include_polished_data: bool = False):
        """
        Convert resume to dictionary.
        
        Args:
            include_parsed_data: Include full parsed_resume_data (can be large)
            include_polished_data: Include full polished_resume_data
        """
        result = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'candidate_id': self.candidate_id,
            'file_key': self.file_key,
            'storage_backend': self.storage_backend,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_size_mb': self.file_size_mb,
            'file_extension': self.file_extension,
            'mime_type': self.mime_type,
            'is_primary': self.is_primary,
            'processing_status': self.processing_status,
            'processing_error': self.processing_error,
            'has_parsed_data': self.parsed_resume_data is not None,
            'has_polished_resume': self.has_polished_resume,
            'uploaded_by_user_id': self.uploaded_by_user_id,
            'uploaded_by_candidate': self.uploaded_by_candidate,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_parsed_data:
            result['parsed_resume_data'] = self.parsed_resume_data
            
        if include_polished_data:
            result['polished_resume_data'] = self.polished_resume_data
            result['polished_resume_markdown'] = self.polished_resume_markdown
            
        return result

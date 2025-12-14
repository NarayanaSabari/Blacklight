"""
Tailored Resume Model

Stores tailored resume versions created for specific candidate-job pairs.
Each record represents a single tailoring operation where a candidate's
resume is optimized to match a specific job description.
"""
from datetime import datetime
from decimal import Decimal
import enum
import uuid

from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime,
    DECIMAL, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship

from app import db
from app.models import BaseModel


class TailoredResumeStatus(enum.Enum):
    """Status of tailored resume generation"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TailoredResume(BaseModel):
    """
    Stores tailored resume versions.
    
    Each record represents a single tailoring operation for a 
    specific candidate-job combination.
    """
    __tablename__ = 'tailored_resumes'
    
    # UUID for external reference (avoids exposing auto-increment IDs)
    tailor_id = db.Column(String(36), unique=True, nullable=False, index=True)
    
    # Foreign Keys
    candidate_id = db.Column(
        Integer, 
        ForeignKey('candidates.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    job_posting_id = db.Column(
        Integer, 
        ForeignKey('job_postings.id', ondelete='SET NULL'), 
        nullable=True,  # Job can be deleted, keep history
        index=True
    )
    tenant_id = db.Column(
        Integer, 
        ForeignKey('tenants.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    created_by_user_id = db.Column(
        Integer, 
        ForeignKey('portal_users.id', ondelete='SET NULL'), 
        nullable=True
    )
    
    # Status & Processing
    status = db.Column(
        SQLEnum(TailoredResumeStatus),
        default=TailoredResumeStatus.PENDING,
        nullable=False,
        index=True
    )
    processing_error = db.Column(Text, nullable=True)
    processing_step = db.Column(String(50), nullable=True)  # Current step for progress
    processing_progress = db.Column(Integer, default=0)  # 0-100
    processing_started_at = db.Column(DateTime, nullable=True)
    processing_completed_at = db.Column(DateTime, nullable=True)
    processing_duration_seconds = db.Column(Integer, nullable=True)
    
    # Original Resume Content (markdown or text representation)
    original_resume_content = db.Column(Text, nullable=False)
    original_resume_keywords = db.Column(ARRAY(String), default=[])
    
    # Tailored Resume Content
    tailored_resume_content = db.Column(Text, nullable=True)  # Markdown format
    tailored_resume_html = db.Column(Text, nullable=True)  # Rendered HTML
    tailored_resume_keywords = db.Column(ARRAY(String), default=[])
    
    # Scoring (0.0000 - 1.0000)
    original_match_score = db.Column(DECIMAL(5, 4), nullable=True)
    tailored_match_score = db.Column(DECIMAL(5, 4), nullable=True)
    score_improvement = db.Column(DECIMAL(5, 4), nullable=True)
    
    # Job Keywords (for reference, even if job is deleted)
    job_title = db.Column(String(255), nullable=True)
    job_company = db.Column(String(255), nullable=True)
    job_keywords = db.Column(ARRAY(String), default=[])
    job_description_snippet = db.Column(Text, nullable=True)  # First 500 chars
    
    # Skill Analysis
    matched_skills = db.Column(ARRAY(String), default=[])
    missing_skills = db.Column(ARRAY(String), default=[])
    added_skills = db.Column(ARRAY(String), default=[])  # Skills added during tailoring
    
    # Improvements Made (JSONB array)
    improvements = db.Column(JSONB, default=[])
    # Structure:
    # [
    #     {
    #         "section": "Experience",
    #         "type": "keyword_addition",
    #         "description": "Added Django framework reference",
    #         "before": "Built REST APIs using FastAPI",
    #         "after": "Built REST APIs using FastAPI and Django"
    #     }
    # ]
    
    # Skill Comparison Details (JSONB array)
    skill_comparison = db.Column(JSONB, default=[])
    # Structure:
    # [
    #     {
    #         "skill": "python",
    #         "resume_mentions": 8,
    #         "job_mentions": 5,
    #         "status": "matched"  # matched, missing, extra
    #     }
    # ]
    
    # AI Provider Info
    ai_provider = db.Column(String(50), nullable=True)  # gemini
    ai_model = db.Column(String(100), nullable=True)  # gemini-2.5-flash
    iterations_used = db.Column(Integer, default=0)  # Number of LLM iterations
    
    # Options used (for reproducibility)
    options = db.Column(JSONB, default={})
    # Structure:
    # {
    #     "preserve_experience": true,
    #     "max_iterations": 5,
    #     "target_score": 0.85
    # }
    
    # Relationships
    candidate = relationship(
        'Candidate', 
        backref='tailored_resumes',
        lazy='joined'
    )
    job_posting = relationship(
        'JobPosting', 
        backref='tailored_resumes',
        lazy='joined'
    )
    tenant = relationship('Tenant', lazy='select')
    created_by = relationship('PortalUser', lazy='select')
    
    def __init__(self, **kwargs):
        """Initialize with auto-generated tailor_id if not provided."""
        if 'tailor_id' not in kwargs:
            kwargs['tailor_id'] = str(uuid.uuid4())
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f"<TailoredResume {self.tailor_id} candidate={self.candidate_id} job={self.job_posting_id}>"
    
    @property
    def is_complete(self) -> bool:
        """Check if tailoring is complete."""
        return self.status == TailoredResumeStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if tailoring failed."""
        return self.status == TailoredResumeStatus.FAILED
    
    @property
    def improvement_percentage(self) -> float:
        """Get improvement as percentage points."""
        if self.score_improvement:
            return float(self.score_improvement) * 100
        return 0.0
    
    def to_dict(self) -> dict:
        """Serialize for API response with flat structure for frontend."""
        # Convert 0-1 scores to 0-100 percentages for frontend
        original_score = float(self.original_match_score) * 100 if self.original_match_score else None
        tailored_score = float(self.tailored_match_score) * 100 if self.tailored_match_score else None
        improvement = float(self.score_improvement) * 100 if self.score_improvement else None
        
        return {
            # IDs
            "id": self.id,
            "tailor_id": self.tailor_id,
            "candidate_id": self.candidate_id,
            "job_posting_id": self.job_posting_id,
            
            # Content (flat structure for frontend)
            "original_resume_content": self.original_resume_content,
            "tailored_resume_content": self.tailored_resume_content,
            
            # Scores as percentages (0-100)
            "original_match_score": original_score,
            "tailored_match_score": tailored_score,
            "score_improvement": improvement,
            
            # Skills analysis (flat)
            "matched_skills": self.matched_skills or [],
            "missing_skills": self.missing_skills or [],
            "added_skills": self.added_skills or [],
            
            # Detailed data
            "improvements": self.improvements or [],
            "skill_comparison": self.skill_comparison or {},
            
            # Processing status
            "status": self.status.value if self.status else None,
            "processing_step": self.processing_step,
            "processing_progress": self.processing_progress,
            "error_message": self.processing_error,
            
            # Job info
            "job_title": self.job_title,
            "job_company": self.job_company,
            
            # Metadata
            "iterations_used": self.iterations_used,
            "ai_provider": self.ai_provider,
            "ai_model": self.ai_model,
            "processing_duration_seconds": self.processing_duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.processing_completed_at.isoformat() if self.processing_completed_at else None,
        }
    
    def to_list_dict(self) -> dict:
        """Serialize for list view (minimal data)."""
        # Convert 0-1 scores to 0-100 percentages
        original_score = float(self.original_match_score) * 100 if self.original_match_score else None
        tailored_score = float(self.tailored_match_score) * 100 if self.tailored_match_score else None
        improvement = float(self.score_improvement) * 100 if self.score_improvement else None
        
        return {
            "id": self.id,
            "tailor_id": self.tailor_id,
            "job_title": self.job_title,
            "job_company": self.job_company,
            "original_match_score": original_score,
            "tailored_match_score": tailored_score,
            "score_improvement": improvement,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def start_processing(self):
        """Mark as processing started."""
        self.status = TailoredResumeStatus.PROCESSING
        self.processing_started_at = datetime.utcnow()
        self.processing_progress = 0
    
    def update_progress(self, step: str, progress: int):
        """Update processing progress."""
        self.processing_step = step
        self.processing_progress = min(progress, 100)
    
    def complete(
        self,
        tailored_content: str,
        tailored_html: str,
        tailored_score: float,
        improvements: list,
        skill_comparison: list,
        iterations: int
    ):
        """Mark as completed with results."""
        self.status = TailoredResumeStatus.COMPLETED
        self.tailored_resume_content = tailored_content
        self.tailored_resume_html = tailored_html
        self.tailored_match_score = Decimal(str(tailored_score))
        self.score_improvement = self.tailored_match_score - (self.original_match_score or Decimal('0'))
        self.improvements = improvements
        self.skill_comparison = skill_comparison
        self.iterations_used = iterations
        self.processing_completed_at = datetime.utcnow()
        self.processing_progress = 100
        
        if self.processing_started_at:
            duration = (self.processing_completed_at - self.processing_started_at).total_seconds()
            self.processing_duration_seconds = int(duration)
    
    def fail(self, error: str):
        """Mark as failed with error."""
        self.status = TailoredResumeStatus.FAILED
        self.processing_error = error
        self.processing_completed_at = datetime.utcnow()
        
        if self.processing_started_at:
            duration = (self.processing_completed_at - self.processing_started_at).total_seconds()
            self.processing_duration_seconds = int(duration)

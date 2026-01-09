"""
Candidate Resume schemas for request/response validation
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ==================== Response Schemas ====================

class CandidateResumeResponseSchema(BaseModel):
    """Schema for candidate resume response"""
    
    id: int
    tenant_id: int
    candidate_id: int
    
    # File info
    file_key: str
    storage_backend: Optional[str] = "gcs"
    original_filename: str
    file_size: Optional[int] = None
    file_size_mb: Optional[float] = None
    file_extension: Optional[str] = None
    mime_type: Optional[str] = None
    
    # Status
    is_primary: bool = False
    processing_status: str = "pending"  # pending, processing, completed, failed
    processing_error: Optional[str] = None
    
    # Document verification status (from CandidateDocument if exists)
    is_verified: Optional[bool] = None
    
    # Data flags (don't include full data by default)
    has_parsed_data: bool = False
    has_polished_resume: bool = False
    
    # Upload info
    uploaded_by_user_id: Optional[int] = None
    uploaded_by_candidate: bool = False
    
    # Timestamps
    uploaded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CandidateResumeDetailSchema(CandidateResumeResponseSchema):
    """Schema for detailed candidate resume response (includes parsed/polished data)"""
    
    parsed_resume_data: Optional[Dict[str, Any]] = None
    polished_resume_data: Optional[Dict[str, Any]] = None
    polished_resume_markdown: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class CandidateResumeListSchema(BaseModel):
    """Schema for list of candidate resumes"""
    
    resumes: list[CandidateResumeResponseSchema]
    total: int
    primary_resume_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


# ==================== Request Schemas ====================

class CandidateResumeUploadSchema(BaseModel):
    """Schema for resume upload request (metadata only, file is multipart)"""
    
    is_primary: bool = Field(default=False, description="Set as primary resume")
    
    model_config = ConfigDict(from_attributes=True)


class SetPrimaryResumeSchema(BaseModel):
    """Schema for setting a resume as primary"""
    
    resume_id: int = Field(..., description="ID of the resume to set as primary")
    
    model_config = ConfigDict(from_attributes=True)


class ReprocessResumeSchema(BaseModel):
    """Schema for reprocessing a resume"""
    
    force: bool = Field(default=False, description="Force reprocess even if already processed")
    
    model_config = ConfigDict(from_attributes=True)


# ==================== Polished Resume Schemas ====================

class PolishedResumeUpdateSchema(BaseModel):
    """Schema for updating polished resume (recruiter edit)"""
    
    markdown_content: str = Field(..., min_length=1, description="Updated markdown content")
    
    model_config = ConfigDict(from_attributes=True)

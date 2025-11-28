"""
Candidate schemas for request/response validation
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


# ==================== Request Schemas ====================

class CandidateCreateSchema(BaseModel):
    """Schema for creating a candidate manually"""
    
    # Basic Info (required)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    
    # Contact Info (optional but recommended)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    
    # Enhanced Personal Info
    full_name: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    portfolio_url: Optional[str] = Field(None, max_length=500)
    
    # Professional Info
    current_title: Optional[str] = Field(None, max_length=200)
    total_experience_years: Optional[int] = Field(None, ge=0, le=70)
    notice_period: Optional[str] = Field(None, max_length=100)
    expected_salary: Optional[str] = Field(None, max_length=100)
    professional_summary: Optional[str] = None
    
    # Arrays
    preferred_locations: Optional[List[str]] = Field(default_factory=list)
    skills: Optional[List[str]] = Field(default_factory=list)
    certifications: Optional[List[str]] = Field(default_factory=list)
    languages: Optional[List[str]] = Field(default_factory=list)
    
    # JSONB data
    education: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    work_experience: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    
    # Metadata
    status: Optional[str] = Field(default='processing', max_length=50)  # Default for manual upload
    source: Optional[str] = Field(default='manual', max_length=100)
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is one of allowed values"""
        allowed = [
            'processing', 'pending_review', 'new', 'screening', 
            'interviewed', 'offered', 'hired', 'rejected', 'withdrawn', 
            'onboarded', 'ready_for_assignment'
        ]
        if v and v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v


class CandidateUpdateSchema(BaseModel):
    """Schema for updating a candidate"""
    
    # All fields optional for updates
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)  # Allow empty string
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    full_name: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    portfolio_url: Optional[str] = Field(None, max_length=500)
    current_title: Optional[str] = Field(None, max_length=200)
    total_experience_years: Optional[int] = Field(None, ge=0, le=70)
    notice_period: Optional[str] = Field(None, max_length=100)
    expected_salary: Optional[str] = Field(None, max_length=100)
    professional_summary: Optional[str] = None
    preferred_locations: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    education: Optional[List[Dict[str, Any]]] = None
    work_experience: Optional[List[Dict[str, Any]]] = None
    preferred_roles: Optional[List[str]] = None
    status: Optional[str] = Field(None, max_length=50)
    source: Optional[str] = Field(None, max_length=100)
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status is one of allowed values"""
        if v is None:
            return v
        allowed = [
            'processing', 'pending_review', 'new', 'screening', 
            'interviewed', 'offered', 'hired', 'rejected', 'withdrawn', 
            'onboarded', 'ready_for_assignment'
        ]
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v


class CandidateFilterSchema(BaseModel):
    """Schema for filtering candidates list"""
    
    status: Optional[str] = None
    skills: Optional[List[str]] = Field(default=None, description="Filter by skills (OR logic)")
    search: Optional[str] = Field(None, description="Search in name, email, title")
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    
    model_config = ConfigDict(from_attributes=True)


# ==================== Response Schemas ====================

class EducationSchema(BaseModel):
    """Schema for education entry"""
    
    degree: str
    field_of_study: Optional[str] = None
    institution: str
    graduation_year: Optional[int] = None
    gpa: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


class WorkExperienceSchema(BaseModel):
    """Schema for work experience entry"""
    
    title: str
    company: str
    location: Optional[str] = None
    start_date: Optional[str] = None  # Format: YYYY-MM
    end_date: Optional[str] = None  # Format: YYYY-MM or 'Present'
    is_current: bool = False
    description: Optional[str] = None
    duration_months: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class CandidateResponseSchema(BaseModel):
    """Schema for candidate response"""
    
    # IDs
    id: int
    tenant_id: int
    
    # Basic Info
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    
    # Resume Info
    resume_file_key: Optional[str] = None
    resume_storage_backend: Optional[str] = None
    resume_uploaded_at: Optional[datetime] = None
    resume_parsed_at: Optional[datetime] = None
    # Note: Signed resume URLs are now available via the dedicated endpoint /api/candidates/<id>/resume-url
    
    # Enhanced Personal Info
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    
    # Professional Info
    current_title: Optional[str] = None
    total_experience_years: Optional[int] = None
    notice_period: Optional[str] = None
    expected_salary: Optional[str] = None
    professional_summary: Optional[str] = None
    
    # Arrays - handle None from database
    preferred_locations: Optional[List[str]] = Field(default_factory=list)
    skills: Optional[List[str]] = Field(default_factory=list)
    certifications: Optional[List[str]] = Field(default_factory=list)
    languages: Optional[List[str]] = Field(default_factory=list)
    preferred_roles: Optional[List[str]] = Field(default_factory=list)
    
    # JSONB data
    education: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    work_experience: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    parsed_resume_data: Optional[Dict[str, Any]] = None
    suggested_roles: Optional[Dict[str, Any]] = None
    
    # Metadata
    status: str
    source: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('preferred_locations', 'skills', 'certifications', 'languages', 'preferred_roles', 'education', 'work_experience', mode='before')
    @classmethod
    def convert_none_to_empty_list(cls, v):
        """Convert None to empty list for array fields"""
        return v if v is not None else []


class CandidateListItemSchema(BaseModel):
    """Schema for candidate in list view (lightweight)"""
    
    id: int
    tenant_id: int
    first_name: str
    last_name: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    current_title: Optional[str] = None
    location: Optional[str] = None
    total_experience_years: Optional[int] = None
    skills: Optional[List[str]] = Field(default_factory=list)
    status: str
    source: str
    resume_uploaded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('skills', mode='before')
    @classmethod
    def convert_none_to_empty_list(cls, v):
        """Convert None to empty list for skills"""
        return v if v is not None else []


class CandidateListResponseSchema(BaseModel):
    """Schema for paginated candidates list"""
    
    candidates: List[CandidateListItemSchema]
    total: int
    page: int
    per_page: int
    pages: int
    
    model_config = ConfigDict(from_attributes=True)


class UploadResumeResponseSchema(BaseModel):
    """Schema for resume upload response"""
    
    candidate_id: Optional[int] = None
    status: str  # 'success' or 'error'
    message: Optional[str] = None
    error: Optional[str] = None
    
    # File info
    file_info: Optional[Dict[str, Any]] = None
    
    # Parsed data
    parsed_data: Optional[Dict[str, Any]] = None
    
    # Extraction metadata
    extracted_metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class ReparseResumeResponseSchema(BaseModel):
    """Schema for resume reparse response"""
    
    candidate_id: int
    status: str  # 'success' or 'error'
    message: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class CandidateStatsSchema(BaseModel):
    """Schema for candidate statistics"""
    
    total_candidates: int
    by_status: Dict[str, int]
    recent_uploads: int  # Last 7 days
    
    model_config = ConfigDict(from_attributes=True)

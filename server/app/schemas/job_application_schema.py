"""
Pydantic schemas for Job Application validation and serialization.
Handles application tracking and status management.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class JobApplicationBase(BaseModel):
    """Base schema for job application shared fields"""
    application_status: Optional[str] = Field(default="APPLIED", max_length=50, description="Application status")
    applied_via: Optional[str] = Field(None, max_length=100, description="Application method (portal, email, direct)")
    cover_letter: Optional[str] = Field(None, description="Cover letter text")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @field_validator('application_status')
    @classmethod
    def validate_status(cls, v):
        """Validate application status"""
        valid_statuses = [
            "APPLIED", "SCREENING", "INTERVIEWING", "OFFER", 
            "ACCEPTED", "REJECTED", "WITHDRAWN"
        ]
        if v and v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class JobApplicationCreate(JobApplicationBase):
    """Schema for creating a new job application"""
    candidate_id: int = Field(..., gt=0, description="Candidate ID")
    job_posting_id: int = Field(..., gt=0, description="Job posting ID")
    applied_by_user_id: Optional[int] = Field(None, gt=0, description="User who applied (recruiter/manager)")


class JobApplicationUpdate(BaseModel):
    """Schema for updating an existing application"""
    application_status: Optional[str] = Field(None, max_length=50, description="Application status")
    cover_letter: Optional[str] = Field(None, description="Cover letter text")
    notes: Optional[str] = Field(None, description="Additional notes")
    feedback: Optional[str] = Field(None, description="Feedback from employer")
    
    @field_validator('application_status')
    @classmethod
    def validate_status(cls, v):
        """Validate application status"""
        if v:
            valid_statuses = [
                "APPLIED", "SCREENING", "INTERVIEWING", "OFFER", 
                "ACCEPTED", "REJECTED", "WITHDRAWN"
            ]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v
    
    model_config = ConfigDict(extra='forbid')


class JobApplicationResponse(JobApplicationBase):
    """Schema for job application response"""
    id: int = Field(..., description="Application ID")
    candidate_id: int = Field(..., description="Candidate ID")
    job_posting_id: int = Field(..., description="Job posting ID")
    applied_by_user_id: Optional[int] = Field(None, description="User who applied")
    applied_at: datetime = Field(..., description="Application timestamp")
    screened_at: Optional[datetime] = Field(None, description="Screening timestamp")
    interviewed_at: Optional[datetime] = Field(None, description="Interview timestamp")
    offer_received_at: Optional[datetime] = Field(None, description="Offer received timestamp")
    offer_accepted_at: Optional[datetime] = Field(None, description="Offer accepted timestamp")
    rejected_at: Optional[datetime] = Field(None, description="Rejection timestamp")
    feedback: Optional[str] = Field(None, description="Employer feedback")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Computed fields from model properties
    days_since_applied: Optional[int] = Field(None, description="Days since application")
    is_active: Optional[bool] = Field(None, description="Is application still active")
    
    # Related data (populated from joins)
    job_title: Optional[str] = Field(None, description="Job title")
    company: Optional[str] = Field(None, description="Company name")
    location: Optional[str] = Field(None, description="Job location")
    candidate_name: Optional[str] = Field(None, description="Candidate name")
    applied_by_name: Optional[str] = Field(None, description="Name of user who applied")
    
    model_config = ConfigDict(from_attributes=True)


class JobApplicationWithDetails(JobApplicationResponse):
    """Schema for application response with full job and candidate details"""
    from app.schemas.job_posting_schema import JobPostingResponse
    from app.schemas.candidate_schema import CandidateResponseSchema
    
    job_details: Optional[JobPostingResponse] = Field(None, description="Full job details")
    candidate_details: Optional[CandidateResponseSchema] = Field(None, description="Full candidate details")


class JobApplicationListResponse(BaseModel):
    """Schema for paginated application list"""
    applications: List[JobApplicationResponse] = Field(..., description="List of applications")
    total: int = Field(..., ge=0, description="Total number of applications")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")


class JobApplicationSearchRequest(BaseModel):
    """Schema for application search request"""
    candidate_id: Optional[int] = Field(None, gt=0, description="Filter by candidate")
    job_posting_id: Optional[int] = Field(None, gt=0, description="Filter by job")
    applied_by_user_id: Optional[int] = Field(None, gt=0, description="Filter by user who applied")
    application_status: Optional[str] = Field(None, max_length=50, description="Filter by status")
    applied_after: Optional[datetime] = Field(None, description="Filter applications after date")
    applied_before: Optional[datetime] = Field(None, description="Filter applications before date")
    is_active: Optional[bool] = Field(None, description="Filter active/inactive applications")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default="applied_at", description="Sort field")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")


class JobApplicationStatusUpdate(BaseModel):
    """Schema for updating application status with timeline"""
    status: str = Field(..., max_length=50, description="New status")
    notes: Optional[str] = Field(None, description="Status update notes")
    feedback: Optional[str] = Field(None, description="Employer feedback")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate application status"""
        valid_statuses = [
            "APPLIED", "SCREENING", "INTERVIEWING", "OFFER", 
            "ACCEPTED", "REJECTED", "WITHDRAWN"
        ]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class ApplicationTimeline(BaseModel):
    """Schema for application timeline/history"""
    status: str = Field(..., description="Status name")
    timestamp: Optional[datetime] = Field(None, description="When status was reached")
    is_current: bool = Field(..., description="Is this the current status")
    is_completed: bool = Field(..., description="Has this status been reached")


class JobApplicationStatsResponse(BaseModel):
    """Schema for job application statistics"""
    total_applications: int = Field(..., ge=0, description="Total number of applications")
    active_applications: int = Field(..., ge=0, description="Active applications")
    applications_by_status: dict = Field(..., description="Application counts by status")
    applications_this_week: int = Field(..., ge=0, description="Applications this week")
    applications_this_month: int = Field(..., ge=0, description="Applications this month")
    avg_time_to_offer: Optional[float] = Field(None, description="Average days to offer")
    success_rate: Optional[float] = Field(None, description="Offer acceptance rate")
    top_applied_companies: List[dict] = Field(default_factory=list, description="Most applied companies")
    applications_by_platform: dict = Field(..., description="Application counts by platform")

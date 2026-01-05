"""
Submission schemas for request/response validation.
Handles submission tracking for the ATS functionality.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, ConfigDict, EmailStr


# ==================== Constants ====================

SUBMISSION_STATUSES = [
    'SUBMITTED', 'CLIENT_REVIEW', 'INTERVIEW_SCHEDULED',
    'INTERVIEWED', 'OFFERED', 'PLACED',
    'REJECTED', 'WITHDRAWN', 'ON_HOLD'
]

RATE_TYPES = ['HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', 'ANNUAL']

INTERVIEW_TYPES = ['PHONE', 'VIDEO', 'ONSITE', 'TECHNICAL', 'HR', 'PANEL']

PRIORITY_LEVELS = ['HIGH', 'MEDIUM', 'LOW']

ACTIVITY_TYPES = [
    'CREATED', 'STATUS_CHANGE', 'NOTE', 'EMAIL_SENT',
    'EMAIL_RECEIVED', 'CALL_LOGGED', 'INTERVIEW_SCHEDULED',
    'INTERVIEW_COMPLETED', 'INTERVIEW_CANCELLED', 'RATE_UPDATED',
    'VENDOR_UPDATED', 'PRIORITY_CHANGED', 'FOLLOW_UP_SET',
    'RESUME_SENT', 'CLIENT_FEEDBACK'
]


# ==================== Request Schemas ====================

class SubmissionCreateSchema(BaseModel):
    """Schema for creating a new submission."""
    
    # Required fields
    candidate_id: int = Field(..., description="ID of the candidate being submitted")
    job_posting_id: int = Field(..., description="ID of the job posting")
    
    # Vendor/Client info (important for bench recruiters)
    vendor_company: Optional[str] = Field(None, max_length=255)
    vendor_contact_name: Optional[str] = Field(None, max_length=255)
    vendor_contact_email: Optional[EmailStr] = None
    vendor_contact_phone: Optional[str] = Field(None, max_length=50)
    client_company: Optional[str] = Field(None, max_length=255)
    
    # Rate information
    bill_rate: Optional[float] = Field(None, ge=0, description="Bill rate ($/hr)")
    pay_rate: Optional[float] = Field(None, ge=0, description="Pay rate ($/hr)")
    rate_type: Optional[str] = Field(default='HOURLY', max_length=20)
    currency: Optional[str] = Field(default='USD', max_length=10)
    
    # Submission details
    submission_notes: Optional[str] = None
    cover_letter: Optional[str] = None
    tailored_resume_id: Optional[int] = None
    
    # Priority
    priority: Optional[str] = Field(default='MEDIUM', max_length=20)
    is_hot: Optional[bool] = Field(default=False)
    follow_up_date: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('rate_type')
    @classmethod
    def validate_rate_type(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in RATE_TYPES:
            raise ValueError(f"Rate type must be one of: {', '.join(RATE_TYPES)}")
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in PRIORITY_LEVELS:
            raise ValueError(f"Priority must be one of: {', '.join(PRIORITY_LEVELS)}")
        return v


class ExternalSubmissionCreateSchema(BaseModel):
    """Schema for creating a submission to an external job (not in portal)."""
    
    # Required fields
    candidate_id: int = Field(..., description="ID of the candidate being submitted")
    
    # External job info (required for external submissions)
    external_job_title: str = Field(..., min_length=1, max_length=255, description="Job title")
    external_job_company: str = Field(..., min_length=1, max_length=255, description="Company name")
    external_job_location: Optional[str] = Field(None, max_length=255)
    external_job_url: Optional[str] = Field(None, max_length=1000, description="URL to the original job posting")
    external_job_description: Optional[str] = Field(None, description="Brief description or notes about the job")
    
    # Vendor/Client info (important for bench recruiters)
    vendor_company: Optional[str] = Field(None, max_length=255)
    vendor_contact_name: Optional[str] = Field(None, max_length=255)
    vendor_contact_email: Optional[EmailStr] = None
    vendor_contact_phone: Optional[str] = Field(None, max_length=50)
    client_company: Optional[str] = Field(None, max_length=255)
    
    # Rate information
    bill_rate: Optional[float] = Field(None, ge=0, description="Bill rate ($/hr)")
    pay_rate: Optional[float] = Field(None, ge=0, description="Pay rate ($/hr)")
    rate_type: Optional[str] = Field(default='HOURLY', max_length=20)
    currency: Optional[str] = Field(default='USD', max_length=10)
    
    # Submission details
    submission_notes: Optional[str] = None
    
    # Priority
    priority: Optional[str] = Field(default='MEDIUM', max_length=20)
    is_hot: Optional[bool] = Field(default=False)
    follow_up_date: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('rate_type')
    @classmethod
    def validate_rate_type(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in RATE_TYPES:
            raise ValueError(f"Rate type must be one of: {', '.join(RATE_TYPES)}")
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in PRIORITY_LEVELS:
            raise ValueError(f"Priority must be one of: {', '.join(PRIORITY_LEVELS)}")
        return v


class SubmissionUpdateSchema(BaseModel):
    """Schema for updating an existing submission."""
    
    # Vendor/Client info
    vendor_company: Optional[str] = Field(None, max_length=255)
    vendor_contact_name: Optional[str] = Field(None, max_length=255)
    vendor_contact_email: Optional[EmailStr] = None
    vendor_contact_phone: Optional[str] = Field(None, max_length=50)
    client_company: Optional[str] = Field(None, max_length=255)
    
    # Rate information
    bill_rate: Optional[float] = Field(None, ge=0)
    pay_rate: Optional[float] = Field(None, ge=0)
    rate_type: Optional[str] = Field(None, max_length=20)
    currency: Optional[str] = Field(None, max_length=10)
    
    # Submission details
    submission_notes: Optional[str] = None
    cover_letter: Optional[str] = None
    tailored_resume_id: Optional[int] = None
    
    # Interview info
    interview_scheduled_at: Optional[datetime] = None
    interview_type: Optional[str] = Field(None, max_length=50)
    interview_location: Optional[str] = Field(None, max_length=500)
    interview_notes: Optional[str] = None
    interview_feedback: Optional[str] = None
    
    # Priority
    priority: Optional[str] = Field(None, max_length=20)
    is_hot: Optional[bool] = None
    follow_up_date: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('rate_type')
    @classmethod
    def validate_rate_type(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in RATE_TYPES:
            raise ValueError(f"Rate type must be one of: {', '.join(RATE_TYPES)}")
        return v
    
    @field_validator('interview_type')
    @classmethod
    def validate_interview_type(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in INTERVIEW_TYPES:
            raise ValueError(f"Interview type must be one of: {', '.join(INTERVIEW_TYPES)}")
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in PRIORITY_LEVELS:
            raise ValueError(f"Priority must be one of: {', '.join(PRIORITY_LEVELS)}")
        return v


class SubmissionStatusUpdateSchema(BaseModel):
    """Schema for updating submission status."""
    
    status: str = Field(..., max_length=50)
    note: Optional[str] = Field(None, description="Optional note about the status change")
    
    # Status-specific fields
    rejection_reason: Optional[str] = None
    rejection_stage: Optional[str] = Field(None, max_length=50)
    withdrawal_reason: Optional[str] = None
    
    # For placement status
    placement_start_date: Optional[datetime] = None
    placement_end_date: Optional[datetime] = None
    placement_duration_months: Optional[int] = Field(None, ge=1)
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in SUBMISSION_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(SUBMISSION_STATUSES)}")
        return v


class SubmissionInterviewScheduleSchema(BaseModel):
    """Schema for scheduling an interview."""
    
    interview_scheduled_at: datetime = Field(..., description="Interview date and time")
    interview_type: str = Field(..., max_length=50)
    interview_location: Optional[str] = Field(None, max_length=500)
    interview_notes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('interview_type')
    @classmethod
    def validate_interview_type(cls, v: str) -> str:
        if v not in INTERVIEW_TYPES:
            raise ValueError(f"Interview type must be one of: {', '.join(INTERVIEW_TYPES)}")
        return v


class SubmissionActivityCreateSchema(BaseModel):
    """Schema for creating a submission activity/note."""
    
    activity_type: str = Field(default='NOTE', max_length=50)
    content: str = Field(..., min_length=1, description="Note content or activity description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('activity_type')
    @classmethod
    def validate_activity_type(cls, v: str) -> str:
        if v not in ACTIVITY_TYPES:
            raise ValueError(f"Activity type must be one of: {', '.join(ACTIVITY_TYPES)}")
        return v


class SubmissionFilterSchema(BaseModel):
    """Schema for filtering submissions list."""
    
    status: Optional[str] = None
    statuses: Optional[List[str]] = None  # Multiple statuses
    candidate_id: Optional[int] = None
    job_posting_id: Optional[int] = None
    submitted_by_user_id: Optional[int] = None
    vendor_company: Optional[str] = None
    client_company: Optional[str] = None
    priority: Optional[str] = None
    is_hot: Optional[bool] = None
    is_active: Optional[bool] = None  # Filter active (non-terminal) submissions
    
    # Date filters
    submitted_after: Optional[datetime] = None
    submitted_before: Optional[datetime] = None
    interview_after: Optional[datetime] = None
    interview_before: Optional[datetime] = None
    
    # Pagination
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    
    # Sorting
    sort_by: Optional[str] = Field(default='submitted_at')
    sort_order: Optional[str] = Field(default='desc')
    
    model_config = ConfigDict(from_attributes=True)


# ==================== Response Schemas ====================

class SubmissionCandidateResponse(BaseModel):
    """Nested candidate info in submission response."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    current_title: Optional[str] = None
    skills: Optional[List[str]] = None
    location: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SubmissionJobResponse(BaseModel):
    """Nested job info in submission response."""
    id: Optional[int] = None  # None for external jobs
    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    is_remote: Optional[bool] = None
    platform: Optional[str] = None  # 'external' for external jobs
    job_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SubmissionUserResponse(BaseModel):
    """Nested user info in submission response."""
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SubmissionActivityResponse(BaseModel):
    """Response schema for submission activity."""
    id: int
    submission_id: int
    activity_type: str
    content: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    created_by_id: Optional[int] = None
    created_by: Optional[SubmissionUserResponse] = None
    
    model_config = ConfigDict(from_attributes=True)


class SubmissionResponse(BaseModel):
    """Response schema for a submission."""
    id: int
    candidate_id: int
    job_posting_id: Optional[int] = None  # Nullable for external jobs
    submitted_by_user_id: Optional[int] = None
    tenant_id: int
    
    # External job info
    is_external_job: bool = False
    external_job_title: Optional[str] = None
    external_job_company: Optional[str] = None
    external_job_location: Optional[str] = None
    external_job_url: Optional[str] = None
    external_job_description: Optional[str] = None
    
    # Status
    status: str
    status_changed_at: Optional[datetime] = None
    
    # Vendor info
    vendor_company: Optional[str] = None
    vendor_contact_name: Optional[str] = None
    vendor_contact_email: Optional[str] = None
    vendor_contact_phone: Optional[str] = None
    client_company: Optional[str] = None
    
    # Rates
    bill_rate: Optional[float] = None
    pay_rate: Optional[float] = None
    rate_type: Optional[str] = None
    currency: Optional[str] = None
    margin: Optional[float] = None
    margin_percentage: Optional[float] = None
    
    # Notes
    submission_notes: Optional[str] = None
    tailored_resume_id: Optional[int] = None
    
    # Interview
    interview_scheduled_at: Optional[datetime] = None
    interview_type: Optional[str] = None
    interview_location: Optional[str] = None
    interview_notes: Optional[str] = None
    interview_feedback: Optional[str] = None
    
    # Outcome
    rejection_reason: Optional[str] = None
    rejection_stage: Optional[str] = None
    withdrawal_reason: Optional[str] = None
    
    # Placement
    placement_start_date: Optional[datetime] = None
    placement_end_date: Optional[datetime] = None
    placement_duration_months: Optional[int] = None
    
    # Priority
    priority: Optional[str] = None
    is_hot: Optional[bool] = None
    follow_up_date: Optional[datetime] = None
    
    # Timestamps
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime
    
    # Days since submitted (computed)
    days_since_submitted: Optional[int] = None
    is_active: Optional[bool] = None
    
    # Nested objects (optional)
    candidate: Optional[SubmissionCandidateResponse] = None
    job: Optional[SubmissionJobResponse] = None
    submitted_by: Optional[SubmissionUserResponse] = None
    activities: Optional[List[SubmissionActivityResponse]] = None
    
    model_config = ConfigDict(from_attributes=True)


class SubmissionListResponse(BaseModel):
    """Response schema for paginated submission list."""
    items: List[SubmissionResponse]
    total: int
    page: int
    per_page: int
    pages: int
    
    model_config = ConfigDict(from_attributes=True)


class SubmissionStatsResponse(BaseModel):
    """Response schema for submission statistics."""
    total: int
    by_status: Dict[str, int]
    submitted_this_week: int
    submitted_this_month: int
    interviews_scheduled: int
    placements_this_month: int
    average_days_to_placement: Optional[float] = None
    interview_rate: Optional[float] = None  # % of submissions that got interviews
    placement_rate: Optional[float] = None  # % of submissions that got placed
    
    model_config = ConfigDict(from_attributes=True)

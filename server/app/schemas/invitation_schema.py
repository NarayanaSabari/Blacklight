"""
Candidate Invitation Schemas
Pydantic models for request/response validation
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field, field_validator


class InvitationCreateSchema(BaseModel):
    """Schema for creating a new invitation"""
    email: EmailStr = Field(..., description="Candidate email address")
    first_name: Optional[str] = Field(None, max_length=100, description="Candidate first name")
    last_name: Optional[str] = Field(None, max_length=100, description="Candidate last name")
    position: Optional[str] = Field(None, max_length=255, description="Position or role for the candidate")
    recruiter_notes: Optional[str] = Field(None, description="Internal notes for the HR team")
    expiry_hours: int = Field(168, ge=1, le=720, description="Hours until invitation expires (1-720, default 7 days)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "candidate@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "expiry_hours": 168
            }
        }


class InvitationResendSchema(BaseModel):
    """Schema for resending an invitation"""
    expiry_hours: int = Field(168, ge=1, le=720, description="New expiry hours (default 7 days)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "expiry_hours": 48
            }
        }


class InvitationSubmitSchema(BaseModel):
    """Schema for candidate submitting their information"""
    # Personal Information
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    location: Optional[str] = Field(None, max_length=200)
    
    # Address (optional for initial submission)
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    zip_code: Optional[str] = Field(None, max_length=10)
    country: Optional[str] = Field("United States", max_length=100)
    
    # Professional Information
    position: Optional[str] = Field(None, max_length=200)
    current_job_title: Optional[str] = Field(None, max_length=200)
    current_employer: Optional[str] = Field(None, max_length=200)
    experience_years: Optional[int] = Field(None, ge=0, le=70)
    years_of_experience: Optional[int] = Field(None, ge=0, le=70)
    skills: Optional[List[str]] = Field(None, description="List of skills")
    preferred_roles: Optional[List[str]] = Field(None, description="List of preferred job roles (max 10)")
    education: Optional[str] = Field(None, description="Education details")
    work_experience: Optional[str] = Field(None, description="Work experience details")
    summary: Optional[str] = Field(None, description="Professional summary")
    
    # Work Authorization (optional for initial submission)
    work_authorization_status: Optional[str] = Field(None, description="US Citizen, Green Card, H1B, etc.")
    requires_sponsorship: Optional[bool] = Field(False)
    
    # Additional
    linkedin_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)
    portfolio_url: Optional[str] = Field(None, max_length=500)
    additional_info: Optional[str] = Field(None, description="Any additional information")
    parsed_resume_data: Optional[dict] = Field(None, description="AI-parsed resume data for reference")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        # Remove common formatting characters
        cleaned = ''.join(c for c in v if c.isdigit() or c == '+')
        if len(cleaned) < 10:
            raise ValueError('Phone number must have at least 10 digits')
        return v
    
    @field_validator('skills')
    @classmethod
    def validate_skills(cls, v):
        if v and len(v) > 50:
            raise ValueError('Maximum 50 skills allowed')
        return v
    
    @field_validator('preferred_roles')
    @classmethod
    def validate_preferred_roles(cls, v):
        if v and len(v) > 10:
            raise ValueError('Maximum 10 preferred roles allowed')
        return v

    
    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone": "+1-555-123-4567",
                "address_line1": "123 Main St",
                "address_line2": "Apt 4B",
                "city": "New York",
                "state": "NY",
                "zip_code": "10001",
                "country": "United States",
                "current_job_title": "Senior Developer",
                "current_employer": "Tech Corp",
                "years_of_experience": 5,
                "skills": ["Python", "React", "PostgreSQL"],
                "work_authorization_status": "US Citizen",
                "requires_sponsorship": False,
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "portfolio_url": "https://johndoe.dev",
                "additional_info": "Available to start in 2 weeks"
            }
        }


class InvitationReviewSchema(BaseModel):
    """Schema for HR approving/rejecting invitation with optional data edits"""
    action: str = Field(..., pattern="^(approve|reject)$", description="approve or reject")
    notes: Optional[str] = Field(None, description="Internal review notes")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection (required if rejecting)")
    
    # Allow HR to edit candidate data during approval
    edited_data: Optional[Dict[str, Any]] = Field(None, description="Edited candidate data (will merge with submitted data)")
    
    @field_validator('rejection_reason')
    @classmethod
    def validate_rejection_reason(cls, v, info):
        if info.data.get('action') == 'reject' and not v:
            raise ValueError('rejection_reason is required when action is reject')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "approve",
                "notes": "Strong candidate, approved for next steps",
                "edited_data": {
                    "phone": "+1-234-567-8900",
                    "location": "San Francisco, CA"
                }
            }
        }


class InvitationResponseSchema(BaseModel):
    """Schema for invitation response (list view - no sensitive data)"""
    id: int
    tenant_id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    position: Optional[str]
    status: str
    expires_at: datetime
    invited_by_id: int
    invited_at: datetime
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    reviewed_by_id: Optional[int]
    candidate_id: Optional[int]
    
    # Computed fields
    is_expired: bool
    is_valid: bool
    can_be_resent: bool
    
    class Config:
        from_attributes = True


class InvitationDetailResponseSchema(InvitationResponseSchema):
    """Extended schema with invitation data, audit trail, and sensitive fields"""
    token: str  # Include token for detailed view (resend functionality)
    invitation_data: Optional[Dict[str, Any]] = None
    review_notes: Optional[str] = None
    recruiter_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    class Config:
        from_attributes = True


class InvitationListResponseSchema(BaseModel):
    """Schema for paginated invitation list"""
    items: List[InvitationResponseSchema]
    total: int
    page: int
    per_page: int
    pages: int
    
    class Config:
        from_attributes = True


class InvitationAuditLogResponseSchema(BaseModel):
    """Schema for audit log entries"""
    id: int
    invitation_id: int
    action: str
    performed_by_id: Optional[int]
    performed_at: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True

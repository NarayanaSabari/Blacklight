"""Pydantic schemas for Candidate Onboarding."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# Request Schemas

class OnboardCandidateSchema(BaseModel):
    """Schema for marking candidate as onboarded."""
    
    candidate_id: int = Field(..., description="ID of candidate to onboard")
    
    model_config = ConfigDict(from_attributes=True)


class ApproveCandidateSchema(BaseModel):
    """Schema for approving a candidate."""
    
    candidate_id: int = Field(..., description="ID of candidate to approve")
    
    model_config = ConfigDict(from_attributes=True)


class RejectCandidateSchema(BaseModel):
    """Schema for rejecting a candidate."""
    
    candidate_id: int = Field(..., description="ID of candidate to reject")
    rejection_reason: str = Field(..., min_length=1, description="Reason for rejection (required)")
    
    model_config = ConfigDict(from_attributes=True)


class UpdateOnboardingStatusSchema(BaseModel):
    """Schema for updating candidate onboarding status."""
    
    candidate_id: int = Field(..., description="ID of candidate")
    new_status: str = Field(
        ..., 
        description="New onboarding status",
        pattern="^(PENDING_ASSIGNMENT|ASSIGNED|PENDING_ONBOARDING|ONBOARDED|APPROVED|REJECTED)$"
    )
    
    model_config = ConfigDict(from_attributes=True)


class GetOnboardingCandidatesQuerySchema(BaseModel):
    """Schema for query parameters when getting onboarding candidates."""
    
    status_filter: Optional[str] = Field(
        None,
        description="Filter by onboarding status"
    )
    assigned_to_user_id: Optional[int] = Field(
        None,
        description="Filter by assigned user ID"
    )
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page (max 100)")
    
    model_config = ConfigDict(from_attributes=True)


# Response Schemas

class OnboardingUserInfoSchema(BaseModel):
    """User information for onboarding displays."""
    
    id: int
    email: str
    first_name: str
    last_name: str
    
    model_config = ConfigDict(from_attributes=True)


class CandidateOnboardingInfoSchema(BaseModel):
    """Candidate information with onboarding details."""
    
    id: int
    tenant_id: int
    first_name: str
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: str
    current_title: Optional[str] = None
    location: Optional[str] = None
    total_experience_years: Optional[int] = None
    
    # Onboarding fields
    onboarding_status: Optional[str] = None
    onboarded_by_user_id: Optional[int] = None
    onboarded_at: Optional[str] = None
    approved_by_user_id: Optional[int] = None
    approved_at: Optional[str] = None
    rejected_by_user_id: Optional[int] = None
    rejected_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    manager_id: Optional[int] = None
    recruiter_id: Optional[int] = None
    
    # Related users
    onboarded_by: Optional[OnboardingUserInfoSchema] = None
    approved_by: Optional[OnboardingUserInfoSchema] = None
    rejected_by: Optional[OnboardingUserInfoSchema] = None
    manager: Optional[OnboardingUserInfoSchema] = None
    recruiter: Optional[OnboardingUserInfoSchema] = None
    
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class OnboardCandidateResponseSchema(BaseModel):
    """Schema for onboard candidate response."""
    
    message: str
    candidate: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


class ApproveCandidateResponseSchema(BaseModel):
    """Schema for approve candidate response."""
    
    message: str
    candidate: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


class RejectCandidateResponseSchema(BaseModel):
    """Schema for reject candidate response."""
    
    message: str
    candidate: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


class OnboardingCandidatesListResponseSchema(BaseModel):
    """Schema for paginated onboarding candidates list."""
    
    candidates: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    pages: int
    
    model_config = ConfigDict(from_attributes=True)


class UpdateOnboardingStatusResponseSchema(BaseModel):
    """Schema for update onboarding status response."""
    
    message: str
    candidate: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


class OnboardingStatsSchema(BaseModel):
    """Schema for onboarding statistics."""
    
    pending_assignment: int
    assigned: int
    pending_onboarding: int
    onboarded: int
    approved: int
    rejected: int
    total: int
    
    model_config = ConfigDict(from_attributes=True)

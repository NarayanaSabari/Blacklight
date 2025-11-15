"""Pydantic schemas for Candidate Assignment."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# Request Schemas

class AssignCandidateSchema(BaseModel):
    """Schema for assigning a candidate to a user."""
    
    candidate_id: int = Field(..., description="ID of candidate to assign")
    assigned_to_user_id: int = Field(..., description="ID of user to assign candidate to")
    assignment_reason: Optional[str] = Field(None, description="Optional reason for assignment")
    
    model_config = ConfigDict(from_attributes=True)


class ReassignCandidateSchema(BaseModel):
    """Schema for reassigning a candidate."""
    
    candidate_id: int = Field(..., description="ID of candidate to reassign")
    new_assigned_to_user_id: int = Field(..., description="ID of new user to assign candidate to")
    assignment_reason: Optional[str] = Field(None, description="Optional reason for reassignment")
    
    model_config = ConfigDict(from_attributes=True)


class UnassignCandidateSchema(BaseModel):
    """Schema for unassigning a candidate."""
    
    candidate_id: int = Field(..., description="ID of candidate to unassign")
    reason: Optional[str] = Field(None, description="Optional reason for unassignment")
    
    model_config = ConfigDict(from_attributes=True)


class MarkNotificationReadSchema(BaseModel):
    """Schema for marking notification as read."""
    
    notification_id: int = Field(..., description="ID of notification to mark as read")
    
    model_config = ConfigDict(from_attributes=True)


# Response Schemas

class UserInfoSchema(BaseModel):
    """User information for assignment displays."""
    
    id: int
    email: str
    first_name: str
    last_name: str
    
    model_config = ConfigDict(from_attributes=True)


class CandidateInfoSchema(BaseModel):
    """Candidate information for assignment displays."""
    
    id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    status: str
    onboarding_status: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class AssignmentSchema(BaseModel):
    """Schema for candidate assignment details."""
    
    id: int
    candidate_id: int
    assigned_to_user_id: int
    assigned_by_user_id: Optional[int] = None
    assignment_type: str
    previous_assignee_id: Optional[int] = None
    assignment_reason: Optional[str] = None
    assigned_at: str
    completed_at: Optional[str] = None
    status: str
    notes: Optional[str] = None
    assigned_to: Optional[UserInfoSchema] = None
    assigned_by: Optional[UserInfoSchema] = None
    previous_assignee: Optional[UserInfoSchema] = None
    candidate: Optional[CandidateInfoSchema] = None
    
    model_config = ConfigDict(from_attributes=True)


class AssignmentNotificationSchema(BaseModel):
    """Schema for assignment notification."""
    
    id: int
    assignment_id: int
    user_id: int
    notification_type: str
    is_read: bool
    read_at: Optional[str] = None
    created_at: str
    assignment: Optional[AssignmentSchema] = None
    user: Optional[UserInfoSchema] = None
    
    model_config = ConfigDict(from_attributes=True)


class AssignCandidateResponseSchema(BaseModel):
    """Schema for candidate assignment response."""
    
    message: str
    assignment: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


class ReassignCandidateResponseSchema(BaseModel):
    """Schema for candidate reassignment response."""
    
    message: str
    assignment: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


class UnassignCandidateResponseSchema(BaseModel):
    """Schema for candidate unassignment response."""
    
    message: str
    candidate_id: int
    
    model_config = ConfigDict(from_attributes=True)


class CandidateAssignmentsResponseSchema(BaseModel):
    """Schema for candidate assignment history response."""
    
    assignments: List[Dict[str, Any]]
    total: int
    
    model_config = ConfigDict(from_attributes=True)


class UserAssignedCandidatesResponseSchema(BaseModel):
    """Schema for user's assigned candidates response."""
    
    candidates: List[Dict[str, Any]]
    total: int
    
    model_config = ConfigDict(from_attributes=True)


class AssignmentHistoryResponseSchema(BaseModel):
    """Schema for assignment history response."""
    
    assignments: List[Dict[str, Any]]
    total: int
    limit: int
    
    model_config = ConfigDict(from_attributes=True)


class NotificationsResponseSchema(BaseModel):
    """Schema for user notifications response."""
    
    notifications: List[Dict[str, Any]]
    total: int
    unread_count: int
    
    model_config = ConfigDict(from_attributes=True)


class MarkNotificationReadResponseSchema(BaseModel):
    """Schema for mark notification as read response."""
    
    message: str
    notification_id: int
    
    model_config = ConfigDict(from_attributes=True)

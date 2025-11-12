"""Pydantic schemas for Portal Users."""

import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from datetime import datetime

logger = logging.getLogger(__name__)


class PortalUserCreateSchema(BaseModel):
    """Schema for creating a portal user (TENANT_ADMIN only)."""
    
    email: EmailStr = Field(..., description="User email (globally unique)")
    password: str = Field(..., min_length=8, description="User password")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    
    model_config = ConfigDict(from_attributes=True)


class PortalUserUpdateSchema(BaseModel):
    """Schema for updating a portal user."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)


class PortalUserResetPasswordSchema(BaseModel):
    """Schema for resetting portal user password."""
    
    new_password: str = Field(..., min_length=8, description="New password")
    
    model_config = ConfigDict(from_attributes=True)


class PortalUserResponseSchema(BaseModel):
    """Schema for portal user response."""
    
    id: int
    tenant_id: int
    email: str
    first_name: str
    last_name: str
    full_name: str
    phone: Optional[str]
    roles: List[Dict[str, Any]] = Field(default_factory=list)  # List of role objects
    is_active: bool
    last_login: Optional[datetime]
    is_locked: bool
    locked_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    permissions: List[str] = Field(default_factory=list) # Added permissions field
    
    # Optional nested tenant data
    tenant: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


class PortalUserListResponseSchema(BaseModel):
    """Schema for paginated portal user list."""
    
    items: List[PortalUserResponseSchema]
    total: int
    page: int
    per_page: int
    
    model_config = ConfigDict(from_attributes=True)


class PortalLoginSchema(BaseModel):
    """Schema for portal user login."""
    
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    
    model_config = ConfigDict(from_attributes=True)


class PortalLoginResponseSchema(BaseModel):
    """Schema for portal login response."""
    
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: PortalUserResponseSchema
    
    model_config = ConfigDict(from_attributes=True)


class UserRoleAssignmentSchema(BaseModel):
    """Schema for assigning roles to a user."""
    role_ids: List[int] = Field(..., description="List of role IDs to assign to the user")
    
    model_config = ConfigDict(from_attributes=True)

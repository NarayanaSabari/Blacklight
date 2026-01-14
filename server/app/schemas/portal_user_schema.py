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
    role_id: int = Field(..., description="Role ID to assign to the user")
    manager_id: Optional[int] = Field(
        None, 
        description="Manager ID to assign. Auto-set to creator for MANAGER role. Required for TEAM_LEAD/RECRUITER."
    )
    
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
    is_tenant_admin: bool = Field(default=False, description="Whether user has TENANT_ADMIN role")
    
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


class ProfileUpdateSchema(BaseModel):
    """Schema for updating own profile."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    
    model_config = ConfigDict(from_attributes=True)


class ChangePasswordSchema(BaseModel):
    """Schema for changing own password."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 chars)")
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password has minimum requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

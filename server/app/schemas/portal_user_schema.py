"""Pydantic schemas for Portal Users."""

from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime
from enum import Enum


class PortalUserRoleEnum(str, Enum):
    """Portal user role enumeration."""
    TENANT_ADMIN = "TENANT_ADMIN"
    RECRUITER = "RECRUITER"
    HIRING_MANAGER = "HIRING_MANAGER"


class PortalUserCreateSchema(BaseModel):
    """Schema for creating a portal user (TENANT_ADMIN only)."""
    
    email: EmailStr = Field(..., description="User email (globally unique)")
    password: str = Field(..., min_length=8, description="User password")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    role: PortalUserRoleEnum = Field(default=PortalUserRoleEnum.RECRUITER, description="User role")
    
    model_config = ConfigDict(from_attributes=True)


class PortalUserUpdateSchema(BaseModel):
    """Schema for updating a portal user."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[PortalUserRoleEnum] = None
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
    role: str
    is_active: bool
    last_login: Optional[datetime]
    is_locked: bool
    locked_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
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

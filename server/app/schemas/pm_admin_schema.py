"""Pydantic schemas for PM Admin Users."""

from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime


class PMAdminUserCreateSchema(BaseModel):
    """Schema for creating a PM admin user."""
    
    email: EmailStr = Field(..., description="Admin email (globally unique)")
    password: str = Field(..., min_length=8, description="Admin password")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    
    model_config = ConfigDict(from_attributes=True)


class PMAdminUserUpdateSchema(BaseModel):
    """Schema for updating a PM admin user."""
    
    email: Optional[EmailStr] = Field(None, description="Admin email (globally unique)")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)


class PMAdminUserResponseSchema(BaseModel):
    """Schema for PM admin user response."""
    
    id: int
    email: str
    first_name: str
    last_name: str
    full_name: str
    phone: Optional[str]
    is_active: bool
    last_login: Optional[datetime]
    is_locked: bool
    locked_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PMAdminUserListResponseSchema(BaseModel):
    """Schema for paginated PM admin user list."""
    
    items: List[PMAdminUserResponseSchema]
    total: int
    page: int
    per_page: int
    
    model_config = ConfigDict(from_attributes=True)


class PMAdminLoginSchema(BaseModel):
    """Schema for PM admin login."""
    
    email: EmailStr = Field(..., description="Admin email")
    password: str = Field(..., description="Admin password")
    
    model_config = ConfigDict(from_attributes=True)


class PMAdminLoginResponseSchema(BaseModel):
    """Schema for PM admin login response."""
    
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    admin: PMAdminUserResponseSchema
    
    model_config = ConfigDict(from_attributes=True)


class ResetTenantAdminPasswordSchema(BaseModel):
    """Schema for resetting tenant admin password by PM admin."""
    
    portal_user_id: int = Field(..., gt=0, description="Portal user ID")
    new_password: str = Field(..., min_length=8, description="New password")
    
    model_config = ConfigDict(from_attributes=True)

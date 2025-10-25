"""Pydantic schemas for Portal Users."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from datetime import datetime


class PortalUserCreateSchema(BaseModel):
    """Schema for creating a portal user (TENANT_ADMIN only)."""
    
    email: EmailStr = Field(..., description="User email (globally unique)")
    password: str = Field(..., min_length=8, description="User password")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    role_id: int = Field(..., description="Role ID (must be a system role or tenant's custom role)")
    
    model_config = ConfigDict(from_attributes=True)


class PortalUserUpdateSchema(BaseModel):
    """Schema for updating a portal user."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role_id: Optional[int] = Field(None, description="Role ID")
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
    role: Dict[str, Any]  # Role object with id, name, display_name, etc.
    role_id: int
    is_active: bool
    last_login: Optional[datetime]
    is_locked: bool
    locked_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Optional nested tenant data
    tenant: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('role', mode='before')
    @classmethod
    def serialize_role(cls, v):
        """Convert Role SQLAlchemy model to dict."""
        if v is None:
            return None
        # If already a dict, return as-is
        if isinstance(v, dict):
            return v
        # If SQLAlchemy model, serialize it
        return {
            'id': v.id,
            'name': v.name,
            'display_name': v.display_name,
            'description': v.description,
            'is_system_role': v.is_system_role,
            'tenant_id': v.tenant_id,
        }
    
    @field_validator('tenant', mode='before')
    @classmethod
    def serialize_tenant(cls, v):
        """Convert Tenant SQLAlchemy model to dict."""
        if v is None:
            return None
        # If already a dict, return as-is
        if isinstance(v, dict):
            return v
        # If SQLAlchemy model, serialize it
        return {
            'id': v.id,
            'slug': v.slug,
            'company_name': v.name,  # Tenant.name is the company name
            'status': v.status.value if hasattr(v.status, 'value') else str(v.status),
        }


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

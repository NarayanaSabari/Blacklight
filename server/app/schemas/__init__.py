"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, field_validator


class TimestampedSchema(BaseModel):
    """Base schema with timestamps."""
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserCreateSchema(BaseModel):
    """Schema for creating a user."""
    
    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    
    @field_validator("username")
    def username_alphanumeric(cls, v):
        """Validate username is alphanumeric with underscores."""
        assert v.replace("_", "").isalnum(), "Username must be alphanumeric with underscores"
        return v


class UserUpdateSchema(BaseModel):
    """Schema for updating a user."""
    
    username: Optional[str] = Field(None, min_length=3, max_length=80)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserResponseSchema(TimestampedSchema):
    """Schema for user response."""
    
    id: int
    username: str
    email: str
    is_active: bool


class UserListSchema(BaseModel):
    """Schema for user list response."""
    
    items: List[UserResponseSchema]
    total: int
    page: int
    per_page: int


class AuditLogSchema(TimestampedSchema):
    """Schema for audit log."""
    
    id: int
    action: str
    entity_type: str
    entity_id: int
    changes: Optional[dict] = None
    user_id: Optional[int] = None


class ErrorResponseSchema(BaseModel):
    """Schema for error responses."""
    
    error: str
    message: str
    status: int
    details: Optional[dict] = None


class HealthCheckSchema(BaseModel):
    """Schema for health check response."""
    
    status: str
    timestamp: datetime
    environment: str


class AppInfoSchema(BaseModel):
    """Schema for app info response."""
    
    name: str
    version: str
    environment: str
    debug: bool
    timestamp: datetime

"""
Pydantic schemas for Role model validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import datetime


class PermissionBase(BaseModel):
    """Base permission schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Permission name (e.g., 'candidates.create')")
    display_name: str = Field(..., min_length=1, max_length=150, description="Human-readable permission name")
    category: Optional[str] = Field(None, max_length=50, description="Permission category (e.g., 'candidates')")
    description: Optional[str] = Field(None, description="Permission description")


class PermissionResponse(PermissionBase):
    """Permission response schema."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    """Base role schema with common fields."""
    name: str = Field(..., min_length=1, max_length=50, description="Role name (e.g., 'RECRUITER')")
    display_name: str = Field(..., min_length=1, max_length=100, description="Human-readable role name")
    description: Optional[str] = Field(None, description="Role description")
    is_active: bool = Field(True, description="Whether role is active")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate role name format (uppercase, alphanumeric + underscore)."""
        if not v.replace('_', '').isalnum():
            raise ValueError('Role name must contain only alphanumeric characters and underscores')
        return v.upper()


class RoleCreate(RoleBase):
    """Schema for creating a new role."""
    tenant_id: Optional[int] = Field(None, description="Tenant ID for custom roles (NULL for system roles)")
    permission_ids: Optional[List[int]] = Field(default_factory=list, description="List of permission IDs to assign")


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    """Role response schema."""
    id: int
    tenant_id: Optional[int]
    is_system_role: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    """Role response schema with permissions included."""
    permissions: List[PermissionResponse] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class RoleAssignPermissions(BaseModel):
    """Schema for assigning permissions to a role."""
    permission_ids: List[int] = Field(..., min_items=0, description="List of permission IDs to assign to the role")


class RoleListResponse(BaseModel):
    """Schema for role list response."""
    roles: List[Union[RoleResponse, RoleWithPermissions]]
    total: int
    page: int = 1
    per_page: int = 50


class PermissionListResponse(BaseModel):
    """Schema for permission list response."""
    permissions: List[PermissionResponse]
    total: int
    categories: List[str] = Field(default_factory=list, description="Available permission categories")

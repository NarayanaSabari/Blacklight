"""Pydantic schemas for Team Management."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# Request Schemas

class AssignManagerSchema(BaseModel):
    """Schema for assigning a manager to a user."""
    
    user_id: int = Field(..., description="ID of user to assign manager to")
    manager_id: int = Field(..., description="ID of manager to assign")
    
    model_config = ConfigDict(from_attributes=True)


class RemoveManagerSchema(BaseModel):
    """Schema for removing manager assignment."""
    
    user_id: int = Field(..., description="ID of user to remove manager from")
    
    model_config = ConfigDict(from_attributes=True)


# Response Schemas

class UserBasicInfoSchema(BaseModel):
    """Basic user information for team displays."""
    
    id: int
    email: str
    first_name: str
    last_name: str
    full_name: str
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class TeamMemberSchema(BaseModel):
    """Schema for team member with role and manager info."""
    
    id: int
    tenant_id: int
    email: str
    first_name: str
    last_name: str
    full_name: str
    phone: Optional[str] = None
    is_active: bool
    manager_id: Optional[int] = None
    roles: Optional[List[Dict[str, Any]]] = None
    manager: Optional[UserBasicInfoSchema] = None
    team_members: Optional[List[Dict[str, Any]]] = None
    hierarchy_level: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ManagerWithCountSchema(BaseModel):
    """Schema for manager with team member count."""
    
    id: int
    email: str
    first_name: str
    last_name: str
    full_name: str
    team_member_count: int
    roles: Optional[List[Dict[str, Any]]] = None
    manager: Optional[UserBasicInfoSchema] = None
    
    model_config = ConfigDict(from_attributes=True)


class TeamHierarchyResponseSchema(BaseModel):
    """Schema for complete team hierarchy response."""
    
    top_level_users: List[TeamMemberSchema]
    total_users: int
    
    model_config = ConfigDict(from_attributes=True)


class AssignManagerResponseSchema(BaseModel):
    """Schema for manager assignment response."""
    
    message: str
    user_id: int
    manager_id: int
    user: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


class RemoveManagerResponseSchema(BaseModel):
    """Schema for manager removal response."""
    
    message: str
    user_id: int
    user: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


class AvailableManagersResponseSchema(BaseModel):
    """Schema for available managers response."""
    
    managers: List[TeamMemberSchema]
    total: int
    
    model_config = ConfigDict(from_attributes=True)

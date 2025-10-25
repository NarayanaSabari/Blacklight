"""Pydantic schemas for Tenants."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict, model_validator
from datetime import datetime
from enum import Enum

from app.schemas.subscription_plan_schema import SubscriptionPlanResponseSchema


class TenantStatusEnum(str, Enum):
    """Tenant status enumeration."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


class BillingCycleEnum(str, Enum):
    """Billing cycle enumeration."""
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class TenantCreateSchema(BaseModel):
    """Schema for creating a tenant."""
    
    # Company Information
    name: str = Field(..., min_length=2, max_length=200, description="Company name")
    slug: Optional[str] = Field(None, max_length=100, description="URL-friendly slug (auto-generated if not provided)")
    company_email: EmailStr = Field(..., description="Company contact email")
    company_phone: Optional[str] = Field(None, max_length=20, description="Company phone number")
    
    # Subscription
    subscription_plan_id: int = Field(..., gt=0, description="Subscription plan ID")
    billing_cycle: Optional[BillingCycleEnum] = Field(None, description="Billing cycle")
    
    # Tenant Admin Account
    tenant_admin_email: EmailStr = Field(..., description="Tenant admin email (globally unique)")
    tenant_admin_password: str = Field(..., min_length=8, description="Tenant admin password")
    tenant_admin_first_name: str = Field(..., min_length=1, max_length=100, description="Admin first name")
    tenant_admin_last_name: str = Field(..., min_length=1, max_length=100, description="Admin last name")
    
    # Metadata
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Tenant settings")
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v):
        """Validate slug is URL-safe."""
        if v is not None:
            import re
            if not re.match(r'^[a-z0-9-]+$', v):
                raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v
    
    model_config = ConfigDict(from_attributes=True)


class TenantUpdateSchema(BaseModel):
    """Schema for updating a tenant."""
    
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    company_email: Optional[EmailStr] = None
    company_phone: Optional[str] = Field(None, max_length=20)
    settings: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class TenantChangePlanSchema(BaseModel):
    """Schema for changing tenant subscription plan."""
    
    new_plan_id: int = Field(..., gt=0, description="New subscription plan ID")
    billing_cycle: Optional[BillingCycleEnum] = Field(None, description="Billing cycle")
    
    model_config = ConfigDict(from_attributes=True)


class TenantSuspendSchema(BaseModel):
    """Schema for suspending a tenant."""
    
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for suspension")
    
    model_config = ConfigDict(from_attributes=True)


class TenantDeleteSchema(BaseModel):
    """Schema for deleting a tenant."""
    
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for deletion")
    
    model_config = ConfigDict(from_attributes=True)


class TenantFilterSchema(BaseModel):
    """Schema for filtering tenants."""
    
    status: Optional[TenantStatusEnum] = None
    subscription_plan_id: Optional[int] = None
    search: Optional[str] = Field(None, max_length=200, description="Search by name or email")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    model_config = ConfigDict(from_attributes=True)


class TenantResponseSchema(BaseModel):
    """Schema for tenant response."""
    
    id: int
    name: str
    slug: str
    company_email: str
    company_phone: Optional[str]
    status: str
    subscription_plan_id: int
    subscription_start_date: datetime
    subscription_end_date: Optional[datetime]
    billing_cycle: Optional[str]
    next_billing_date: Optional[datetime]
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    # Optional nested data
    subscription_plan: Optional[SubscriptionPlanResponseSchema] = None
    tenant_admin_email: Optional[str] = None
    
    @model_validator(mode='before')
    @classmethod
    def convert_enums(cls, data):
        """Convert enum values to strings before validation."""
        if hasattr(data, '__dict__'):
            # If it's a model instance, convert to dict
            data = data.__dict__.copy()
        
        # Convert status enum to string
        if 'status' in data and hasattr(data['status'], 'value'):
            data['status'] = data['status'].value
        
        # Convert billing_cycle enum to string
        if 'billing_cycle' in data and data['billing_cycle'] is not None and hasattr(data['billing_cycle'], 'value'):
            data['billing_cycle'] = data['billing_cycle'].value
        
        # Ensure settings is a dict, not None
        if 'settings' in data and data['settings'] is None:
            data['settings'] = {}
        
        return data
    
    model_config = ConfigDict(from_attributes=True)


class TenantListResponseSchema(BaseModel):
    """Schema for paginated tenant list."""
    
    items: List[TenantResponseSchema]
    total: int
    page: int
    per_page: int
    
    model_config = ConfigDict(from_attributes=True)


class TenantStatsSchema(BaseModel):
    """Schema for tenant usage statistics."""
    
    tenant_id: int
    tenant_name: str
    
    # Current usage
    user_count: int
    candidate_count: int = 0  # Placeholder until candidates table exists
    job_count: int = 0  # Placeholder until jobs table exists
    storage_used_gb: float = 0.0  # Placeholder
    
    # Plan limits
    max_users: int
    max_candidates: int
    max_jobs: int
    max_storage_gb: int
    
    # Percentage usage
    user_usage_percent: float
    candidate_usage_percent: float
    job_usage_percent: float
    storage_usage_percent: float
    
    model_config = ConfigDict(from_attributes=True)


class TenantDeleteResponseSchema(BaseModel):
    """Schema for tenant deletion response."""
    
    message: str
    tenant_id: int
    tenant_name: str
    deleted_counts: Dict[str, int]  # e.g., {"portal_users": 5, "candidates": 100}
    
    model_config = ConfigDict(from_attributes=True)

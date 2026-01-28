"""Pydantic schemas for Subscription Plans."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime


class SubscriptionPlanBaseSchema(BaseModel):
    """Base schema for subscription plan."""
    
    name: str = Field(..., max_length=50, description="Plan name (e.g., FREE, STARTER)")
    display_name: str = Field(..., max_length=100, description="Human-readable plan name")
    description: Optional[str] = Field(None, description="Plan description")
    price_monthly: Decimal = Field(..., ge=0, description="Monthly price")
    price_yearly: Optional[Decimal] = Field(None, ge=0, description="Yearly price")
    max_users: int = Field(..., gt=0, description="Maximum users allowed")
    max_candidates: int = Field(..., gt=0, description="Maximum candidates allowed")
    max_storage_gb: int = Field(default=1, gt=0, description="Maximum storage in GB")
    features: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Plan features")
    is_active: bool = Field(default=True, description="Is plan active")
    sort_order: int = Field(default=0, description="Display order")


class SubscriptionPlanCreateSchema(SubscriptionPlanBaseSchema):
    """Schema for creating a subscription plan."""
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlanUpdateSchema(BaseModel):
    """Schema for updating a subscription plan."""
    
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price_monthly: Optional[Decimal] = Field(None, ge=0)
    price_yearly: Optional[Decimal] = Field(None, ge=0)
    max_users: Optional[int] = Field(None, gt=0)
    max_candidates: Optional[int] = Field(None, gt=0)
    max_storage_gb: Optional[int] = Field(None, gt=0)
    features: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlanResponseSchema(BaseModel):
    """Schema for subscription plan response."""
    
    id: int
    name: str
    display_name: str
    description: Optional[str]
    price_monthly: Decimal
    price_yearly: Optional[Decimal]
    max_users: int
    max_candidates: int
    max_storage_gb: int
    features: Dict[str, Any]
    is_active: bool
    sort_order: int
    is_custom: bool
    custom_for_tenant_id: Optional[int]
    custom_for_tenant_name: Optional[str] = None
    custom_for_tenant_slug: Optional[str] = None
    assigned_tenants_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlanListResponseSchema(BaseModel):
    """Schema for paginated subscription plan list."""
    
    items: List[SubscriptionPlanResponseSchema]
    total: int
    page: int
    per_page: int
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlanUsageSchema(BaseModel):
    """Schema for subscription plan usage stats."""
    
    plan: SubscriptionPlanResponseSchema
    active_tenants_count: int
    total_tenants_count: int
    
    model_config = ConfigDict(from_attributes=True)


# Custom Plan Schemas


class CustomPlanCreateSchema(BaseModel):
    """Schema for creating a custom tenant-specific plan."""
    
    tenant_id: int = Field(..., gt=0, description="Tenant ID this custom plan is for")
    base_plan_id: Optional[int] = Field(None, gt=0, description="Plan to clone limits/features from")
    display_name: str = Field(..., min_length=1, max_length=100, description="Human-readable plan name")
    description: Optional[str] = Field(None, description="Plan description")
    price_monthly: Decimal = Field(..., ge=0, description="Monthly price in dollars (must be >= 0)")
    price_yearly: Optional[Decimal] = Field(None, ge=0, description="Yearly price in dollars (must be >= 0)")
    max_users: int = Field(..., gt=0, description="Maximum users allowed (must be >= 1)")
    max_candidates: int = Field(..., gt=0, description="Maximum candidates allowed (must be >= 1)")
    max_storage_gb: int = Field(..., gt=0, description="Maximum storage in GB (must be >= 1)")
    features: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Plan features")
    
    model_config = ConfigDict(from_attributes=True)


class CustomPlanUpdateSchema(BaseModel):
    """Schema for updating a custom plan."""
    
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price_monthly: Optional[Decimal] = Field(None, ge=0, description="Monthly price in dollars (must be >= 0)")
    price_yearly: Optional[Decimal] = Field(None, ge=0, description="Yearly price in dollars (must be >= 0)")
    max_users: Optional[int] = Field(None, gt=0, description="Maximum users allowed (must be >= 1)")
    max_candidates: Optional[int] = Field(None, gt=0, description="Maximum candidates allowed (must be >= 1)")
    max_storage_gb: Optional[int] = Field(None, gt=0, description="Maximum storage in GB (must be >= 1)")
    features: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class CustomPlanResponseSchema(BaseModel):
    """Schema for custom plan response (extends standard plan response)."""
    
    id: int
    name: str
    display_name: str
    description: Optional[str]
    price_monthly: Decimal
    price_yearly: Optional[Decimal]
    max_users: int
    max_candidates: int
    max_storage_gb: int
    features: Dict[str, Any]
    is_active: bool
    sort_order: int
    is_custom: bool
    custom_for_tenant_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
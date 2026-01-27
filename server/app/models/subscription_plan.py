"""Subscription Plan model for tenant subscription management."""

from sqlalchemy import Enum as SQLEnum
from app import db
from app.models import BaseModel


class SubscriptionPlan(BaseModel):
    """
    Subscription Plan model.
    
    Defines subscription tiers with pricing and resource limits.
    Default plans: FREE, STARTER, PROFESSIONAL, ENTERPRISE
    """
    
    __tablename__ = "subscription_plans"
    
    # Plan Information
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Pricing
    price_monthly = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    price_yearly = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Resource Limits
    max_users = db.Column(db.Integer, nullable=False)
    max_candidates = db.Column(db.Integer, nullable=False)
    max_storage_gb = db.Column(db.Integer, nullable=False, default=1)
    
    # Features (JSON for flexibility)
    # Example: {"advanced_analytics": true, "custom_branding": false, "api_access": true}
    features = db.Column(db.JSON, nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    
    # Custom Plan Support
    is_custom = db.Column(db.Boolean, nullable=False, default=False, index=True)
    custom_for_tenant_id = db.Column(
        db.Integer,
        db.ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=True,
        index=True
    )
    
    # Relationships
    tenants = db.relationship(
        'Tenant',
        foreign_keys='Tenant.subscription_plan_id',
        back_populates='subscription_plan',
        lazy='dynamic'
    )
    
    custom_tenant = db.relationship(
        'Tenant',
        foreign_keys=[custom_for_tenant_id],
        back_populates='custom_plans'
    )
    
    subscription_histories = db.relationship(
        'TenantSubscriptionHistory',
        back_populates='subscription_plan',
        lazy='dynamic'
    )
    
    def to_dict(self):
        """Convert model to dictionary."""
        data = super().to_dict()
        data.update({
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "price_monthly": float(self.price_monthly) if self.price_monthly else 0.00,
            "price_yearly": float(self.price_yearly) if self.price_yearly else None,
            "max_users": self.max_users,
            "max_candidates": self.max_candidates,
            "max_storage_gb": self.max_storage_gb,
            "features": self.features or {},
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "is_custom": self.is_custom,
            "custom_for_tenant_id": self.custom_for_tenant_id,
        })
        return data
    
    def __repr__(self):
        """String representation."""
        return f"<SubscriptionPlan {self.name} - {self.display_name}>"

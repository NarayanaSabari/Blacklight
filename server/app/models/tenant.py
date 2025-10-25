"""Tenant model for multi-tenant SaaS management."""

from datetime import datetime
from sqlalchemy import Enum as SQLEnum
import enum
from app import db
from app.models import BaseModel


class TenantStatus(enum.Enum):
    """Tenant status enumeration."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


class BillingCycle(enum.Enum):
    """Billing cycle enumeration."""
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class Tenant(BaseModel):
    """
    Tenant model.
    
    Represents a company/organization using the platform.
    Each tenant has isolated data and configuration.
    """
    
    __tablename__ = "tenants"
    
    # Basic Information
    name = db.Column(db.String(200), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # Contact Information
    company_email = db.Column(db.String(120), unique=True, nullable=False)
    company_phone = db.Column(db.String(20), nullable=True)
    
    # Subscription & Status
    status = db.Column(
        SQLEnum(TenantStatus),
        nullable=False,
        default=TenantStatus.ACTIVE,
        index=True
    )
    subscription_plan_id = db.Column(
        db.Integer,
        db.ForeignKey('subscription_plans.id', ondelete='RESTRICT'),
        nullable=False,
        index=True
    )
    subscription_start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    
    # Billing
    billing_cycle = db.Column(
        SQLEnum(BillingCycle),
        nullable=True
    )
    next_billing_date = db.Column(db.DateTime, nullable=True)
    
    # Metadata (tenant-specific configurations)
    settings = db.Column(db.JSON, nullable=True)
    
    # Relationships
    subscription_plan = db.relationship(
        'SubscriptionPlan',
        back_populates='tenants'
    )
    
    portal_users = db.relationship(
        'PortalUser',
        back_populates='tenant',
        lazy='dynamic',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    
    custom_roles = db.relationship(
        'Role',
        back_populates='tenant',
        lazy='dynamic',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    
    subscription_history = db.relationship(
        'TenantSubscriptionHistory',
        back_populates='tenant',
        lazy='dynamic',
        order_by='TenantSubscriptionHistory.started_at.desc()',
        passive_deletes=True
    )
    
    def to_dict(self, include_plan=False, include_stats=False):
        """Convert model to dictionary."""
        data = super().to_dict()
        data.update({
            "name": self.name,
            "slug": self.slug,
            "company_email": self.company_email,
            "company_phone": self.company_phone,
            "status": self.status.value if self.status else None,
            "subscription_plan_id": self.subscription_plan_id,
            "subscription_start_date": self.subscription_start_date.isoformat() if self.subscription_start_date else None,
            "subscription_end_date": self.subscription_end_date.isoformat() if self.subscription_end_date else None,
            "billing_cycle": self.billing_cycle.value if self.billing_cycle else None,
            "next_billing_date": self.next_billing_date.isoformat() if self.next_billing_date else None,
            "settings": self.settings or {},
        })
        
        if include_plan and self.subscription_plan:
            data["subscription_plan"] = self.subscription_plan.to_dict()
        
        if include_stats:
            data["stats"] = {
                "user_count": self.portal_users.count(),
                "max_users": self.subscription_plan.max_users,
                "max_candidates": self.subscription_plan.max_candidates,
                "max_jobs": self.subscription_plan.max_jobs,
                "max_storage_gb": self.subscription_plan.max_storage_gb,
            }
        
        return data
    
    def __repr__(self):
        """String representation."""
        return f"<Tenant {self.name} ({self.slug}) - {self.status.value if self.status else 'UNKNOWN'}>"

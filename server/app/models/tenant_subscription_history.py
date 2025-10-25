"""Tenant Subscription History model for tracking plan changes."""

from sqlalchemy import Enum as SQLEnum
from app import db
from app.models import BaseModel
from app.models.tenant import BillingCycle


class TenantSubscriptionHistory(BaseModel):
    """
    Tenant Subscription History model.
    
    Tracks all subscription plan changes for audit and billing purposes.
    Preserves history even when tenant is deleted (for compliance).
    """
    
    __tablename__ = "tenant_subscription_history"
    
    # Tenant & Plan
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    subscription_plan_id = db.Column(
        db.Integer,
        db.ForeignKey('subscription_plans.id', ondelete='RESTRICT'),
        nullable=False,
        index=True
    )
    
    # Billing
    billing_cycle = db.Column(
        SQLEnum(BillingCycle),
        nullable=True
    )
    
    # Timeline
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)  # NULL for current active plan
    
    # Audit
    changed_by = db.Column(
        db.Integer,
        db.ForeignKey('pm_admin_users.id', ondelete='SET NULL'),
        nullable=True
    )
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    tenant = db.relationship(
        'Tenant',
        back_populates='subscription_history'
    )
    
    subscription_plan = db.relationship(
        'SubscriptionPlan',
        back_populates='subscription_histories'
    )
    
    admin = db.relationship(
        'PMAdminUser',
        back_populates='subscription_history_changes'
    )
    
    def to_dict(self, include_details=False):
        """Convert model to dictionary."""
        data = super().to_dict()
        data.update({
            "tenant_id": self.tenant_id,
            "subscription_plan_id": self.subscription_plan_id,
            "billing_cycle": self.billing_cycle.value if self.billing_cycle else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "changed_by": self.changed_by,
            "notes": self.notes,
        })
        
        if include_details:
            if self.subscription_plan:
                data["subscription_plan"] = self.subscription_plan.to_dict()
            
            if self.admin:
                data["admin"] = {
                    "id": self.admin.id,
                    "email": self.admin.email,
                    "full_name": self.admin.full_name,
                }
            
            if self.tenant:
                data["tenant"] = {
                    "id": self.tenant.id,
                    "name": self.tenant.name,
                    "slug": self.tenant.slug,
                }
        
        return data
    
    def __repr__(self):
        """String representation."""
        status = "ACTIVE" if self.ended_at is None else "ENDED"
        return f"<TenantSubscriptionHistory Tenant:{self.tenant_id} Plan:{self.subscription_plan_id} {status}>"

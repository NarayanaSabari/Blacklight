"""PM Admin User model for Platform Management administrators."""

from datetime import datetime
from app import db
from app.models import BaseModel


class PMAdminUser(BaseModel):
    """
    Platform Management Admin User model.
    
    Super-admin users who manage the platform via ui/centralD.
    These users have full access to tenant management and system configuration.
    No tenant association - they manage ALL tenants.
    """
    
    __tablename__ = "pm_admin_users"
    
    # Authentication
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Personal Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    
    # Status & Access
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Security
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    subscription_history_changes = db.relationship(
        'TenantSubscriptionHistory',
        back_populates='admin',
        lazy='dynamic'
    )
    
    @property
    def full_name(self):
        """Get full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_locked(self):
        """Check if account is locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def to_dict(self):
        """Convert model to dictionary."""
        data = super().to_dict()
        data.update({
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone": self.phone,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_locked": self.is_locked,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
        })
        return data
    
    def __repr__(self):
        """String representation."""
        return f"<PMAdminUser {self.email} - {self.full_name}>"

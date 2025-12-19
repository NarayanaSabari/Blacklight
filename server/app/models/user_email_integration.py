"""User Email Integration model for OAuth email connections."""

from datetime import datetime
from app import db
from app.models import BaseModel


class UserEmailIntegration(BaseModel):
    """
    Stores OAuth credentials and sync state for user email integrations.
    Supports Gmail and Outlook connections for job email scanning.
    """
    
    __tablename__ = "user_email_integrations"
    
    # Foreign Keys
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey('portal_users.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    tenant_id = db.Column(
        db.Integer, 
        db.ForeignKey('tenants.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    
    # Integration Type
    provider = db.Column(db.String(20), nullable=False)  # 'gmail' or 'outlook'
    
    # OAuth Credentials (ENCRYPTED)
    access_token_encrypted = db.Column(db.Text, nullable=False)
    refresh_token_encrypted = db.Column(db.Text, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    
    # Email Account Info
    email_address = db.Column(db.String(255), nullable=True)
    
    # Sync State
    is_active = db.Column(db.Boolean, default=True, index=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    consecutive_failures = db.Column(db.Integer, default=0)
    
    # Sync Configuration
    sync_frequency_minutes = db.Column(db.Integer, default=15)
    
    # Statistics
    emails_processed_count = db.Column(db.Integer, default=0)
    jobs_created_count = db.Column(db.Integer, default=0)
    
    # Relationships
    user = db.relationship('PortalUser', back_populates='email_integrations')
    tenant = db.relationship('Tenant')
    processed_emails = db.relationship(
        'ProcessedEmail', 
        back_populates='integration',
        cascade='all, delete-orphan'
    )
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('user_id', 'provider', name='uq_user_email_integration_user_provider'),
    )
    
    def to_dict(self):
        """Convert model to dictionary (excludes sensitive token data)."""
        data = super().to_dict()
        data.update({
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "provider": self.provider,
            "email_address": self.email_address,
            "is_active": self.is_active,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "sync_frequency_minutes": self.sync_frequency_minutes,
            "emails_processed_count": self.emails_processed_count,
            "jobs_created_count": self.jobs_created_count,
        })
        return data
    
    def __repr__(self):
        return f"<UserEmailIntegration {self.provider}:{self.email_address}>"

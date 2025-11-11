"""
Candidate Invitation Model
Manages self-onboarding invitations sent to candidates
"""
import secrets
from datetime import datetime, timedelta
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app import db
from app.models import BaseModel


class CandidateInvitation(BaseModel):
    """
    Candidate invitation model for self-onboarding workflow.
    Tracks invitations sent to candidates with email links.
    """
    __tablename__ = 'candidate_invitations'
    
    # Tenant relationship
    tenant_id = db.Column(Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Candidate information
    email = db.Column(String(255), nullable=False, index=True)
    first_name = db.Column(String(100))
    last_name = db.Column(String(100))
    
    # Token and security
    token = db.Column(String(100), nullable=False, unique=True, index=True)
    expires_at = db.Column(DateTime, nullable=False, index=True)
    
    # Status tracking
    status = db.Column(
        String(50),
        nullable=False,
        default='sent',
        index=True
    )
    # Status values: sent, opened, in_progress, submitted, approved, rejected, expired, cancelled
    
    # Invitation metadata
    invited_by_id = db.Column(Integer, ForeignKey('portal_users.id'), nullable=False, index=True)
    invited_at = db.Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Submission data
    invitation_data = db.Column(JSONB)  # Candidate's submitted form data
    submitted_at = db.Column(DateTime)
    
    # Review information
    reviewed_by_id = db.Column(Integer, ForeignKey('portal_users.id'), index=True)
    reviewed_at = db.Column(DateTime)
    review_notes = db.Column(Text)
    rejection_reason = db.Column(Text)
    
    # Link to created candidate (after approval)
    candidate_id = db.Column(Integer, ForeignKey('candidates.id'))
    
    # Relationships
    tenant = relationship('Tenant', backref='invitations')
    invited_by = relationship('PortalUser', foreign_keys=[invited_by_id], backref='sent_invitations')
    reviewed_by = relationship('PortalUser', foreign_keys=[reviewed_by_id], backref='reviewed_invitations')
    candidate = relationship('Candidate', backref='invitation', foreign_keys=[candidate_id])
    
    # Audit logs relationship (defined in InvitationAuditLog model)
    # audit_logs = relationship('InvitationAuditLog', back_populates='invitation')
    
    # Documents relationship (defined in CandidateDocument model)
    # documents = relationship('CandidateDocument', back_populates='invitation')
    
    @staticmethod
    def generate_token():
        """
        Generate a cryptographically secure random token.
        Returns a URL-safe base64-encoded string (~43 characters).
        """
        return secrets.token_urlsafe(32)
    
    @property
    def is_expired(self):
        """Check if invitation has expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self):
        """
        Check if invitation is valid for use.
        Valid if: not expired AND status is sent/opened/in_progress
        """
        if self.is_expired:
            return False
        return self.status in ['sent', 'opened', 'in_progress']
    
    @property
    def can_be_resent(self):
        """Check if invitation can be resent"""
        return self.status in ['sent', 'opened', 'in_progress', 'expired', 'cancelled']
    
    @property
    def time_until_expiry(self):
        """Get time until expiry as timedelta"""
        if self.is_expired:
            return timedelta(0)
        return self.expires_at - datetime.utcnow()
    
    def __repr__(self):
        return f'<CandidateInvitation {self.email} - {self.status}>'
    
    def to_dict(self, include_sensitive=False):
        """
        Convert invitation to dictionary.
        
        Args:
            include_sensitive: If True, include invitation_data and rejection_reason
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'status': self.status,
            'invited_by_id': self.invited_by_id,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired,
            'is_valid': self.is_valid,
            'can_be_resent': self.can_be_resent,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'reviewed_by_id': self.reviewed_by_id,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'candidate_id': self.candidate_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # Include sensitive data only if requested (for HR view)
        if include_sensitive:
            data.update({
                'token': self.token,
                'invitation_data': self.invitation_data,
                'review_notes': self.review_notes,
                'rejection_reason': self.rejection_reason,
            })
        
        return data

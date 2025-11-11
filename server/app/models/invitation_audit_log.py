"""
Invitation Audit Log Model
Tracks all actions performed on candidate invitations for audit trail
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app import db


class InvitationAuditLog(db.Model):
    """
    Audit log for candidate invitations.
    Immutable record of all actions performed on invitations.
    """
    __tablename__ = 'invitation_audit_logs'
    
    # Primary key
    id = db.Column(Integer, primary_key=True)
    
    # Foreign key to invitation
    invitation_id = db.Column(
        Integer,
        ForeignKey('candidate_invitations.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Action details
    action = db.Column(String(50), nullable=False, index=True)
    # Action values: invitation_sent, invitation_opened, invitation_submitted,
    #                invitation_approved, invitation_rejected, invitation_resent, invitation_cancelled
    
    # Who performed the action
    performed_by = db.Column(String(100))  # Format: 'portal_user:123' or 'candidate' or 'system'
    
    # Request metadata
    ip_address = db.Column(String(45))  # IPv4 or IPv6
    user_agent = db.Column(String(500))
    
    # Additional context
    extra_data = db.Column(JSONB)  # Flexible JSON for additional details
    
    # Timestamp (immutable)
    timestamp = db.Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationship to invitation
    invitation = relationship(
        'CandidateInvitation',
        backref='audit_logs',
        foreign_keys=[invitation_id]
    )
    
    # Validation constants
    VALID_ACTIONS = {
        'invitation_sent',
        'invitation_opened',
        'invitation_in_progress',
        'invitation_submitted',
        'invitation_approved',
        'invitation_rejected',
        'invitation_resent',
        'invitation_cancelled',
        'invitation_expired'
    }
    
    def __repr__(self):
        return f'<InvitationAuditLog {self.action} - invitation_id={self.invitation_id}>'
    
    @classmethod
    def log_action(cls, invitation_id, action, performed_by=None, ip_address=None, user_agent=None, extra_data=None):
        """
        Create a new audit log entry.
        
        Args:
            invitation_id: ID of the invitation
            action: Action performed (must be in VALID_ACTIONS)
            performed_by: Who performed the action (portal_user:ID, candidate, or system)
            ip_address: IP address of the requester
            user_agent: User agent string
            extra_data: Additional context as dict
            
        Returns:
            InvitationAuditLog: Created audit log entry
        """
        if action not in cls.VALID_ACTIONS:
            raise ValueError(f"Invalid action: {action}. Must be one of {cls.VALID_ACTIONS}")
        
        log_entry = cls(
            invitation_id=invitation_id,
            action=action,
            performed_by=performed_by,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data or {}
        )
        
        db.session.add(log_entry)
        # Note: Caller must commit the session
        
        return log_entry
    
    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            'id': self.id,
            'invitation_id': self.invitation_id,
            'action': self.action,
            'performed_by': self.performed_by,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'metadata': self.extra_data,  # Return as 'metadata' for API compatibility
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }

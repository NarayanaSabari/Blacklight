"""
AssignmentNotification Model
Tracks notifications for candidate assignments
"""
from datetime import datetime
from app import db


class AssignmentNotification(db.Model):
    """
    Tracks notifications related to candidate assignments.
    Allows users to see when they've been assigned candidates.
    """
    
    __tablename__ = 'assignment_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Notification Details
    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey('candidate_assignments.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('portal_users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Notification Type
    notification_type = db.Column(
        db.String(50),
        nullable=False
    )  # ASSIGNED, REASSIGNED, COMPLETED, CANCELLED
    
    # Read Status
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    assignment = db.relationship(
        'CandidateAssignment',
        backref=db.backref('notifications', cascade='all, delete-orphan')
    )
    # Note: passive_deletes=True tells SQLAlchemy to let the DB handle CASCADE deletes
    user = db.relationship(
        'PortalUser',
        backref=db.backref('assignment_notifications', passive_deletes=True)
    )
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_notification_user_id', 'user_id'),
        db.Index('idx_notification_is_read', 'is_read'),
        db.Index('idx_notification_type', 'notification_type'),
        db.Index('idx_notification_user_read', 'user_id', 'is_read'),
    )
    
    def __repr__(self):
        return f'<AssignmentNotification user={self.user_id} type={self.notification_type} read={self.is_read}>'
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
    
    def to_dict(self, include_assignment=False, include_user=False):
        """Convert notification to dictionary"""
        result = {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'user_id': self.user_id,
            'notification_type': self.notification_type,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_assignment and self.assignment:
            result['assignment'] = self.assignment.to_dict(include_users=True, include_candidate=True)
        
        if include_user and self.user:
            result['user'] = {
                'id': self.user.id,
                'email': self.user.email,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
            }
        
        return result

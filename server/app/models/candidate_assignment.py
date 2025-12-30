"""
CandidateAssignment Model
Tracks assignment history of candidates to managers/recruiters
"""
from datetime import datetime
from app import db


class CandidateAssignment(db.Model):
    """
    Tracks candidate assignment history.
    Records who assigned a candidate to whom, when, and why.
    """
    
    __tablename__ = 'candidate_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Assignment Details
    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey('candidates.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    assigned_to_user_id = db.Column(
        db.Integer,
        db.ForeignKey('portal_users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    assigned_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey('portal_users.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    
    # Assignment Type and Context
    assignment_type = db.Column(
        db.String(50),
        nullable=False,
        default='INITIAL'
    )  # INITIAL, REASSIGNMENT
    
    previous_assignee_id = db.Column(
        db.Integer,
        db.ForeignKey('portal_users.id', ondelete='SET NULL'),
        nullable=True
    )
    
    assignment_reason = db.Column(db.Text, nullable=True)
    
    # Timestamps
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Status
    status = db.Column(
        db.String(50),
        nullable=False,
        default='PENDING'
    )  # PENDING, ACCEPTED, REJECTED, COMPLETED, CANCELLED
    
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    # Note: passive_deletes=True tells SQLAlchemy to let the DB handle CASCADE deletes
    # This is needed because assigned_to_user_id has ondelete='CASCADE' and is NOT NULL
    assigned_to = db.relationship(
        'PortalUser',
        foreign_keys=[assigned_to_user_id],
        backref=db.backref('received_assignments', passive_deletes=True)
    )
    assigned_by = db.relationship(
        'PortalUser',
        foreign_keys=[assigned_by_user_id],
        backref=db.backref('made_assignments', passive_deletes=True)
    )
    previous_assignee = db.relationship(
        'PortalUser',
        foreign_keys=[previous_assignee_id],
        backref=db.backref('previous_assignments', passive_deletes=True)
    )
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_assignment_candidate_id', 'candidate_id'),
        db.Index('idx_assignment_assigned_to', 'assigned_to_user_id'),
        db.Index('idx_assignment_status', 'status'),
        db.Index('idx_assignment_type', 'assignment_type'),
    )
    
    def __repr__(self):
        return f'<CandidateAssignment candidate={self.candidate_id} assigned_to={self.assigned_to_user_id}>'
    
    def to_dict(self, include_users=False, include_candidate=False):
        """Convert assignment to dictionary"""
        result = {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'assigned_to_user_id': self.assigned_to_user_id,
            'assigned_by_user_id': self.assigned_by_user_id,
            'assignment_type': self.assignment_type,
            'previous_assignee_id': self.previous_assignee_id,
            'assignment_reason': self.assignment_reason,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'notes': self.notes,
        }
        
        if include_users:
            if self.assigned_to:
                result['assigned_to'] = {
                    'id': self.assigned_to.id,
                    'email': self.assigned_to.email,
                    'first_name': self.assigned_to.first_name,
                    'last_name': self.assigned_to.last_name,
                }
            if self.assigned_by:
                result['assigned_by'] = {
                    'id': self.assigned_by.id,
                    'email': self.assigned_by.email,
                    'first_name': self.assigned_by.first_name,
                    'last_name': self.assigned_by.last_name,
                }
            if self.previous_assignee:
                result['previous_assignee'] = {
                    'id': self.previous_assignee.id,
                    'email': self.previous_assignee.email,
                    'first_name': self.previous_assignee.first_name,
                    'last_name': self.previous_assignee.last_name,
                }
        
        if include_candidate and self.candidate:
            result['candidate'] = {
                'id': self.candidate.id,
                'first_name': self.candidate.first_name,
                'last_name': self.candidate.last_name,
                'email': self.candidate.email,
                'status': self.candidate.status,
                'onboarding_status': self.candidate.onboarding_status,
            }
        
        return result

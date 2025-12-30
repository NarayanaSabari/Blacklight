"""
Submission Activity Model
Tracks all activities and notes on a submission for audit trail and communication.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from app import db


class ActivityType:
    """Activity type constants."""
    CREATED = "CREATED"                     # Submission created
    STATUS_CHANGE = "STATUS_CHANGE"         # Status changed
    NOTE = "NOTE"                           # Manual note added
    EMAIL_SENT = "EMAIL_SENT"               # Submission email sent
    EMAIL_RECEIVED = "EMAIL_RECEIVED"       # Response received
    CALL_LOGGED = "CALL_LOGGED"             # Phone call logged
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"  # Interview scheduled
    INTERVIEW_COMPLETED = "INTERVIEW_COMPLETED"  # Interview done with feedback
    INTERVIEW_CANCELLED = "INTERVIEW_CANCELLED"  # Interview cancelled
    RATE_UPDATED = "RATE_UPDATED"           # Bill/pay rate changed
    VENDOR_UPDATED = "VENDOR_UPDATED"       # Vendor info changed
    PRIORITY_CHANGED = "PRIORITY_CHANGED"   # Priority changed
    FOLLOW_UP_SET = "FOLLOW_UP_SET"         # Follow-up date set
    RESUME_SENT = "RESUME_SENT"             # Resume sent to vendor
    CLIENT_FEEDBACK = "CLIENT_FEEDBACK"     # Feedback from client
    
    @classmethod
    def all(cls) -> list[str]:
        return [
            cls.CREATED, cls.STATUS_CHANGE, cls.NOTE, cls.EMAIL_SENT,
            cls.EMAIL_RECEIVED, cls.CALL_LOGGED, cls.INTERVIEW_SCHEDULED,
            cls.INTERVIEW_COMPLETED, cls.INTERVIEW_CANCELLED, cls.RATE_UPDATED,
            cls.VENDOR_UPDATED, cls.PRIORITY_CHANGED, cls.FOLLOW_UP_SET,
            cls.RESUME_SENT, cls.CLIENT_FEEDBACK
        ]


class SubmissionActivity(db.Model):
    """
    Tracks activities on a submission.
    
    Every action on a submission creates an activity record:
    - Status changes (automatic)
    - Notes added by recruiters
    - Emails sent/received
    - Interview scheduling
    - Rate changes
    - Vendor updates
    """
    __tablename__ = 'submission_activities'
    
    id = db.Column(Integer, primary_key=True)
    
    # Core Relationships
    submission_id = db.Column(
        Integer,
        ForeignKey('submissions.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    created_by_id = db.Column(
        Integer,
        ForeignKey('portal_users.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    
    # Activity Details
    activity_type = db.Column(String(50), nullable=False, index=True)
    content = db.Column(Text)  # Note content or description
    
    # For tracking changes (STATUS_CHANGE, RATE_UPDATED, etc.)
    old_value = db.Column(String(255))  # Previous value
    new_value = db.Column(String(255))  # New value
    
    # Metadata for extra info (email details, interview info, etc.)
    # Note: Python attribute is 'activity_metadata' to avoid SQLAlchemy reserved name collision,
    # but the database column is still named 'metadata' for backward compatibility.
    activity_metadata = db.Column('metadata', JSONB, default=dict)
    # Example activity_metadata:
    # For EMAIL_SENT: {"to": "vendor@example.com", "subject": "Candidate Submission"}
    # For INTERVIEW_SCHEDULED: {"date": "2025-01-15T14:00:00", "type": "VIDEO", "with": "Hiring Manager"}
    # For RATE_UPDATED: {"old_bill": 100, "new_bill": 110, "old_pay": 80, "new_pay": 85}
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    submission = db.relationship('Submission', back_populates='activities')
    created_by = db.relationship(
        'PortalUser',
        backref='submission_activities_created'
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_submission_activity_submission_created', 'submission_id', 'created_at', postgresql_ops={'created_at': 'DESC'}),
        Index('idx_submission_activity_type', 'activity_type'),
    )
    
    def __repr__(self):
        return f'<SubmissionActivity {self.id} submission={self.submission_id} type={self.activity_type}>'
    
    def to_dict(self, include_created_by: bool = True) -> dict:
        """Convert activity to dictionary."""
        result = {
            'id': self.id,
            'submission_id': self.submission_id,
            'activity_type': self.activity_type,
            'content': self.content,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'metadata': self.activity_metadata or {},  # Return as 'metadata' for API compatibility
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_id': self.created_by_id,
        }
        
        if include_created_by and self.created_by:
            result['created_by'] = {
                'id': self.created_by.id,
                'email': self.created_by.email,
                'first_name': self.created_by.first_name,
                'last_name': self.created_by.last_name,
            }
        
        return result
    
    @classmethod
    def create_status_change(
        cls,
        submission_id: int,
        old_status: str,
        new_status: str,
        created_by_id: int | None,
        note: str | None = None
    ) -> 'SubmissionActivity':
        """Create a status change activity."""
        return cls(
            submission_id=submission_id,
            activity_type=ActivityType.STATUS_CHANGE,
            old_value=old_status,
            new_value=new_status,
            content=note or f"Status changed from {old_status} to {new_status}",
            created_by_id=created_by_id,
        )
    
    @classmethod
    def create_note(
        cls,
        submission_id: int,
        content: str,
        created_by_id: int | None
    ) -> 'SubmissionActivity':
        """Create a note activity."""
        return cls(
            submission_id=submission_id,
            activity_type=ActivityType.NOTE,
            content=content,
            created_by_id=created_by_id,
        )
    
    @classmethod
    def create_interview_scheduled(
        cls,
        submission_id: int,
        interview_date: datetime,
        interview_type: str,
        created_by_id: int | None,
        note: str | None = None,
        location: str | None = None
    ) -> 'SubmissionActivity':
        """Create an interview scheduled activity."""
        return cls(
            submission_id=submission_id,
            activity_type=ActivityType.INTERVIEW_SCHEDULED,
            content=note or f"Interview scheduled for {interview_date.strftime('%B %d, %Y at %I:%M %p')}",
            created_by_id=created_by_id,
            activity_metadata={
                'date': interview_date.isoformat(),
                'type': interview_type,
                'location': location,
            }
        )

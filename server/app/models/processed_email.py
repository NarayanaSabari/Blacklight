"""Processed Email model for tracking which emails have been processed."""

from app import db
from app.models import BaseModel


class ProcessedEmail(BaseModel):
    """
    Tracks which emails have been processed to avoid reprocessing.
    Stores minimal metadata for deduplication and auditing.
    """
    
    __tablename__ = "processed_emails"
    
    # Foreign Keys
    integration_id = db.Column(
        db.Integer, 
        db.ForeignKey('user_email_integrations.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    tenant_id = db.Column(
        db.Integer, 
        db.ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Email Identification (for deduplication)
    email_message_id = db.Column(db.String(255), nullable=False)  # RFC 2822 Message-ID
    email_thread_id = db.Column(db.String(255), nullable=True)    # Gmail/Outlook thread ID
    
    # Processing Result
    processing_result = db.Column(db.String(50), nullable=False)  # job_created, skipped, failed, irrelevant
    
    # Link to created job (if applicable)
    job_id = db.Column(
        db.Integer, 
        db.ForeignKey('job_postings.id', ondelete='SET NULL'), 
        nullable=True
    )
    
    # Email Metadata (for auditing, not full content)
    email_subject = db.Column(db.String(500), nullable=True)
    email_sender = db.Column(db.String(255), nullable=True)
    
    # Skip/Fail reason
    skip_reason = db.Column(db.String(255), nullable=True)
    
    # AI Parsing Metadata
    parsing_confidence = db.Column(db.Float, nullable=True)  # 0.0 - 1.0
    
    # Relationships
    integration = db.relationship('UserEmailIntegration', back_populates='processed_emails')
    job = db.relationship('JobPosting')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('integration_id', 'email_message_id', name='uq_processed_email_integration_message'),
    )
    
    def to_dict(self):
        """Convert model to dictionary."""
        data = super().to_dict()
        data.update({
            "integration_id": self.integration_id,
            "tenant_id": self.tenant_id,
            "email_message_id": self.email_message_id,
            "email_thread_id": self.email_thread_id,
            "processed_at": self.created_at.isoformat() if self.created_at else None,  # Use created_at as processed_at
            "processing_result": self.processing_result,
            "job_id": self.job_id,
            "email_subject": self.email_subject,
            "email_sender": self.email_sender,
            "skip_reason": self.skip_reason,
            "parsing_confidence": self.parsing_confidence,
        })
        return data
    
    def __repr__(self):
        return f"<ProcessedEmail {self.email_message_id[:30]}... result={self.processing_result}>"

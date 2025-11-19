"""
Job Application Model
Tracks actual job applications submitted by candidates
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Index
from app import db


class JobApplication(db.Model):
    """
    Tracks when candidates apply to jobs.
    Links candidates to job postings with application status tracking.
    """
    __tablename__ = 'job_applications'
    
    id = db.Column(Integer, primary_key=True)
    
    # Relationships
    candidate_id = db.Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False, index=True)
    job_posting_id = db.Column(Integer, ForeignKey('job_postings.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Application Details
    application_status = db.Column(
        String(50), 
        default='APPLIED',
        index=True
    )  # APPLIED, SCREENING, INTERVIEWING, OFFER, ACCEPTED, REJECTED, WITHDRAWN
    
    applied_via = db.Column(String(50))  # PLATFORM, DIRECT, REFERRAL
    applied_by_user_id = db.Column(Integer, ForeignKey('portal_users.id', ondelete='SET NULL'))  # Recruiter who applied on behalf
    
    # Timeline
    applied_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    screened_at = db.Column(DateTime)
    interviewed_at = db.Column(DateTime)
    offer_received_at = db.Column(DateTime)
    offer_accepted_at = db.Column(DateTime)
    rejected_at = db.Column(DateTime)
    
    # Communication
    cover_letter = db.Column(Text)
    notes = db.Column(Text)
    feedback = db.Column(Text)  # From employer
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    candidate = db.relationship('Candidate', backref='job_applications')
    job_posting = db.relationship('JobPosting', back_populates='applications')
    applied_by = db.relationship('PortalUser', backref='applications_made', foreign_keys=[applied_by_user_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_job_application_unique', 'candidate_id', 'job_posting_id', unique=True),
        Index('idx_job_application_candidate_status', 'candidate_id', 'application_status'),
        Index('idx_job_application_applied_at_desc', 'applied_at', postgresql_ops={'applied_at': 'DESC'}),
    )
    
    def __repr__(self):
        return f'<JobApplication candidate={self.candidate_id} job={self.job_posting_id} status={self.application_status}>'
    
    def to_dict(self, include_candidate=False, include_job=False, include_applied_by=False):
        """Convert application to dictionary"""
        result = {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'job_posting_id': self.job_posting_id,
            'application_status': self.application_status,
            'applied_via': self.applied_via,
            'applied_by_user_id': self.applied_by_user_id,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'screened_at': self.screened_at.isoformat() if self.screened_at else None,
            'interviewed_at': self.interviewed_at.isoformat() if self.interviewed_at else None,
            'offer_received_at': self.offer_received_at.isoformat() if self.offer_received_at else None,
            'offer_accepted_at': self.offer_accepted_at.isoformat() if self.offer_accepted_at else None,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'cover_letter': self.cover_letter,
            'notes': self.notes,
            'feedback': self.feedback,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_candidate and self.candidate:
            result['candidate'] = {
                'id': self.candidate.id,
                'first_name': self.candidate.first_name,
                'last_name': self.candidate.last_name,
                'email': self.candidate.email,
                'current_title': self.candidate.current_title,
            }
        
        if include_job and self.job_posting:
            result['job'] = self.job_posting.to_dict(include_description=False)
        
        if include_applied_by and self.applied_by:
            result['applied_by'] = {
                'id': self.applied_by.id,
                'email': self.applied_by.email,
                'first_name': self.applied_by.first_name,
                'last_name': self.applied_by.last_name,
            }
        
        return result
    
    @property
    def days_since_applied(self):
        """Calculate days since application was submitted"""
        if self.applied_at:
            return (datetime.utcnow() - self.applied_at).days
        return None
    
    @property
    def is_active(self):
        """Check if application is still active (not rejected/accepted/withdrawn)"""
        inactive_statuses = ['ACCEPTED', 'REJECTED', 'WITHDRAWN']
        return self.application_status not in inactive_statuses

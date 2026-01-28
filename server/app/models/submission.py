"""
Submission Model
Tracks candidate submissions to job postings by recruiters.
Core model for the ATS (Applicant Tracking System) functionality.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    String, Integer, Text, DateTime, Boolean, 
    ForeignKey, Index, DECIMAL, ARRAY
)
from sqlalchemy.dialects.postgresql import JSONB
from app import db


class SubmissionStatus:
    """Submission status constants."""
    SUBMITTED = "SUBMITTED"           # Initial submission to vendor
    CLIENT_REVIEW = "CLIENT_REVIEW"   # Vendor sent to client
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"  # Interview set up
    INTERVIEWED = "INTERVIEWED"       # Interview completed
    OFFERED = "OFFERED"               # Offer extended
    PLACED = "PLACED"                 # Candidate placed (won!)
    REJECTED = "REJECTED"             # Rejected at any stage
    WITHDRAWN = "WITHDRAWN"           # Recruiter withdrew submission
    ON_HOLD = "ON_HOLD"               # Temporarily on hold
    
    @classmethod
    def all(cls) -> list[str]:
        return [
            cls.SUBMITTED, cls.CLIENT_REVIEW, cls.INTERVIEW_SCHEDULED,
            cls.INTERVIEWED, cls.OFFERED, cls.PLACED, 
            cls.REJECTED, cls.WITHDRAWN, cls.ON_HOLD
        ]
    
    @classmethod
    def active(cls) -> list[str]:
        """Statuses that are still in progress."""
        return [
            cls.SUBMITTED, cls.CLIENT_REVIEW, cls.INTERVIEW_SCHEDULED,
            cls.INTERVIEWED, cls.OFFERED, cls.ON_HOLD
        ]
    
    @classmethod
    def terminal(cls) -> list[str]:
        """Final statuses (no further action)."""
        return [cls.PLACED, cls.REJECTED, cls.WITHDRAWN]


class Submission(db.Model):
    """
    Tracks when a recruiter submits a candidate to a job posting.
    
    This is the core ATS model for bench recruiters to track:
    - Which candidates were submitted to which jobs
    - Current status in the hiring pipeline
    - Vendor/client information
    - Bill and pay rates
    - Activity history
    """
    __tablename__ = 'submissions'
    
    id = db.Column(Integer, primary_key=True)
    
    # Core Relationships
    candidate_id = db.Column(
        Integer, 
        ForeignKey('candidates.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    # job_posting_id is nullable to support external/manual job submissions
    job_posting_id = db.Column(
        Integer, 
        ForeignKey('job_postings.id', ondelete='CASCADE'), 
        nullable=True,  # Nullable for external jobs
        index=True
    )
    
    # External Job Fields (for jobs not in the portal)
    # These are used when job_posting_id is NULL
    is_external_job = db.Column(Boolean, default=False, nullable=False)
    external_job_title = db.Column(String(255))
    external_job_company = db.Column(String(255))
    external_job_location = db.Column(String(255))
    external_job_url = db.Column(String(1000))  # URL to the original job posting
    external_job_description = db.Column(Text)  # Brief description or notes about the job
    submitted_by_user_id = db.Column(
        Integer, 
        ForeignKey('portal_users.id', ondelete='SET NULL'), 
        nullable=True, 
        index=True
    )
    tenant_id = db.Column(
        Integer, 
        ForeignKey('tenants.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Status Tracking
    status = db.Column(
        String(50), 
        nullable=False, 
        default=SubmissionStatus.SUBMITTED,
        index=True
    )
    status_changed_at = db.Column(DateTime, default=datetime.utcnow)
    status_changed_by_id = db.Column(
        Integer, 
        ForeignKey('portal_users.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # Vendor/Client Information
    vendor_company = db.Column(String(255))  # Vendor/Staffing agency name
    vendor_contact_name = db.Column(String(255))  # Contact person
    vendor_contact_email = db.Column(String(255))  # Contact email
    vendor_contact_phone = db.Column(String(50))  # Contact phone
    client_company = db.Column(String(255))  # End client company (if known)
    
    # Rate Information
    bill_rate = db.Column(DECIMAL(10, 2))  # What client pays ($/hr)
    pay_rate = db.Column(DECIMAL(10, 2))   # What candidate gets ($/hr)
    rate_type = db.Column(String(20), default='HOURLY')  # HOURLY, DAILY, WEEKLY, MONTHLY, ANNUAL
    currency = db.Column(String(10), default='USD')
    
    # Submission Details
    submission_notes = db.Column(Text)  # Notes about the submission
    cover_letter = db.Column(Text)  # Cover letter if sent
    resume_version_used = db.Column(String(255))  # Which resume was sent
    tailored_resume_id = db.Column(
        Integer, 
        ForeignKey('tailored_resumes.id', ondelete='SET NULL'),
        nullable=True
    )  # If a tailored resume was used
    
    # Interview Information
    interview_scheduled_at = db.Column(DateTime)  # Interview date/time
    interview_type = db.Column(String(50))  # PHONE, VIDEO, ONSITE, TECHNICAL
    interview_location = db.Column(String(500))  # Location or video link
    interview_notes = db.Column(Text)  # Pre-interview notes
    interview_feedback = db.Column(Text)  # Post-interview feedback
    
    # Outcome Information
    rejection_reason = db.Column(Text)  # If rejected, why
    rejection_stage = db.Column(String(50))  # At which stage rejected
    withdrawal_reason = db.Column(Text)  # If withdrawn, why
    
    # Placement Information (if placed)
    placement_start_date = db.Column(DateTime)  # When candidate starts
    placement_end_date = db.Column(DateTime)  # Contract end date (if known)
    placement_duration_months = db.Column(Integer)  # Expected duration
    
    # Priority and Flags
    priority = db.Column(String(20), default='MEDIUM')  # HIGH, MEDIUM, LOW
    is_hot = db.Column(Boolean, default=False)  # Hot/urgent submission
    follow_up_date = db.Column(DateTime)  # When to follow up
    
    # Timestamps
    submitted_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    candidate = db.relationship('Candidate', backref=db.backref('submissions', lazy='dynamic'))
    job_posting = db.relationship('JobPosting', backref=db.backref('submissions', lazy='dynamic'))
    submitted_by = db.relationship(
        'PortalUser', 
        foreign_keys=[submitted_by_user_id],
        backref='submissions_made'
    )
    status_changed_by = db.relationship(
        'PortalUser',
        foreign_keys=[status_changed_by_id],
        backref='submission_status_changes'
    )
    tenant = db.relationship('Tenant', backref=db.backref('submissions', lazy='dynamic'))
    tailored_resume = db.relationship('TailoredResume', backref='submission')
    activities = db.relationship(
        'SubmissionActivity',
        back_populates='submission',
        cascade='all, delete-orphan',
        order_by='desc(SubmissionActivity.created_at)'
    )
    
    # Indexes
    __table_args__ = (
        # Unique constraint: one submission per candidate per job per tenant
        # Note: This only applies to internal jobs (job_posting_id NOT NULL)
        # External jobs are not constrained by this index
        Index('idx_submission_unique', 'candidate_id', 'job_posting_id', 'tenant_id', unique=True, postgresql_where=db.text('job_posting_id IS NOT NULL')),
        # Common query patterns
        Index('idx_submission_tenant_status', 'tenant_id', 'status'),
        Index('idx_submission_submitted_at', 'submitted_at', postgresql_ops={'submitted_at': 'DESC'}),
        Index('idx_submission_submitted_by', 'submitted_by_user_id', 'status'),
        # External job queries
        Index('idx_submission_external', 'tenant_id', 'is_external_job'),
    )
    
    def __repr__(self):
        return f'<Submission {self.id} candidate={self.candidate_id} job={self.job_posting_id} status={self.status}>'
    
    def to_dict(
        self, 
        include_candidate: bool = False, 
        include_job: bool = False,
        include_submitted_by: bool = False,
        include_activities: bool = False,
        include_rates: bool = True
    ) -> dict:
        """Convert submission to dictionary."""
        result = {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'job_posting_id': self.job_posting_id,
            'submitted_by_user_id': self.submitted_by_user_id,
            'tenant_id': self.tenant_id,
            
            # External Job Info
            'is_external_job': self.is_external_job,
            'external_job_title': self.external_job_title,
            'external_job_company': self.external_job_company,
            'external_job_location': self.external_job_location,
            'external_job_url': self.external_job_url,
            'external_job_description': self.external_job_description,
            
            # Status
            'status': self.status,
            'status_changed_at': self.status_changed_at.isoformat() if self.status_changed_at else None,
            
            # Vendor Info
            'vendor_company': self.vendor_company,
            'vendor_contact_name': self.vendor_contact_name,
            'vendor_contact_email': self.vendor_contact_email,
            'vendor_contact_phone': self.vendor_contact_phone,
            'client_company': self.client_company,
            
            # Notes
            'submission_notes': self.submission_notes,
            'tailored_resume_id': self.tailored_resume_id,
            
            # Interview
            'interview_scheduled_at': self.interview_scheduled_at.isoformat() if self.interview_scheduled_at else None,
            'interview_type': self.interview_type,
            'interview_location': self.interview_location,
            'interview_notes': self.interview_notes,
            'interview_feedback': self.interview_feedback,
            
            # Outcome
            'rejection_reason': self.rejection_reason,
            'rejection_stage': self.rejection_stage,
            'withdrawal_reason': self.withdrawal_reason,
            
            # Placement
            'placement_start_date': self.placement_start_date.isoformat() if self.placement_start_date else None,
            'placement_end_date': self.placement_end_date.isoformat() if self.placement_end_date else None,
            'placement_duration_months': self.placement_duration_months,
            
            # Priority
            'priority': self.priority,
            'is_hot': self.is_hot,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            
            # Timestamps
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # Rate info (optional, might be sensitive)
        if include_rates:
            result.update({
                'bill_rate': float(self.bill_rate) if self.bill_rate else None,
                'pay_rate': float(self.pay_rate) if self.pay_rate else None,
                'rate_type': self.rate_type,
                'currency': self.currency,
                'margin': self.margin,
                'margin_percentage': self.margin_percentage,
            })
        
        # Include related objects
        if include_candidate and self.candidate:
            result['candidate'] = {
                'id': self.candidate.id,
                'first_name': self.candidate.first_name,
                'last_name': self.candidate.last_name,
                'email': self.candidate.email,
                'phone': self.candidate.phone,
                'current_title': self.candidate.current_title,
                'skills': self.candidate.skills,
                'location': self.candidate.location,
                'visa_type': self.candidate.visa_type,
            }
        
        if include_job:
            if self.job_posting:
                result['job'] = {
                    'id': self.job_posting.id,
                    'title': self.job_posting.title,
                    'company': self.job_posting.company,
                    'location': self.job_posting.location,
                    'job_type': self.job_posting.job_type,
                    'is_remote': self.job_posting.is_remote,
                    'platform': self.job_posting.platform,
                    'job_url': self.job_posting.job_url,
                }
            elif self.is_external_job:
                # Return external job info when job_posting is null
                result['job'] = {
                    'id': None,
                    'title': self.external_job_title,
                    'company': self.external_job_company,
                    'location': self.external_job_location,
                    'job_type': None,
                    'is_remote': None,
                    'platform': 'external',
                    'job_url': self.external_job_url,
                }
        
        if include_submitted_by and self.submitted_by:
            result['submitted_by'] = {
                'id': self.submitted_by.id,
                'email': self.submitted_by.email,
                'first_name': self.submitted_by.first_name,
                'last_name': self.submitted_by.last_name,
            }
        
        if include_activities:
            activities_list = list(self.activities) if self.activities else []  # type: ignore
            result['activities'] = [
                activity.to_dict() for activity in activities_list[:10]  # Last 10 activities
            ]
        
        return result
    
    @property
    def margin(self) -> float | None:
        """Calculate margin (bill_rate - pay_rate)."""
        if self.bill_rate and self.pay_rate:
            return float(self.bill_rate - self.pay_rate)
        return None
    
    @property
    def margin_percentage(self) -> float | None:
        """Calculate margin percentage."""
        if self.bill_rate and self.pay_rate and self.bill_rate > 0:
            return round(float((self.bill_rate - self.pay_rate) / self.bill_rate * 100), 2)
        return None
    
    @property
    def days_since_submitted(self) -> int | None:
        """Calculate days since submission."""
        if self.submitted_at:
            return (datetime.utcnow() - self.submitted_at).days
        return None
    
    @property
    def is_active(self) -> bool:
        """Check if submission is still active."""
        return self.status in SubmissionStatus.active()
    
    @property
    def is_terminal(self) -> bool:
        """Check if submission has reached a terminal state."""
        return self.status in SubmissionStatus.terminal()

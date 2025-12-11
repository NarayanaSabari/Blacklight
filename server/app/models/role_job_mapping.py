"""
Role Job Mapping Model
Links jobs to the role that triggered their scrape.

This enables:
- Tracking which jobs came from which role scrape
- Finding all jobs for a specific role
- Understanding which roles produce the most jobs
"""
from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, Index, UniqueConstraint
from app import db


class RoleJobMapping(db.Model):
    """
    Links job postings to the global role that triggered their import.
    
    When external scraper posts jobs for a role:
    1. Jobs are imported into job_postings table
    2. RoleJobMapping records link each job to the source role
    3. This enables finding all jobs for a role, and all roles that found a job
    
    Note: A job can be found by multiple roles (e.g., "Python Developer" and
    "Backend Engineer" might both find the same job posting).
    """
    __tablename__ = 'role_job_mappings'
    
    id = db.Column(Integer, primary_key=True)
    
    # Foreign Keys
    global_role_id = db.Column(
        Integer,
        ForeignKey('global_roles.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    job_posting_id = db.Column(
        Integer,
        ForeignKey('job_postings.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Audit - when was this job found for this role
    scraped_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    global_role = db.relationship('GlobalRole', back_populates='role_job_mappings')
    job_posting = db.relationship('JobPosting', back_populates='role_job_mappings')
    
    # Indexes and Constraints
    __table_args__ = (
        # Unique: one mapping per role-job pair
        UniqueConstraint('global_role_id', 'job_posting_id', name='uq_role_job_mapping'),
        # Role lookup (get jobs for a role)
        Index('idx_role_job_mapping_role', 'global_role_id'),
        # Job lookup (which roles found this job)
        Index('idx_role_job_mapping_job', 'job_posting_id'),
    )
    
    def __repr__(self):
        return f'<RoleJobMapping role={self.global_role_id} job={self.job_posting_id}>'
    
    def to_dict(self, include_role=False, include_job=False):
        """Convert to dictionary."""
        result = {
            'id': self.id,
            'global_role_id': self.global_role_id,
            'job_posting_id': self.job_posting_id,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_role and self.global_role:
            result['global_role'] = self.global_role.to_dict()
        
        if include_job and self.job_posting:
            result['job_posting'] = self.job_posting.to_dict(include_description=False)
        
        return result

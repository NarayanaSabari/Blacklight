"""
Job Import Batch Model
Tracks job import operations and their results
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from app import db


class JobImportBatch(db.Model):
    """
    Tracks job import batches for auditing and debugging.
    Each import operation creates a batch record.
    
    NOTE: Job imports are managed by PM_ADMIN (product owner) at the platform level.
    No tenant association needed since jobs are global across all tenants.
    """
    __tablename__ = 'job_import_batches'
    
    id = db.Column(Integer, primary_key=True)
    
    # Batch Identification
    batch_id = db.Column(String(255), nullable=False, unique=True, index=True)
    platform = db.Column(String(50), nullable=False, index=True)  # indeed, dice, techfetch, glassdoor, monster
    import_source = db.Column(String(100), nullable=False)  # "manual_upload", "scheduled_sync", "api"
    
    # Import Statistics
    total_jobs = db.Column(Integer, nullable=False, default=0)
    new_jobs = db.Column(Integer, default=0)
    updated_jobs = db.Column(Integer, default=0)
    failed_jobs = db.Column(Integer, default=0)
    
    # Import Details
    import_status = db.Column(String(50), default='IN_PROGRESS', index=True)  # IN_PROGRESS, COMPLETED, FAILED
    error_log = db.Column(JSONB)  # Array of error objects
    
    # Timestamps
    started_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(DateTime)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_job_import_batch_platform', 'platform'),
        Index('idx_job_import_batch_status', 'import_status'),
        Index('idx_job_import_batch_started_at_desc', 'started_at', postgresql_ops={'started_at': 'DESC'}),
    )
    
    def __repr__(self):
        return f'<JobImportBatch {self.batch_id} - {self.import_status}>'
    
    def to_dict(self):
        """Convert batch to dictionary"""
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'platform': self.platform,
            'import_source': self.import_source,
            'total_jobs': self.total_jobs,
            'new_jobs': self.new_jobs,
            'updated_jobs': self.updated_jobs,
            'failed_jobs': self.failed_jobs,
            'import_status': self.import_status,
            'error_log': self.error_log,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'duration_seconds': self.duration_seconds,
            'success_rate': self.success_rate,
        }
    
    @property
    def duration_seconds(self):
        """Calculate import duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None
    
    @property
    def success_rate(self):
        """Calculate success rate as percentage"""
        if self.total_jobs > 0:
            successful = self.new_jobs + self.updated_jobs
            return round((successful / self.total_jobs) * 100, 2)
        return 0.0
    
    def add_error(self, error_message, job_data=None):
        """Add an error to the error log"""
        if self.error_log is None:
            self.error_log = []
        
        error_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'message': error_message,
        }
        
        if job_data:
            error_entry['job_data'] = job_data
        
        self.error_log.append(error_entry)
        self.failed_jobs += 1

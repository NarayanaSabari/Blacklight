"""
Session Platform Status Model
Tracks per-platform status within a scrape session (platform checklist).
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app import db


class SessionPlatformStatus(db.Model):
    """
    Tracks the status of each platform within a scrape session.
    
    When a session is created, an entry is created for each active platform.
    As the scraper submits jobs for each platform, the status is updated.
    
    Status Flow:
    - pending: Waiting for scraper to submit jobs
    - in_progress: Scraper is currently processing this platform
    - completed: Jobs submitted successfully
    - failed: Scraper reported failure for this platform
    - skipped: Platform was skipped (disabled or not applicable)
    """
    __tablename__ = 'session_platform_status'
    
    id = db.Column(Integer, primary_key=True)
    
    # Session Reference
    session_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey('scrape_sessions.session_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Platform Reference
    platform_id = db.Column(
        Integer,
        ForeignKey('scraper_platforms.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Platform name (cached for easy access)
    platform_name = db.Column(String(50), nullable=False)
    
    # Status
    status = db.Column(String(20), default='pending', nullable=False, index=True)
    # pending: Waiting for submission
    # in_progress: Currently being processed
    # completed: Successfully submitted
    # failed: Failed with error
    # skipped: Skipped (platform disabled)
    
    # Results
    jobs_found = db.Column(Integer, default=0)
    jobs_imported = db.Column(Integer, default=0)
    jobs_skipped = db.Column(Integer, default=0)
    
    # Batch Tracking (for handling large job lists split across multiple Inngest events)
    total_batches = db.Column(Integer, default=1)  # Total number of batches for this platform
    completed_batches = db.Column(Integer, default=0)  # Number of batches completed
    
    # Error Tracking
    error_message = db.Column(Text, nullable=True)
    
    # Timing
    started_at = db.Column(DateTime, nullable=True)  # When scraper started this platform
    completed_at = db.Column(DateTime, nullable=True)  # When submission received
    duration_seconds = db.Column(Integer, nullable=True)
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    session = db.relationship('ScrapeSession', back_populates='platform_statuses')
    platform = db.relationship('ScraperPlatform', back_populates='session_statuses')
    
    # Constraints
    __table_args__ = (
        # Only one entry per platform per session
        UniqueConstraint('session_id', 'platform_id', name='uq_session_platform'),
        # Indexes for common queries
        Index('idx_session_platform_status', 'session_id', 'status'),
    )
    
    def __repr__(self):
        return f'<SessionPlatformStatus session={self.session_id} platform={self.platform_name} status={self.status}>'
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'session_id': str(self.session_id),
            'platform_id': self.platform_id,
            'platform_name': self.platform_name,
            'status': self.status,
            'jobs_found': self.jobs_found,
            'jobs_imported': self.jobs_imported,
            'jobs_skipped': self.jobs_skipped,
            'total_batches': self.total_batches,
            'completed_batches': self.completed_batches,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def mark_completed(self, jobs_found: int, jobs_imported: int, jobs_skipped: int):
        """Mark platform as completed with results."""
        self.completed_at = datetime.utcnow()
        self.jobs_found = jobs_found
        self.jobs_imported = jobs_imported
        self.jobs_skipped = jobs_skipped
        self.status = 'completed'
        
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
    
    def mark_failed(self, error_message: str):
        """Mark platform as failed with error message."""
        self.completed_at = datetime.utcnow()
        self.status = 'failed'
        self.error_message = error_message
        
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
    
    def mark_in_progress(self):
        """Mark platform as in progress (scraper started)."""
        self.started_at = datetime.utcnow()
        self.status = 'in_progress'

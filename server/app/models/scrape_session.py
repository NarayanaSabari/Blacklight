"""
Scrape Session Model
Simplified session tracking for scraper observability.

Sessions are created when scraper fetches a role and completed when scraper posts jobs.
This enables monitoring of scraper health, performance, and job import statistics.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app import db


class ScrapeSession(db.Model):
    """
    Simplified session tracking for scraper observability.
    
    Session Lifecycle:
    1. Scraper calls: GET /api/scraper/queue/next-role
       → Session created with status="in_progress"
       → session_id returned to scraper
       → global_role.queue_status = "processing"

    2. Scraper scrapes job boards for the role
       (No intermediate updates needed - simplified)

    3. Scraper calls: POST /api/scraper/queue/jobs
       → Session status="completed"
       → jobs_found, jobs_imported, jobs_skipped recorded
       → duration_seconds calculated
       → global_role.queue_status = "completed"
       → Inngest event triggered: "jobs/imported"
    """
    __tablename__ = 'scrape_sessions'
    
    id = db.Column(Integer, primary_key=True)
    
    # Unique session identifier (UUID)
    session_id = db.Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    
    # Scraper Identification
    scraper_key_id = db.Column(
        Integer,
        ForeignKey('scraper_api_keys.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    scraper_name = db.Column(String(100), nullable=True)  # Cached from API key for reporting
    
    # What's Being Scraped
    global_role_id = db.Column(
        Integer,
        ForeignKey('global_roles.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    role_name = db.Column(String(255), nullable=True)  # Cached role name for reporting
    
    # Timing
    started_at = db.Column(DateTime, nullable=False, default=datetime.utcnow)  # When scraper fetched role
    completed_at = db.Column(DateTime, nullable=True)  # When scraper posted jobs
    duration_seconds = db.Column(Integer, nullable=True)  # Computed on complete
    
    # Results
    jobs_found = db.Column(Integer, default=0)  # Total jobs posted in this session
    jobs_imported = db.Column(Integer, default=0)  # Successfully imported (non-duplicate)
    jobs_skipped = db.Column(Integer, default=0)  # Skipped (duplicates)
    
    # Status
    status = db.Column(String(20), default='in_progress', index=True)
    # in_progress: Scraper is working on this role
    # completed: Session finished successfully
    # failed: Session ended with error
    # timeout: Session timed out (no response from scraper)
    
    error_message = db.Column(Text, nullable=True)  # Error details if failed
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    scraper_key = db.relationship('ScraperApiKey', back_populates='scrape_sessions')
    global_role = db.relationship('GlobalRole', back_populates='scrape_sessions')
    
    # Indexes
    __table_args__ = (
        # Session lookup
        Index('idx_scrape_sessions_session', 'session_id'),
        # Time-based queries for dashboards
        Index('idx_scrape_sessions_started', 'started_at'),
        # Status filtering
        Index('idx_scrape_sessions_status', 'status'),
        # Role lookup
        Index('idx_scrape_sessions_role', 'global_role_id'),
    )
    
    def __repr__(self):
        return f'<ScrapeSession {self.session_id} status={self.status} role={self.role_name}>'
    
    def to_dict(self, include_role=False, include_scraper=False):
        """Convert session to dictionary."""
        result = {
            'id': self.id,
            'session_id': str(self.session_id),
            'scraper_key_id': self.scraper_key_id,
            'scraper_name': self.scraper_name,
            'global_role_id': self.global_role_id,
            'role_name': self.role_name,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'jobs_found': self.jobs_found,
            'jobs_imported': self.jobs_imported,
            'jobs_skipped': self.jobs_skipped,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_role and self.global_role:
            result['global_role'] = self.global_role.to_dict()
        
        if include_scraper and self.scraper_key:
            result['scraper_key'] = self.scraper_key.to_dict()
        
        return result
    
    def complete(self, jobs_found: int, jobs_imported: int, jobs_skipped: int):
        """Mark session as completed with results."""
        self.completed_at = datetime.utcnow()
        self.jobs_found = jobs_found
        self.jobs_imported = jobs_imported
        self.jobs_skipped = jobs_skipped
        self.status = 'completed'
        
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
    
    def fail(self, error_message: str):
        """Mark session as failed with error message."""
        self.completed_at = datetime.utcnow()
        self.status = 'failed'
        self.error_message = error_message
        
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
    
    def timeout(self):
        """Mark session as timed out."""
        self.status = 'timeout'
        self.error_message = 'Session timed out - no response from scraper'

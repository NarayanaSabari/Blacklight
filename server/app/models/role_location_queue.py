"""
Role Location Queue Model

Represents a unique Role + Location combination in the scraping queue.
This enables location-specific job scraping:
- DevOps Engineer in New York → one queue entry
- DevOps Engineer in Los Angeles → another queue entry

When a candidate is approved with preferred roles and locations,
all combinations are added to this queue for the scraper to process.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import JSONB
from app import db


class RoleLocationQueue(db.Model):
    """
    Queue entry for role + location combination to be scraped.
    
    Example:
        Candidate A: DevOps Engineer, locations: [New York, LA]
        → Creates 2 queue entries:
          1. RoleLocationQueue(global_role_id=1, location="New York, NY")
          2. RoleLocationQueue(global_role_id=1, location="Los Angeles, CA")
        
        Candidate B: DevOps Engineer, locations: [New York]
        → Reuses existing entry #1, increments candidate_count
    
    Queue Status Flow:
        pending → approved → processing → completed
                    ↓
                 rejected
    """
    __tablename__ = 'role_location_queue'
    
    id = db.Column(Integer, primary_key=True)
    
    # Foreign Key to GlobalRole
    global_role_id = db.Column(
        Integer,
        ForeignKey('global_roles.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Normalized location string (e.g., "New York, NY", "Los Angeles, CA", "Remote")
    location = db.Column(String(255), nullable=False, index=True)
    
    # Queue Management
    queue_status = db.Column(
        String(50), 
        default='pending', 
        nullable=False,
        index=True
    )  # pending, approved, processing, completed, rejected
    
    priority = db.Column(
        String(20), 
        default='normal', 
        nullable=False
    )  # urgent, high, normal, low
    
    # Candidate tracking - how many candidates need this role+location
    candidate_count = db.Column(Integer, default=0, nullable=False)
    
    # Scraping Statistics
    total_jobs_scraped = db.Column(Integer, default=0)
    last_scraped_at = db.Column(DateTime)
    last_scrape_session_id = db.Column(String(255))
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Extra data for extensibility (renamed from 'metadata' which is reserved in SQLAlchemy)
    extra_data = db.Column(JSONB, default=dict)
    
    # Relationships
    global_role = db.relationship('GlobalRole', back_populates='location_queue_entries')
    
    # Indexes and Constraints
    __table_args__ = (
        # Unique: one queue entry per role+location combination
        UniqueConstraint('global_role_id', 'location', name='uq_role_location_queue'),
        # Queue lookup: find next role+location to scrape
        Index('idx_role_location_queue_status_priority', 'queue_status', 'priority'),
        # Role lookup: find all locations for a role
        Index('idx_role_location_queue_role', 'global_role_id'),
    )
    
    def __repr__(self):
        return f'<RoleLocationQueue role_id={self.global_role_id} location="{self.location}" status={self.queue_status}>'
    
    def to_dict(self, include_role=False):
        """Convert to dictionary."""
        result = {
            'id': self.id,
            'global_role_id': self.global_role_id,
            'location': self.location,
            'queue_status': self.queue_status,
            'priority': self.priority,
            'candidate_count': self.candidate_count,
            'total_jobs_scraped': self.total_jobs_scraped,
            'last_scraped_at': self.last_scraped_at.isoformat() if self.last_scraped_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_role and self.global_role:
            result['global_role'] = {
                'id': self.global_role.id,
                'name': self.global_role.name,
            }
        
        return result
    
    def increment_candidate_count(self):
        """Increment candidate count for this role+location."""
        self.candidate_count = (self.candidate_count or 0) + 1
    
    def decrement_candidate_count(self):
        """Decrement candidate count for this role+location."""
        if self.candidate_count and self.candidate_count > 0:
            self.candidate_count -= 1
    
    def mark_processing(self, session_id: str):
        """Mark queue entry as being processed by a scraper."""
        self.queue_status = 'processing'
        self.last_scrape_session_id = session_id
    
    def mark_completed(self, jobs_found: int):
        """Mark queue entry as completed after successful scrape."""
        self.queue_status = 'completed'
        self.total_jobs_scraped = (self.total_jobs_scraped or 0) + jobs_found
        self.last_scraped_at = datetime.utcnow()
    
    def reset_to_approved(self):
        """Reset to approved state (for re-scraping)."""
        self.queue_status = 'approved'

"""
Global Role Model
Canonical/normalized job roles for role-based scrape queue management.

This model implements:
- Role-based scraping: Multiple candidates share the same role
- AI role normalization: Vector embeddings for semantic similarity matching
- Queue management: Priority-based processing for external scrapers
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import ARRAY
from pgvector.sqlalchemy import Vector
from app import db


class GlobalRole(db.Model):
    """
    Canonical/normalized job role for role-based scrape queue.
    
    Key Design Decisions:
    - ROLE-BASED (not candidate-based): One role entry, many candidates
    - AI normalization: Embedding similarity for role deduplication
    - Queue management: External scraper fetches roles, not individual candidates
    
    Example:
        "Python Developer" role with candidate_count=100 means 100 candidates
        want this role. Scraping once benefits all 100 candidates.
    """
    __tablename__ = 'global_roles'
    
    id = db.Column(Integer, primary_key=True)
    
    # Canonical Role Name (normalized form)
    name = db.Column(String(255), nullable=False, unique=True, index=True)
    
    # Vector embedding for AI role normalization (Option B: embedding similarity first)
    embedding = db.Column(Vector(768), nullable=False)
    
    # Role Metadata
    aliases = db.Column(ARRAY(String), default=[])  # Alternative names that map to this role
    # Example: ["Sr Python Dev", "Python Engineer", "Senior Python Developer"]
    category = db.Column(String(100), nullable=True)  # "Engineering", "Data Science", etc.
    
    # Queue Management (ROLE-BASED, not candidate-based)
    candidate_count = db.Column(Integer, default=0)  # Number of candidates wanting this role
    queue_status = db.Column(String(20), default='pending', index=True)
    # pending: waiting to be scraped
    # processing: currently being scraped by external scraper
    # completed: recently scraped (within 24h)
    
    priority = db.Column(String(20), default='normal')
    # urgent: High-value roles, manual escalation
    # high: Roles with many candidates waiting  
    # normal: Regular queue processing
    # low: Background refresh (stale roles)
    
    # Statistics
    total_jobs_scraped = db.Column(Integer, default=0)  # Jobs found for this role (all time)
    
    # Timing
    last_scraped_at = db.Column(DateTime, nullable=True)  # Last successful scrape
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    candidate_links = db.relationship('CandidateGlobalRole', back_populates='global_role', cascade='all, delete-orphan')
    scrape_sessions = db.relationship('ScrapeSession', back_populates='global_role', cascade='all, delete-orphan')
    role_job_mappings = db.relationship('RoleJobMapping', back_populates='global_role', cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        # Vector similarity search for role normalization (AI Option B)
        Index(
            'idx_global_roles_embedding',
            'embedding',
            postgresql_using='ivfflat',
            postgresql_with={'lists': 50},
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
        # Queue processing: status + priority + candidate_count
        Index('idx_global_roles_queue', 'queue_status', 'priority', 'candidate_count'),
        # Category filtering
        Index('idx_global_roles_category', 'category'),
    )
    
    def __repr__(self):
        return f'<GlobalRole {self.name} (candidates={self.candidate_count}, status={self.queue_status})>'
    
    def to_dict(self, include_stats=False, include_embedding=False):
        """Convert global role to dictionary."""
        result = {
            'id': self.id,
            'name': self.name,
            'aliases': self.aliases or [],
            'category': self.category,
            'candidate_count': self.candidate_count,
            'queue_status': self.queue_status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_stats:
            result['total_jobs_scraped'] = self.total_jobs_scraped
            result['last_scraped_at'] = self.last_scraped_at.isoformat() if self.last_scraped_at else None
        
        if include_embedding and self.embedding is not None:
            result['embedding'] = list(self.embedding)
        
        return result
    
    def increment_candidate_count(self):
        """Increment candidate count and reset queue status if needed."""
        self.candidate_count += 1
        # If role was completed, reset to pending for next scrape cycle
        if self.queue_status == 'completed':
            self.queue_status = 'pending'
    
    def decrement_candidate_count(self):
        """Decrement candidate count (when candidate is removed)."""
        if self.candidate_count > 0:
            self.candidate_count -= 1

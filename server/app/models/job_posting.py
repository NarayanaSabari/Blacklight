"""
Job Posting Model
Stores external job listings from various platforms (GLOBAL - not tenant-specific)
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean, Date, ARRAY, Index, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector
from app import db


class JobPosting(db.Model):
    """
    Job posting from external platforms (Indeed, Dice, TechFetch, Glassdoor, Monster).
    Includes AI embeddings for semantic search.
    
    NOTE: Jobs are GLOBAL (not tenant-specific) as they come from public platforms.
    Only candidate_job_matches and job_applications are tenant-specific.
    """
    __tablename__ = 'job_postings'
    
    id = db.Column(Integer, primary_key=True)
    
    # External Job Data
    external_job_id = db.Column(String(255), nullable=False)  # Platform-specific ID
    platform = db.Column(String(50), nullable=False, index=True)  # indeed, dice, techfetch, glassdoor, monster
    
    # Basic Details
    title = db.Column(String(500), nullable=False)
    company = db.Column(String(255), nullable=False)
    location = db.Column(String(255), index=True)
    salary_range = db.Column(String(255))
    salary_min = db.Column(Integer)  # Parsed numeric values
    salary_max = db.Column(Integer)
    salary_currency = db.Column(String(10), default='USD')
    
    # Job Description
    description = db.Column(Text, nullable=False)
    snippet = db.Column(Text)
    requirements = db.Column(Text)  # Extracted from description
    
    # Job Metadata
    posted_date = db.Column(Date, index=True)
    expires_at = db.Column(Date)
    job_type = db.Column(String(50))  # Full-time, Contract, Part-time
    is_remote = db.Column(Boolean, default=False, index=True)
    experience_required = db.Column(String(100))  # "3-5 years"
    experience_min = db.Column(Integer)  # Parsed: 3
    experience_max = db.Column(Integer)  # Parsed: 5
    
    # Skills & Keywords
    skills = db.Column(ARRAY(String))  # Array of skill keywords
    keywords = db.Column(ARRAY(String))  # Additional extracted keywords
    
    # Application Links
    job_url = db.Column(Text, nullable=False)
    apply_url = db.Column(Text)
    
    # Status
    status = db.Column(String(50), default='ACTIVE', index=True)  # ACTIVE, EXPIRED, FILLED, CLOSED
    
    # AI Matching Data
    embedding = db.Column(Vector(768))  # Google Gemini embeddings (768 dimensions)
    raw_metadata = db.Column(JSONB)  # Original platform-specific data
    
    # Import Tracking
    imported_at = db.Column(DateTime, default=datetime.utcnow)
    last_synced_at = db.Column(DateTime)
    import_batch_id = db.Column(String(255), index=True)
    
    # Scraper Tracking (for observability)
    scraped_by_key_id = db.Column(
        Integer,
        ForeignKey('scraper_api_keys.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )  # Which API key imported this
    scrape_session_id = db.Column(UUID(as_uuid=True), nullable=True, index=True)  # Links to scrape_sessions.session_id
    normalized_role_id = db.Column(
        Integer,
        ForeignKey('global_roles.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )  # Links to queued role that triggered this job import
    
    # Audit Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    matches = db.relationship('CandidateJobMatch', back_populates='job_posting', cascade='all, delete-orphan')
    applications = db.relationship('JobApplication', back_populates='job_posting', cascade='all, delete-orphan')
    role_job_mappings = db.relationship('RoleJobMapping', back_populates='job_posting', cascade='all, delete-orphan')
    scraped_by_key = db.relationship('ScraperApiKey', backref='imported_jobs')
    normalized_role = db.relationship('GlobalRole', backref='jobs')
    
    # Indexes
    __table_args__ = (
        Index('idx_job_posting_platform_external', 'platform', 'external_job_id', unique=True),
        Index('idx_job_posting_skills', 'skills', postgresql_using='gin'),
        Index('idx_job_posting_keywords', 'keywords', postgresql_using='gin'),
        Index('idx_job_posting_posted_date_desc', 'posted_date', postgresql_ops={'posted_date': 'DESC'}),
        Index('idx_job_posting_embedding', 'embedding', postgresql_using='ivfflat', postgresql_with={'lists': 100}, postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )
    
    def __repr__(self):
        return f'<JobPosting {self.title} @ {self.company} ({self.platform})>'
    
    def to_dict(self, include_description=True, include_embedding=False):
        """Convert job posting to dictionary"""
        result = {
            'id': self.id,
            'external_job_id': self.external_job_id,
            'platform': self.platform,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'salary_range': self.salary_range,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'salary_currency': self.salary_currency,
            'snippet': self.snippet,
            'requirements': self.requirements,
            'posted_date': self.posted_date.isoformat() if self.posted_date else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'job_type': self.job_type,
            'is_remote': self.is_remote,
            'experience_required': self.experience_required,
            'experience_min': self.experience_min,
            'experience_max': self.experience_max,
            'skills': self.skills,
            'keywords': self.keywords,
            'job_url': self.job_url,
            'apply_url': self.apply_url,
            'status': self.status,
            'imported_at': self.imported_at.isoformat() if self.imported_at else None,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_description:
            result['description'] = self.description
        
        if include_embedding and self.embedding:
            result['embedding'] = self.embedding
        
        return result
    
    @property
    def is_expired(self):
        """Check if job posting has expired"""
        if self.expires_at:
            return datetime.utcnow().date() > self.expires_at
        return False
    
    @property
    def days_since_posted(self):
        """Calculate days since job was posted"""
        if self.posted_date:
            return (datetime.utcnow().date() - self.posted_date).days
        return None

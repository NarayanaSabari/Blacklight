"""
Scraper API Key Model
API key management for external scraper authentication.

Provides:
- Secure API key authentication for external scrapers
- Usage tracking and rate limiting
- Key rotation and revocation support
"""
from datetime import datetime
import hashlib
import secrets
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Index
from app import db


class ScraperApiKey(db.Model):
    """
    API key management for external scraper authentication.
    
    Security Features:
    - Keys are hashed using SHA256 before storage
    - Original key is only shown once at creation
    - Keys can be revoked without deletion for audit trail
    
    Usage Tracking:
    - Tracks total requests made with each key
    - Records last usage timestamp
    - Enables rate limiting per key
    """
    __tablename__ = 'scraper_api_keys'
    
    id = db.Column(Integer, primary_key=True)
    
    # Key Data (SHA256 hash of actual key)
    key_hash = db.Column(String(64), nullable=False, unique=True, index=True)
    
    # Key Identification
    name = db.Column(String(100), nullable=False)  # "production-scraper", "test-scraper"
    description = db.Column(String(500), nullable=True)  # Optional description
    
    # Status
    is_active = db.Column(Boolean, default=True, index=True)
    
    # Usage Tracking
    last_used_at = db.Column(DateTime, nullable=True)
    total_requests = db.Column(Integer, default=0)
    total_jobs_imported = db.Column(Integer, default=0)
    
    # Rate Limiting
    rate_limit_per_minute = db.Column(Integer, default=60)  # Requests per minute
    
    # Audit
    created_by = db.Column(
        Integer,
        ForeignKey('pm_admin_users.id', ondelete='SET NULL'),
        nullable=True
    )
    revoked_by = db.Column(
        Integer,
        ForeignKey('pm_admin_users.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    revoked_at = db.Column(DateTime, nullable=True)
    
    # Relationships
    scrape_sessions = db.relationship('ScrapeSession', back_populates='scraper_key', cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        Index('idx_scraper_api_keys_active', 'is_active'),
        Index('idx_scraper_api_keys_name', 'name'),
    )
    
    def __repr__(self):
        return f'<ScraperApiKey {self.name} (active={self.is_active})>'
    
    def to_dict(self, include_stats=True):
        """Convert API key to dictionary (never include the actual key hash)."""
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
        }
        
        if include_stats:
            result['last_used_at'] = self.last_used_at.isoformat() if self.last_used_at else None
            result['total_requests'] = self.total_requests
            result['total_jobs_imported'] = self.total_jobs_imported
        
        return result
    
    def record_usage(self, jobs_imported: int = 0):
        """Record API key usage."""
        self.last_used_at = datetime.utcnow()
        self.total_requests += 1
        self.total_jobs_imported += jobs_imported
    
    def revoke(self, revoked_by_id: int = None):
        """Revoke the API key."""
        self.is_active = False
        self.revoked_at = datetime.utcnow()
        if revoked_by_id:
            self.revoked_by = revoked_by_id
    
    @staticmethod
    def hash_key(api_key: str) -> str:
        """Hash an API key using SHA256."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @classmethod
    def generate_key(cls) -> str:
        """Generate a secure random API key (32 bytes, hex encoded)."""
        return secrets.token_hex(32)
    
    @classmethod
    def create_new_key(cls, name: str, description: str = None, created_by_id: int = None, rate_limit: int = 60):
        """
        Create a new API key with a randomly generated value.
        
        Args:
            name: Name/identifier for the key
            description: Optional description
            created_by_id: PM_ADMIN user ID who created the key
            rate_limit: Requests per minute limit
        
        Returns:
            Tuple of (ScraperApiKey instance, raw_api_key)
            Note: raw_api_key is only returned once, it cannot be retrieved later
        """
        raw_key = cls.generate_key()
        key_hash = cls.hash_key(raw_key)
        
        api_key = cls(
            key_hash=key_hash,
            name=name,
            description=description,
            created_by=created_by_id,
            rate_limit_per_minute=rate_limit
        )
        
        return api_key, raw_key
    
    @classmethod
    def validate_key(cls, raw_key: str):
        """
        Validate an API key and return the key record if valid.
        
        Args:
            raw_key: The raw API key to validate
        
        Returns:
            ScraperApiKey instance if valid and active, None otherwise
        """
        key_hash = cls.hash_key(raw_key)
        return cls.query.filter_by(key_hash=key_hash, is_active=True).first()

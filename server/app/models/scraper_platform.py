"""
Scraper Platform Model
Dynamic list of job platforms for scraping (LinkedIn, Monster, Indeed, etc.)
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean, Text
from app import db


class ScraperPlatform(db.Model):
    """
    Dynamic platform configuration for job scraping.
    
    Platforms can be added, enabled/disabled, and prioritized through CentralD Dashboard.
    Each scrape session will create a checklist entry for all active platforms.
    """
    __tablename__ = 'scraper_platforms'
    
    id = db.Column(Integer, primary_key=True)
    
    # Platform Identification
    name = db.Column(String(50), unique=True, nullable=False, index=True)  # "linkedin", "monster"
    display_name = db.Column(String(100), nullable=False)  # "LinkedIn", "Monster Jobs"
    
    # Platform Details
    base_url = db.Column(String(255), nullable=True)  # "https://linkedin.com/jobs"
    icon = db.Column(String(50), nullable=True)  # Icon name for UI (lucide icon or emoji)
    description = db.Column(Text, nullable=True)  # Optional description
    
    # Status & Priority
    is_active = db.Column(Boolean, default=True, nullable=False, index=True)  # Enable/disable platform
    priority = db.Column(Integer, default=0, nullable=False)  # Lower number = higher priority
    
    # Statistics (updated periodically)
    total_jobs_scraped = db.Column(Integer, default=0)  # All-time job count
    success_rate = db.Column(Integer, default=100)  # Percentage (0-100)
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    session_statuses = db.relationship(
        'SessionPlatformStatus',
        back_populates='platform',
        cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f'<ScraperPlatform {self.name} active={self.is_active}>'
    
    def to_dict(self, include_stats=False):
        """Convert platform to dictionary."""
        result = {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'base_url': self.base_url,
            'icon': self.icon,
            'description': self.description,
            'is_active': self.is_active,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_stats:
            result['total_jobs_scraped'] = self.total_jobs_scraped
            result['success_rate'] = self.success_rate
        
        return result
    
    @classmethod
    def get_active_platforms(cls):
        """Get all active platforms ordered by priority."""
        return cls.query.filter_by(is_active=True).order_by(cls.priority).all()
    
    @classmethod
    def seed_default_platforms(cls):
        """Seed initial platforms if none exist."""
        if cls.query.count() == 0:
            default_platforms = [
                {'name': 'linkedin', 'display_name': 'LinkedIn', 'icon': 'linkedin', 'priority': 1},
                {'name': 'monster', 'display_name': 'Monster', 'icon': 'briefcase', 'priority': 2},
                {'name': 'indeed', 'display_name': 'Indeed', 'icon': 'search', 'priority': 3},
                {'name': 'dice', 'display_name': 'Dice', 'icon': 'dice-5', 'priority': 4},
                {'name': 'glassdoor', 'display_name': 'Glassdoor', 'icon': 'door-open', 'priority': 5},
                {'name': 'techfetch', 'display_name': 'TechFetch', 'icon': 'cpu', 'priority': 6},
            ]
            
            for platform_data in default_platforms:
                platform = cls(**platform_data)
                db.session.add(platform)
            
            db.session.commit()
            return True
        return False

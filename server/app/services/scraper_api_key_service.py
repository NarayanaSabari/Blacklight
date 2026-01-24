"""
Scraper API Key Service
Business logic for managing scraper API keys.

Features:
- Create API keys with secure generation
- Revoke and activate keys
- Update key metadata
"""
import logging
from typing import Optional, Tuple
from datetime import datetime

from app import db
from app.models.scraper_api_key import ScraperApiKey

logger = logging.getLogger(__name__)


class ScraperApiKeyService:
    """Service for managing scraper API keys."""
    
    @staticmethod
    def create_api_key(
        name: str,
        description: Optional[str] = None,
        created_by_id: Optional[int] = None,
        rate_limit: int = 60
    ) -> Tuple[ScraperApiKey, str]:
        """
        Create a new scraper API key.
        
        Args:
            name: Name/identifier for the key
            description: Optional description
            created_by_id: PM_ADMIN user ID who created the key
            rate_limit: Requests per minute limit
            
        Returns:
            Tuple of (ScraperApiKey instance, raw_api_key)
            Note: raw_api_key is only returned once
            
        Raises:
            ValueError: If validation fails
        """
        if not name or not name.strip():
            raise ValueError("name is required")
        
        # Create new key using model's factory method
        api_key, raw_key = ScraperApiKey.create_new_key(
            name=name.strip(),
            description=description,
            created_by_id=created_by_id,
            rate_limit=rate_limit
        )
        
        # Commit to database
        db.session.add(api_key)
        db.session.commit()
        db.session.refresh(api_key)
        
        logger.info(f"Created API key: {name} (ID: {api_key.id})")
        
        return api_key, raw_key
    
    @staticmethod
    def revoke_api_key(
        key_id: int,
        revoked_by_id: Optional[int] = None
    ) -> ScraperApiKey:
        """
        Revoke an API key.
        
        Args:
            key_id: ID of the API key to revoke
            revoked_by_id: PM_ADMIN user ID who revoked the key
            
        Returns:
            Updated ScraperApiKey instance
            
        Raises:
            ValueError: If key not found
        """
        api_key = db.session.get(ScraperApiKey, key_id)
        
        if not api_key:
            raise ValueError(f"API key {key_id} not found")
        
        # Mark as revoked
        api_key.is_active = False
        api_key.revoked_at = datetime.utcnow()
        if revoked_by_id:
            api_key.revoked_by = revoked_by_id
        
        db.session.commit()
        db.session.refresh(api_key)
        
        logger.info(f"Revoked API key {key_id}: {api_key.name}")
        
        return api_key
    
    @staticmethod
    def activate_api_key(key_id: int) -> ScraperApiKey:
        """
        Reactivate a revoked API key.
        
        Args:
            key_id: ID of the API key to activate
            
        Returns:
            Updated ScraperApiKey instance
            
        Raises:
            ValueError: If key not found
        """
        api_key = db.session.get(ScraperApiKey, key_id)
        
        if not api_key:
            raise ValueError(f"API key {key_id} not found")
        
        # Reactivate
        api_key.is_active = True
        api_key.revoked_at = None
        api_key.revoked_by = None
        
        db.session.commit()
        db.session.refresh(api_key)
        
        logger.info(f"Activated API key {key_id}: {api_key.name}")
        
        return api_key
    
    @staticmethod
    def update_api_key_status(
        key_id: int,
        status: str
    ) -> ScraperApiKey:
        """
        Update API key status (active/paused).
        
        Args:
            key_id: ID of the API key
            status: New status ('active' or 'paused')
            
        Returns:
            Updated ScraperApiKey instance
            
        Raises:
            ValueError: If key not found or status invalid
        """
        if status not in ('active', 'paused'):
            raise ValueError("status must be 'active' or 'paused'")
        
        api_key = db.session.get(ScraperApiKey, key_id)
        
        if not api_key:
            raise ValueError(f"API key {key_id} not found")
        
        if api_key.revoked_at:
            raise ValueError("Cannot update status of a revoked key")
        
        api_key.is_active = (status == 'active')
        
        db.session.commit()
        db.session.refresh(api_key)
        
        logger.info(f"Updated API key {key_id} status to: {status}")
        
        return api_key

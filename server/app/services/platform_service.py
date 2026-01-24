"""
Platform Service

Manages scraper platforms (CRUD operations and statistics).
Used by CentralD Dashboard to manage dynamic platform list.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_

from app import db
from app.models.scraper_platform import ScraperPlatform
from app.models.session_platform_status import SessionPlatformStatus
from app.models.scrape_session import ScrapeSession

logger = logging.getLogger(__name__)


class PlatformService:
    """
    Service for managing scraper platforms.
    
    Provides CRUD operations and statistics for job scraping platforms.
    """
    
    @staticmethod
    def get_all_platforms(include_inactive: bool = False, include_stats: bool = False) -> List[Dict]:
        """
        Get all platforms, optionally including inactive ones.
        
        Args:
            include_inactive: If True, include inactive platforms
            include_stats: If True, include statistics for each platform
        
        Returns:
            List of platform dictionaries
        """
        stmt = select(ScraperPlatform).order_by(ScraperPlatform.priority)
        
        if not include_inactive:
            stmt = stmt.where(ScraperPlatform.is_active == True)
        
        platforms = db.session.scalars(stmt).all()
        
        result = []
        for platform in platforms:
            platform_dict = platform.to_dict(include_stats=include_stats)
            
            if include_stats:
                # Get additional stats
                stats = PlatformService.get_platform_stats(platform.id)
                platform_dict.update(stats)
            
            result.append(platform_dict)
        
        return result
    
    @staticmethod
    def get_platform_by_id(platform_id: int) -> Optional[ScraperPlatform]:
        """Get platform by ID."""
        return db.session.get(ScraperPlatform, platform_id)
    
    @staticmethod
    def get_platform_by_name(name: str) -> Optional[ScraperPlatform]:
        """Get platform by name."""
        stmt = select(ScraperPlatform).where(ScraperPlatform.name == name.lower())
        return db.session.scalar(stmt)
    
    @staticmethod
    def create_platform(
        name: str,
        display_name: str,
        base_url: Optional[str] = None,
        icon: Optional[str] = None,
        description: Optional[str] = None,
        priority: int = 0,
        is_active: bool = True
    ) -> ScraperPlatform:
        """
        Create a new platform.
        
        Args:
            name: Unique platform identifier (lowercase, no spaces)
            display_name: Human-readable name
            base_url: Platform's job listing URL
            icon: Icon name for UI
            description: Optional description
            priority: Scraping priority (lower = higher priority)
            is_active: Whether platform is active
        
        Returns:
            Created ScraperPlatform instance
        """
        # Normalize name
        name = name.lower().strip().replace(' ', '_')
        
        # Check for duplicate
        stmt = select(ScraperPlatform).where(ScraperPlatform.name == name)
        if db.session.scalar(stmt):
            raise ValueError(f"Platform '{name}' already exists")
        
        platform = ScraperPlatform(
            name=name,
            display_name=display_name,
            base_url=base_url,
            icon=icon,
            description=description,
            priority=priority,
            is_active=is_active
        )
        
        db.session.add(platform)
        db.session.commit()
        
        logger.info(f"Created platform: {name}")
        return platform
    
    @staticmethod
    def update_platform(
        platform_id: int,
        **kwargs
    ) -> Optional[ScraperPlatform]:
        """
        Update a platform.
        
        Args:
            platform_id: Platform ID
            **kwargs: Fields to update
        
        Returns:
            Updated ScraperPlatform instance
        """
        platform = db.session.get(ScraperPlatform, platform_id)
        if not platform:
            return None
        
        # Allowed fields to update
        allowed_fields = ['display_name', 'base_url', 'icon', 'description', 'priority', 'is_active']
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(platform, field, value)
        
        db.session.commit()
        
        logger.info(f"Updated platform: {platform.name}")
        return platform
    
    @staticmethod
    def delete_platform(platform_id: int) -> bool:
        """
        Delete a platform.
        
        Args:
            platform_id: Platform ID
        
        Returns:
            True if deleted, False if not found
        """
        platform = db.session.get(ScraperPlatform, platform_id)
        if not platform:
            return False
        
        name = platform.name
        db.session.delete(platform)
        db.session.commit()
        db.session.expire_all()
        
        logger.info(f"Deleted platform: {name}")
        return True
    
    @staticmethod
    def toggle_platform(platform_id: int) -> Optional[ScraperPlatform]:
        """
        Toggle platform active status.
        
        Args:
            platform_id: Platform ID
        
        Returns:
            Updated ScraperPlatform instance
        """
        platform = db.session.get(ScraperPlatform, platform_id)
        if not platform:
            return None
        
        platform.is_active = not platform.is_active
        db.session.commit()
        
        logger.info(f"Toggled platform {platform.name} to {'active' if platform.is_active else 'inactive'}")
        return platform
    
    @staticmethod
    def reorder_platforms(platform_ids: List[int]) -> bool:
        """
        Reorder platforms by setting priorities.
        
        Args:
            platform_ids: List of platform IDs in new order
        
        Returns:
            True if successful
        """
        for idx, platform_id in enumerate(platform_ids):
            platform = db.session.get(ScraperPlatform, platform_id)
            if platform:
                platform.priority = idx + 1
        
        db.session.commit()
        logger.info("Reordered platforms")
        return True
    
    @staticmethod
    def get_platform_stats(platform_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Get statistics for a platform.
        
        Args:
            platform_id: Platform ID
            days: Number of days to look back
        
        Returns:
            Dict with statistics
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        # Get job counts from session_platform_status
        stats_query = db.session.execute(
            select(
                func.count(SessionPlatformStatus.id).label('total_sessions'),
                func.sum(SessionPlatformStatus.jobs_imported).label('jobs_imported'),
                func.sum(
                    func.case(
                        (SessionPlatformStatus.status == 'completed', 1),
                        else_=0
                    )
                ).label('successful_sessions'),
                func.sum(
                    func.case(
                        (SessionPlatformStatus.status == 'failed', 1),
                        else_=0
                    )
                ).label('failed_sessions'),
            ).where(
                and_(
                    SessionPlatformStatus.platform_id == platform_id,
                    SessionPlatformStatus.created_at >= since
                )
            )
        ).first()
        
        total_sessions = stats_query.total_sessions or 0
        successful_sessions = stats_query.successful_sessions or 0
        failed_sessions = stats_query.failed_sessions or 0
        jobs_imported = stats_query.jobs_imported or 0
        
        success_rate = 0
        if total_sessions > 0:
            success_rate = round((successful_sessions / total_sessions) * 100, 1)
        
        return {
            'jobs_imported_last_n_days': jobs_imported,
            'sessions_last_n_days': total_sessions,
            'success_rate': success_rate,
            'failed_sessions': failed_sessions,
            'days_period': days
        }
    
    @staticmethod
    def get_all_platforms_stats(days: int = 7) -> List[Dict[str, Any]]:
        """
        Get statistics for all platforms.
        
        Args:
            days: Number of days to look back
        
        Returns:
            List of platform stats
        """
        platforms = PlatformService.get_all_platforms(include_inactive=True)
        
        for platform in platforms:
            stats = PlatformService.get_platform_stats(platform['id'], days)
            platform.update(stats)
        
        return platforms
    
    @staticmethod
    def seed_default_platforms() -> bool:
        """
        Seed default platforms if none exist.
        
        Returns:
            True if seeded, False if platforms already exist
        """
        return ScraperPlatform.seed_default_platforms()

"""
Scraper Service
Business logic for managing scraper sessions and platform status.

Features:
- Platform failure marking
- Platform batch initialization (CRITICAL: commits before Inngest to avoid race)
- Session completion marking
"""
import logging
from typing import Tuple
from uuid import UUID

from sqlalchemy import select

from app import db
from app.models.scrape_session import ScrapeSession
from app.models.session_platform_status import SessionPlatformStatus

logger = logging.getLogger(__name__)


class ScraperService:
    """Service for managing scraper sessions."""
    
    @staticmethod
    def mark_platform_failed(
        session_id: UUID,
        platform_name: str,
        error_message: str,
        scraper_key_id: int
    ) -> Tuple[ScrapeSession, SessionPlatformStatus]:
        """
        Mark platform as failed and update session counters.
        
        Args:
            session_id: UUID of scraper session
            platform_name: Name of platform that failed
            error_message: Failure error message
            scraper_key_id: ID of scraper API key (authorization)
            
        Returns:
            Tuple of (session, platform_status)
            
        Raises:
            ValueError: If session or platform_status not found
        """
        # Query session with authorization check
        stmt = select(ScrapeSession).where(
            ScrapeSession.session_id == session_id,
            ScrapeSession.scraper_key_id == scraper_key_id
        )
        session = db.session.scalar(stmt)
        
        if not session:
            raise ValueError("Session not found or unauthorized")
        
        # Query platform status
        stmt = select(SessionPlatformStatus).where(
            SessionPlatformStatus.session_id == session.id,
            SessionPlatformStatus.platform_name == platform_name
        )
        platform_status = db.session.scalar(stmt)
        
        if not platform_status:
            raise ValueError(f"Platform status not found: {platform_name}")
        
        # Mark platform as failed
        platform_status.mark_failed(error_message)
        
        # Update session counters
        session.platforms_completed += 1
        session.platforms_failed += 1
        
        # Commit transaction
        db.session.commit()
        
        logger.info(
            f"Platform {platform_name} marked failed for session {session_id}: {error_message}"
        )
        
        return session, platform_status
    
    @staticmethod
    def initialize_platform_batches(
        session_id: UUID,
        platform_name: str,
        total_batches: int,
        scraper_key_id: int
    ) -> SessionPlatformStatus:
        """
        Initialize batch tracking for platform import.
        
        CRITICAL: This MUST commit BEFORE Inngest events are sent to avoid race condition.
        Inngest processes events async - batches might complete before we set total_batches.
        
        Args:
            session_id: UUID of scraper session
            platform_name: Name of platform
            total_batches: Total number of batches to process
            scraper_key_id: ID of scraper API key (authorization)
            
        Returns:
            Updated platform_status
            
        Raises:
            ValueError: If session or platform_status not found
        """
        # Query session with authorization check
        stmt = select(ScrapeSession).where(
            ScrapeSession.session_id == session_id,
            ScrapeSession.scraper_key_id == scraper_key_id
        )
        session = db.session.scalar(stmt)
        
        if not session:
            raise ValueError("Session not found or unauthorized")
        
        # Query platform status
        stmt = select(SessionPlatformStatus).where(
            SessionPlatformStatus.session_id == session.id,
            SessionPlatformStatus.platform_name == platform_name
        )
        platform_status = db.session.scalar(stmt)
        
        if not platform_status:
            raise ValueError(f"Platform status not found: {platform_name}")
        
        # Mark as in progress and set batch tracking
        platform_status.mark_in_progress()
        platform_status.total_batches = total_batches
        platform_status.completed_batches = 0
        
        # CRITICAL: Commit BEFORE Inngest events are sent
        db.session.commit()
        
        logger.info(
            f"Platform {platform_name} batch tracking initialized: "
            f"{total_batches} batch(es) (session: {session_id})"
        )
        
        return platform_status
    
    @staticmethod
    def mark_session_pending_completion(
        session_id: UUID,
        scraper_key_id: int
    ) -> ScrapeSession:
        """
        Mark session as pending completion.
        
        The session will be completed when the last batch finishes processing.
        This avoids race condition where complete is called before batches finish.
        
        Args:
            session_id: UUID of scraper session
            scraper_key_id: ID of scraper API key (authorization)
            
        Returns:
            Updated session
            
        Raises:
            ValueError: If session not found or already completed
        """
        # Query session with authorization check
        stmt = select(ScrapeSession).where(
            ScrapeSession.session_id == session_id,
            ScrapeSession.scraper_key_id == scraper_key_id
        )
        session = db.session.scalar(stmt)
        
        if not session:
            raise ValueError("Session not found or unauthorized")
        
        if session.status == 'completed':
            raise ValueError("Session already completed")
        
        # Mark as pending completion
        session.status = 'pending_completion'
        
        # Commit transaction
        db.session.commit()
        
        logger.info(
            f"Session {session_id} marked as pending_completion. "
            f"Completion will be triggered when all platform batches finish."
        )
        
        return session

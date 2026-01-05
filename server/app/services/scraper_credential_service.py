"""
Scraper Credential Service
Business logic for managing scraper credentials.

Features:
- CRUD operations for credentials
- Queue-based credential assignment for scrapers
- Failure reporting and tracking
- Credential rotation
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import and_, or_

from app import db
from app.models.scraper_credential import (
    ScraperCredential,
    CredentialPlatform,
    CredentialStatus
)


class ScraperCredentialService:
    """Service for managing scraper credentials."""
    
    # Supported platforms with their credential types
    PLATFORMS = {
        CredentialPlatform.LINKEDIN.value: 'email_password',
        CredentialPlatform.TECHFETCH.value: 'email_password',
        CredentialPlatform.GLASSDOOR.value: 'json',
    }
    
    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================
    
    @staticmethod
    def create_credential(
        platform: str,
        name: str,
        email: Optional[str] = None,
        password: Optional[str] = None,
        json_credentials: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> ScraperCredential:
        """
        Create a new scraper credential.
        
        Args:
            platform: Platform name (linkedin, glassdoor, techfetch)
            name: Display name for the credential
            email: Email for email/password credentials
            password: Password for email/password credentials
            json_credentials: JSON data for JSON credentials (glassdoor)
            notes: Optional admin notes
            
        Returns:
            Created ScraperCredential instance
            
        Raises:
            ValueError: If required fields are missing or invalid platform
        """
        platform = platform.lower()
        
        if platform not in ScraperCredentialService.PLATFORMS:
            raise ValueError(f"Invalid platform: {platform}. Supported: {list(ScraperCredentialService.PLATFORMS.keys())}")
        
        cred_type = ScraperCredentialService.PLATFORMS[platform]
        
        if cred_type == 'email_password':
            if not email or not password:
                raise ValueError(f"Email and password are required for {platform}")
            credential = ScraperCredential.create_email_credential(
                platform=platform,
                name=name,
                email=email,
                password=password,
                notes=notes
            )
        else:  # json
            if not json_credentials:
                raise ValueError(f"JSON credentials are required for {platform}")
            credential = ScraperCredential.create_json_credential(
                platform=platform,
                name=name,
                json_data=json_credentials,
                notes=notes
            )
        
        db.session.add(credential)
        db.session.commit()
        
        return credential
    
    @staticmethod
    def update_credential(
        credential_id: int,
        name: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        json_credentials: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> ScraperCredential:
        """
        Update an existing credential.
        
        Args:
            credential_id: ID of the credential to update
            name: New display name
            email: New email (for email/password credentials)
            password: New password (for email/password credentials)
            json_credentials: New JSON data (for JSON credentials)
            notes: New admin notes
            
        Returns:
            Updated ScraperCredential instance
            
        Raises:
            ValueError: If credential not found
        """
        credential = ScraperCredential.query.get(credential_id)
        if not credential:
            raise ValueError(f"Credential not found: {credential_id}")
        
        if name is not None:
            credential.name = name
        
        if notes is not None:
            credential.notes = notes
        
        cred_type = ScraperCredentialService.PLATFORMS[credential.platform]
        
        if cred_type == 'email_password':
            if email is not None:
                credential.email = email
            if password is not None:
                credential.set_password(password)
        else:  # json
            if json_credentials is not None:
                credential.set_json_credentials(json_credentials)
        
        db.session.commit()
        return credential
    
    @staticmethod
    def delete_credential(credential_id: int) -> bool:
        """
        Delete a credential.
        
        Args:
            credential_id: ID of the credential to delete
            
        Returns:
            True if deleted, False if not found
        """
        credential = ScraperCredential.query.get(credential_id)
        if not credential:
            return False
        
        db.session.delete(credential)
        db.session.commit()
        return True
    
    @staticmethod
    def get_credential(credential_id: int, include_credentials: bool = False) -> Optional[ScraperCredential]:
        """Get a credential by ID."""
        return ScraperCredential.query.get(credential_id)
    
    @staticmethod
    def get_credentials_by_platform(
        platform: str,
        status: Optional[str] = None,
        include_credentials: bool = False
    ) -> List[ScraperCredential]:
        """
        Get all credentials for a platform.
        
        Args:
            platform: Platform name
            status: Optional status filter
            include_credentials: Include decrypted credentials in response
            
        Returns:
            List of credentials
        """
        query = ScraperCredential.query.filter(
            ScraperCredential.platform == platform.lower()
        )
        
        if status:
            query = query.filter(ScraperCredential.status == status)
        
        return query.order_by(ScraperCredential.created_at.desc()).all()
    
    @staticmethod
    def get_all_credentials(
        platform: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[ScraperCredential]:
        """
        Get all credentials with optional filters.
        
        Args:
            platform: Optional platform filter
            status: Optional status filter
            
        Returns:
            List of credentials
        """
        query = ScraperCredential.query
        
        if platform:
            query = query.filter(ScraperCredential.platform == platform.lower())
        
        if status:
            query = query.filter(ScraperCredential.status == status)
        
        return query.order_by(
            ScraperCredential.platform,
            ScraperCredential.created_at.desc()
        ).all()
    
    # =========================================================================
    # STATUS MANAGEMENT
    # =========================================================================
    
    @staticmethod
    def enable_credential(credential_id: int) -> ScraperCredential:
        """Enable a disabled/failed credential."""
        credential = ScraperCredential.query.get(credential_id)
        if not credential:
            raise ValueError(f"Credential not found: {credential_id}")
        
        credential.mark_available()
        db.session.commit()
        return credential
    
    @staticmethod
    def disable_credential(credential_id: int) -> ScraperCredential:
        """Disable a credential."""
        credential = ScraperCredential.query.get(credential_id)
        if not credential:
            raise ValueError(f"Credential not found: {credential_id}")
        
        credential.disable()
        db.session.commit()
        return credential
    
    @staticmethod
    def reset_credential(credential_id: int) -> ScraperCredential:
        """Reset a credential to available status (clear failure state)."""
        credential = ScraperCredential.query.get(credential_id)
        if not credential:
            raise ValueError(f"Credential not found: {credential_id}")
        
        credential.mark_available()
        credential.last_failure_message = None
        db.session.commit()
        return credential
    
    # =========================================================================
    # SCRAPER QUEUE OPERATIONS
    # =========================================================================
    
    @staticmethod
    def get_next_credential_for_scraper(
        platform: str,
        session_id: str
    ) -> Optional[ScraperCredential]:
        """
        Get the next available credential for a scraper.
        Assigns the credential to the scraper session.
        
        Args:
            platform: Platform to get credential for
            session_id: Scraper session ID (for tracking)
            
        Returns:
            Available credential or None if none available
        """
        now = datetime.utcnow()
        
        # Find available credential
        credential = ScraperCredential.query.filter(
            ScraperCredential.platform == platform.lower(),
            ScraperCredential.status == CredentialStatus.AVAILABLE.value,
            or_(
                ScraperCredential.cooldown_until.is_(None),
                ScraperCredential.cooldown_until <= now
            )
        ).order_by(
            # Prioritize credentials with fewer failures
            ScraperCredential.failure_count.asc(),
            # Then by least recently used
            ScraperCredential.last_success_at.asc().nullsfirst()
        ).with_for_update(skip_locked=True).first()
        
        if credential:
            credential.assign_to_scraper(session_id)
            db.session.commit()
        
        return credential
    
    @staticmethod
    def report_credential_failure(
        credential_id: int,
        error_message: str,
        cooldown_minutes: int = 0
    ) -> ScraperCredential:
        """
        Report that a credential failed.
        Called by scraper when credentials don't work.
        
        Args:
            credential_id: ID of the failed credential
            error_message: Error message describing the failure
            cooldown_minutes: Optional cooldown period before retry
            
        Returns:
            Updated credential
        """
        credential = ScraperCredential.query.get(credential_id)
        if not credential:
            raise ValueError(f"Credential not found: {credential_id}")
        
        credential.mark_failed(error_message)
        
        if cooldown_minutes > 0:
            credential.cooldown_until = datetime.utcnow() + timedelta(minutes=cooldown_minutes)
            credential.status = CredentialStatus.COOLDOWN.value
        
        db.session.commit()
        return credential
    
    @staticmethod
    def report_credential_success(credential_id: int) -> ScraperCredential:
        """
        Report that a credential was used successfully.
        Releases it back to the available pool.
        
        Args:
            credential_id: ID of the credential
            
        Returns:
            Updated credential
        """
        credential = ScraperCredential.query.get(credential_id)
        if not credential:
            raise ValueError(f"Credential not found: {credential_id}")
        
        credential.release(success=True)
        db.session.commit()
        return credential
    
    @staticmethod
    def release_credential(
        credential_id: int,
        success: bool = True
    ) -> ScraperCredential:
        """
        Release a credential back to the pool.
        
        Args:
            credential_id: ID of the credential
            success: Whether the usage was successful
            
        Returns:
            Updated credential
        """
        credential = ScraperCredential.query.get(credential_id)
        if not credential:
            raise ValueError(f"Credential not found: {credential_id}")
        
        credential.release(success=success)
        db.session.commit()
        return credential
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    @staticmethod
    def get_platform_stats(platform: str) -> Dict[str, Any]:
        """
        Get credential statistics for a platform.
        
        Args:
            platform: Platform name
            
        Returns:
            Dictionary with stats
        """
        credentials = ScraperCredential.query.filter(
            ScraperCredential.platform == platform.lower()
        ).all()
        
        stats = {
            'platform': platform,
            'total': len(credentials),
            'available': 0,
            'in_use': 0,
            'failed': 0,
            'disabled': 0,
            'cooldown': 0,
            'total_successes': 0,
            'total_failures': 0,
        }
        
        for cred in credentials:
            if cred.status == CredentialStatus.AVAILABLE.value:
                stats['available'] += 1
            elif cred.status == CredentialStatus.IN_USE.value:
                stats['in_use'] += 1
            elif cred.status == CredentialStatus.FAILED.value:
                stats['failed'] += 1
            elif cred.status == CredentialStatus.DISABLED.value:
                stats['disabled'] += 1
            elif cred.status == CredentialStatus.COOLDOWN.value:
                stats['cooldown'] += 1
            
            stats['total_successes'] += cred.success_count
            stats['total_failures'] += cred.failure_count
        
        return stats
    
    @staticmethod
    def get_all_platform_stats() -> Dict[str, Dict[str, Any]]:
        """Get statistics for all platforms."""
        return {
            platform: ScraperCredentialService.get_platform_stats(platform)
            for platform in ScraperCredentialService.PLATFORMS.keys()
        }
    
    # =========================================================================
    # CLEANUP OPERATIONS
    # =========================================================================
    
    @staticmethod
    def cleanup_stale_assignments(timeout_minutes: int = 60) -> int:
        """
        Release credentials that have been assigned for too long.
        Prevents credentials from being stuck if scraper crashes.
        
        Args:
            timeout_minutes: Minutes after which to release
            
        Returns:
            Number of credentials released
        """
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        stale_credentials = ScraperCredential.query.filter(
            ScraperCredential.status == CredentialStatus.IN_USE.value,
            ScraperCredential.assigned_at < cutoff
        ).all()
        
        count = 0
        for cred in stale_credentials:
            cred.release(success=False)
            count += 1
        
        if count > 0:
            db.session.commit()
        
        return count
    
    @staticmethod
    def clear_expired_cooldowns() -> int:
        """
        Clear cooldown status for credentials whose cooldown has expired.
        
        Returns:
            Number of credentials cleared
        """
        now = datetime.utcnow()
        
        expired = ScraperCredential.query.filter(
            ScraperCredential.status == CredentialStatus.COOLDOWN.value,
            ScraperCredential.cooldown_until <= now
        ).all()
        
        count = 0
        for cred in expired:
            cred.mark_available()
            count += 1
        
        if count > 0:
            db.session.commit()
        
        return count

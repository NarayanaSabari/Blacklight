"""
Scraper Credential Model
Manages login credentials for different scraping platforms (LinkedIn, Glassdoor, Techfetch).

Features:
- Queue-based credential assignment (one credential per scraper at a time)
- Failure tracking with error messages
- Support for different credential types (email/password vs JSON)
- Credential rotation and cooldown management
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, Boolean, Text, Index, Enum
from sqlalchemy.dialects.postgresql import JSONB
from cryptography.fernet import Fernet
from flask import current_app
import enum

from app import db


class CredentialPlatform(enum.Enum):
    """Supported platforms for scraper credentials."""
    LINKEDIN = "linkedin"
    GLASSDOOR = "glassdoor"
    TECHFETCH = "techfetch"


class CredentialStatus(enum.Enum):
    """Status of a scraper credential."""
    AVAILABLE = "available"      # Ready to be assigned to a scraper
    IN_USE = "in_use"           # Currently assigned to a scraper
    FAILED = "failed"           # Reported as failed by scraper
    DISABLED = "disabled"       # Manually disabled by admin
    COOLDOWN = "cooldown"       # Temporarily unavailable (rate limited)


class ScraperCredential(db.Model):
    """
    Stores login credentials for scraping platforms.
    
    Credential Types:
    - LinkedIn: email + password
    - Techfetch: email + password
    - Glassdoor: JSON blob (cookies, tokens, etc.)
    
    Queue System:
    - Credentials are assigned one at a time to scrapers
    - Once assigned, status changes to 'in_use'
    - Scraper reports success or failure after use
    - Failed credentials are marked with error message
    """
    __tablename__ = 'scraper_credentials'
    
    id = db.Column(Integer, primary_key=True)
    
    # Platform identification
    platform = db.Column(
        String(50),
        nullable=False,
        index=True
    )  # linkedin, glassdoor, techfetch
    
    # Credential label/name for identification
    name = db.Column(String(100), nullable=False)  # "LinkedIn Account 1", etc.
    
    # Encrypted credentials storage
    # For LinkedIn/Techfetch: email stored here
    email = db.Column(String(255), nullable=True)
    
    # For LinkedIn/Techfetch: encrypted password
    # For Glassdoor: encrypted JSON blob
    encrypted_data = db.Column(Text, nullable=False)
    
    # Status management
    status = db.Column(
        String(20),
        default=CredentialStatus.AVAILABLE.value,
        nullable=False,
        index=True
    )
    
    # Assignment tracking
    assigned_to_session_id = db.Column(String(255), nullable=True)
    assigned_at = db.Column(DateTime, nullable=True)
    
    # Failure tracking
    failure_count = db.Column(Integer, default=0)
    last_failure_at = db.Column(DateTime, nullable=True)
    last_failure_message = db.Column(Text, nullable=True)
    
    # Success tracking
    success_count = db.Column(Integer, default=0)
    last_success_at = db.Column(DateTime, nullable=True)
    
    # Cooldown management
    cooldown_until = db.Column(DateTime, nullable=True)
    
    # Admin notes
    notes = db.Column(Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_scraper_credentials_platform_status', 'platform', 'status'),
        Index('idx_scraper_credentials_available', 'platform', 'status', 'cooldown_until'),
    )
    
    def __repr__(self):
        return f'<ScraperCredential {self.platform}:{self.name} status={self.status}>'
    
    # =========================================================================
    # ENCRYPTION HELPERS
    # =========================================================================
    
    @staticmethod
    def _get_fernet() -> Fernet:
        """Get Fernet instance for encryption/decryption."""
        key = current_app.config.get('CREDENTIAL_ENCRYPTION_KEY')
        if not key:
            # Fallback to SECRET_KEY if specific key not set
            import hashlib
            import base64
            secret = current_app.config.get('SECRET_KEY', 'default-secret-key')
            # Create a valid Fernet key from SECRET_KEY
            key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
        elif isinstance(key, str):
            key = key.encode()
        return Fernet(key)
    
    def _encrypt(self, data: str) -> str:
        """Encrypt a string."""
        fernet = self._get_fernet()
        return fernet.encrypt(data.encode()).decode()
    
    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt a string."""
        fernet = self._get_fernet()
        return fernet.decrypt(encrypted_data.encode()).decode()
    
    # =========================================================================
    # CREDENTIAL SETTERS/GETTERS
    # =========================================================================
    
    def set_password(self, password: str) -> None:
        """Set encrypted password for LinkedIn/Techfetch credentials."""
        self.encrypted_data = self._encrypt(password)
    
    def get_password(self) -> str:
        """Get decrypted password for LinkedIn/Techfetch credentials."""
        return self._decrypt(self.encrypted_data)
    
    def set_json_credentials(self, json_data: Dict[str, Any]) -> None:
        """Set encrypted JSON credentials for Glassdoor."""
        import json
        self.encrypted_data = self._encrypt(json.dumps(json_data))
    
    def get_json_credentials(self) -> Dict[str, Any]:
        """Get decrypted JSON credentials for Glassdoor."""
        import json
        return json.loads(self._decrypt(self.encrypted_data))
    
    # =========================================================================
    # STATUS MANAGEMENT
    # =========================================================================
    
    def assign_to_scraper(self, session_id: str) -> None:
        """Mark credential as in use by a scraper session."""
        self.status = CredentialStatus.IN_USE.value
        self.assigned_to_session_id = session_id
        self.assigned_at = datetime.utcnow()
    
    def release(self, success: bool = True) -> None:
        """Release credential back to available pool."""
        self.assigned_to_session_id = None
        self.assigned_at = None
        
        # Always set status to AVAILABLE when releasing
        # (If failure occurred, mark_failed should be called instead)
        self.status = CredentialStatus.AVAILABLE.value
        
        if success:
            self.success_count += 1
            self.last_success_at = datetime.utcnow()
    
    def mark_failed(self, error_message: str) -> None:
        """Mark credential as failed with error message."""
        self.status = CredentialStatus.FAILED.value
        self.failure_count += 1
        self.last_failure_at = datetime.utcnow()
        self.last_failure_message = error_message
        self.assigned_to_session_id = None
        self.assigned_at = None
    
    def mark_available(self) -> None:
        """Reset credential to available status (admin action)."""
        self.status = CredentialStatus.AVAILABLE.value
        self.assigned_to_session_id = None
        self.assigned_at = None
        self.cooldown_until = None
    
    def disable(self) -> None:
        """Disable credential (admin action)."""
        self.status = CredentialStatus.DISABLED.value
        self.assigned_to_session_id = None
        self.assigned_at = None
    
    def enable(self) -> None:
        """Enable previously disabled credential."""
        self.status = CredentialStatus.AVAILABLE.value
    
    def set_cooldown(self, until: datetime) -> None:
        """Set credential on cooldown until specified time."""
        self.status = CredentialStatus.COOLDOWN.value
        self.cooldown_until = until
        self.assigned_to_session_id = None
        self.assigned_at = None
    
    def is_available(self) -> bool:
        """Check if credential is available for assignment."""
        if self.status != CredentialStatus.AVAILABLE.value:
            return False
        if self.cooldown_until and self.cooldown_until > datetime.utcnow():
            return False
        return True
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def to_dict(self, include_credentials: bool = False, include_stats: bool = True) -> Dict[str, Any]:
        """
        Convert credential to dictionary.
        
        Args:
            include_credentials: Include decrypted credentials (use with caution!)
            include_stats: Include usage statistics
        """
        result = {
            'id': self.id,
            'platform': self.platform,
            'name': self.name,
            'email': self.email,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_credentials:
            if self.platform == CredentialPlatform.GLASSDOOR.value:
                result['json_credentials'] = self.get_json_credentials()
            else:
                result['password'] = self.get_password()
        
        if include_stats:
            result.update({
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'last_failure_at': self.last_failure_at.isoformat() if self.last_failure_at else None,
                'last_failure_message': self.last_failure_message,
                'last_success_at': self.last_success_at.isoformat() if self.last_success_at else None,
                'assigned_to_session_id': self.assigned_to_session_id,
                'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
                'cooldown_until': self.cooldown_until.isoformat() if self.cooldown_until else None,
            })
        
        return result
    
    def to_scraper_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for scraper API response.
        Includes decrypted credentials.
        """
        result = {
            'id': self.id,
            'platform': self.platform,
            'name': self.name,
        }
        
        if self.platform == CredentialPlatform.GLASSDOOR.value:
            result['credentials'] = self.get_json_credentials()
        else:
            result['email'] = self.email
            result['password'] = self.get_password()
        
        return result
    
    # =========================================================================
    # CLASS METHODS
    # =========================================================================
    
    @classmethod
    def create_email_credential(
        cls,
        platform: str,
        name: str,
        email: str,
        password: str,
        notes: Optional[str] = None
    ) -> 'ScraperCredential':
        """
        Create a new email/password credential (LinkedIn, Techfetch).
        
        Args:
            platform: Platform name (linkedin, techfetch)
            name: Display name for the credential
            email: Login email
            password: Login password (will be encrypted)
            notes: Optional admin notes
        """
        credential = cls(
            platform=platform.lower(),
            name=name,
            email=email,
            notes=notes
        )
        credential.set_password(password)
        return credential
    
    @classmethod
    def create_json_credential(
        cls,
        platform: str,
        name: str,
        json_data: Dict[str, Any],
        notes: Optional[str] = None
    ) -> 'ScraperCredential':
        """
        Create a new JSON credential (Glassdoor).
        
        Args:
            platform: Platform name (glassdoor)
            name: Display name for the credential
            json_data: JSON credentials (will be encrypted)
            notes: Optional admin notes
        """
        credential = cls(
            platform=platform.lower(),
            name=name,
            notes=notes
        )
        credential.set_json_credentials(json_data)
        return credential
    
    @classmethod
    def get_next_available(cls, platform: str) -> Optional['ScraperCredential']:
        """
        Get the next available credential for a platform.
        Uses round-robin based on last success time.
        
        Args:
            platform: Platform name (linkedin, glassdoor, techfetch)
        
        Returns:
            Available credential or None
        """
        now = datetime.utcnow()
        
        # Query for available credentials, prioritizing those not recently used
        credential = cls.query.filter(
            cls.platform == platform.lower(),
            cls.status == CredentialStatus.AVAILABLE.value,
            db.or_(
                cls.cooldown_until.is_(None),
                cls.cooldown_until <= now
            )
        ).order_by(
            # Prioritize credentials that haven't been used recently
            cls.last_success_at.asc().nullsfirst(),
            # Then by failure count (prefer less failures)
            cls.failure_count.asc()
        ).first()
        
        return credential

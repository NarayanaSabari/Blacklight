"""Business logic services package."""

import hashlib
import logging
from typing import Optional, Dict, List
from datetime import datetime

from app import db
from app.models import User, AuditLog
from app.schemas import UserResponseSchema

logger = logging.getLogger(__name__)


class UserService:
    """Service for user-related operations."""
    
    @staticmethod
    def create_user(username: str, email: str, password: str, is_active: bool = True) -> User:
        """Create a new user.
        
        Args:
            username: Username
            email: Email address
            password: Plain text password
            is_active: Whether user is active
        
        Returns:
            Created user
        
        Raises:
            ValueError: If user already exists
        """
        # Check if user already exists
        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing:
            raise ValueError("User already exists")
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            is_active=is_active,
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Log the action
        AuditLogService.log_action(
            action="CREATE",
            entity_type="User",
            entity_id=user.id,
            changes={"username": username, "email": email},
        )
        
        logger.info(f"User created: {username}")
        return user
    
    @staticmethod
    def get_user(user_id: int) -> Optional[User]:
        """Get user by ID.
        
        Args:
            user_id: User ID
        
        Returns:
            User or None
        """
        return db.session.get(User, user_id)
    
    @staticmethod
    def list_users(page: int = 1, per_page: int = 10) -> Dict:
        """List users with pagination.
        
        Args:
            page: Page number
            per_page: Items per page
        
        Returns:
            Paginated user list
        """
        pagination = db.paginate(
            db.select(User).order_by(User.created_at.desc()),
            page=page,
            per_page=per_page,
        )
        
        return {
            "items": [UserResponseSchema.model_validate(u) for u in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
        }
    
    @staticmethod
    def update_user(user_id: int, **kwargs) -> Optional[User]:
        """Update user.
        
        Args:
            user_id: User ID
            **kwargs: Fields to update
        
        Returns:
            Updated user or None
        
        Raises:
            ValueError: If user not found or invalid data
        """
        user = db.session.get(User, user_id)
        
        if not user:
            raise ValueError("User not found")
        
        allowed_fields = ["username", "email", "is_active"]
        changes = {}
        
        for field, value in kwargs.items():
            if field not in allowed_fields:
                continue
            
            if value is not None and getattr(user, field) != value:
                changes[field] = (getattr(user, field), value)
                setattr(user, field, value)
        
        if changes:
            db.session.commit()
            
            # Log the action
            AuditLogService.log_action(
                action="UPDATE",
                entity_type="User",
                entity_id=user_id,
                changes=changes,
            )
            
            logger.info(f"User updated: {user_id}")
        
        return user
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """Delete user.
        
        Args:
            user_id: User ID
        
        Returns:
            True if successful
        
        Raises:
            ValueError: If user not found
        """
        user = db.session.get(User, user_id)
        
        if not user:
            raise ValueError("User not found")
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        # Log the action
        AuditLogService.log_action(
            action="DELETE",
            entity_type="User",
            entity_id=user_id,
            changes={"username": username},
        )
        
        logger.info(f"User deleted: {user_id}")
        return True
    
    @staticmethod
    def verify_password(user: User, password: str) -> bool:
        """Verify user password.
        
        Args:
            user: User object
            password: Plain text password
        
        Returns:
            True if password matches
        """
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return user.password_hash == password_hash


class AuditLogService:
    """Service for audit logging."""
    
    @staticmethod
    def log_action(action: str, entity_type: str, entity_id: int, 
                   changes: Optional[Dict] = None, user_id: Optional[int] = None) -> AuditLog:
        """Log an action.
        
        Args:
            action: Action type (CREATE, UPDATE, DELETE, etc.)
            entity_type: Type of entity
            entity_id: Entity ID
            changes: Dictionary of changes
            user_id: User performing action
        
        Returns:
            Created audit log
        """
        audit_log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            user_id=user_id,
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
        logger.debug(f"Audit log: {action} {entity_type} {entity_id}")
        return audit_log
    
    @staticmethod
    def get_logs(entity_type: Optional[str] = None, 
                 entity_id: Optional[int] = None,
                 limit: int = 100) -> List[AuditLog]:
        """Get audit logs.
        
        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            limit: Maximum number of logs
        
        Returns:
            List of audit logs
        """
        query = AuditLog.query.order_by(AuditLog.created_at.desc())
        
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        
        if entity_id:
            query = query.filter_by(entity_id=entity_id)
        
        return query.limit(limit).all()

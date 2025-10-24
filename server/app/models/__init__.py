"""SQLAlchemy models package."""

from datetime import datetime
from app import db


class BaseModel(db.Model):
    """Base model with common columns."""
    
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        """String representation."""
        return f"<{self.__class__.__name__} id={self.id}>"


class User(BaseModel):
    """User model."""
    
    __tablename__ = "users"
    
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    def to_dict(self):
        """Convert model to dictionary."""
        data = super().to_dict()
        data.update({
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
        })
        return data


class AuditLog(BaseModel):
    """Audit log model for tracking changes."""
    
    __tablename__ = "audit_logs"
    
    action = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(100), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    changes = db.Column(db.JSON, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    
    def to_dict(self):
        """Convert model to dictionary."""
        data = super().to_dict()
        data.update({
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "changes": self.changes,
            "user_id": self.user_id,
        })
        return data

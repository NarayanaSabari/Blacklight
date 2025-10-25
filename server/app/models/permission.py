"""
Permission model for granular access control.
"""

from app import db
from sqlalchemy.orm import relationship
from datetime import datetime


class Permission(db.Model):
    """
    Permission model for RBAC system.
    
    Attributes:
        id: Primary key
        name: Permission name (e.g., 'candidates.create', 'jobs.delete')
        display_name: Human-readable permission name
        category: Permission category (e.g., 'candidates', 'jobs')
        description: Permission description
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    roles = relationship(
        'Role',
        secondary='role_permissions',
        back_populates='permissions',
        lazy='dynamic'
    )
    
    def __repr__(self):
        return f'<Permission {self.name}>'
    
    def to_dict(self):
        """Convert permission to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'category': self.category,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @staticmethod
    def get_by_category(category):
        """Get all permissions in a category."""
        return Permission.query.filter_by(category=category).all()
    
    @staticmethod
    def get_all_categories():
        """Get all unique permission categories."""
        return db.session.query(Permission.category).distinct().all()

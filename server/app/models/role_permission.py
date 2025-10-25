"""
RolePermission association table for many-to-many relationship.
"""

from app import db
from datetime import datetime


class RolePermission(db.Model):
    """
    Association table for Role-Permission many-to-many relationship.
    
    Attributes:
        id: Primary key
        role_id: Foreign key to roles
        permission_id: Foreign key to permissions
        created_at: Timestamp of assignment
    """
    
    __tablename__ = 'role_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(
        db.Integer,
        db.ForeignKey('roles.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    permission_id = db.Column(
        db.Integer,
        db.ForeignKey('permissions.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Table constraints
    __table_args__ = (
        db.UniqueConstraint('role_id', 'permission_id', name='uq_role_permissions_role_permission'),
    )
    
    def __repr__(self):
        return f'<RolePermission role_id={self.role_id} permission_id={self.permission_id}>'

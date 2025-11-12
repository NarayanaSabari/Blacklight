"""
UserRole association table for many-to-many relationship between PortalUser and Role.
"""

from app import db
from datetime import datetime


class UserRole(db.Model):
    """
    Association table for PortalUser-Role many-to-many relationship.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to portal_users
        role_id: Foreign key to roles
        created_at: Timestamp of assignment
    """
    
    __tablename__ = 'user_roles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('portal_users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    role_id = db.Column(
        db.Integer,
        db.ForeignKey('roles.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Table constraints
    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_id', name='uq_user_roles_user_role'),
    )
    
    def __repr__(self):
        return f'<UserRole user_id={self.user_id} role_id={self.role_id}>'

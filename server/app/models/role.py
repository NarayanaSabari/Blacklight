"""
Role model for dynamic role-based access control.
Supports both system roles and tenant-specific custom roles.
"""

from app import db
from sqlalchemy.orm import relationship
from datetime import datetime


class Role(db.Model):
    """
    Role model for RBAC system.
    
    Attributes:
        id: Primary key
        tenant_id: Foreign key to tenants (NULL for system roles)
        name: Role name (e.g., 'TENANT_ADMIN', 'RECRUITER')
        display_name: Human-readable role name
        description: Role description
        is_system_role: True for built-in roles, False for custom roles
        is_active: Whether role is currently active
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer, 
        db.ForeignKey('tenants.id', ondelete='CASCADE'), 
        nullable=True,
        index=True
    )
    name = db.Column(db.String(50), nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_system_role = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship('Tenant', back_populates='custom_roles')
    portal_users = relationship(
        'PortalUser',
        secondary='user_roles',
        back_populates='roles',
        lazy='select'
    )
    permissions = relationship(
        'Permission',
        secondary='role_permissions',
        back_populates='roles',
        lazy='dynamic'
    )
    
    # Table constraints
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'name', name='uq_roles_tenant_name'),
        db.CheckConstraint(
            '(is_system_role = true AND tenant_id IS NULL) OR (is_system_role = false)',
            name='ck_roles_system_role_tenant'
        ),
    )
    
    def __repr__(self):
        role_type = "System" if self.is_system_role else f"Tenant {self.tenant_id}"
        return f'<Role {self.name} ({role_type})>'
    
    def to_dict(self, include_permissions=False):
        """
        Convert role to dictionary.
        
        Args:
            include_permissions: Whether to include permission list
            
        Returns:
            Dictionary representation of role
        """
        data = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'is_system_role': self.is_system_role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_permissions:
            data['permissions'] = [p.to_dict() for p in self.permissions]
        
        return data
    
    @staticmethod
    def get_system_roles():
        """Get all system roles."""
        return Role.query.filter_by(is_system_role=True, is_active=True).all()
    
    @staticmethod
    def get_tenant_roles(tenant_id):
        """Get all roles for a specific tenant (including system roles)."""
        return Role.query.filter(
            db.or_(
                Role.tenant_id == tenant_id,
                Role.is_system_role == True
            ),
            Role.is_active == True
        ).all()

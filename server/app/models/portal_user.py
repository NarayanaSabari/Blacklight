"""Portal User model for tenant-specific users."""

from datetime import datetime
from sqlalchemy import Index
from app import db
from app.models import BaseModel


class PortalUser(BaseModel):
    """
    Portal User model.
    
    Tenant-specific users who access the ui/portal application.
    Each user belongs to exactly one tenant.
    Email is globally unique across ALL tenants.
    Login requires only email + password (tenant auto-detected).
    """
    
    __tablename__ = "portal_users"
    
    # Tenant Association (REQUIRED)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Authentication
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Personal Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    
    # Role & Permissions (Many-to-many with roles)
    roles = db.relationship(
        'Role',
        secondary='user_roles',
        back_populates='portal_users',
        lazy='select'
    )
    
    # Status & Access
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Security
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    tenant = db.relationship(
        'Tenant',
        back_populates='portal_users'
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_portal_user_tenant_id', 'tenant_id'),
        Index('idx_portal_user_email', 'email'),
    )
    
    @property
    def full_name(self):
        """Get full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_locked(self):
        """Check if account is locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    @property
    def is_tenant_admin(self):
        """Check if user is a tenant admin."""
        return any(role.name == 'TENANT_ADMIN' for role in self.roles)
    
    def has_permission(self, permission_name):
        """Check if user has a specific permission."""
        for role in self.roles:
            if any(p.name == permission_name for p in role.permissions):
                return True
        return False
    
    def get_permissions(self):
        """Get all unique permission names for this user."""
        permissions = set()
        for role in self.roles:
            for p in role.permissions:
                permissions.add(p.name)
        return list(permissions)
    
    def to_dict(self, include_tenant=False, include_permissions=False, include_roles=False):
        """Convert model to dictionary."""
        data = super().to_dict()
        data.update({
            "tenant_id": self.tenant_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone": self.phone,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_locked": self.is_locked,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
        })
        
        if include_roles:
            data["roles"] = [role.to_dict(include_permissions=False) for role in self.roles]
        
        if include_permissions:
            data["permissions"] = self.get_permissions()
        
        if include_tenant and self.tenant:
            data["tenant"] = {
                "id": self.tenant.id,
                "name": self.tenant.name,
                "slug": self.tenant.slug,
                "status": self.tenant.status.value if self.tenant.status else None,
            }
        
        return data
    
    def __repr__(self):
        """String representation."""
        role_names = ", ".join([role.name for role in self.roles]) if self.roles else 'NO_ROLES'
        return f"<PortalUser {self.email} - Roles: {role_names} (Tenant: {self.tenant_id})>"

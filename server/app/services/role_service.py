"""
Role service for managing roles and permissions.
Handles both system roles and tenant-specific custom roles.
"""

from typing import List, Optional, Dict
from sqlalchemy import or_
from app import db
from app.models import Role, Permission, RolePermission, Tenant


class RoleService:
    """Service for role management operations."""
    
    @staticmethod
    def get_all_roles(
        include_inactive: bool = False,
        tenant_id: Optional[int] = None,
        system_only: bool = False
    ) -> List[Role]:
        """
        Get all roles with optional filtering.
        
        Args:
            include_inactive: Include inactive roles
            tenant_id: Filter by tenant (includes system roles + tenant's custom roles)
            system_only: Only return system roles
            
        Returns:
            List of roles
        """
        query = db.session.query(Role)
        
        if system_only:
            query = query.filter(Role.is_system_role == True)
        elif tenant_id is not None:
            # Get system roles + tenant's custom roles
            query = query.filter(
                or_(
                    Role.is_system_role == True,
                    Role.tenant_id == tenant_id
                )
            )
        
        if not include_inactive:
            query = query.filter(Role.is_active == True)
        
        return query.order_by(Role.is_system_role.desc(), Role.name).all()
    
    @staticmethod
    def get_role_by_id(role_id: int) -> Optional[Role]:
        """Get role by ID."""
        return db.session.get(Role, role_id)
    
    @staticmethod
    def get_role_by_name(name: str, tenant_id: Optional[int] = None) -> Optional[Role]:
        """
        Get role by name.
        
        Args:
            name: Role name
            tenant_id: Tenant ID for custom roles (NULL for system roles)
            
        Returns:
            Role if found, None otherwise
        """
        query = db.session.query(Role).filter(Role.name == name.upper())
        
        if tenant_id is None:
            query = query.filter(Role.tenant_id.is_(None))
        else:
            query = query.filter(Role.tenant_id == tenant_id)
        
        return query.first()
    
    @staticmethod
    def create_role(
        name: str,
        display_name: str,
        description: Optional[str] = None,
        tenant_id: Optional[int] = None,
        permission_ids: Optional[List[int]] = None
    ) -> Role:
        """
        Create a new role.
        
        Args:
            name: Role name (will be uppercased)
            display_name: Human-readable name
            description: Role description
            tenant_id: Tenant ID for custom roles (NULL for system roles)
            permission_ids: List of permission IDs to assign
            
        Returns:
            Created role
            
        Raises:
            ValueError: If role already exists or validation fails
        """
        name = name.upper()
        
        # Check if role already exists for this tenant
        existing = RoleService.get_role_by_name(name, tenant_id)
        if existing:
            scope = f"tenant {tenant_id}" if tenant_id else "system"
            raise ValueError(f"Role '{name}' already exists for {scope}")
        
        # Validate tenant exists if tenant_id provided
        if tenant_id:
            tenant = db.session.get(Tenant, tenant_id)
            if not tenant:
                raise ValueError(f"Tenant with ID {tenant_id} not found")
            is_system_role = False
        else:
            is_system_role = True
        
        # Create role
        role = Role(
            name=name,
            display_name=display_name,
            description=description,
            tenant_id=tenant_id,
            is_system_role=is_system_role,
            is_active=True
        )
        
        db.session.add(role)
        db.session.flush()  # Get role ID before assigning permissions
        
        # Assign permissions if provided
        if permission_ids:
            RoleService.assign_permissions(role.id, permission_ids)
        
        db.session.commit()
        return role
    
    @staticmethod
    def update_role(
        role_id: int,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Role:
        """
        Update role.
        
        System roles: Only display_name, description, and is_active can be updated
        Custom roles: Same restrictions
        
        Args:
            role_id: Role ID
            display_name: New display name
            description: New description
            is_active: Active status
            
        Returns:
            Updated role
            
        Raises:
            ValueError: If role not found
        """
        role = RoleService.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")
        
        # Update allowed fields
        if display_name is not None:
            role.display_name = display_name
        if description is not None:
            role.description = description
        if is_active is not None:
            role.is_active = is_active
        
        db.session.commit()
        return role
    
    @staticmethod
    def delete_role(role_id: int) -> bool:
        """
        Delete a custom role.
        
        System roles cannot be deleted.
        Roles with assigned users cannot be deleted.
        
        Args:
            role_id: Role ID
            
        Returns:
            True if deleted
            
        Raises:
            ValueError: If role cannot be deleted
        """
        role = RoleService.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")
        
        if role.is_system_role:
            raise ValueError("Cannot delete system roles")
        
        # Check if role has assigned users
        user_count = role.users.count()
        if user_count > 0:
            raise ValueError(f"Cannot delete role with {user_count} assigned user(s)")
        
        db.session.delete(role)
        db.session.commit()
        return True
    
    @staticmethod
    def get_role_permissions(role_id: int) -> List[Permission]:
        """
        Get all permissions for a role.
        
        Args:
            role_id: Role ID
            
        Returns:
            List of permissions
            
        Raises:
            ValueError: If role not found
        """
        role = RoleService.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")
        
        return list(role.permissions)
    
    @staticmethod
    def assign_permissions(role_id: int, permission_ids: List[int]) -> Role:
        """
        Assign permissions to a role (replaces existing permissions).
        
        Args:
            role_id: Role ID
            permission_ids: List of permission IDs
            
        Returns:
            Updated role
            
        Raises:
            ValueError: If role not found or permissions invalid
        """
        role = RoleService.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")
        
        # Fetch permissions
        permissions = db.session.query(Permission).filter(
            Permission.id.in_(permission_ids)
        ).all()
        
        if len(permissions) != len(permission_ids):
            found_ids = {p.id for p in permissions}
            missing_ids = set(permission_ids) - found_ids
            raise ValueError(f"Permissions not found: {missing_ids}")
        
        # Remove existing permissions and add new ones
        db.session.query(RolePermission).filter(
            RolePermission.role_id == role_id
        ).delete()
        
        # Add new permissions
        for permission in permissions:
            role_permission = RolePermission(
                role_id=role.id,
                permission_id=permission.id
            )
            db.session.add(role_permission)
        
        db.session.commit()
        return role
    
    @staticmethod
    def add_permissions(role_id: int, permission_ids: List[int]) -> Role:
        """
        Add permissions to a role (keeps existing permissions).
        
        Args:
            role_id: Role ID
            permission_ids: List of permission IDs to add
            
        Returns:
            Updated role
        """
        role = RoleService.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")
        
        # Get existing permission IDs
        existing_ids = {p.id for p in role.permissions}
        
        # Filter out already assigned permissions
        new_ids = [pid for pid in permission_ids if pid not in existing_ids]
        
        if not new_ids:
            return role
        
        # Fetch new permissions
        permissions = db.session.query(Permission).filter(
            Permission.id.in_(new_ids)
        ).all()
        
        # Add new permissions
        for permission in permissions:
            role_permission = RolePermission(
                role_id=role.id,
                permission_id=permission.id
            )
            db.session.add(role_permission)
        
        db.session.commit()
        return role
    
    @staticmethod
    def remove_permissions(role_id: int, permission_ids: List[int]) -> Role:
        """
        Remove permissions from a role.
        
        Args:
            role_id: Role ID
            permission_ids: List of permission IDs to remove
            
        Returns:
            Updated role
        """
        role = RoleService.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")
        
        # Remove specified permissions
        db.session.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id.in_(permission_ids)
        ).delete(synchronize_session=False)
        
        db.session.commit()
        return role
    
    @staticmethod
    def get_role_stats() -> Dict:
        """
        Get role statistics.
        
        Returns:
            Dictionary with role counts
        """
        total_roles = db.session.query(Role).count()
        system_roles = db.session.query(Role).filter(Role.is_system_role == True).count()
        custom_roles = db.session.query(Role).filter(Role.is_system_role == False).count()
        active_roles = db.session.query(Role).filter(Role.is_active == True).count()
        
        return {
            'total_roles': total_roles,
            'system_roles': system_roles,
            'custom_roles': custom_roles,
            'active_roles': active_roles,
            'inactive_roles': total_roles - active_roles
        }

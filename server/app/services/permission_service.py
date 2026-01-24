"""
Permission service for managing permissions.
"""

from typing import List, Optional, Dict
from app import db
from app.models import Permission


class PermissionService:
    """Service for permission management operations."""
    
    @staticmethod
    def get_all_permissions(category: Optional[str] = None) -> List[Permission]:
        """
        Get all permissions with optional category filter.
        
        Args:
            category: Filter by category (e.g., 'candidates', 'jobs')
            
        Returns:
            List of permissions
        """
        query = db.session.query(Permission)
        
        if category:
            query = query.filter(Permission.category == category)
        
        return query.order_by(Permission.category, Permission.name).all()
    
    @staticmethod
    def get_permission_by_id(permission_id: int) -> Optional[Permission]:
        """Get permission by ID."""
        return db.session.get(Permission, permission_id)
    
    @staticmethod
    def get_permission_by_name(name: str) -> Optional[Permission]:
        """Get permission by name."""
        return db.session.query(Permission).filter(Permission.name == name).first()
    
    @staticmethod
    def get_permissions_by_category() -> Dict[str, List[Permission]]:
        """
        Get permissions grouped by category.
        
        Returns:
            Dictionary mapping category name to list of permissions
        """
        permissions = PermissionService.get_all_permissions()
        
        grouped = {}
        for permission in permissions:
            category = permission.category or 'other'
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(permission)
        
        return grouped
    
    @staticmethod
    def get_all_categories() -> List[str]:
        """
        Get all unique permission categories.
        
        Returns:
            List of category names
        """
        categories = db.session.query(Permission.category).distinct().all()
        return [cat[0] for cat in categories if cat[0]]
    
    @staticmethod
    def create_permission(
        name: str,
        display_name: str,
        category: Optional[str] = None,
        description: Optional[str] = None
    ) -> Permission:
        """
        Create a new permission.
        
        Note: Permissions should generally be seeded via migrations.
        This is for dynamic permission creation if needed.
        
        Args:
            name: Permission name (e.g., 'candidates.create')
            display_name: Human-readable name
            category: Permission category
            description: Permission description
            
        Returns:
            Created permission
            
        Raises:
            ValueError: If permission already exists
        """
        existing = PermissionService.get_permission_by_name(name)
        if existing:
            raise ValueError(f"Permission '{name}' already exists")
        
        permission = Permission(
            name=name,
            display_name=display_name,
            category=category,
            description=description
        )
        
        db.session.add(permission)
        db.session.commit()
        return permission
    
    @staticmethod
    def update_permission(
        permission_id: int,
        display_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Permission:
        """
        Update permission metadata.
        
        Note: Permission name and category are immutable.
        
        Args:
            permission_id: Permission ID
            display_name: New display name
            description: New description
            
        Returns:
            Updated permission
            
        Raises:
            ValueError: If permission not found
        """
        permission = PermissionService.get_permission_by_id(permission_id)
        if not permission:
            raise ValueError(f"Permission with ID {permission_id} not found")
        
        if display_name is not None:
            permission.display_name = display_name
        if description is not None:
            permission.description = description
        
        db.session.commit()
        return permission
    
    @staticmethod
    def delete_permission(permission_id: int) -> bool:
        """
        Delete a permission.
        
        Warning: This will cascade delete all role-permission associations.
        Should only be used for cleaning up unused permissions.
        
        Args:
            permission_id: Permission ID
            
        Returns:
            True if deleted
            
        Raises:
            ValueError: If permission not found or in use
        """
        permission = PermissionService.get_permission_by_id(permission_id)
        if not permission:
            raise ValueError(f"Permission with ID {permission_id} not found")
        
        # Check if permission is assigned to any roles
        role_count = permission.roles.count()
        if role_count > 0:
            raise ValueError(f"Cannot delete permission assigned to {role_count} role(s)")
        
        db.session.delete(permission)
        db.session.commit()
        db.session.expire_all()
        return True
    
    @staticmethod
    def get_permission_stats() -> Dict:
        """
        Get permission statistics.
        
        Returns:
            Dictionary with permission counts
        """
        total_permissions = db.session.query(Permission).count()
        categories = PermissionService.get_all_categories()
        
        category_counts = {}
        for category in categories:
            count = db.session.query(Permission).filter(
                Permission.category == category
            ).count()
            category_counts[category] = count
        
        return {
            'total_permissions': total_permissions,
            'total_categories': len(categories),
            'category_counts': category_counts
        }

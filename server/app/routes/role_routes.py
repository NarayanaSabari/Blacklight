"""
API routes for role and permission management.
"""

from flask import Blueprint, request, jsonify
from app.services import RoleService, PermissionService, AuditLogService
from app.schemas import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleWithPermissions,
    RoleListResponse,
    RoleAssignPermissions,
    PermissionResponse,
    PermissionListResponse,
)
from app.middleware.pm_admin import require_pm_admin
from app.middleware.portal_auth import require_portal_auth, require_tenant_admin, require_permission


# Use /api/portal prefix to avoid conflict with global_role_routes (/api/roles)
# Portal app uses these routes for tenant-specific role management
bp = Blueprint('roles', __name__, url_prefix='/api/portal')


# ============================================================================
# PERMISSION ROUTES
# ============================================================================

@bp.route('/permissions', methods=['GET'])
@require_portal_auth
@require_permission('roles.view')
def get_permissions():
    """
    Get all permissions.
    
    Query Parameters:
        category (str, optional): Filter by category
        
    Returns:
        200: List of permissions with categories
        500: Server error
    """
    try:
        category = request.args.get('category')
        permissions = PermissionService.get_all_permissions(category=category)
        categories = PermissionService.get_all_categories()
        
        response = PermissionListResponse(
            permissions=[PermissionResponse.model_validate(p) for p in permissions],
            total=len(permissions),
            categories=categories
        )
        
        return jsonify(response.model_dump()), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch permissions', 'message': str(e)}), 500


@bp.route('/permissions/<int:permission_id>', methods=['GET'])
@require_portal_auth
@require_permission('roles.view')
def get_permission(permission_id):
    """
    Get permission by ID.
    
    Args:
        permission_id: Permission ID
        
    Returns:
        200: Permission details
        404: Permission not found
        500: Server error
    """
    try:
        permission = PermissionService.get_permission_by_id(permission_id)
        if not permission:
            return jsonify({'error': 'Permission not found'}), 404
        
        response = PermissionResponse.model_validate(permission)
        return jsonify(response.model_dump()), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch permission', 'message': str(e)}), 500


@bp.route('/permissions/by-category', methods=['GET'])
@require_portal_auth
@require_permission('roles.view')
def get_permissions_by_category():
    """
    Get permissions grouped by category.
    
    Returns:
        200: Permissions grouped by category
        500: Server error
    """
    try:
        grouped = PermissionService.get_permissions_by_category()
        
        result = {}
        for category, permissions in grouped.items():
            result[category] = [PermissionResponse.model_validate(p).model_dump() for p in permissions]
        
        return jsonify({
            'permissions_by_category': result,
            'total_categories': len(result)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch permissions', 'message': str(e)}), 500


# ============================================================================
# SYSTEM ROLE ROUTES (PM Admin Only)
# ============================================================================

@bp.route('/roles/system', methods=['GET'])
@require_pm_admin
def get_system_roles():
    """
    Get all system roles.
    
    Query Parameters:
        include_inactive (bool): Include inactive roles
        include_permissions (bool): Include permission details
        
    Returns:
        200: List of system roles
        500: Server error
    """
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        include_permissions = request.args.get('include_permissions', 'false').lower() == 'true'
        
        roles = RoleService.get_all_roles(
            include_inactive=include_inactive,
            system_only=True
        )
        
        if include_permissions:
            response_roles = [RoleWithPermissions.model_validate(r) for r in roles]
        else:
            response_roles = [RoleResponse.model_validate(r) for r in roles]
        
        response = RoleListResponse(
            roles=response_roles,
            total=len(roles),
            page=1,
            per_page=len(roles)
        )
        
        return jsonify(response.model_dump()), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch system roles', 'message': str(e)}), 500


@bp.route('/roles/system/<int:role_id>/permissions', methods=['GET'])
@require_pm_admin
def get_system_role_permissions(role_id):
    """
    Get permissions for a system role.
    
    Args:
        role_id: Role ID
        
    Returns:
        200: List of permissions
        404: Role not found
        500: Server error
    """
    try:
        permissions = RoleService.get_role_permissions(role_id)
        
        response = PermissionListResponse(
            permissions=[PermissionResponse.model_validate(p) for p in permissions],
            total=len(permissions),
            categories=[]
        )
        
        return jsonify(response.model_dump()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': 'Failed to fetch permissions', 'message': str(e)}), 500


@bp.route('/roles/system/<int:role_id>/permissions', methods=['PUT'])
@require_pm_admin
def update_system_role_permissions(role_id):
    """
    Update permissions for a system role (PM Admin only).
    
    Args:
        role_id: Role ID
        
    Request Body:
        permission_ids: List of permission IDs
        
    Returns:
        200: Updated role with permissions
        400: Invalid request
        404: Role not found
        500: Server error
    """
    try:
        data = RoleAssignPermissions.model_validate(request.get_json())
        
        role = RoleService.assign_permissions(role_id, data.permission_ids)
        
        # Audit log
        pm_admin = getattr(request, 'pm_admin', {})
        changed_by = f"pm_admin:{pm_admin.get('user_id', 'system')}"
        AuditLogService.log_action(
            action='UPDATE_PERMISSIONS',
            entity_type='Role',
            entity_id=role.id,
            changed_by=changed_by,
            changes={'permission_ids': data.permission_ids}
        )
        
        response = RoleWithPermissions.model_validate(role)
        return jsonify(response.model_dump()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': 'Failed to update permissions', 'message': str(e)}), 500


# ============================================================================
# SIMPLIFIED ROLE ROUTES (Uses current user's tenant from JWT)
# ============================================================================

@bp.route('/roles', methods=['GET'])
@require_portal_auth
@require_permission('roles.view')
def get_roles():
    """
    Get all roles available to current user's tenant (system roles + tenant's custom roles).
    
    Uses tenant_id from authenticated user's JWT token.
    
    Query Parameters:
        include_inactive (bool): Include inactive roles
        include_permissions (bool): Include permission details
        include_user_counts (bool): Include user count for each role (default: true)
        
    Returns:
        200: List of roles
        500: Server error
    """
    try:
        # Get tenant_id from authenticated user's JWT token
        portal_user = getattr(request, 'portal_user', {})
        tenant_id = portal_user.get('tenant_id')
        
        if not tenant_id:
            return jsonify({'error': 'Tenant ID not found in session'}), 400
        
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        include_permissions = request.args.get('include_permissions', 'false').lower() == 'true'
        include_user_counts = request.args.get('include_user_counts', 'true').lower() == 'true'
        
        if include_user_counts:
            # Use new method that includes user counts
            roles_data = RoleService.get_all_roles_with_counts(
                include_inactive=include_inactive,
                tenant_id=tenant_id
            )
            
            # If permissions requested, fetch and add them
            if include_permissions:
                for role_data in roles_data:
                    role = RoleService.get_role_by_id(role_data['id'])
                    role_data['permissions'] = [p.to_dict() for p in role.permissions]
            
            return jsonify({
                'roles': roles_data,
                'total': len(roles_data),
                'page': 1,
                'per_page': len(roles_data)
            }), 200
        else:
            # Original behavior without user counts
            roles = RoleService.get_all_roles(
                include_inactive=include_inactive,
                tenant_id=tenant_id
            )
            
            if include_permissions:
                response_roles = [RoleWithPermissions.model_validate(r) for r in roles]
            else:
                response_roles = [RoleResponse.model_validate(r) for r in roles]
            
            response = RoleListResponse(
                roles=response_roles,
                total=len(roles),
                page=1,
                per_page=len(roles)
            )
            
            return jsonify(response.model_dump()), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch roles', 'message': str(e)}), 500


# ============================================================================
# TENANT ROLE ROUTES (Available to Tenant Admins)
# ============================================================================

@bp.route('/tenants/<int:tenant_id>/roles', methods=['GET'])
@require_tenant_admin
@require_permission('roles.view')
def get_tenant_roles(tenant_id):
    """
    Get all roles available to a tenant (system roles + tenant's custom roles).
    
    Args:
        tenant_id: Tenant ID
        
    Query Parameters:
        include_inactive (bool): Include inactive roles
        include_permissions (bool): Include permission details
        
    Returns:
        200: List of roles
        500: Server error
    """
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        include_permissions = request.args.get('include_permissions', 'false').lower() == 'true'
        
        roles = RoleService.get_all_roles(
            include_inactive=include_inactive,
            tenant_id=tenant_id
        )
        
        if include_permissions:
            response_roles = [RoleWithPermissions.model_validate(r) for r in roles]
        else:
            response_roles = [RoleResponse.model_validate(r) for r in roles]
        
        response = RoleListResponse(
            roles=response_roles,
            total=len(roles),
            page=1,
            per_page=len(roles)
        )
        
        return jsonify(response.model_dump()), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch roles', 'message': str(e)}), 500


@bp.route('/tenants/<int:tenant_id>/roles', methods=['POST'])
@require_tenant_admin
@require_permission('roles.create')
def create_tenant_role(tenant_id):
    """
    Create a custom role for a tenant (Tenant Admin only).
    
    Args:
        tenant_id: Tenant ID
        
    Request Body:
        name: Role name
        display_name: Display name
        description: Description (optional)
        permission_ids: List of permission IDs (optional)
        
    Returns:
        201: Created role
        400: Invalid request
        409: Role already exists
        500: Server error
    """
    try:
        data = RoleCreate.model_validate(request.get_json())
        
        # Force tenant_id from URL (security)
        role = RoleService.create_role(
            name=data.name,
            display_name=data.display_name,
            description=data.description,
            tenant_id=tenant_id,
            permission_ids=data.permission_ids
        )
        
        # Audit log
        portal_user = getattr(request, 'portal_user', {})
        changed_by = f"portal_user:{portal_user.get('user_id', 'unknown')}"
        AuditLogService.log_action(
            action='CREATE',
            entity_type='Role',
            entity_id=role.id,
            changed_by=changed_by,
            changes={'name': role.name, 'tenant_id': tenant_id}
        )
        
        response = RoleWithPermissions.model_validate(role)
        return jsonify(response.model_dump()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        return jsonify({'error': 'Failed to create role', 'message': str(e)}), 500


@bp.route('/tenants/<int:tenant_id>/roles/<int:role_id>', methods=['GET'])
@require_tenant_admin
@require_permission('roles.view')
def get_tenant_role(tenant_id, role_id):
    """
    Get a specific role.
    
    Args:
        tenant_id: Tenant ID
        role_id: Role ID
        
    Returns:
        200: Role details with permissions
        404: Role not found
        500: Server error
    """
    try:
        role = RoleService.get_role_by_id(role_id)
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Verify role belongs to tenant or is a system role
        if role.tenant_id is not None and role.tenant_id != tenant_id:
            return jsonify({'error': 'Role not found'}), 404
        
        response = RoleWithPermissions.model_validate(role)
        return jsonify(response.model_dump()), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch role', 'message': str(e)}), 500


@bp.route('/tenants/<int:tenant_id>/roles/<int:role_id>', methods=['PUT'])
@require_tenant_admin
@require_permission('roles.edit')
def update_tenant_role(tenant_id, role_id):
    """
    Update a custom role (Tenant Admin only).
    
    Can only update roles that belong to the tenant.
    System roles cannot be updated by tenant admins.
    
    Args:
        tenant_id: Tenant ID
        role_id: Role ID
        
    Request Body:
        display_name: New display name (optional)
        description: New description (optional)
        is_active: Active status (optional)
        
    Returns:
        200: Updated role
        403: Cannot update system role
        404: Role not found
        500: Server error
    """
    try:
        role = RoleService.get_role_by_id(role_id)
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Verify role belongs to tenant
        if role.tenant_id != tenant_id:
            return jsonify({'error': 'Cannot update system role or role from another tenant'}), 403
        
        data = RoleUpdate.model_validate(request.get_json())
        
        updated_role = RoleService.update_role(
            role_id=role_id,
            display_name=data.display_name,
            description=data.description,
            is_active=data.is_active
        )
        
        # Audit log
        portal_user = getattr(request, 'portal_user', {})
        changed_by = f"portal_user:{portal_user.get('user_id', 'unknown')}"
        AuditLogService.log_action(
            action='UPDATE',
            entity_type='Role',
            entity_id=role_id,
            changed_by=changed_by,
            changes=data.model_dump(exclude_unset=True)
        )
        
        response = RoleResponse.model_validate(updated_role)
        return jsonify(response.model_dump()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': 'Failed to update role', 'message': str(e)}), 500


@bp.route('/tenants/<int:tenant_id>/roles/<int:role_id>', methods=['DELETE'])
@require_tenant_admin
@require_permission('roles.delete')
def delete_tenant_role(tenant_id, role_id):
    """
    Delete a custom role (Tenant Admin only).
    
    Can only delete roles that belong to the tenant.
    System roles cannot be deleted.
    Roles with assigned users cannot be deleted.
    
    Args:
        tenant_id: Tenant ID
        role_id: Role ID
        
    Returns:
        200: Role deleted successfully
        403: Cannot delete system role
        404: Role not found
        409: Role has assigned users
        500: Server error
    """
    try:
        role = RoleService.get_role_by_id(role_id)
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Verify role belongs to tenant
        if role.tenant_id != tenant_id:
            return jsonify({'error': 'Cannot delete system role or role from another tenant'}), 403
        
        RoleService.delete_role(role_id)
        
        # Audit log
        portal_user = getattr(request, 'portal_user', {})
        changed_by = f"portal_user:{portal_user.get('user_id', 'unknown')}"
        AuditLogService.log_action(
            action='DELETE',
            entity_type='Role',
            entity_id=role_id,
            changed_by=changed_by,
            changes={'name': role.name}
        )
        
        return jsonify({'message': 'Role deleted successfully'}), 200
    except ValueError as e:
        if 'assigned user' in str(e).lower():
            return jsonify({'error': str(e)}), 409
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': 'Failed to delete role', 'message': str(e)}), 500


@bp.route('/tenants/<int:tenant_id>/roles/<int:role_id>/permissions', methods=['PUT'])
@require_tenant_admin
@require_permission('roles.edit')
def update_tenant_role_permissions(tenant_id, role_id):
    """
    Update permissions for a custom role (Tenant Admin only).
    
    Args:
        tenant_id: Tenant ID
        role_id: Role ID
        
    Request Body:
        permission_ids: List of permission IDs
        
    Returns:
        200: Updated role with permissions
        403: Cannot update system role
        404: Role not found
        500: Server error
    """
    try:
        role = RoleService.get_role_by_id(role_id)
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Verify role belongs to tenant
        if role.tenant_id != tenant_id:
            return jsonify({'error': 'Cannot update system role or role from another tenant'}), 403
        
        data = RoleAssignPermissions.model_validate(request.get_json())
        
        updated_role = RoleService.assign_permissions(role_id, data.permission_ids)
        
        # Audit log
        portal_user = getattr(request, 'portal_user', {})
        changed_by = f"portal_user:{portal_user.get('user_id', 'unknown')}"
        AuditLogService.log_action(
            action='UPDATE_PERMISSIONS',
            entity_type='Role',
            entity_id=role_id,
            changed_by=changed_by,
            changes={'permission_ids': data.permission_ids}
        )
        
        response = RoleWithPermissions.model_validate(updated_role)
        return jsonify(response.model_dump()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': 'Failed to update permissions', 'message': str(e)}), 500


# ============================================================================
# STATS & UTILITY ROUTES
# ============================================================================

@bp.route('/roles/stats', methods=['GET'])
@require_pm_admin
def get_role_stats():
    """
    Get role statistics (PM Admin only).
    
    Returns:
        200: Role statistics
        500: Server error
    """
    try:
        stats = RoleService.get_role_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch stats', 'message': str(e)}), 500


@bp.route('/permissions/stats', methods=['GET'])
@require_pm_admin
def get_permission_stats():
    """
    Get permission statistics (PM Admin only).
    
    Returns:
        200: Permission statistics
        500: Server error
    """
    try:
        stats = PermissionService.get_permission_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch stats', 'message': str(e)}), 500

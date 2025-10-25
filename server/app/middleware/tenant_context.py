"""Tenant context middleware - Extract and attach tenant context for portal users."""

from functools import wraps
from flask import request, g
from typing import Optional


def with_tenant_context(f):
    """
    Decorator to extract tenant context from authenticated portal user.
    
    Requires portal authentication to be applied first.
    Attaches tenant_id to Flask's g object for easy access in services.
    
    Usage:
        @bp.route("/tenant-specific")
        @require_portal_auth
        @with_tenant_context
        def tenant_endpoint():
            tenant_id = g.tenant_id
            return {"tenant_id": tenant_id}
    
    Note: This should be applied AFTER authentication decorators.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get portal user from request context (set by portal_auth middleware)
        portal_user = getattr(request, "portal_user", None)
        
        if portal_user:
            # Extract tenant_id and attach to Flask's g object
            g.tenant_id = portal_user.get("tenant_id")
            g.user_id = portal_user.get("user_id")
            g.user_role = portal_user.get("role")
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_tenant_id() -> Optional[int]:
    """
    Helper function to get current tenant ID from context.
    
    Returns:
        Tenant ID if available, None otherwise
    
    Usage:
        from app.middleware.tenant_context import get_current_tenant_id
        
        tenant_id = get_current_tenant_id()
        if tenant_id:
            # Do tenant-specific operations
    """
    return getattr(g, "tenant_id", None)


def get_current_user_id() -> Optional[int]:
    """
    Helper function to get current portal user ID from context.
    
    Returns:
        User ID if available, None otherwise
    
    Usage:
        from app.middleware.tenant_context import get_current_user_id
        
        user_id = get_current_user_id()
        if user_id:
            # Do user-specific operations
    """
    return getattr(g, "user_id", None)


def get_current_user_role() -> Optional[str]:
    """
    Helper function to get current portal user role from context.
    
    Returns:
        User role if available, None otherwise
    
    Usage:
        from app.middleware.tenant_context import get_current_user_role
        
        role = get_current_user_role()
        if role == "TENANT_ADMIN":
            # Admin-specific operations
    """
    return getattr(g, "user_role", None)


def require_role(*allowed_roles):
    """
    Decorator to require specific portal user roles.
    
    Must be used after @require_portal_auth and @with_tenant_context.
    
    Args:
        *allowed_roles: One or more role strings (e.g., "TENANT_ADMIN", "RECRUITER")
    
    Usage:
        @bp.route("/admin-or-recruiter")
        @require_portal_auth
        @with_tenant_context
        @require_role("TENANT_ADMIN", "RECRUITER")
        def admin_or_recruiter_endpoint():
            return {"message": "Admin or recruiter access"}
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import jsonify
            
            current_role = get_current_user_role()
            
            if not current_role:
                return jsonify({
                    "error": "Forbidden",
                    "message": "User role not found in context",
                    "status": 403,
                }), 403
            
            if current_role not in allowed_roles:
                return jsonify({
                    "error": "Forbidden",
                    "message": f"Access denied. Required roles: {', '.join(allowed_roles)}",
                    "status": 403,
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

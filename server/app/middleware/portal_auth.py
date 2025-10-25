"""Portal user authentication middleware."""

from functools import wraps
from flask import request, jsonify
from app.services import PortalAuthService


def error_response(message: str, status: int = 401):
    """Helper to create error responses."""
    return jsonify({
        "error": "Unauthorized",
        "message": message,
        "status": status,
    }), status


def require_portal_auth(f):
    """
    Decorator to require Portal user authentication.
    
    Validates JWT token, checks if user exists and is active,
    verifies tenant is active, and attaches user info to request context.
    
    Usage:
        @bp.route("/portal-only")
        @require_portal_auth
        def portal_endpoint():
            user = request.portal_user
            return {"user_id": user["user_id"], "tenant_id": user["tenant_id"]}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return error_response("Authorization header is required")
        
        # Extract token
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return error_response("Invalid Authorization header format. Use: Bearer <token>")
        
        access_token = parts[1]
        
        try:
            # Validate token (also checks user is active and tenant is ACTIVE)
            payload = PortalAuthService.validate_token(access_token)
            
            # Attach user info to request context
            request.portal_user = payload
            
            return f(*args, **kwargs)
            
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            return error_response(f"Authentication failed: {str(e)}", 500)
    
    return decorated_function


def require_tenant_admin(f):
    """
    Decorator to require Portal user authentication with TENANT_ADMIN role.
    
    First validates authentication, then checks if user is TENANT_ADMIN.
    
    Usage:
        @bp.route("/admin-only")
        @require_tenant_admin
        def tenant_admin_endpoint():
            user = request.portal_user
            return {"message": "Only TENANT_ADMIN can access this"}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return error_response("Authorization header is required")
        
        # Extract token
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return error_response("Invalid Authorization header format. Use: Bearer <token>")
        
        access_token = parts[1]
        
        try:
            # Validate token
            payload = PortalAuthService.validate_token(access_token)
            
            # Check if user is TENANT_ADMIN
            if payload.get("role_name") != "TENANT_ADMIN":
                return error_response(
                    "Access denied: TENANT_ADMIN role required",
                    403
                )
            
            # Attach user info to request context
            request.portal_user = payload
            
            return f(*args, **kwargs)
            
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            return error_response(f"Authentication failed: {str(e)}", 500)
    
    return decorated_function


def optional_portal_auth(f):
    """
    Decorator to optionally extract Portal user info if token is present.
    
    Does not require authentication, but if a valid token is present,
    it will be validated and attached to request context.
    
    Usage:
        @bp.route("/maybe-auth")
        @optional_portal_auth
        def maybe_auth_endpoint():
            user = getattr(request, "portal_user", None)
            if user:
                return {"user_id": user["user_id"]}
            return {"message": "No user authenticated"}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get Authorization header
        auth_header = request.headers.get("Authorization")
        
        if auth_header:
            # Extract token
            parts = auth_header.split()
            
            if len(parts) == 2 and parts[0].lower() == "bearer":
                access_token = parts[1]
                
                try:
                    # Validate token
                    payload = PortalAuthService.validate_token(access_token)
                    
                    # Attach user info to request context
                    request.portal_user = payload
                    
                except Exception:
                    # Silently ignore invalid tokens for optional auth
                    pass
        
        return f(*args, **kwargs)
    
    return decorated_function

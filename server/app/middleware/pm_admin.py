"""PM Admin authentication middleware."""

from functools import wraps
from flask import request, jsonify
from app.services import PMAdminAuthService


def error_response(message: str, status: int = 401):
    """Helper to create error responses."""
    return jsonify({
        "error": "Unauthorized",
        "message": message,
        "status": status,
    }), status


def require_pm_admin(f):
    """
    Decorator to require PM Admin authentication.
    
    Validates JWT token, checks if admin exists and is active,
    and attaches admin info to request context.
    
    Usage:
        @bp.route("/admin-only")
        @require_pm_admin
        def admin_endpoint():
            admin = request.pm_admin
            return {"admin_id": admin["user_id"]}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return f(*args, **kwargs)
        
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
            payload = PMAdminAuthService.validate_token(access_token)
            
            # Attach admin info to request context
            request.pm_admin = payload
            
            return f(*args, **kwargs)
            
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            return error_response(f"Authentication failed: {str(e)}", 500)
    
    return decorated_function


def optional_pm_admin(f):
    """
    Decorator to optionally extract PM Admin info if token is present.
    
    Does not require authentication, but if a valid token is present,
    it will be validated and attached to request context.
    
    Usage:
        @bp.route("/maybe-admin")
        @optional_pm_admin
        def maybe_admin_endpoint():
            admin = getattr(request, "pm_admin", None)
            if admin:
                return {"admin_id": admin["user_id"]}
            return {"message": "No admin authenticated"}
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
                    payload = PMAdminAuthService.validate_token(access_token)
                    
                    # Attach admin info to request context
                    request.pm_admin = payload
                    
                except Exception:
                    # Silently ignore invalid tokens for optional auth
                    pass
        
        return f(*args, **kwargs)
    
    return decorated_function

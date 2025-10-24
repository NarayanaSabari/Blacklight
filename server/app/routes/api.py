"""API routes for the application."""

from flask import Blueprint, jsonify, current_app, request
from datetime import datetime
from pydantic import ValidationError

from app import db
from app.models import User, AuditLog
from app.schemas import (
    UserCreateSchema,
    UserUpdateSchema,
    UserResponseSchema,
    UserListSchema,
    HealthCheckSchema,
    AppInfoSchema,
    ErrorResponseSchema,
)

bp = Blueprint("api", __name__, url_prefix="/api")


def error_response(message: str, status: int = 400, details: dict = None):
    """Create a standardized error response."""
    return jsonify({
        "error": "Error",
        "message": message,
        "status": status,
        "details": details,
    }), status


@bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    schema = HealthCheckSchema(
        status="healthy",
        timestamp=datetime.utcnow(),
        environment=current_app.config.get("ENV", "development"),
    )
    return jsonify(schema.model_dump()), 200


@bp.route("/info", methods=["GET"])
def app_info():
    """Get application information."""
    schema = AppInfoSchema(
        name="Blacklight Server",
        version="0.1.0",
        environment=current_app.config.get("ENV", "development"),
        debug=current_app.debug,
        timestamp=datetime.utcnow(),
    )
    return jsonify(schema.model_dump()), 200


@bp.route("/", methods=["GET"])
def root():
    """Root API endpoint."""
    return jsonify({
        "message": "Welcome to Blacklight API",
        "endpoints": {
            "health": "/api/health",
            "info": "/api/info",
            "users": "/api/users",
        },
    }), 200


# User Endpoints

@bp.route("/users", methods=["GET"])
def list_users():
    """List all users with pagination."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    
    # Validate pagination parameters
    if page < 1 or per_page < 1 or per_page > 100:
        return error_response("Invalid pagination parameters", 400)
    
    pagination = db.paginate(
        db.select(User).order_by(User.created_at.desc()),
        page=page,
        per_page=per_page,
    )
    
    items = [UserResponseSchema.model_validate(user) for user in pagination.items]
    
    response = UserListSchema(
        items=items,
        total=pagination.total,
        page=page,
        per_page=per_page,
    )
    
    return jsonify(response.model_dump()), 200


@bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    """Get a user by ID."""
    user = db.session.get(User, user_id)
    
    if not user:
        return error_response("User not found", 404)
    
    schema = UserResponseSchema.model_validate(user)
    return jsonify(schema.model_dump()), 200


@bp.route("/users", methods=["POST"])
def create_user():
    """Create a new user."""
    try:
        # Validate request body
        schema = UserCreateSchema.model_validate(request.get_json())
    except ValidationError as e:
        return error_response(
            "Invalid request body",
            400,
            details=e.errors()
        )
    
    # Check if user already exists
    existing_user = User.query.filter(
        (User.username == schema.username) | (User.email == schema.email)
    ).first()
    
    if existing_user:
        return error_response("User already exists", 409)
    
    # Create new user
    import hashlib
    user = User(
        username=schema.username,
        email=schema.email,
        password_hash=hashlib.sha256(schema.password.encode()).hexdigest(),
        is_active=True,
    )
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # Log the action
        audit_log = AuditLog(
            action="CREATE",
            entity_type="User",
            entity_id=user.id,
            changes={"username": user.username, "email": user.email},
        )
        db.session.add(audit_log)
        db.session.commit()
        
        response_schema = UserResponseSchema.model_validate(user)
        return jsonify(response_schema.model_dump()), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating user: {e}")
        return error_response("Failed to create user", 500)


@bp.route("/users/<int:user_id>", methods=["PUT", "PATCH"])
def update_user(user_id: int):
    """Update a user."""
    user = db.session.get(User, user_id)
    
    if not user:
        return error_response("User not found", 404)
    
    try:
        schema = UserUpdateSchema.model_validate(request.get_json())
    except ValidationError as e:
        return error_response(
            "Invalid request body",
            400,
            details=e.errors()
        )
    
    try:
        # Track changes
        changes = {}
        
        if schema.username is not None and schema.username != user.username:
            changes["username"] = (user.username, schema.username)
            user.username = schema.username
        
        if schema.email is not None and schema.email != user.email:
            changes["email"] = (user.email, schema.email)
            user.email = schema.email
        
        if schema.is_active is not None and schema.is_active != user.is_active:
            changes["is_active"] = (user.is_active, schema.is_active)
            user.is_active = schema.is_active
        
        if changes:
            db.session.commit()
            
            # Log the action
            audit_log = AuditLog(
                action="UPDATE",
                entity_type="User",
                entity_id=user.id,
                changes=changes,
            )
            db.session.add(audit_log)
            db.session.commit()
        
        response_schema = UserResponseSchema.model_validate(user)
        return jsonify(response_schema.model_dump()), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user: {e}")
        return error_response("Failed to update user", 500)


@bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id: int):
    """Delete a user."""
    user = db.session.get(User, user_id)
    
    if not user:
        return error_response("User not found", 404)
    
    try:
        db.session.delete(user)
        db.session.commit()
        
        # Log the action
        audit_log = AuditLog(
            action="DELETE",
            entity_type="User",
            entity_id=user_id,
            changes={"username": user.username},
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({"message": "User deleted successfully"}), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {e}")
        return error_response("Failed to delete user", 500)

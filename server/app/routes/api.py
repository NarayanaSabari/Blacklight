"""API routes for the application."""

from flask import Blueprint, jsonify, current_app, request
from datetime import datetime
from pydantic import ValidationError

from app import db
from app.models import AuditLog
from app.schemas import (
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
        "version": "0.1.0",
        "endpoints": {
            "health": "/api/health",
            "info": "/api/info",
        },
    }), 200


@bp.route("/debug/routes", methods=["GET"])
def debug_routes():
    """Debug endpoint to list all registered routes."""
    import sys
    
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": sorted(list(rule.methods - {"HEAD", "OPTIONS"})),
            "path": rule.rule,
        })
    
    # Sort by path
    routes.sort(key=lambda x: x["path"])
    
    return jsonify({
        "python_executable": sys.executable,
        "python_version": sys.version,
        "total_routes": len(routes),
        "tenant_routes": [r for r in routes if "tenant" in r["path"]],
        "all_routes": routes,
    }), 200

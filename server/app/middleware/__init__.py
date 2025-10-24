"""Custom middleware package."""

from flask import Flask, request, jsonify
from datetime import datetime
import uuid
import logging


def setup_request_logging_middleware(app: Flask) -> None:
    """Setup request logging middleware."""
    
    @app.before_request
    def log_request():
        """Log incoming requests."""
        request.request_id = str(uuid.uuid4())
        request.start_time = datetime.utcnow()
        
        app.logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                "request_id": request.request_id,
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
            }
        )
    
    @app.after_request
    def log_response(response):
        """Log outgoing responses."""
        duration = (datetime.utcnow() - request.start_time).total_seconds() * 1000
        
        app.logger.info(
            f"Request completed: {request.method} {request.path}",
            extra={
                "request_id": request.request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration,
            }
        )
        
        response.headers["X-Request-ID"] = request.request_id
        return response


def setup_error_response_middleware(app: Flask) -> None:
    """Setup error response formatting middleware."""
    
    @app.before_request
    def check_request_json():
        """Validate JSON content type when necessary."""
        if request.method in ["POST", "PUT", "PATCH"]:
            if request.data and not request.is_json:
                return jsonify({
                    "error": "Bad Request",
                    "message": "Content-Type must be application/json",
                    "status": 400,
                }), 400


def register_middleware(app: Flask) -> None:
    """Register all middleware."""
    setup_request_logging_middleware(app)
    setup_error_response_middleware(app)

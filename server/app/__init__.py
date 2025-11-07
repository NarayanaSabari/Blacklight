"""Flask application factory and initialization."""

import logging
import logging.config
from typing import Type

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import redis

from config.base import BaseConfig

# Initialize extensions
db = SQLAlchemy()
cors = CORS()
redis_client = None


def setup_logging(app: Flask, log_format: str = "json") -> None:
    """Setup logging configuration for the application."""
    log_level = app.config.get("LOG_LEVEL", "INFO")
    
    if log_format == "json":
        # Structured JSON logging
        from pythonjsonlogger import jsonlogger
        
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter()
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)
    
    # Set log level
    app.logger.setLevel(getattr(logging, log_level))
    
    # Log application startup information
    app.logger.info(
        "Application initialized",
        extra={
            "environment": app.config.get("ENV", "development"),
            "debug": app.debug,
            "testing": app.testing,
        }
    )


def setup_redis(app: Flask) -> redis.Redis:
    """Setup Redis connection."""
    redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        redis_conn = redis.from_url(redis_url, decode_responses=True)
        redis_conn.ping()
        app.logger.info(f"Redis connected: {redis_url}")
        return redis_conn
    except Exception as e:
        app.logger.error(f"Failed to connect to Redis: {e}")
        if app.config.get("ENV") == "production":
            raise
        return None


def setup_error_handlers(app: Flask) -> None:
    """Register error handlers."""
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return {
            "error": "Not Found",
            "message": "The requested resource was not found",
            "status": 404,
        }, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        app.logger.error(f"Internal server error: {error}")
        return {
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status": 500,
        }, 500
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors."""
        return {
            "error": "Method Not Allowed",
            "message": "The HTTP method is not allowed for this resource",
            "status": 405,
        }, 405
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 errors."""
        return {
            "error": "Bad Request",
            "message": "The request was invalid",
            "status": 400,
        }, 400


def register_blueprints(app: Flask) -> None:
    """Register Flask blueprints."""
    from app.routes import api
    from app.routes import subscription_plan_routes
    from app.routes import tenant_routes
    from app.routes import portal_user_routes
    from app.routes import pm_admin_routes
    from app.routes import role_routes
    from app.routes import candidate_routes
    
    # Legacy API routes (health check, etc.)
    app.register_blueprint(api.bp)
    
    # Tenant Management System routes
    app.register_blueprint(subscription_plan_routes.bp)
    app.register_blueprint(tenant_routes.bp)
    app.register_blueprint(portal_user_routes.bp)
    app.register_blueprint(pm_admin_routes.bp)
    
    # Role and Permission Management routes
    app.register_blueprint(role_routes.bp)
    
    # Candidate and Resume Parsing routes
    app.register_blueprint(candidate_routes.candidate_bp)


def create_app(config: Type[BaseConfig] = None) -> Flask:
    """Create and configure Flask application.
    
    Args:
        config: Configuration class to use. If None, uses environment-based config.
    
    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    
    # Load configuration
    if config is None:
        from config.settings import settings
        
        if settings.is_production:
            from config.production import ProductionConfig
            config = ProductionConfig
        elif settings.is_testing:
            from config.testing import TestingConfig
            config = TestingConfig
        else:
            from config.development import DevelopmentConfig
            config = DevelopmentConfig
    
    app.config.from_object(config)
    
    # Setup logging
    setup_logging(app, app.config.get("LOG_FORMAT", "json"))
    
    # Initialize extensions
    db.init_app(app)
    cors.init_app(app, resources={
        r"/*": {
            "origins": app.config.get("CORS_ORIGINS", ["*"]),
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": app.config.get("CORS_ALLOW_HEADERS", ["*"]),
            "expose_headers": app.config.get("CORS_EXPOSE_HEADERS", ["*"]),
            "supports_credentials": app.config.get("CORS_SUPPORTS_CREDENTIALS", True),
        }
    })
    
    # Setup Redis
    global redis_client
    redis_client = setup_redis(app)
    
    # Setup error handlers
    setup_error_handlers(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Log application info
    app.logger.info(
        "Flask application created",
        extra={
            "config": config.__name__,
            "database": app.config.get("SQLALCHEMY_DATABASE_URI", "").split("://")[0],
        }
    )
    
    return app


def get_db():
    """Get database instance."""
    return db


def get_redis():
    """Get Redis client instance."""
    return redis_client

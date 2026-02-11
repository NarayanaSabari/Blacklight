"""Flask application factory and initialization."""

import logging
import logging.config
from typing import Type

from flask import Flask, request, has_request_context, g
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis

from config.base import BaseConfig

# Initialize extensions
db = SQLAlchemy()
cors = CORS()

# Custom key function for rate limiting that exempts certain endpoints
def _get_rate_limit_key():
    """
    Get key for rate limiting. Returns None for exempt endpoints.
    Returning None disables rate limiting for that request.
    """
    if has_request_context() and request.path:
        # Exempt Inngest endpoint from rate limiting (heartbeat + function execution)
        if request.path.startswith('/api/inngest'):
            return None
        # Exempt scraper monitoring routes (admin dashboard polling)
        if request.path.startswith('/api/scraper-monitoring'):
            return None
    # For all other endpoints, use remote address
    return get_remote_address()

limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[]
)
redis_client = None


class SuppressInngestHeartbeatFilter(logging.Filter):
    """Filter to suppress Inngest heartbeat requests from access logs."""
    
    def filter(self, record):
        # Suppress PUT requests to /api/inngest (Inngest heartbeat/sync)
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            if 'PUT /api/inngest' in record.msg and '200' in record.msg:
                return False
        return True


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
    
    # Suppress Inngest heartbeat logs from Werkzeug (Flask's request logger)
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(SuppressInngestHeartbeatFilter())
    
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
    from app.routes import candidate_resume_routes
    from app.routes import invitation_routes
    from app.routes import document_routes
    from app.routes import public_document_routes
    from app.routes import public_onboarding_routes
    from app.routes import team_routes
    from app.routes import candidate_assignment_routes
    from app.routes import candidate_onboarding_routes
    from app.routes import job_import_routes
    from app.routes import job_match_routes
    from app.routes import job_posting_routes
    from app.routes import embedding_routes
    from app.routes import scraper_routes
    from app.routes import global_role_routes
    from app.routes import scraper_monitoring_routes
    from app.routes import resume_tailor_routes
    from app.routes import email_integration_routes
    from app.routes import email_jobs_routes
    from app.routes import dashboard_routes
    from app.routes import submission_routes
    from app.routes import scraper_credential_routes
    
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
    
    # Candidate Resume Management routes (multi-resume support)
    app.register_blueprint(candidate_resume_routes.candidate_resume_bp)
    
    # Candidate Onboarding routes
    app.register_blueprint(invitation_routes.bp)
    
    # Document Management routes
    app.register_blueprint(document_routes.document_bp)
    app.register_blueprint(public_document_routes.public_document_bp)
    
    # Public Onboarding routes (resume parsing, etc.)
    app.register_blueprint(public_onboarding_routes.public_onboarding_bp)
    
    # Team Management routes
    app.register_blueprint(team_routes.team_bp)
    
    # Candidate Assignment routes
    app.register_blueprint(candidate_assignment_routes.assignment_bp)
    
    # Candidate Onboarding Workflow routes
    app.register_blueprint(candidate_onboarding_routes.onboarding_bp)
    
        # Job Import and Management routes
    app.register_blueprint(job_import_routes.job_import_bp)
    
    # Job Posting routes
    app.register_blueprint(job_posting_routes.job_posting_bp)
    
    # Job Matching routes (AI-powered)
    app.register_blueprint(job_match_routes.job_match_bp)
    
    # Embedding Management routes (PM_ADMIN only)
    app.register_blueprint(embedding_routes.embedding_bp)
    
    # Scraper API routes (for external job scrapers)
    app.register_blueprint(scraper_routes.scraper_bp)
    
    # Global Role Management routes (PM_ADMIN only)
    app.register_blueprint(global_role_routes.global_role_bp)
    
    # Scraper Monitoring routes (PM_ADMIN dashboard)
    app.register_blueprint(scraper_monitoring_routes.scraper_monitoring_bp)
    
    # Resume Tailor routes (AI-powered resume optimization)
    app.register_blueprint(resume_tailor_routes.resume_tailor_bp)
    
    # Email Integration routes (Gmail/Outlook OAuth)
    app.register_blueprint(email_integration_routes.bp)
    
    # Email Jobs routes (jobs sourced from email)
    app.register_blueprint(email_jobs_routes.bp)
    
    # Dashboard routes (portal dashboard stats)
    app.register_blueprint(dashboard_routes.dashboard_bp)
    
    # Submission Tracking routes (ATS - candidate submissions to jobs)
    app.register_blueprint(submission_routes.submission_bp)
    
    # Scraper Credential routes (credential management for scrapers)
    app.register_blueprint(scraper_credential_routes.scraper_credentials_bp)


def register_inngest(app: Flask) -> None:
    """Register Inngest background job functions."""
    try:
        from inngest.flask import serve as inngest_serve_func
        from app.inngest import inngest_client
        from app.inngest.functions import INNGEST_FUNCTIONS
        from config.settings import settings
        
        # Get the Inngest serve path (default: /api/inngest)
        inngest_path = app.config.get('INNGEST_SERVE_PATH', '/api/inngest')
        
        app.logger.info(f"Inngest: Attempting to register {len(INNGEST_FUNCTIONS)} functions")
        app.logger.info(f"Inngest: Functions to register: {[f.name for f in INNGEST_FUNCTIONS]}")
        app.logger.info(f"Inngest: Production Mode: {inngest_client.is_production}")
        
        # Build serve_origin for production (tells Inngest Cloud where to reach this server)
        serve_origin = settings.inngest_serve_host if not settings.inngest_dev else None
        app.logger.info(f"Inngest: Serve Origin: {serve_origin}")
        
        # Register Inngest endpoint
        inngest_serve_func(
            app,
            inngest_client,
            INNGEST_FUNCTIONS,
            serve_origin=serve_origin,
            serve_path=inngest_path,
        )
        
        app.logger.info(f"Inngest: Successfully registered {len(INNGEST_FUNCTIONS)} functions")
        app.logger.info(f"Inngest: Serving at {inngest_path}")
        app.logger.info(f"Inngest: Rate limiting automatically exempted for {inngest_path}")
    except ImportError as e:
        app.logger.warning(f"Inngest not available: {e}")
    except Exception as e:
        app.logger.error(f"Failed to register Inngest: {e}", exc_info=True)
        raise  # Re-raise to see full stack trace


def create_app(config: Type[BaseConfig] = None) -> Flask:
    """Create and configure Flask application.
    
    Args:
        config: Configuration class to use. If None, uses environment-based config.
    
    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    
    # Display configuration at startup
    from config.settings import settings as app_settings
    app_settings.display_config()
    
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
    try:
        db.init_app(app)
    except Exception:
        app.logger.error("Failed to initialize database extension", exc_info=True)
        raise
    
    # Initialize limiter with logging
    limiter.init_app(app)
    app.logger.info("Rate limiter initialized with Inngest exemption")
    
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
    try:
        register_blueprints(app)
    except Exception as e:
        app.logger.error("Failed to register blueprints during app startup", exc_info=True)
        raise
    
    # Register Inngest background jobs
    try:
        register_inngest(app)
    except Exception as e:
        app.logger.error("Failed to register Inngest during app startup", exc_info=True)
        raise
    
    # Note: Database tables are managed via Alembic migrations (python manage.py migrate)
    # Do not use db.create_all() as it bypasses migration tracking
    # with app.app_context():
    #     db.create_all()
    
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

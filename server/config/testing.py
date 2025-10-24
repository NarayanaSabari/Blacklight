"""Testing environment configuration."""

import os

from .base import BaseConfig


class TestingConfig(BaseConfig):
    """Testing environment configuration."""

    DEBUG = True
    TESTING = True
    
    # Use in-memory SQLite for tests
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ECHO = False
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Session
    SESSION_COOKIE_SECURE = False
    
    # CORS - Allow all for testing
    CORS_ORIGINS = ["*"]
    
    # Logging
    LOG_LEVEL = "DEBUG"
    
    # Redis - Use separate test database
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/15")
    REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL", "redis://localhost:6379/14")
    
    # Allowed Hosts
    ALLOWED_HOSTS = ["*"]

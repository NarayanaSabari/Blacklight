"""Development environment configuration."""

import os

from .base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""

    DEBUG = True
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/blacklight"
    )
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true"
    
    # Session
    SESSION_COOKIE_SECURE = False
    
    # CORS - Allow all origins in development
    CORS_ORIGINS = ["*"]
    
    # Logging
    LOG_LEVEL = "DEBUG"
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL", "redis://localhost:6379/1")
    
    # Allowed Hosts
    ALLOWED_HOSTS = ["*"]

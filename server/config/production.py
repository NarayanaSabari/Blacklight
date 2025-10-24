"""Production environment configuration."""

import os

from .base import BaseConfig


class ProductionConfig(BaseConfig):
    """Production environment configuration."""

    DEBUG = False
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/blacklight"
    )
    SQLALCHEMY_ECHO = False
    
    # Session
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Strict"
    
    # CORS - Restrict to specific origins
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "localhost").split(",")
    
    # Logging
    LOG_LEVEL = "INFO"
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL")
    REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL")
    
    if not REDIS_URL or not REDIS_CACHE_URL:
        raise ValueError("REDIS_URL and REDIS_CACHE_URL must be set in production")
    
    # Allowed Hosts
    ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost").split(",")
    
    # Security
    SECURE_HEADERS = True
    
    # SQLAlchemy Engine Options - Stricter pooling for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.getenv("SQLALCHEMY_ENGINE_OPTIONS_POOL_SIZE", 20)),
        "pool_recycle": int(os.getenv("SQLALCHEMY_ENGINE_OPTIONS_POOL_RECYCLE", 1800)),
        "pool_pre_ping": True,
        "connect_args": {
            "connect_timeout": 10,
        },
    }

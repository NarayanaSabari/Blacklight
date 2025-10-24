"""Base configuration for all environments."""

import os
from datetime import timedelta
from typing import List


class BaseConfig:
    """Base configuration class with common settings."""

    # Flask Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Database Configuration
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = False
    
    # SQLAlchemy Engine Options
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.getenv("SQLALCHEMY_ENGINE_OPTIONS_POOL_SIZE", 10)),
        "pool_recycle": int(os.getenv("SQLALCHEMY_ENGINE_OPTIONS_POOL_RECYCLE", 3600)),
        "pool_pre_ping": os.getenv("SQLALCHEMY_ENGINE_OPTIONS_POOL_PRE_PING", "True").lower() == "true",
    }
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(days=7)
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    CORS_EXPOSE_HEADERS: List[str] = ["*"]
    CORS_SUPPORTS_CREDENTIALS: bool = True
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    
    # Server Configuration
    JSON_SORT_KEYS: bool = False
    JSON_DATETIME_FORMAT: str = "iso"
    
    # Security
    SECURE_HEADERS: bool = True
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

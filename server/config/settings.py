"""Application settings using Pydantic for environment variable validation."""

import os
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with Pydantic validation."""

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    testing: bool = Field(default=False, env="TESTING")
    
    # Flask
    flask_app: str = Field(default="wsgi.py", env="FLASK_APP")
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    
    # Database
    database_url: str = Field(default="postgresql://postgres:postgres@localhost:5432/blacklight", env="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_cache_url: str = Field(default="redis://localhost:6379/1", env="REDIS_CACHE_URL")
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=5000, env="PORT")
    workers: int = Field(default=4, env="WORKERS")
    worker_class: str = Field(default="sync", env="WORKER_CLASS")
    worker_connections: int = Field(default=1000, env="WORKER_CONNECTIONS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # CORS
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")
    cors_allow_headers: str = Field(default="*", env="CORS_ALLOW_HEADERS")
    cors_expose_headers: str = Field(default="*", env="CORS_EXPOSE_HEADERS")
    cors_supports_credentials: bool = Field(default=True, env="CORS_SUPPORTS_CREDENTIALS")
    
    # Security
    allowed_hosts: str = Field(default="localhost,127.0.0.1", env="ALLOWED_HOSTS")
    secure_headers: bool = Field(default=True, env="SECURE_HEADERS")
    
    # Database Pool
    pool_size: int = Field(default=10, env="SQLALCHEMY_ENGINE_OPTIONS_POOL_SIZE")
    pool_recycle: int = Field(default=3600, env="SQLALCHEMY_ENGINE_OPTIONS_POOL_RECYCLE")
    pool_pre_ping: bool = Field(default=True, env="SQLALCHEMY_ENGINE_OPTIONS_POOL_PRE_PING")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env
    
    @property
    def cors_origins_list(self) -> list:
        """Get CORS origins as list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def allowed_hosts_list(self) -> list:
        """Get allowed hosts as list."""
        return [host.strip() for host in self.allowed_hosts.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing."""
        return self.testing or self.environment.lower() == "testing"
    
    @validator("environment")
    def environment_must_be_valid(cls, v):
        """Validate environment value."""
        valid_envs = ["development", "production", "testing"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v.lower()
    
    @validator("log_level")
    def log_level_must_be_valid(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @validator("worker_class")
    def worker_class_must_be_valid(cls, v):
        """Validate worker class."""
        valid_classes = ["sync", "eventlet", "gevent", "tornado"]
        if v.lower() not in valid_classes:
            raise ValueError(f"Worker class must be one of {valid_classes}")
        return v.lower()


# Create global settings instance
settings = Settings()

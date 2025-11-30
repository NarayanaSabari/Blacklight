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
    
    # Email Configuration
    smtp_enabled: bool = Field(default=False, env="SMTP_ENABLED")
    smtp_host: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    smtp_from_email: str = Field(default="noreply@blacklight.io", env="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="Blacklight HR", env="SMTP_FROM_NAME")
    
    # Invitation Settings
    invitation_expiry_hours: int = Field(default=168, env="INVITATION_EXPIRY_HOURS")  # 7 days
    frontend_base_url: str = Field(default="http://localhost:5174", env="FRONTEND_BASE_URL")
    
    # File Storage Configuration
    storage_backend: str = Field(default="local", env="STORAGE_BACKEND")  # 'local' or 'gcs'
    storage_local_path: str = Field(default="./storage/uploads", env="STORAGE_LOCAL_PATH")
    
    # Google Cloud Storage (GCS) Configuration
    gcs_bucket_name: str = Field(default="", env="GCS_BUCKET_NAME")
    gcs_project_id: str = Field(default="", env="GCS_PROJECT_ID")
    gcs_credentials_path: str = Field(default="", env="GCS_CREDENTIALS_PATH")  # Path to service account JSON
    gcs_credentials_json: str = Field(default="", env="GCS_CREDENTIALS_JSON")  # Or inline JSON string
    
    # File Upload Limits
    max_file_size_mb: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    allowed_document_types: str = Field(default="pdf,doc,docx,jpg,jpeg,png", env="ALLOWED_DOCUMENT_TYPES")
    signed_url_expiry_seconds: int = Field(default=1800, env="SIGNED_URL_EXPIRY_SECONDS")  # 30 minutes
    
    # Database Pool
    pool_size: int = Field(default=10, env="SQLALCHEMY_ENGINE_OPTIONS_POOL_SIZE")
    pool_recycle: int = Field(default=3600, env="SQLALCHEMY_ENGINE_OPTIONS_POOL_RECYCLE")
    pool_pre_ping: bool = Field(default=True, env="SQLALCHEMY_ENGINE_OPTIONS_POOL_PRE_PING")
    
    # Inngest Configuration
    inngest_dev: bool = Field(default=True, env="INNGEST_DEV")
    inngest_base_url: str = Field(default="http://localhost:8288", env="INNGEST_BASE_URL")
    inngest_event_key: str = Field(default="", env="INNGEST_EVENT_KEY")
    inngest_signing_key: str = Field(default="", env="INNGEST_SIGNING_KEY")
    inngest_serve_host: str = Field(default="http://localhost:5000", env="INNGEST_SERVE_HOST")
    inngest_serve_path: str = Field(default="/api/inngest", env="INNGEST_SERVE_PATH")
    
    # AI/Resume Parsing Configuration
    ai_parsing_provider: str = Field(default="gemini", env="AI_PARSING_PROVIDER")  # 'gemini' or 'openai'
    
    # Google Gemini API Configuration
    google_api_key: str = Field(default="", env="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", env="GEMINI_MODEL")  # For resume parsing & suggestions
    gemini_embedding_model: str = Field(default="models/embedding-001", env="GEMINI_EMBEDDING_MODEL")
    gemini_embedding_dimension: int = Field(default=768, env="GEMINI_EMBEDDING_DIMENSION")
    
    # OpenAI Configuration (optional alternative to Gemini)
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    
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
    
    def display_config(self) -> None:
        """Display all environment variables in a formatted table at startup."""
        
        def mask_sensitive(key: str, value: str) -> str:
            """Mask sensitive values like passwords and API keys."""
            sensitive_keywords = ['password', 'secret', 'key', 'token', 'credentials']
            if any(kw in key.lower() for kw in sensitive_keywords):
                if value and len(value) > 8:
                    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"
                elif value:
                    return '*' * len(value)
            return value
        
        # Group settings by category
        categories = {
            "🔧 Core": ["environment", "debug", "testing"],
            "🗄️ Database": ["database_url", "pool_size", "pool_recycle", "pool_pre_ping"],
            "📦 Redis": ["redis_url", "redis_cache_url"],
            "🌐 Server": ["host", "port", "workers", "worker_class", "worker_connections"],
            "📝 Logging": ["log_level", "log_format"],
            "🔗 CORS": ["cors_origins", "cors_supports_credentials"],
            "🔒 Security": ["secret_key", "allowed_hosts", "secure_headers"],
            "🤖 AI/Parsing": ["ai_parsing_provider", "google_api_key", "gemini_model", "gemini_embedding_model", "openai_api_key"],
            "📁 Storage": ["storage_backend", "storage_local_path", "gcs_bucket_name", "gcs_project_id", "max_file_size_mb"],
            "📧 Email": ["smtp_enabled", "smtp_host", "smtp_port", "smtp_username", "smtp_from_email"],
            "🔗 Frontend": ["frontend_base_url", "invitation_expiry_hours"],
            "⚡ Inngest": ["inngest_dev", "inngest_base_url", "inngest_serve_host", "inngest_event_key"],
        }
        
        print("\n" + "=" * 80)
        print("🚀 BLACKLIGHT SERVER CONFIGURATION")
        print("=" * 80)
        
        for category, keys in categories.items():
            print(f"\n{category}")
            print("-" * 40)
            for key in keys:
                if hasattr(self, key):
                    value = str(getattr(self, key))
                    masked_value = mask_sensitive(key, value)
                    # Truncate long values
                    if len(masked_value) > 50:
                        masked_value = masked_value[:47] + "..."
                    print(f"  {key:30} = {masked_value}")
        
        print("\n" + "=" * 80)
        print(f"✅ Configuration loaded from: .env")
        print("=" * 80 + "\n")


# Create global settings instance
settings = Settings()

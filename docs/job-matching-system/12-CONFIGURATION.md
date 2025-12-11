# Configuration Guide

This guide covers all configuration options for the Job Matching System.

## Environment Variables

### Required Variables

```bash
# .env or environment configuration

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/blacklight

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_URL=redis://localhost:6379/1

# Application
SECRET_KEY=your-super-secret-key-min-32-chars
ENVIRONMENT=development  # development, production, testing

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:5173
```

### Job Matching Configuration

```bash
# Google Gemini API (for embeddings)
GEMINI_API_KEY=your-gemini-api-key

# Embedding Configuration
EMBEDDING_MODEL=models/embedding-001
EMBEDDING_DIMENSION=768

# Matching Thresholds
MATCH_SCORE_THRESHOLD=60      # Minimum score to show match (0-100)
TOP_MATCHES_LIMIT=50          # Max matches per candidate

# Skill Matching
FUZZY_MATCH_THRESHOLD=80      # Minimum fuzzy match score (0-100)
```

### Inngest Configuration

```bash
# Inngest (Background Jobs)
INNGEST_EVENT_KEY=your-event-key
INNGEST_SIGNING_KEY=your-signing-key
INNGEST_DEV_SERVER_URL=http://localhost:8288  # For local development
```

### Email Configuration

```bash
# SMTP Settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@blacklight.com
SMTP_FROM_NAME=Blacklight
```

### Scraper API Configuration

```bash
# Rate Limiting
SCRAPER_RATE_LIMIT_PER_MINUTE=60
SCRAPER_MAX_CONCURRENT_REQUESTS=10

# Job Sources (comma-separated)
ENABLED_JOB_SOURCES=monster,indeed,dice,glassdoor,techfetch,linkedin
```

## Python Configuration

### config/settings.py

```python
# server/config/settings.py

from pydantic import BaseSettings, Field
from typing import List, Optional

class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")
    
    # Redis
    REDIS_URL: str = Field("redis://localhost:6379/0")
    REDIS_CACHE_URL: str = Field("redis://localhost:6379/1")
    
    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    
    # Environment
    ENVIRONMENT: str = Field("development", regex="^(development|production|testing)$")
    
    # Embedding Configuration
    GEMINI_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "models/embedding-001"
    EMBEDDING_DIMENSION: int = 768
    
    # Matching Configuration
    MATCH_SCORE_THRESHOLD: int = Field(60, ge=0, le=100)
    TOP_MATCHES_LIMIT: int = Field(50, ge=1, le=500)
    FUZZY_MATCH_THRESHOLD: int = Field(80, ge=0, le=100)
    
    # Role Normalization
    ROLE_SIMILARITY_THRESHOLD: float = Field(0.85, ge=0.0, le=1.0)
    AUTO_CREATE_NEW_ROLES: bool = True
    
    # Inngest
    INNGEST_EVENT_KEY: Optional[str] = None
    INNGEST_SIGNING_KEY: Optional[str] = None
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = "noreply@blacklight.com"
    
    # Scraper
    SCRAPER_RATE_LIMIT_PER_MINUTE: int = 60
    ENABLED_JOB_SOURCES: List[str] = ["monster", "indeed", "dice"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

## Database Setup

### PostgreSQL with pgvector

```sql
-- Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create indexes for vector similarity search
CREATE INDEX idx_candidates_embedding 
ON candidates 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

CREATE INDEX idx_job_postings_embedding 
ON job_postings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

CREATE INDEX idx_global_roles_embedding 
ON global_roles 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

### Alembic Migration for pgvector

```python
# migrations/versions/xxxx_add_pgvector.py

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

def upgrade():
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Add embedding column to candidates
    op.add_column(
        'candidates',
        sa.Column('embedding', Vector(768), nullable=True)
    )
    
    # Add embedding column to job_postings
    op.add_column(
        'job_postings',
        sa.Column('embedding', Vector(768), nullable=True)
    )
    
    # Create IVFFlat indexes
    op.execute('''
        CREATE INDEX idx_candidates_embedding 
        ON candidates 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100)
    ''')
    
    op.execute('''
        CREATE INDEX idx_job_postings_embedding 
        ON job_postings 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100)
    ''')

def downgrade():
    op.drop_index('idx_job_postings_embedding')
    op.drop_index('idx_candidates_embedding')
    op.drop_column('job_postings', 'embedding')
    op.drop_column('candidates', 'embedding')
    op.execute('DROP EXTENSION IF EXISTS vector')
```

## Docker Configuration

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: ./server
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/blacklight
      - REDIS_URL=redis://redis:6379/0
      - REDIS_CACHE_URL=redis://redis:6379/1
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - INNGEST_DEV_SERVER_URL=http://inngest:8288
    depends_on:
      - db
      - redis
      - inngest

  db:
    image: ankane/pgvector:latest  # PostgreSQL with pgvector pre-installed
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: blacklight
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

  inngest:
    image: inngest/inngest:latest
    ports:
      - "8288:8288"
    command: inngest dev

volumes:
  pgdata:
  redisdata:
```

## Inngest Function Configuration

### Workflow Settings

```python
# app/inngest/__init__.py

import inngest

inngest_client = inngest.Inngest(
    app_id="blacklight",
    event_key=settings.INNGEST_EVENT_KEY,
)

# Default function options
DEFAULT_FUNCTION_OPTIONS = {
    "retries": 3,
    "concurrency": [
        {
            "scope": "account",
            "limit": 10  # Max 10 concurrent jobs per tenant
        }
    ]
}
```

### Rate Limiting Configuration

```python
# Email rate limiting
email_rate_limit = inngest.RateLimit(
    limit=50,
    period="1m"  # 50 emails per minute
)

@inngest_client.create_function(
    fn_id="send-invitation-email",
    trigger=inngest.TriggerEvent(event="email/invitation"),
    rate_limit=email_rate_limit,
    retries=5
)
async def send_invitation_email(ctx, step):
    ...
```

## Frontend Configuration

### Vite Environment

```typescript
// ui/portal/.env.local
VITE_API_URL=http://localhost:5000
VITE_WS_URL=ws://localhost:5000

// ui/centralD/.env.local
VITE_API_URL=http://localhost:5000
VITE_WS_URL=ws://localhost:5000
```

### React Query Configuration

```typescript
// ui/portal/src/lib/query-client.ts

import { QueryClient } from "@tanstack/react-query"

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0,  // Always refetch for fresh data
      gcTime: 5 * 60 * 1000,  // 5 minutes cache
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: 1,
    },
  },
})
```

## Matching Algorithm Weights

### Configurable Weights

```python
# app/services/job_matching_service.py

class MatchingWeights:
    """Configurable weights for matching algorithm."""
    
    # Component weights (must sum to 1.0)
    SKILL_WEIGHT = float(os.getenv('MATCH_SKILL_WEIGHT', 0.40))
    EXPERIENCE_WEIGHT = float(os.getenv('MATCH_EXPERIENCE_WEIGHT', 0.25))
    LOCATION_WEIGHT = float(os.getenv('MATCH_LOCATION_WEIGHT', 0.15))
    SALARY_WEIGHT = float(os.getenv('MATCH_SALARY_WEIGHT', 0.10))
    SEMANTIC_WEIGHT = float(os.getenv('MATCH_SEMANTIC_WEIGHT', 0.10))
    
    # Validation
    @classmethod
    def validate(cls):
        total = (
            cls.SKILL_WEIGHT + 
            cls.EXPERIENCE_WEIGHT + 
            cls.LOCATION_WEIGHT + 
            cls.SALARY_WEIGHT + 
            cls.SEMANTIC_WEIGHT
        )
        assert abs(total - 1.0) < 0.001, f"Weights must sum to 1.0, got {total}"
    
    # Get as dict
    @classmethod
    def as_dict(cls):
        return {
            "skills": cls.SKILL_WEIGHT,
            "experience": cls.EXPERIENCE_WEIGHT,
            "location": cls.LOCATION_WEIGHT,
            "salary": cls.SALARY_WEIGHT,
            "semantic": cls.SEMANTIC_WEIGHT
        }


# Environment variables for tuning
# MATCH_SKILL_WEIGHT=0.40
# MATCH_EXPERIENCE_WEIGHT=0.25
# MATCH_LOCATION_WEIGHT=0.15
# MATCH_SALARY_WEIGHT=0.10
# MATCH_SEMANTIC_WEIGHT=0.10
```

## Redis Cache Configuration

### Cache TTL Settings

```python
# app/utils/redis_client.py

class CacheTTL:
    """Cache time-to-live settings (in seconds)."""
    
    # Job data
    JOB_POSTING = 3600  # 1 hour
    JOB_SEARCH_RESULTS = 300  # 5 minutes
    
    # Candidate data
    CANDIDATE_MATCHES = 1800  # 30 minutes
    CANDIDATE_EMBEDDING = 86400  # 24 hours
    
    # Role data
    ROLE_MAPPING = 3600  # 1 hour
    ROLE_EMBEDDING = 86400  # 24 hours
    
    # Statistics
    DASHBOARD_STATS = 60  # 1 minute
    QUEUE_STATS = 30  # 30 seconds


# Usage
@cached(ttl=CacheTTL.JOB_SEARCH_RESULTS, key_prefix="job_search")
def search_jobs(query: str, filters: dict) -> List[JobPosting]:
    ...
```

## Logging Configuration

### Structured Logging

```python
# config/logging_config.py

import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_record)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": JSONFormatter
        },
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if os.getenv("ENVIRONMENT") == "production" else "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json"
        }
    },
    "root": {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "handlers": ["console", "file"]
    },
    "loggers": {
        "app.services.job_matching": {
            "level": "DEBUG"
        },
        "app.services.embedding": {
            "level": "DEBUG"
        }
    }
}
```

## Security Configuration

### API Key Hashing

```python
# app/services/scraper_api_key_service.py

import secrets
import hashlib

def generate_api_key() -> tuple[str, str]:
    """Generate API key and its hash."""
    
    # Generate 32-byte random key
    raw_key = secrets.token_urlsafe(32)
    
    # Prefix for identification
    key = f"sk_{raw_key}"
    
    # Store hash, not raw key
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    
    return key, key_hash


def verify_api_key(key: str, stored_hash: str) -> bool:
    """Verify API key against stored hash."""
    
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return secrets.compare_digest(key_hash, stored_hash)
```

### CORS Configuration

```python
# server/app/__init__.py

from flask_cors import CORS

def create_app(config=None):
    app = Flask(__name__)
    
    # CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://localhost:5174",
                "https://app.blacklight.com",
                "https://admin.blacklight.com"
            ],
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization", "X-Scraper-API-Key"],
            "expose_headers": ["X-Request-ID"],
            "supports_credentials": True
        }
    })
    
    return app
```

## See Also

- [13-TROUBLESHOOTING.md](./13-TROUBLESHOOTING.md) - Common issues and solutions
- [03-DATA-MODELS.md](./03-DATA-MODELS.md) - Database schema details
- [07-INNGEST-WORKFLOWS.md](./07-INNGEST-WORKFLOWS.md) - Background job configuration

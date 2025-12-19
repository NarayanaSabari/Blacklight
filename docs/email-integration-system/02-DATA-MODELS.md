# Data Models

## Overview

This document describes the database models required for the Email Integration System.

## New Models

### 1. UserEmailIntegration

Stores OAuth credentials and sync state for each user's email integration.

**Table**: `user_email_integrations`

```python
class UserEmailIntegration(BaseModel):
    __tablename__ = "user_email_integrations"
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('portal_users.id', ondelete='CASCADE'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Integration Type
    provider = db.Column(db.String(20), nullable=False)  # 'gmail' or 'outlook'
    
    # OAuth Credentials (ENCRYPTED)
    access_token_encrypted = db.Column(db.Text, nullable=True)
    refresh_token_encrypted = db.Column(db.Text, nullable=False)
    token_expiry = db.Column(db.DateTime, nullable=True)
    
    # Email Account Info
    email_address = db.Column(db.String(255), nullable=False)  # Connected email
    
    # Sync State
    is_active = db.Column(db.Boolean, default=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    last_sync_status = db.Column(db.String(50), default='pending')  # pending, success, failed
    last_sync_error = db.Column(db.Text, nullable=True)
    
    # Sync Configuration
    sync_frequency_minutes = db.Column(db.Integer, default=15)
    sync_lookback_days = db.Column(db.Integer, default=7)  # How far back to search
    
    # Tracking
    emails_processed_count = db.Column(db.Integer, default=0)
    jobs_created_count = db.Column(db.Integer, default=0)
    
    # Relationships
    user = db.relationship('PortalUser', back_populates='email_integrations')
    tenant = db.relationship('Tenant')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('user_id', 'provider', name='unique_user_provider'),
    )
```

**Key Design Decisions:**
- One integration per provider per user (enforced by unique constraint)
- Tokens are encrypted at rest using Fernet encryption
- Tracks sync state for debugging and monitoring
- Configurable sync frequency and lookback period

### 2. EmailSourcedJob

Extends job data with email-specific metadata. Uses the existing `JobPosting` model with additional fields.

**Option A: Add columns to existing `job_postings` table** (Recommended)

```python
# Additional columns for JobPosting model
class JobPosting(db.Model):
    # ... existing columns ...
    
    # Email Source Fields (nullable for non-email jobs)
    is_email_sourced = db.Column(db.Boolean, default=False, index=True)
    source_tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    sourced_by_user_id = db.Column(db.Integer, db.ForeignKey('portal_users.id'), nullable=True)
    source_email_id = db.Column(db.String(255), nullable=True)  # Email Message-ID for dedup
    source_email_subject = db.Column(db.String(500), nullable=True)
    source_email_sender = db.Column(db.String(255), nullable=True)
    source_email_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    source_tenant = db.relationship('Tenant', foreign_keys=[source_tenant_id])
    sourced_by_user = db.relationship('PortalUser', foreign_keys=[sourced_by_user_id])
```

**Option B: Separate EmailSourcedJob table** (Alternative)

```python
class EmailSourcedJob(BaseModel):
    __tablename__ = "email_sourced_jobs"
    
    # Link to main job
    job_id = db.Column(db.Integer, db.ForeignKey('job_postings.id', ondelete='CASCADE'))
    
    # Tenant scoping
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete='CASCADE'))
    
    # Source attribution
    sourced_by_user_id = db.Column(db.Integer, db.ForeignKey('portal_users.id'))
    integration_id = db.Column(db.Integer, db.ForeignKey('user_email_integrations.id'))
    
    # Email metadata
    email_message_id = db.Column(db.String(255), unique=True)  # For deduplication
    email_subject = db.Column(db.String(500))
    email_sender = db.Column(db.String(255))
    email_received_at = db.Column(db.DateTime)
    email_body_snippet = db.Column(db.Text)  # First 500 chars
    
    # Parsing metadata
    ai_parsing_confidence = db.Column(db.Float)  # 0.0 - 1.0
    ai_model_used = db.Column(db.String(50))
    parsing_warnings = db.Column(db.JSON)  # Any issues during parsing
    
    # Relationships
    job = db.relationship('JobPosting', back_populates='email_source')
    tenant = db.relationship('Tenant')
    sourced_by = db.relationship('PortalUser')
```

**Recommendation**: Use **Option A** for simplicity. Email-sourced jobs are just regular jobs with extra metadata columns.

### 3. ProcessedEmail (For Deduplication)

Tracks which emails have been processed to avoid reprocessing.

**Table**: `processed_emails`

```python
class ProcessedEmail(BaseModel):
    __tablename__ = "processed_emails"
    
    # Foreign Keys
    integration_id = db.Column(db.Integer, db.ForeignKey('user_email_integrations.id', ondelete='CASCADE'))
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete='CASCADE'))
    
    # Email Identification
    email_message_id = db.Column(db.String(255), nullable=False)  # RFC 2822 Message-ID
    email_thread_id = db.Column(db.String(255), nullable=True)  # Gmail thread ID
    
    # Processing Result
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
    processing_result = db.Column(db.String(50))  # 'job_created', 'skipped', 'failed', 'irrelevant'
    job_id = db.Column(db.Integer, db.ForeignKey('job_postings.id'), nullable=True)  # If job was created
    
    # Metadata for debugging
    email_subject = db.Column(db.String(500))
    email_sender = db.Column(db.String(255))
    skip_reason = db.Column(db.String(255), nullable=True)  # Why it was skipped
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('integration_id', 'email_message_id', name='unique_integration_email'),
    )
```

## Model Relationships

```
┌──────────────────┐      ┌─────────────────────────┐      ┌──────────────────┐
│    Tenant        │      │  UserEmailIntegration   │      │   PortalUser     │
│                  │◄────►│                         │◄────►│                  │
│  - id            │      │  - id                   │      │  - id            │
│  - name          │      │  - tenant_id            │      │  - tenant_id     │
│                  │      │  - user_id              │      │  - email         │
└──────────────────┘      │  - provider             │      └──────────────────┘
         ▲                │  - tokens (encrypted)   │               ▲
         │                │  - sync_state           │               │
         │                └───────────┬─────────────┘               │
         │                            │                             │
         │                            │ has_many                    │
         │                            ▼                             │
         │                ┌─────────────────────────┐               │
         │                │    ProcessedEmail       │               │
         │                │                         │               │
         │                │  - integration_id       │               │
         │                │  - email_message_id     │               │
         │                │  - processing_result    │               │
         │                └───────────┬─────────────┘               │
         │                            │                             │
         │                            │ creates                     │
         │                            ▼                             │
         │                ┌─────────────────────────┐               │
         └───────────────►│      JobPosting         │◄──────────────┘
                          │  (with email fields)    │
                          │                         │
                          │  - is_email_sourced     │
                          │  - source_tenant_id     │
                          │  - sourced_by_user_id   │
                          │  - source_email_*       │
                          └─────────────────────────┘
```

## Migration Strategy

### Migration 1: Create UserEmailIntegration table

```python
def upgrade():
    op.create_table(
        'user_email_integrations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('portal_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=True),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=False),
        sa.Column('token_expiry', sa.DateTime(), nullable=True),
        sa.Column('email_address', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_status', sa.String(50), default='pending'),
        sa.Column('last_sync_error', sa.Text(), nullable=True),
        sa.Column('sync_frequency_minutes', sa.Integer(), default=15),
        sa.Column('sync_lookback_days', sa.Integer(), default=7),
        sa.Column('emails_processed_count', sa.Integer(), default=0),
        sa.Column('jobs_created_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), onupdate=datetime.utcnow),
        sa.UniqueConstraint('user_id', 'provider', name='unique_user_provider'),
    )
    op.create_index('ix_user_email_integrations_tenant_id', 'user_email_integrations', ['tenant_id'])
    op.create_index('ix_user_email_integrations_is_active', 'user_email_integrations', ['is_active'])
```

### Migration 2: Add email source columns to job_postings

```python
def upgrade():
    op.add_column('job_postings', sa.Column('is_email_sourced', sa.Boolean(), default=False))
    op.add_column('job_postings', sa.Column('source_tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=True))
    op.add_column('job_postings', sa.Column('sourced_by_user_id', sa.Integer(), sa.ForeignKey('portal_users.id'), nullable=True))
    op.add_column('job_postings', sa.Column('source_email_id', sa.String(255), nullable=True))
    op.add_column('job_postings', sa.Column('source_email_subject', sa.String(500), nullable=True))
    op.add_column('job_postings', sa.Column('source_email_sender', sa.String(255), nullable=True))
    op.add_column('job_postings', sa.Column('source_email_date', sa.DateTime(), nullable=True))
    
    op.create_index('ix_job_postings_is_email_sourced', 'job_postings', ['is_email_sourced'])
    op.create_index('ix_job_postings_source_tenant_id', 'job_postings', ['source_tenant_id'])
    op.create_index('ix_job_postings_source_email_id', 'job_postings', ['source_email_id'])
```

### Migration 3: Create processed_emails table

```python
def upgrade():
    op.create_table(
        'processed_emails',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('integration_id', sa.Integer(), sa.ForeignKey('user_email_integrations.id', ondelete='CASCADE')),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE')),
        sa.Column('email_message_id', sa.String(255), nullable=False),
        sa.Column('email_thread_id', sa.String(255), nullable=True),
        sa.Column('processed_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('processing_result', sa.String(50)),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('job_postings.id'), nullable=True),
        sa.Column('email_subject', sa.String(500)),
        sa.Column('email_sender', sa.String(255)),
        sa.Column('skip_reason', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), onupdate=datetime.utcnow),
        sa.UniqueConstraint('integration_id', 'email_message_id', name='unique_integration_email'),
    )
    op.create_index('ix_processed_emails_tenant_id', 'processed_emails', ['tenant_id'])
```

## Encryption Utility

```python
# app/utils/encryption.py
from cryptography.fernet import Fernet
from config.settings import settings

class TokenEncryption:
    """Utility for encrypting/decrypting OAuth tokens."""
    
    def __init__(self):
        # Generate key from secret: must be 32 url-safe base64-encoded bytes
        self.fernet = Fernet(settings.token_encryption_key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return base64-encoded ciphertext."""
        return self.fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64-encoded ciphertext and return plaintext."""
        return self.fernet.decrypt(ciphertext.encode()).decode()

# Singleton instance
token_encryption = TokenEncryption()
```

## Pydantic Schemas

```python
# app/schemas/email_integration_schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Literal

class EmailIntegrationCreate(BaseModel):
    provider: Literal['gmail', 'outlook']

class EmailIntegrationResponse(BaseModel):
    id: int
    provider: str
    email_address: str
    is_active: bool
    last_synced_at: Optional[datetime]
    last_sync_status: str
    emails_processed_count: int
    jobs_created_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class EmailIntegrationListResponse(BaseModel):
    integrations: list[EmailIntegrationResponse]

class EmailSourcedJobResponse(BaseModel):
    id: int
    title: str
    company: Optional[str]
    location: Optional[str]
    description: Optional[str]
    job_type: Optional[str]
    salary_range: Optional[str]
    skills: list[str]
    
    # Email source info
    is_email_sourced: bool
    source_email_subject: Optional[str]
    source_email_sender: Optional[str]
    source_email_date: Optional[datetime]
    
    # Attribution
    sourced_by_user: Optional[dict]  # {id, first_name, last_name, email}
    
    created_at: datetime
    
    class Config:
        from_attributes = True
```

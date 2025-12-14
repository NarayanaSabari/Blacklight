# Resume Tailor Integration - Data Models

## Overview

This document defines the database schema changes required for the Resume Tailor feature. We'll add new models while leveraging existing Blacklight models for candidates, job postings, and matches.

---

## New Models

### 1. TailoredResume

Stores each tailored resume version created for a candidate-job pair.

```python
# server/app/models/tailored_resume.py

from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime,
    DECIMAL, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class TailoredResumeStatus(enum.Enum):
    """Status of tailored resume generation"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TailoredResume(BaseModel):
    """
    Stores tailored resume versions.
    
    Each record represents a single tailoring operation for a 
    specific candidate-job combination.
    """
    __tablename__ = 'tailored_resumes'
    
    id = Column(Integer, primary_key=True)
    tailor_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    
    # Foreign Keys
    candidate_id = Column(
        Integer, 
        ForeignKey('candidates.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    job_posting_id = Column(
        Integer, 
        ForeignKey('job_postings.id', ondelete='SET NULL'), 
        nullable=True,  # Job can be deleted, keep history
        index=True
    )
    tenant_id = Column(
        Integer, 
        ForeignKey('tenants.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    created_by_user_id = Column(
        Integer, 
        ForeignKey('portal_users.id', ondelete='SET NULL'), 
        nullable=True
    )
    
    # Status & Processing
    status = Column(
        SQLEnum(TailoredResumeStatus),
        default=TailoredResumeStatus.PENDING,
        nullable=False,
        index=True
    )
    processing_error = Column(Text, nullable=True)
    processing_step = Column(String(50), nullable=True)  # Current step for progress
    processing_progress = Column(Integer, default=0)  # 0-100
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_duration_seconds = Column(Integer, nullable=True)
    
    # Original Resume Content
    original_resume_content = Column(Text, nullable=False)  # Markdown format
    original_resume_keywords = Column(ARRAY(String), default=[])
    
    # Tailored Resume Content
    tailored_resume_content = Column(Text, nullable=True)  # Markdown format
    tailored_resume_html = Column(Text, nullable=True)  # Rendered HTML
    tailored_resume_keywords = Column(ARRAY(String), default=[])
    
    # Scoring (0.0000 - 1.0000)
    original_match_score = Column(DECIMAL(5, 4), nullable=True)
    tailored_match_score = Column(DECIMAL(5, 4), nullable=True)
    score_improvement = Column(DECIMAL(5, 4), nullable=True)
    
    # Job Keywords (for reference, even if job is deleted)
    job_title = Column(String(255), nullable=True)
    job_company = Column(String(255), nullable=True)
    job_keywords = Column(ARRAY(String), default=[])
    
    # Skill Analysis
    matched_skills = Column(ARRAY(String), default=[])
    missing_skills = Column(ARRAY(String), default=[])
    added_skills = Column(ARRAY(String), default=[])  # Skills added during tailoring
    
    # Improvements Made (JSONB array)
    improvements = Column(JSONB, default=[])
    """
    Structure:
    [
        {
            "section": "Experience",
            "type": "keyword_addition",
            "description": "Added Django framework reference",
            "before": "Built REST APIs using FastAPI",
            "after": "Built REST APIs using FastAPI and Django"
        }
    ]
    """
    
    # Skill Comparison Details (JSONB array)
    skill_comparison = Column(JSONB, default=[])
    """
    Structure:
    [
        {
            "skill": "python",
            "resume_mentions": 8,
            "job_mentions": 5,
            "status": "matched"  # matched, missing, extra
        }
    ]
    """
    
    # AI Provider Info
    ai_provider = Column(String(50), nullable=True)  # openai, ollama, gemini
    ai_model = Column(String(100), nullable=True)  # gpt-4o-mini, llama3.2, etc.
    iterations_used = Column(Integer, default=0)  # Number of LLM iterations
    
    # Options used
    options = Column(JSONB, default={})
    """
    Structure:
    {
        "preserve_experience": true,
        "max_iterations": 5,
        "target_score": 0.85
    }
    """
    
    # Timestamps (inherited from BaseModel but explicit for clarity)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    # Relationships
    candidate = relationship(
        'Candidate', 
        backref='tailored_resumes',
        lazy='joined'
    )
    job_posting = relationship(
        'JobPosting', 
        backref='tailored_resumes',
        lazy='joined'
    )
    tenant = relationship('Tenant', lazy='select')
    created_by = relationship('PortalUser', lazy='select')
    
    def __repr__(self):
        return f"<TailoredResume {self.tailor_id} candidate={self.candidate_id} job={self.job_posting_id}>"
    
    @property
    def is_complete(self) -> bool:
        return self.status == TailoredResumeStatus.COMPLETED
    
    @property
    def improvement_percentage(self) -> float:
        """Get improvement as percentage points"""
        if self.score_improvement:
            return float(self.score_improvement) * 100
        return 0.0
    
    def to_dict(self) -> dict:
        """Serialize for API response"""
        return {
            "id": self.id,
            "tailor_id": self.tailor_id,
            "candidate_id": self.candidate_id,
            "job_posting_id": self.job_posting_id,
            "status": self.status.value,
            "original": {
                "content_markdown": self.original_resume_content,
                "keywords": self.original_resume_keywords,
                "match_score": float(self.original_match_score) if self.original_match_score else None,
            },
            "tailored": {
                "content_markdown": self.tailored_resume_content,
                "content_html": self.tailored_resume_html,
                "keywords": self.tailored_resume_keywords,
                "match_score": float(self.tailored_match_score) if self.tailored_match_score else None,
            },
            "job": {
                "id": self.job_posting_id,
                "title": self.job_title,
                "company": self.job_company,
                "keywords": self.job_keywords,
            },
            "analysis": {
                "matched_skills": self.matched_skills,
                "missing_skills": self.missing_skills,
                "added_skills": self.added_skills,
                "skill_comparison": self.skill_comparison,
            },
            "improvements": self.improvements,
            "score_improvement": float(self.score_improvement) if self.score_improvement else None,
            "iterations_used": self.iterations_used,
            "ai_provider": self.ai_provider,
            "ai_model": self.ai_model,
            "processing_duration_seconds": self.processing_duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.processing_completed_at.isoformat() if self.processing_completed_at else None,
        }
```

---

### 2. ResumeTailorSession (Optional - For Bulk Operations)

Tracks bulk tailoring operations when multiple candidates are processed.

```python
# server/app/models/resume_tailor_session.py

from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ResumeTailorSession(BaseModel):
    """
    Tracks bulk resume tailoring sessions.
    
    Created when user requests to tailor multiple candidates for a single job.
    """
    __tablename__ = 'resume_tailor_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True)
    
    # Foreign Keys
    job_posting_id = Column(
        Integer,
        ForeignKey('job_postings.id', ondelete='SET NULL'),
        nullable=True
    )
    tenant_id = Column(
        Integer,
        ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    created_by_user_id = Column(
        Integer,
        ForeignKey('portal_users.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # Counts
    total_candidates = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Status
    status = Column(String(50), default='processing')  # processing, completed, partial, failed
    
    # Metadata
    options = Column(JSONB, default={})
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    job_posting = relationship('JobPosting', lazy='joined')
    tenant = relationship('Tenant', lazy='select')
    created_by = relationship('PortalUser', lazy='select')
```

---

## Existing Models Integration

### Candidate Model Updates

No schema changes required. We use existing fields:

```python
# Already in server/app/models/candidate.py

class Candidate(BaseModel):
    # ... existing fields ...
    
    # Resume content - we'll use this as source
    resume_content = Column(Text)  # Markdown content
    
    # Parsed data - structured resume info
    parsed_resume_data = Column(JSONB)
    """
    {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "skills": ["python", "django", "aws"],
        "experience": [...],
        "education": [...]
    }
    """
    
    # Embedding for semantic matching
    embedding = Column(Vector(768))  # Gemini embeddings
    
    # Skills array for quick access
    skills = Column(ARRAY(String))
```

### JobPosting Model Usage

No schema changes required. We use existing fields:

```python
# Already in server/app/models/job_posting.py

class JobPosting(BaseModel):
    # ... existing fields ...
    
    # Full description
    description = Column(Text)
    
    # Extracted skills/keywords
    skills = Column(ARRAY(String))
    keywords = Column(ARRAY(String))
    
    # Embedding for matching
    embedding = Column(Vector(768))
```

---

## Migration Process

Blacklight uses `manage.py` for database migrations with Alembic autogeneration.

### Step 1: Create the Model File

Create `server/app/models/tailored_resume.py` with the model code above.

### Step 2: Register Model in `__init__.py`

Add to `server/app/models/__init__.py`:

```python
# Import resume tailor models
from app.models.tailored_resume import TailoredResume, TailoredResumeStatus
```

### Step 3: Generate Migration (Autogenerate)

```bash
cd server

# Using manage.py (recommended)
python manage.py create-migration "add_tailored_resumes"

# This runs: alembic revision --autogenerate -m "add_tailored_resumes"
# Alembic will auto-detect the new model and generate the migration
```

### Step 4: Review Generated Migration

Check the generated file in `server/migrations/versions/` and verify:
- Table creation is correct
- Indexes are created
- Foreign keys are correct
- Enum types are created

### Step 5: Apply Migration

```bash
# Using manage.py
python manage.py migrate

# This runs: alembic upgrade head
```

### Expected Auto-Generated Migration

The migration will be auto-generated, but should create something like:

```python
# server/migrations/versions/xxxx_add_tailored_resumes.py (auto-generated by Alembic)

"""add tailored resumes

Revision ID: xxxx
Revises: previous_revision
Create Date: 2025-xx-xx
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Alembic will auto-generate the upgrade() and downgrade() functions
# based on the model definitions. Review before applying.
```

### Downgrade Safety

If you need to rollback:

```bash
# Rollback one migration
python manage.py downgrade -1

# Or use alembic directly
alembic downgrade -1
```

---

## Pydantic Schemas

```python
# server/app/schemas/tailored_resume.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


class TailoredResumeStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SkillComparisonItem(BaseModel):
    skill: str
    resume_mentions: int
    job_mentions: int
    status: str  # matched, missing, extra


class ImprovementItem(BaseModel):
    section: str
    type: str
    description: str
    before: Optional[str] = None
    after: Optional[str] = None


class TailorOptions(BaseModel):
    preserve_experience: bool = True
    max_iterations: int = Field(default=5, ge=1, le=10)
    target_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None


class TailoredResumeCreate(BaseModel):
    candidate_id: int
    job_posting_id: int
    options: Optional[TailorOptions] = None


class ResumeContent(BaseModel):
    content_markdown: str
    keywords: List[str]
    match_score: Optional[float] = None


class JobInfo(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    company: Optional[str] = None
    keywords: List[str] = []


class AnalysisResult(BaseModel):
    matched_skills: List[str]
    missing_skills: List[str]
    added_skills: List[str]
    skill_comparison: List[SkillComparisonItem]


class TailoredResumeResponse(BaseModel):
    id: int
    tailor_id: str
    candidate_id: int
    job_posting_id: Optional[int]
    status: TailoredResumeStatus
    original: ResumeContent
    tailored: Optional[ResumeContent] = None
    job: JobInfo
    analysis: Optional[AnalysisResult] = None
    improvements: List[ImprovementItem] = []
    score_improvement: Optional[float] = None
    iterations_used: int = 0
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    processing_duration_seconds: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TailoredResumeListItem(BaseModel):
    id: int
    tailor_id: str
    job_title: Optional[str]
    job_company: Optional[str]
    original_score: Optional[float]
    tailored_score: Optional[float]
    score_improvement: Optional[float]
    status: TailoredResumeStatus
    created_at: datetime

    class Config:
        from_attributes = True


class ProgressUpdate(BaseModel):
    status: str
    step: str
    progress: int
    iteration: Optional[int] = None
    initial_score: Optional[float] = None
    current_score: Optional[float] = None
```

---

## Entity Relationship Diagram

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│     tenants      │       │   portal_users   │       │   job_postings   │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)          │       │ id (PK)          │       │ id (PK)          │
│ name             │       │ name             │       │ title            │
│ ...              │       │ ...              │       │ company          │
└────────┬─────────┘       └────────┬─────────┘       │ description      │
         │                          │                 │ skills []        │
         │                          │                 │ keywords []      │
         │                          │                 │ embedding        │
         │                          │                 └────────┬─────────┘
         │                          │                          │
         │  ┌──────────────────────┼──────────────────────────┤
         │  │                      │                          │
         ▼  ▼                      ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           tailored_resumes                               │
├──────────────────────────────────────────────────────────────────────────┤
│ id (PK)                                                                  │
│ tailor_id (UUID, UNIQUE)                                                 │
│ candidate_id (FK → candidates) ON DELETE CASCADE                        │
│ job_posting_id (FK → job_postings) ON DELETE SET NULL                   │
│ tenant_id (FK → tenants) ON DELETE CASCADE                              │
│ created_by_user_id (FK → portal_users) ON DELETE SET NULL               │
│──────────────────────────────────────────────────────────────────────────│
│ status: ENUM (pending, processing, completed, failed)                    │
│ processing_error: TEXT                                                   │
│ processing_step: VARCHAR(50)                                             │
│ processing_progress: INTEGER (0-100)                                     │
│──────────────────────────────────────────────────────────────────────────│
│ original_resume_content: TEXT (markdown)                                 │
│ original_resume_keywords: VARCHAR[]                                      │
│ original_match_score: DECIMAL(5,4)                                       │
│──────────────────────────────────────────────────────────────────────────│
│ tailored_resume_content: TEXT (markdown)                                 │
│ tailored_resume_html: TEXT                                               │
│ tailored_resume_keywords: VARCHAR[]                                      │
│ tailored_match_score: DECIMAL(5,4)                                       │
│ score_improvement: DECIMAL(5,4)                                          │
│──────────────────────────────────────────────────────────────────────────│
│ job_title: VARCHAR(255)                                                  │
│ job_company: VARCHAR(255)                                                │
│ job_keywords: VARCHAR[]                                                  │
│──────────────────────────────────────────────────────────────────────────│
│ matched_skills: VARCHAR[]                                                │
│ missing_skills: VARCHAR[]                                                │
│ added_skills: VARCHAR[]                                                  │
│ improvements: JSONB                                                      │
│ skill_comparison: JSONB                                                  │
│──────────────────────────────────────────────────────────────────────────│
│ ai_provider: VARCHAR(50)                                                 │
│ ai_model: VARCHAR(100)                                                   │
│ iterations_used: INTEGER                                                 │
│ options: JSONB                                                           │
│──────────────────────────────────────────────────────────────────────────│
│ created_at: TIMESTAMP                                                    │
│ updated_at: TIMESTAMP                                                    │
│ processing_started_at: TIMESTAMP                                         │
│ processing_completed_at: TIMESTAMP                                       │
│ processing_duration_seconds: INTEGER                                     │
└──────────────────────────────────────────────────────────────────────────┘
         ▲
         │
┌────────┴─────────┐
│    candidates    │
├──────────────────┤
│ id (PK)          │
│ tenant_id (FK)   │
│ name             │
│ email            │
│ resume_content   │
│ parsed_resume_data│
│ embedding        │
│ skills []        │
│ ...              │
└──────────────────┘
```

---

## Indexes for Performance

```sql
-- Primary access patterns
CREATE INDEX ix_tailored_resumes_tailor_id ON tailored_resumes(tailor_id);
CREATE INDEX ix_tailored_resumes_candidate_id ON tailored_resumes(candidate_id);
CREATE INDEX ix_tailored_resumes_job_posting_id ON tailored_resumes(job_posting_id);
CREATE INDEX ix_tailored_resumes_tenant_id ON tailored_resumes(tenant_id);
CREATE INDEX ix_tailored_resumes_status ON tailored_resumes(status);

-- Compound index for candidate-job lookup
CREATE INDEX ix_tailored_resumes_candidate_job ON tailored_resumes(candidate_id, job_posting_id);

-- Recent tailored resumes per tenant
CREATE INDEX ix_tailored_resumes_tenant_created ON tailored_resumes(tenant_id, created_at DESC);

-- Find pending/processing jobs
CREATE INDEX ix_tailored_resumes_status_pending ON tailored_resumes(status) 
    WHERE status IN ('pending', 'processing');
```

---

**Document Status**: Draft - Pending Approval  
**Last Updated**: 2025-12-14

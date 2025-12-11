# Phase 2: Data Models

## Overview

This document details the database schemas for the Job Matching System. The system uses PostgreSQL with the `pgvector` extension for vector storage and similarity search.

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA MODEL OVERVIEW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  GLOBAL TABLES                              TENANT-SPECIFIC TABLES          │
│  ─────────────                              ──────────────────────          │
│                                                                             │
│  ┌─────────────────┐                        ┌─────────────────┐            │
│  │  job_postings   │                        │   candidates    │            │
│  │  (GLOBAL)       │◄──────────────────────▶│  (tenant_id)    │            │
│  │                 │                        │                 │            │
│  │ PK: id          │                        │ PK: id          │            │
│  │ embedding: Vec  │         1:N            │ FK: tenant_id   │            │
│  └────────┬────────┘     ┌──────────┐       │ embedding: Vec  │            │
│           │              │candidate_│       └────────┬────────┘            │
│           │              │job_matches│              │                      │
│           │              └──────────┘               │                      │
│           │                   ▲                     │                      │
│           └───────────────────┴─────────────────────┘                      │
│                                                                             │
│  ┌─────────────────┐      ┌─────────────────┐                              │
│  │  global_roles   │      │ role_job_mapping│                              │
│  │  (GLOBAL)       │◄────▶│  (GLOBAL)       │                              │
│  │                 │ 1:N  │                 │                              │
│  │ PK: id          │      │ FK: role_id     │                              │
│  │ embedding: Vec  │      │ FK: job_id      │                              │
│  └─────────────────┘      └────────┬────────┘                              │
│                                    │                                        │
│                                    │ N:1                                    │
│                                    ▼                                        │
│                           ┌─────────────────┐                              │
│                           │  job_postings   │                              │
│                           │  (referenced)   │                              │
│                           └─────────────────┘                              │
│                                                                             │
│  ┌─────────────────┐      ┌─────────────────┐                              │
│  │job_import_batch │      │job_applications │                              │
│  │  (GLOBAL)       │      │ (via candidate) │                              │
│  └─────────────────┘      └─────────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Table 1: `job_postings` (Global)

Jobs imported from external platforms. Shared across all tenants.

### Schema

```sql
CREATE TABLE job_postings (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- External Reference (for deduplication)
    external_job_id VARCHAR(255),           -- Platform-specific job ID
    platform VARCHAR(50) NOT NULL,          -- indeed, dice, linkedin, etc.
    
    -- Core Fields
    title VARCHAR(500) NOT NULL,            -- Job title
    company VARCHAR(255),                   -- Company name
    location VARCHAR(255),                  -- Job location
    description TEXT,                       -- Full job description
    requirements TEXT,                      -- Job requirements section
    
    -- Parsed Salary
    salary_range VARCHAR(255),              -- Raw salary string ("$150K - $180K")
    salary_min INTEGER,                     -- Parsed min (150000)
    salary_max INTEGER,                     -- Parsed max (180000)
    
    -- Parsed Experience
    experience_required VARCHAR(100),       -- Raw experience string ("5+ years")
    experience_min INTEGER,                 -- Parsed min years (5)
    experience_max INTEGER,                 -- Parsed max years (NULL if no max)
    
    -- Arrays (with GIN indexes)
    skills VARCHAR(100)[] DEFAULT '{}',     -- Required skills ["Python", "AWS"]
    keywords VARCHAR(100)[] DEFAULT '{}',   -- Search keywords
    
    -- Flags
    is_remote BOOLEAN DEFAULT FALSE,        -- Remote work available
    
    -- URLs
    job_url TEXT,                           -- Original posting URL
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',    -- active, expired, filled, closed
    
    -- Observability: Scraper Tracking
    scraped_by_key_id INTEGER REFERENCES scraper_api_keys(id), -- Which API key imported this
    import_batch_id INTEGER REFERENCES job_import_batches(id), -- Batch tracking
    scrape_session_id UUID,                 -- Links to scrape_sessions.session_id
    normalized_role_id INTEGER REFERENCES global_roles(id),    -- Links to queued role
    
    -- Vector Embedding (pgvector)
    embedding VECTOR(768),                  -- Google Gemini embedding
    
    -- Timestamps
    posted_date DATE,                       -- When originally posted
    imported_at TIMESTAMP DEFAULT NOW(),    -- When we imported it
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes

```sql
-- Unique constraint: prevent duplicate imports
CREATE UNIQUE INDEX idx_job_postings_external 
ON job_postings (platform, external_job_id);

-- GIN indexes for array queries
CREATE INDEX idx_job_postings_skills 
ON job_postings USING GIN (skills);

CREATE INDEX idx_job_postings_keywords 
ON job_postings USING GIN (keywords);

-- IVFFlat index for vector similarity search
CREATE INDEX idx_job_postings_embedding 
ON job_postings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Status filter
CREATE INDEX idx_job_postings_status 
ON job_postings (status);

-- Platform filter
CREATE INDEX idx_job_postings_platform 
ON job_postings (platform);
```

### Status Values

| Status | Description |
|--------|-------------|
| `active` | Job is currently open |
| `expired` | Job past 30-day cutoff |
| `filled` | Position has been filled |
| `closed` | Manually closed by admin |

---

## Table 2: `scrape_sessions` (Global - Simplified Observability)

Simplified session tracking for scraper observability. **Sessions are created when scraper fetches a role and completed when scraper posts jobs.**

### Schema

```sql
CREATE TABLE scrape_sessions (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL UNIQUE,         -- Unique session identifier
    
    -- Scraper Identification
    scraper_key_id INTEGER NOT NULL REFERENCES scraper_api_keys(id),
    scraper_name VARCHAR(100),               -- Cached from API key for reporting
    
    -- What's Being Scraped
    global_role_id INTEGER REFERENCES global_roles(id),  -- The role being scraped
    role_name VARCHAR(255),                  -- Cached role name for reporting
    
    -- Timing
    started_at TIMESTAMP NOT NULL,           -- When scraper fetched role (GET /next-role)
    completed_at TIMESTAMP,                  -- When scraper posted jobs (POST /jobs)
    duration_seconds INTEGER,                -- Computed on complete
    
    -- Results
    jobs_found INTEGER DEFAULT 0,            -- Total jobs posted in this session
    jobs_imported INTEGER DEFAULT 0,         -- Successfully imported (non-duplicate)
    jobs_skipped INTEGER DEFAULT 0,          -- Skipped (duplicates)
    
    -- Status
    status VARCHAR(20) DEFAULT 'in_progress', -- in_progress, completed, failed, timeout
    error_message TEXT,                      -- Error details if failed
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes

```sql
-- Session lookup
CREATE INDEX idx_scrape_sessions_session 
ON scrape_sessions (session_id);

-- Scraper key lookup
CREATE INDEX idx_scrape_sessions_scraper_key 
ON scrape_sessions (scraper_key_id);

-- Time-based queries for dashboards
CREATE INDEX idx_scrape_sessions_started 
ON scrape_sessions (started_at DESC);

-- Status filtering
CREATE INDEX idx_scrape_sessions_status 
ON scrape_sessions (status);

-- Role lookup
CREATE INDEX idx_scrape_sessions_role 
ON scrape_sessions (global_role_id);
```

### Session Lifecycle

```
1. Scraper calls: GET /api/scraper/queue/next-role
   → Session created with status="in_progress"
   → session_id returned to scraper
   → global_role.queue_status = "processing"

2. Scraper scrapes job boards for the role
   (No intermediate updates needed - simplified)

3. Scraper calls: POST /api/scraper/queue/jobs
   → Session status="completed"
   → jobs_found, jobs_imported, jobs_skipped recorded
   → duration_seconds calculated
   → global_role.queue_status = "completed"
   → Inngest event triggered: "jobs/imported"
```

---

## Table 3: `candidates` (Tenant-Specific)

Candidate profiles with embedding for semantic matching.

### Schema

```sql
CREATE TABLE candidates (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Tenant Isolation
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    
    -- Basic Info
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    
    -- Professional Info
    current_title VARCHAR(200),             -- "Senior Software Engineer"
    skills VARCHAR(100)[] DEFAULT '{}',     -- ["Python", "AWS", "React"]
    total_experience_years INTEGER,         -- 7
    professional_summary TEXT,              -- Resume summary
    
    -- Preferences
    expected_salary VARCHAR(100),           -- "$150K - $180K"
    location VARCHAR(200),                  -- Current location
    preferred_locations VARCHAR(200)[] DEFAULT '{}',  -- Desired locations
    preferred_roles VARCHAR(200)[] DEFAULT '{}',      -- For scrape queue
    
    -- Vector Embedding (pgvector)
    embedding VECTOR(768),                  -- Profile embedding
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending_review',
    -- pending_review, approved, rejected, ready_for_assignment
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes

```sql
-- Tenant isolation
CREATE INDEX idx_candidates_tenant 
ON candidates (tenant_id);

-- Status filter
CREATE INDEX idx_candidates_status 
ON candidates (status);

-- Email lookup
CREATE INDEX idx_candidates_email 
ON candidates (email);

-- Skills array
CREATE INDEX idx_candidates_skills 
ON candidates USING GIN (skills);

-- Preferred roles array (for queue sync)
CREATE INDEX idx_candidates_preferred_roles 
ON candidates USING GIN (preferred_roles);

-- Vector search
CREATE INDEX idx_candidates_embedding 
ON candidates 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 50);
```

---

## Table 3: `candidate_job_matches` (Tenant-Specific via Candidate)

Stores match results with scores.

### Schema

```sql
CREATE TABLE candidate_job_matches (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    job_posting_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    
    -- Overall Score
    match_score DECIMAL(5,2) NOT NULL,      -- 0-100
    
    -- Component Scores
    skill_match_score DECIMAL(5,2),         -- 0-100
    experience_match_score DECIMAL(5,2),    -- 0-100
    location_match_score DECIMAL(5,2),      -- 0-100
    salary_match_score DECIMAL(5,2),        -- 0-100
    semantic_similarity DECIMAL(5,2),       -- 0-100
    
    -- Skill Details
    matched_skills VARCHAR(100)[] DEFAULT '{}',   -- Skills candidate has
    missing_skills VARCHAR(100)[] DEFAULT '{}',   -- Skills candidate lacks
    
    -- Human-Readable Explanations
    match_reasons TEXT[] DEFAULT '{}',      -- ["Good skill match (4/5)", ...]
    
    -- Status
    status VARCHAR(50) DEFAULT 'suggested',
    -- suggested, viewed, applied, rejected, shortlisted
    
    -- Recommendation Flag
    is_recommended BOOLEAN DEFAULT FALSE,   -- Score >= 70
    
    -- Timestamps
    matched_at TIMESTAMP DEFAULT NOW(),
    viewed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes

```sql
-- Unique constraint: one match per candidate-job pair
CREATE UNIQUE INDEX idx_candidate_job_matches_unique 
ON candidate_job_matches (candidate_id, job_posting_id);

-- Candidate lookup (most common query)
CREATE INDEX idx_candidate_job_matches_candidate 
ON candidate_job_matches (candidate_id);

-- Score sorting
CREATE INDEX idx_candidate_job_matches_score 
ON candidate_job_matches (candidate_id, match_score DESC);

-- Status filter
CREATE INDEX idx_candidate_job_matches_status 
ON candidate_job_matches (status);
```

### Status Values

| Status | Description |
|--------|-------------|
| `suggested` | Match generated, not yet viewed |
| `viewed` | Recruiter has viewed this match |
| `applied` | Candidate applied to this job |
| `rejected` | Recruiter rejected this match |
| `shortlisted` | Recruiter shortlisted this match |

---

## Table 4: `job_applications` (Tenant-Specific via Candidate)

Tracks actual job applications.

### Schema

```sql
CREATE TABLE job_applications (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    job_posting_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    match_id INTEGER REFERENCES candidate_job_matches(id),
    
    -- Application Details
    application_status VARCHAR(50) DEFAULT 'applied',
    -- applied, screening, interviewing, offer, accepted, rejected, withdrawn
    
    applied_via VARCHAR(50),                -- platform, direct, referral
    cover_letter TEXT,
    notes TEXT,
    
    -- Timestamps
    applied_at TIMESTAMP DEFAULT NOW(),
    status_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes

```sql
-- Unique: one application per candidate-job
CREATE UNIQUE INDEX idx_job_applications_unique 
ON job_applications (candidate_id, job_posting_id);

-- Candidate lookup
CREATE INDEX idx_job_applications_candidate 
ON job_applications (candidate_id);

-- Status filter
CREATE INDEX idx_job_applications_status 
ON job_applications (application_status);
```

---

## Table 5: `job_import_batches` (Global)

Tracks import operations for auditing.

### Schema

```sql
CREATE TABLE job_import_batches (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Batch Identification
    batch_id VARCHAR(255) NOT NULL UNIQUE,  -- UUID or timestamp-based
    
    -- Source Info
    platform VARCHAR(50) NOT NULL,          -- Platform being imported
    file_name VARCHAR(255),                 -- Original filename
    
    -- Statistics
    total_jobs INTEGER DEFAULT 0,           -- Jobs in file
    new_jobs INTEGER DEFAULT 0,             -- Newly created
    updated_jobs INTEGER DEFAULT 0,         -- Existing updated
    failed_jobs INTEGER DEFAULT 0,          -- Failed to import
    
    -- Status
    import_status VARCHAR(50) DEFAULT 'in_progress',
    -- in_progress, completed, failed, partial
    
    error_message TEXT,                     -- If failed
    
    -- Audit
    imported_by INTEGER REFERENCES users(id),  -- PM_ADMIN who imported
    
    -- Timestamps
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Table 6: `global_roles` (Global - Role-Based Scrape Queue)

Canonical roles for role-based scraping. **Multiple candidates share the same role**, enabling efficient queue processing where we scrape for roles (not individual candidates).

### Schema

```sql
CREATE TABLE global_roles (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Canonical Role Name
    name VARCHAR(255) NOT NULL UNIQUE,  -- "Python Developer"
    
    -- Vector Embedding for AI similarity matching (role normalization)
    embedding VECTOR(768) NOT NULL,
    
    -- Role Metadata
    aliases TEXT[] DEFAULT '{}',        -- Alternative names: ["Sr Python Dev", "Python Engineer"]
    category VARCHAR(100),              -- "Engineering", "Data Science", etc.
    
    -- Candidate Tracking (denormalized for queue priority)
    candidate_count INTEGER DEFAULT 0,  -- Candidates wanting this role (via candidate_global_roles)
    
    -- Queue Management (ROLE-BASED, not candidate-based)
    queue_status VARCHAR(20) DEFAULT 'pending',
    -- pending: waiting to be scraped
    -- processing: currently being scraped by external scraper
    -- completed: recently scraped (within 24h)
    
    priority VARCHAR(20) DEFAULT 'normal',
    -- urgent, high, normal, low
    
    -- Statistics
    total_jobs_scraped INTEGER DEFAULT 0,   -- Jobs found for this role (all time)
    
    -- Timing
    last_scraped_at TIMESTAMP,              -- Last successful scrape
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes

```sql
-- Vector similarity search for role normalization (AI Option B)
CREATE INDEX idx_global_roles_embedding 
ON global_roles 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 50);

-- Queue processing: priority + candidate_count (higher count = more urgent)
-- Status "pending" → Order by priority DESC, candidate_count DESC
CREATE INDEX idx_global_roles_queue 
ON global_roles (queue_status, priority, candidate_count DESC);

-- Fast role lookup by name
CREATE INDEX idx_global_roles_name 
ON global_roles (name);

-- Category filtering
CREATE INDEX idx_global_roles_category 
ON global_roles (category);
```

---

## Table 7: `candidate_global_roles` (Linking Table)

Links candidates to their normalized preferred roles. **This is the key to role-based queue processing** - when a role is scraped, all candidates linked to it receive matches.

### Schema

```sql
CREATE TABLE candidate_global_roles (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    global_role_id INTEGER NOT NULL REFERENCES global_roles(id) ON DELETE CASCADE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes

```sql
-- Unique: candidate can only have each role once
CREATE UNIQUE INDEX idx_candidate_global_roles_unique 
ON candidate_global_roles (candidate_id, global_role_id);

-- Find all candidates for a role (for matching after job import)
CREATE INDEX idx_candidate_global_roles_role 
ON candidate_global_roles (global_role_id);

-- Find all roles for a candidate
CREATE INDEX idx_candidate_global_roles_candidate 
ON candidate_global_roles (candidate_id);
```

### Usage Flow

```
1. Candidate selects preferred roles during onboarding
2. AI normalizes each role → finds/creates global_role
3. Creates candidate_global_roles record
4. global_role.candidate_count is incremented
5. Role appears in scrape queue (if pending)
6. When jobs imported for role → match to ALL linked candidates
```

---

## Table 8: `role_job_mapping` (Global)

Links jobs to the role that triggered their scrape.

### Schema

```sql
CREATE TABLE role_job_mapping (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    global_role_id INTEGER NOT NULL REFERENCES global_roles(id) ON DELETE CASCADE,
    job_posting_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    
    -- Audit
    scraped_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes

```sql
-- Unique: one mapping per role-job pair
CREATE UNIQUE INDEX idx_role_job_mapping_unique 
ON role_job_mapping (global_role_id, job_posting_id);

-- Role lookup (get jobs for a role)
CREATE INDEX idx_role_job_mapping_role 
ON role_job_mapping (global_role_id);

-- Job lookup (which roles found this job)
CREATE INDEX idx_role_job_mapping_job 
ON role_job_mapping (job_posting_id);
```

---

## Table 9: `scraper_api_keys` (Global)

API keys for external scraper authentication.

### Schema

```sql
CREATE TABLE scraper_api_keys (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Key Data
    key_hash VARCHAR(255) NOT NULL UNIQUE,  -- SHA256 hash
    name VARCHAR(100) NOT NULL,             -- "production-scraper"
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Usage Tracking
    last_used_at TIMESTAMP,
    total_requests INTEGER DEFAULT 0,
    
    -- Audit
    created_by INTEGER REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    revoked_at TIMESTAMP
);
```

---

## SQLAlchemy Models

### JobPosting Model

```python
# server/app/models/job_posting.py
from app import db
from app.models.base import BaseModel
from pgvector.sqlalchemy import Vector

class JobPosting(BaseModel):
    __tablename__ = 'job_postings'
    
    # External reference
    external_job_id = db.Column(db.String(255))
    platform = db.Column(db.String(50), nullable=False)
    
    # Core fields
    title = db.Column(db.String(500), nullable=False)
    company = db.Column(db.String(255))
    location = db.Column(db.String(255))
    description = db.Column(db.Text)
    requirements = db.Column(db.Text)
    
    # Parsed salary
    salary_range = db.Column(db.String(255))
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    
    # Parsed experience
    experience_required = db.Column(db.String(100))
    experience_min = db.Column(db.Integer)
    experience_max = db.Column(db.Integer)
    
    # Arrays
    skills = db.Column(db.ARRAY(db.String(100)), default=list)
    keywords = db.Column(db.ARRAY(db.String(100)), default=list)
    
    # Flags
    is_remote = db.Column(db.Boolean, default=False)
    
    # URLs
    job_url = db.Column(db.Text)
    
    # Status
    status = db.Column(db.String(50), default='active')
    
    # Vector embedding
    embedding = db.Column(Vector(768))
    
    # Timestamps
    posted_date = db.Column(db.Date)
    imported_at = db.Column(db.DateTime, default=db.func.now())
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('platform', 'external_job_id', 
                           name='uq_job_posting_external'),
    )
```

### CandidateJobMatch Model

```python
# server/app/models/candidate_job_match.py
from app import db
from app.models.base import BaseModel

class CandidateJobMatch(BaseModel):
    __tablename__ = 'candidate_job_matches'
    
    # Foreign keys
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    job_posting_id = db.Column(db.Integer, db.ForeignKey('job_postings.id', ondelete='CASCADE'), nullable=False)
    
    # Scores
    match_score = db.Column(db.Numeric(5, 2), nullable=False)
    skill_match_score = db.Column(db.Numeric(5, 2))
    experience_match_score = db.Column(db.Numeric(5, 2))
    location_match_score = db.Column(db.Numeric(5, 2))
    salary_match_score = db.Column(db.Numeric(5, 2))
    semantic_similarity = db.Column(db.Numeric(5, 2))
    
    # Skill details
    matched_skills = db.Column(db.ARRAY(db.String(100)), default=list)
    missing_skills = db.Column(db.ARRAY(db.String(100)), default=list)
    
    # Explanations
    match_reasons = db.Column(db.ARRAY(db.Text), default=list)
    
    # Status
    status = db.Column(db.String(50), default='suggested')
    is_recommended = db.Column(db.Boolean, default=False)
    
    # Timestamps
    matched_at = db.Column(db.DateTime, default=db.func.now())
    viewed_at = db.Column(db.DateTime)
    
    # Relationships
    candidate = db.relationship('Candidate', backref='job_matches')
    job_posting = db.relationship('JobPosting', backref='candidate_matches')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('candidate_id', 'job_posting_id', 
                           name='uq_candidate_job_match'),
    )
```

### GlobalRole Model

```python
# server/app/models/global_role.py
from app import db
from app.models.base import BaseModel
from pgvector.sqlalchemy import Vector

class GlobalRole(BaseModel):
    __tablename__ = 'global_roles'
    
    # Canonical role
    canonical_role = db.Column(db.String(255), nullable=False, unique=True)
    
    # Vector embedding
    embedding = db.Column(Vector(768), nullable=False)
    
    # Variants
    mapped_variants = db.Column(db.JSON, default=list)
    
    # Queue status
    status = db.Column(db.String(50), default='pending')
    
    # Statistics
    candidate_count = db.Column(db.Integer, default=0)
    total_jobs_scraped = db.Column(db.Integer, default=0)
    
    # Timing
    last_scraped_at = db.Column(db.DateTime)
    
    # Relationships
    jobs = db.relationship('RoleJobMapping', backref='role', lazy='dynamic')
```

---

## Migration Example

```python
# migrations/versions/xxx_add_job_matching_tables.py
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

def upgrade():
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create job_postings table
    op.create_table(
        'job_postings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('external_job_id', sa.String(255)),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('company', sa.String(255)),
        sa.Column('location', sa.String(255)),
        sa.Column('description', sa.Text()),
        sa.Column('skills', sa.ARRAY(sa.String(100)), default=[]),
        sa.Column('embedding', Vector(768)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.UniqueConstraint('platform', 'external_job_id', name='uq_job_posting_external')
    )
    
    # Create vector index
    op.execute("""
        CREATE INDEX idx_job_postings_embedding 
        ON job_postings 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100)
    """)

def downgrade():
    op.drop_table('job_postings')
```

---

## Next: [04-EMBEDDING-SYSTEM.md](./04-EMBEDDING-SYSTEM.md) - Embedding Generation & Storage

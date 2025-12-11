# Phase 1: System Overview

## Introduction

The Blacklight Job Matching System is an AI-powered job recommendation engine designed for multi-tenant HR bench sales recruiting workflows. It matches candidates with job postings using multi-factor scoring and semantic embeddings.

## System Goals

1. **Automate Job Discovery**: Reduce manual effort in finding relevant jobs for candidates
2. **Intelligent Matching**: Use AI to understand semantic similarity beyond keyword matching
3. **Multi-Tenant Support**: Isolate candidate data while sharing global job postings
4. **Scalable Architecture**: Handle thousands of candidates and jobs efficiently
5. **Recruiter Productivity**: Surface the best matches with actionable insights

---

## Key Features

### 1. AI-Powered Matching
- 768-dimensional semantic embeddings via Google Gemini
- Multi-factor scoring: skills, experience, location, salary, semantic similarity
- Match grades (A+ to F) for quick assessment

### 2. Global Job Repository
- Jobs imported from multiple platforms (Indeed, Dice, LinkedIn, etc.)
- Deduplication by platform + external_job_id
- Automatic salary/experience parsing
- Skill extraction and normalization

### 3. Candidate-Centric Scraping (Phase 2)
- Jobs scraped based on candidate preferred roles
- AI-based role normalization using vector similarity
- Continuous queue rotation for fresh job data

### 4. Background Workflows
- **Event-driven matching on new job import** - When jobs are posted, immediately match with candidates who have matching preferred roles
- Event-driven matching on candidate profile updates
- Automatic job expiration (30-day cutoff)

---

## Multi-Tenant Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MULTI-TENANT DATA MODEL                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  GLOBAL (Shared)                    TENANT-SPECIFIC                 │
│  ──────────────                     ────────────────                │
│                                                                     │
│  job_postings                       candidates                      │
│  ├── id                             ├── id                          │
│  ├── external_job_id                ├── tenant_id (FK) ◄──── Filter │
│  ├── platform (indeed, dice, etc)   ├── first_name, last_name       │
│  ├── title, company, location       ├── skills[]                    │
│  ├── description, requirements      ├── preferred_roles[]           │
│  ├── salary_range, salary_min/max   ├── embedding (Vector 768)      │
│  ├── experience_min/max             └── status                      │
│  ├── skills[] (ARRAY)                                               │
│  ├── keywords[] (ARRAY)             candidate_job_matches           │
│  ├── job_type, is_remote            ├── candidate_id (FK)           │
│  ├── job_url, apply_url             ├── job_posting_id (FK)         │
│  ├── embedding (Vector 768)         ├── match_score                 │
│  ├── status (ACTIVE/EXPIRED)        └── matched_skills[]            │
│  ├── posted_date, expires_at                                        │
│  └── import_batch_id                job_applications                │
│                                     (tracks applications)           │
│  global_roles                                                       │
│  ├── name, normalized_name                                          │
│  ├── category, seniority_level                                      │
│  └── embedding (Vector 768)                                         │
│                                                                     │
│  job_import_batches                                                 │
│  role_job_mapping                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Isolation Rules

| Entity | Scope | Isolation Method |
|--------|-------|------------------|
| Job Postings | Global | All tenants see same jobs |
| Global Roles | Global | Shared scrape queue |
| Candidates | Tenant | `tenant_id` foreign key |
| Job Matches | Tenant | Via `candidate.tenant_id` |
| Applications | Tenant | Via `candidate.tenant_id` |

---

## User Roles & Permissions

### Portal Users (Tenant-Specific)

| Role | Job Matching Permissions |
|------|-------------------------|
| **TENANT_ADMIN** | Full access: view all candidate matches, manage match settings |
| **MANAGER** | View all candidate matches |
| **TEAM_LEAD** | View assigned candidates' matches |
| **RECRUITER** | View assigned candidates' matches only |

> **Note:** Match generation is fully automated - triggered by job imports and candidate approvals. No manual trigger needed.

### Central Platform (PM_ADMIN)

| Role | Job Matching Permissions |
|------|-------------------------|
| **PM_ADMIN** | Job import, scrape queue management, role merge, API key management |

---

## Core Workflows

### 1. Job Import Flow (Manual)

```
PM_ADMIN uploads JSON    →    JobImportService parses    →    Jobs stored globally
(from Indeed, Dice, etc)       ├── Parse salary                with embeddings
                               ├── Parse experience
                               ├── Extract skills
                               └── Generate embedding
```

### 2. Job Import Match Flow (Event-Driven)

```
New jobs imported     →    Inngest event triggered     →    Find matching candidates
(from scraper)             "jobs/imported"                  ├── Get job's normalized role
                                                             ├── Find candidates with
                                                             │   matching preferred_roles
                                                             ├── Calculate match scores
                                                             └── Store matches
```

### 3. Candidate Onboarding Match Flow

```
Candidate approved    →    Inngest event triggered     →    Find matching jobs
(onboarding)               "candidate/approved"             ├── Get candidate's preferred_roles
                                                             ├── Find jobs with matching roles
                                                             ├── Calculate match scores
                                                             └── Store top 50 matches
```

### 4. Scrape Queue Flow (Candidate-Driven)

```
Candidate selects roles    →    Roles normalized (AI)    →    Scraper fetches jobs
["Senior Python Dev"]          → "Python Developer"           for queued roles
                                  (vector similarity)
                                                              ↓
                                                         Jobs imported
                                                              ↓
                                                         Auto-match triggered
                                                         (for candidates with
                                                         preferred_role = "Python Developer")
```

---

## Technology Decisions

### Why Google Gemini for Embeddings?

| Factor | Decision |
|--------|----------|
| **Quality** | State-of-the-art semantic understanding |
| **Dimensions** | 768 (good balance of precision vs storage) |
| **Task Types** | Supports `RETRIEVAL_DOCUMENT` and `SEMANTIC_SIMILARITY` |
| **Cost** | Competitive pricing for batch generation |

### Why pgvector over Pinecone/Qdrant?

| Factor | Decision |
|--------|----------|
| **Scale** | <100K jobs - pgvector sufficient |
| **Simplicity** | No additional infrastructure |
| **Transactions** | Same DB for data + vectors |
| **Migration** | Abstract interface allows future migration |

### Why Inngest for Background Jobs?

| Factor | Decision |
|--------|----------|
| **Observability** | Built-in dashboard for monitoring |
| **Retry Logic** | Automatic exponential backoff |
| **Rate Limiting** | Built-in concurrency control |
| **Event-Driven** | Natural fit for triggering matches |

---

## Performance Characteristics

### Current System Capacity

| Metric | Capacity | Notes |
|--------|----------|-------|
| Jobs | ~50,000 | With IVFFlat index |
| Candidates per Tenant | ~5,000 | Per tenant |
| Match Generation | ~2 sec/candidate | With 50K jobs |
| Nightly Refresh | ~4 hours | For 10K total candidates |

### Scaling Thresholds

| Scale | Recommendation |
|-------|----------------|
| <10K jobs | Current setup (pgvector) ✅ |
| 10K-100K jobs | Add table partitioning |
| 100K-1M jobs | Migrate to dedicated vector DB |
| 1M+ jobs | Distributed vector search (Vespa/Elasticsearch) |

---

## Security Considerations

### Job Data
- Jobs are public (no tenant isolation)
- Scraper uses API key authentication
- PM_ADMIN only for import operations

### Match Data
- Matches inherit tenant isolation from candidates
- Portal auth required for all match endpoints
- Role-based permission checks

### Embeddings
- Stored in same DB as source data
- No PII in embedding text (skills, title, summary only)
- API key for Gemini stored securely

---

## Integration Points

### External Systems

| System | Integration |
|--------|-------------|
| Google Gemini | Embedding generation API |
| Job Platforms | JSON import (Indeed, Dice, LinkedIn, etc.) |
| External Scraper | REST API for queue management |

### Internal Systems

| System | Integration |
|--------|-------------|
| Onboarding | Triggers match generation on approval |
| Candidate Service | Profile updates trigger re-matching |
| Inngest | Background job orchestration |
| Redis | Caching for hot embeddings (future) |

---

## Next Steps

1. **[02-ARCHITECTURE-DIAGRAM.md](./02-ARCHITECTURE-DIAGRAM.md)** - Visual architecture diagrams
2. **[03-DATA-MODELS.md](./03-DATA-MODELS.md)** - Detailed database schemas

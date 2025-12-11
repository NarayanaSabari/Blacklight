# Blacklight Job Matching System Documentation

## Overview

This folder contains comprehensive documentation for the Blacklight Job Matching System - an AI-powered job recommendation engine that matches candidates with job postings using multi-factor scoring and semantic embeddings.

## Documentation Structure

The documentation is organized into phases for easier understanding and implementation:

### Phase 1: Core Architecture
- **[01-OVERVIEW.md](./01-OVERVIEW.md)** - System overview, high-level architecture, and design principles
- **[02-ARCHITECTURE-DIAGRAM.md](./02-ARCHITECTURE-DIAGRAM.md)** - Visual system architecture and component interactions

### Phase 2: Data Layer
- **[03-DATA-MODELS.md](./03-DATA-MODELS.md)** - Database schemas, relationships, and indexing strategies
- **[04-EMBEDDING-SYSTEM.md](./04-EMBEDDING-SYSTEM.md)** - Google Gemini integration, vector storage with pgvector

### Phase 3: Matching Engine
- **[05-MATCHING-ALGORITHM.md](./05-MATCHING-ALGORITHM.md)** - Multi-factor scoring algorithm, weights, and grade system
- **[06-SKILL-MATCHING.md](./06-SKILL-MATCHING.md)** - Skill matching strategies (exact, synonym, fuzzy)

### Phase 4: Background Workflows
- **[07-INNGEST-WORKFLOWS.md](./07-INNGEST-WORKFLOWS.md)** - Scheduled jobs, event-driven matching, nightly refresh

### Phase 5: API Reference
- **[08-API-ENDPOINTS.md](./08-API-ENDPOINTS.md)** - Complete REST API documentation for job matching

### Phase 6: CentralD Queue Monitoring
- **[09-SCRAPE-QUEUE-SYSTEM.md](./09-SCRAPE-QUEUE-SYSTEM.md)** - Candidate-centric job scraping architecture with observability
- **[10-AI-ROLE-NORMALIZATION.md](./10-AI-ROLE-NORMALIZATION.md)** - AI + Vector-based role normalization
- **[11-CENTRALD-DASHBOARD.md](./11-CENTRALD-DASHBOARD.md)** - PM_ADMIN dashboard for queue and scraper monitoring

### Phase 7: Operations & Future
- **[12-CONFIGURATION.md](./12-CONFIGURATION.md)** - Environment variables, database setup, performance tuning
- **[13-TROUBLESHOOTING.md](./13-TROUBLESHOOTING.md)** - Common issues and debugging guide
- **[14-FUTURE-IMPROVEMENTS.md](./14-FUTURE-IMPROVEMENTS.md)** - Roadmap, scalability, and enhancement recommendations

---

## Quick Links

| Topic | File |
|-------|------|
| How does matching work? | [05-MATCHING-ALGORITHM.md](./05-MATCHING-ALGORITHM.md) |
| Database schemas | [03-DATA-MODELS.md](./03-DATA-MODELS.md) |
| API endpoints | [08-API-ENDPOINTS.md](./08-API-ENDPOINTS.md) |
| Scraper integration | [09-SCRAPE-QUEUE-SYSTEM.md](./09-SCRAPE-QUEUE-SYSTEM.md) |
| Scraper observability | [09-SCRAPE-QUEUE-SYSTEM.md#scraper-observability](./09-SCRAPE-QUEUE-SYSTEM.md#scraper-observability) |
| CentralD dashboard | [11-CENTRALD-DASHBOARD.md](./11-CENTRALD-DASHBOARD.md) |
| Troubleshooting | [13-TROUBLESHOOTING.md](./13-TROUBLESHOOTING.md) |

---

## Key Concepts

### Multi-Tenant Architecture
- **Job Postings**: Global (shared across all tenants)
- **Candidates**: Tenant-specific (isolated by `tenant_id`)
- **Matches**: Tenant-specific (via candidate relationship)

### Matching Score Components
| Factor | Weight | Description |
|--------|--------|-------------|
| Skills | 40% | Skill overlap with synonym/fuzzy matching |
| Experience | 25% | Years vs job requirements |
| Location | 15% | Remote preference, city/state match |
| Salary | 10% | Expected vs offered alignment |
| Semantic | 10% | Embedding cosine similarity |

### Role-Based Scrape Queue Flow
1. Candidate selects preferred roles during onboarding
2. **AI normalizes roles** (Option B: embedding similarity first, then Gemini AI)
3. Candidate linked to `GlobalRole` via `candidate_global_roles` table
4. `GlobalRole.candidate_count` incremented → role appears in queue
5. External scraper fetches next role (`GET /api/scraper/queue/next-role`)
6. Scraper posts jobs (`POST /api/scraper/queue/jobs`)
7. **`jobs/imported` event triggered → matches created for ALL candidates with that role**

### Event-Driven Matching (No Nightly Refresh)
- **Job Import** → `jobs/imported` event → Match to ALL candidates linked to that global_role
- **Candidate Approved** → `job-match/generate-candidate` event → Match against existing jobs
- **No nightly batch refresh** - matches are created in real-time

---

## Files Reference (Server)

```
server/app/
├── models/
│   ├── job_posting.py           # JobPosting with embedding, normalized_role_id
│   ├── candidate_job_match.py   # Match results
│   ├── job_import_batch.py      # Import tracking
│   ├── global_role.py           # Canonical roles (role-based queue)
│   ├── candidate_global_roles.py # Links candidates to normalized roles
│   ├── scrape_session.py        # Simplified session tracking
│   └── scraper_api_key.py       # API key management
├── services/
│   ├── job_import_service.py    # JSON import logic
│   ├── job_matching_service.py  # Matching algorithm
│   ├── embedding_service.py     # Gemini embeddings
│   ├── scrape_queue_service.py  # Role queue management
│   └── ai_role_normalization_service.py  # Option B: embedding + AI normalization
├── routes/
│   ├── job_import_routes.py     # PM_ADMIN import APIs
│   ├── job_match_routes.py      # Portal matching APIs
│   ├── scraper_routes.py        # Scraper APIs (queue/next-role, queue/jobs)
│   └── scraper_monitoring_routes.py # CentralD observability APIs
└── inngest/functions/
    └── job_matching_tasks.py    # Event-driven matching workflows
```

---

## Scraper Observability (Simplified)

Session tracking is simplified to two key events:
1. **Session Start**: When scraper fetches a role (`GET /api/scraper/queue/next-role`)
2. **Session Complete**: When scraper posts jobs (`POST /api/scraper/queue/jobs`)

| Metric | Description |
|--------|-------------|
| `session_id` | Unique session identifier |
| `scraper_key_id` | Which API key (scraper) |
| `role_name` | The role being scraped |
| `started_at` / `completed_at` | Timestamps |
| `duration_seconds` | Total session duration |
| `jobs_found` / `jobs_imported` / `jobs_skipped` | Job counts |
| `status` | `in_progress`, `completed`, `failed`, `timeout` |

**Key Endpoints**:

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /api/scraper/queue/next-role` | Scraper API Key | Get next role + start session |
| `POST /api/scraper/queue/jobs` | Scraper API Key | Post jobs + complete session |
| `GET /api/scraper-monitoring/sessions` | PM_ADMIN | View recent sessions |
| `GET /api/scraper-monitoring/stats` | PM_ADMIN | Aggregated statistics |
| `GET /api/scraper-monitoring/queue` | PM_ADMIN | View role queue status |

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask (Python 3.11) |
| Database | PostgreSQL 15 with pgvector |
| Embeddings | Google Gemini `models/embedding-001` |
| Vector Dimensions | 768 |
| Background Jobs | Inngest |
| Vector Index | IVFFlat (100 lists) |

---

## Getting Started

1. **Setup Environment**
   ```bash
   # Required env vars
   GOOGLE_API_KEY=your-gemini-api-key
   DATABASE_URL=postgresql://user:pass@host:5432/blacklight
   ```

2. **Enable pgvector**
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

4. **Create Scraper API Key** (PM_ADMIN)
   - Generate key via CentralD dashboard
   - Share with external scraper

5. **Match Generation** (Automatic)
   - On candidate approval: `job-match/generate-candidate` event
   - On job import: `jobs/imported` event
   - No manual intervention needed

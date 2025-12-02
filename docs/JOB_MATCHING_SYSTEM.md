# Blacklight Job Matching System

## Overview

The Blacklight Job Matching System is an AI-powered job recommendation engine that matches candidates with job postings using multi-factor scoring and semantic embeddings. The system is designed for multi-tenant HR bench sales recruiting workflows.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JOB MATCHING SYSTEM                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐        ┌─────────────────────┐                    │
│  │  External Platforms │        │    Central Platform │                    │
│  │  ─────────────────  │        │  (PM_ADMIN Only)    │                    │
│  │  • Indeed           │        │  ─────────────────  │                    │
│  │  • Dice             │───────▶│  Job Import API     │                    │
│  │  • TechFetch        │  JSON  │  /api/jobs/import   │                    │
│  │  • Glassdoor        │        └──────────┬──────────┘                    │
│  │  • Monster          │                   │                               │
│  └─────────────────────┘                   ▼                               │
│                              ┌─────────────────────────┐                   │
│                              │    JobImportService     │                   │
│                              │  ───────────────────    │                   │
│                              │  • Parse salary         │                   │
│                              │  • Parse experience     │                   │
│                              │  • Normalize skills     │                   │
│                              │  • Detect remote        │                   │
│                              │  • Generate keywords    │                   │
│                              └───────────┬─────────────┘                   │
│                                          │                                 │
│                                          ▼                                 │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │                      POSTGRESQL DATABASE                          │    │
│  │  ─────────────────────────────────────────────────────────────    │    │
│  │                                                                   │    │
│  │  job_postings (GLOBAL)           candidates (PER TENANT)          │    │
│  │  ─────────────────────           ────────────────────────         │    │
│  │  • id                            • id                             │    │
│  │  • title, company, location      • tenant_id (FK)                 │    │
│  │  • description, requirements     • first_name, last_name          │    │
│  │  • skills[] (ARRAY)              • skills[] (ARRAY)               │    │
│  │  • salary_min, salary_max        • expected_salary                │    │
│  │  • experience_min/max            • total_experience_years         │    │
│  │  • embedding (Vector 768)        • embedding (Vector 768)         │    │
│  │  • platform, external_job_id     • preferred_locations[]          │    │
│  │  • status (ACTIVE/EXPIRED)       • status                         │    │
│  │                                                                   │    │
│  │  candidate_job_matches (PER TENANT)                               │    │
│  │  ──────────────────────────────────                               │    │
│  │  • candidate_id (FK)                                              │    │
│  │  • job_posting_id (FK)                                            │    │
│  │  • match_score (0-100)                                            │    │
│  │  • skill_match_score                                              │    │
│  │  • experience_match_score                                         │    │
│  │  • location_match_score                                           │    │
│  │  • salary_match_score                                             │    │
│  │  • semantic_similarity                                            │    │
│  │  • matched_skills[], missing_skills[]                             │    │
│  │  • status (SUGGESTED/VIEWED/APPLIED/REJECTED/SHORTLISTED)         │    │
│  └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        INNGEST WORKFLOWS                            │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │                                                                     │   │
│  │  nightly-match-refresh (Cron: 2 AM daily)                          │   │
│  │  ───────────────────────────────────────                           │   │
│  │  1. Fetch all active tenants                                       │   │
│  │  2. For each tenant: generate matches for all candidates           │   │
│  │  3. Aggregate statistics                                           │   │
│  │                                                                     │   │
│  │  generate-candidate-matches (Event: job-match/generate-candidate)  │   │
│  │  ────────────────────────────────────────────────────────────────  │   │
│  │  Triggered by: onboarding approval, profile update, manual         │   │
│  │  1. Validate candidate                                             │   │
│  │  2. Ensure embedding exists (generate if missing)                  │   │
│  │  3. Generate matches                                               │   │
│  │  4. Update status to 'ready_for_assignment' (if onboarding)        │   │
│  │                                                                     │   │
│  │  update-job-embeddings (Event: job-posting/updated)                │   │
│  │  ────────────────────────────────────────────────                  │   │
│  │  Regenerates job embedding when content fields change              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### 1. JobPosting (Global - Shared Across Tenants)

Jobs are imported from external platforms and stored globally. They are NOT tenant-specific.

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `external_job_id` | String(255) | Platform-specific ID |
| `platform` | String(50) | Source: indeed, dice, techfetch, glassdoor, monster |
| `title` | String(500) | Job title |
| `company` | String(255) | Company name |
| `location` | String(255) | Job location |
| `description` | Text | Full job description |
| `salary_range` | String(255) | Raw salary string |
| `salary_min` | Integer | Parsed minimum salary (annual USD) |
| `salary_max` | Integer | Parsed maximum salary (annual USD) |
| `experience_required` | String(100) | Raw experience string |
| `experience_min` | Integer | Parsed minimum years |
| `experience_max` | Integer | Parsed maximum years |
| `skills` | Array[String] | Required skills (GIN indexed) |
| `keywords` | Array[String] | Search keywords (GIN indexed) |
| `is_remote` | Boolean | Remote work flag |
| `job_url` | Text | Original job posting URL |
| `status` | String(50) | ACTIVE, EXPIRED, FILLED, CLOSED |
| `embedding` | Vector(768) | Google Gemini embedding (IVFFlat indexed) |
| `posted_date` | Date | When job was posted |
| `imported_at` | DateTime | When imported to system |

**Indexes:**
- Unique: `(platform, external_job_id)` - Prevents duplicate imports
- GIN: `skills`, `keywords` - Fast array containment queries
- IVFFlat: `embedding` - Fast vector similarity search

### 2. Candidate (Tenant-Specific)

Each candidate belongs to exactly one tenant.

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `tenant_id` | Integer (FK) | Tenant isolation |
| `first_name`, `last_name` | String | Name |
| `email` | String(255) | Contact email |
| `skills` | Array[String] | Technical skills |
| `total_experience_years` | Integer | Years of experience |
| `expected_salary` | String(100) | Expected compensation |
| `location` | String(200) | Current location |
| `preferred_locations` | Array[String] | Desired work locations |
| `embedding` | Vector(768) | Profile embedding |
| `status` | String(50) | pending_review, ready_for_assignment, etc. |

### 3. CandidateJobMatch (Tenant-Specific via Candidate)

Stores match results between candidates and jobs.

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `candidate_id` | Integer (FK) | Link to candidate |
| `job_posting_id` | Integer (FK) | Link to job |
| `match_score` | Decimal(5,2) | Overall score 0-100 |
| `skill_match_score` | Decimal(5,2) | Skills component |
| `experience_match_score` | Decimal(5,2) | Experience component |
| `location_match_score` | Decimal(5,2) | Location component |
| `salary_match_score` | Decimal(5,2) | Salary component |
| `semantic_similarity` | Decimal(5,2) | Embedding similarity |
| `matched_skills` | Array[String] | Matching skills |
| `missing_skills` | Array[String] | Skills candidate lacks |
| `match_reasons` | Array[String] | Human-readable explanations |
| `status` | String(50) | SUGGESTED, VIEWED, APPLIED, REJECTED, SHORTLISTED |
| `is_recommended` | Boolean | Grade B (70+) or higher |

**Unique Constraint:** `(candidate_id, job_posting_id)` - One match per candidate-job pair

### 4. JobApplication (Tenant-Specific)

Tracks actual job applications submitted.

| Field | Type | Description |
|-------|------|-------------|
| `candidate_id` | Integer (FK) | Candidate who applied |
| `job_posting_id` | Integer (FK) | Job applied to |
| `application_status` | String(50) | APPLIED, SCREENING, INTERVIEWING, OFFER, ACCEPTED, REJECTED |
| `applied_via` | String(50) | PLATFORM, DIRECT, REFERRAL |
| `applied_at` | DateTime | Application timestamp |

### 5. JobImportBatch (Global)

Tracks import operations for auditing.

| Field | Type | Description |
|-------|------|-------------|
| `batch_id` | String(255) | Unique batch identifier |
| `platform` | String(50) | Source platform |
| `total_jobs` | Integer | Jobs in import file |
| `new_jobs` | Integer | Newly imported |
| `updated_jobs` | Integer | Existing jobs updated |
| `failed_jobs` | Integer | Failed to import |
| `import_status` | String(50) | IN_PROGRESS, COMPLETED, FAILED |

---

## Embedding System

### Google Gemini Integration

The system uses **Google Gemini `models/embedding-001`** to generate 768-dimensional semantic embeddings.

```python
# EmbeddingService (server/app/services/embedding_service.py)

class EmbeddingService:
    MODEL_NAME = "models/embedding-001"
    EMBEDDING_DIMENSION = 768
    
    def generate_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """Generate 768-dim embedding using Gemini API"""
        result = genai.embed_content(
            model=self.MODEL_NAME,
            content=text,
            task_type=task_type
        )
        return result['embedding']
```

### Candidate Embedding Generation

Candidate profiles are converted to text that captures their professional identity:

```python
def generate_candidate_embedding(self, candidate_data) -> List[float]:
    parts = []
    
    # Title
    if candidate.current_title:
        parts.append(f"Title: {candidate.current_title}")
    
    # Experience
    if candidate.total_experience_years:
        parts.append(f"Experience: {candidate.total_experience_years} years")
    
    # Skills
    if candidate.skills:
        parts.append(f"Skills: {', '.join(candidate.skills)}")
    
    # Summary
    if candidate.professional_summary:
        parts.append(f"Summary: {candidate.professional_summary}")
    
    profile_text = ". ".join(parts)
    return self.generate_embedding(profile_text)
```

**Example Input:**
```
Title: Senior Software Engineer. Experience: 7 years. Skills: Python, React, AWS, PostgreSQL. 
Summary: Full-stack developer with expertise in cloud architecture and microservices.
```

### Job Embedding Generation

Job postings are embedded with title, skills, and description:

```python
def generate_job_embedding(self, job_data) -> List[float]:
    parts = []
    
    parts.append(f"Job Title: {job.title}")
    parts.append(f"Required Skills: {', '.join(job.skills)}")
    
    if job.experience_min:
        parts.append(f"Minimum Experience: {job.experience_min} years")
    
    # Truncate description to 500 chars
    parts.append(f"Description: {job.description[:500]}")
    
    job_text = ". ".join(parts)
    return self.generate_embedding(job_text, task_type="RETRIEVAL_DOCUMENT")
```

### Vector Storage (pgvector)

Embeddings are stored in PostgreSQL using the `pgvector` extension:

```sql
-- Vector column definition
embedding = db.Column(Vector(768))

-- IVFFlat index for fast similarity search
Index('idx_job_posting_embedding', 'embedding', 
      postgresql_using='ivfflat', 
      postgresql_with={'lists': 100}, 
      postgresql_ops={'embedding': 'vector_cosine_ops'})
```

---

## Matching Algorithm

### Scoring Weights

The matching score is a weighted combination of five factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Skills Match** | 40% | Overlap between candidate and job skills |
| **Experience Match** | 25% | Years of experience vs requirements |
| **Location Match** | 15% | Location preference compatibility |
| **Salary Match** | 10% | Expected vs offered salary alignment |
| **Semantic Similarity** | 10% | Embedding cosine similarity |

```python
# JobMatchingService scoring weights
WEIGHT_SKILLS = 0.40
WEIGHT_EXPERIENCE = 0.25
WEIGHT_LOCATION = 0.15
WEIGHT_SALARY = 0.10
WEIGHT_SEMANTIC = 0.10

# Final score calculation
overall_score = (
    skill_score * 0.40 +
    experience_score * 0.25 +
    location_score * 0.15 +
    salary_score * 0.10 +
    semantic_score * 0.10
)
```

### 1. Skills Matching (40%)

Three-strategy matching:

1. **Exact Match** (case-insensitive)
2. **Synonym Match** (predefined mappings)
3. **Fuzzy Match** (85% string similarity threshold)

```python
SKILL_SYNONYMS = {
    'aws': ['amazon web services', 'amazon aws'],
    'k8s': ['kubernetes'],
    'js': ['javascript'],
    'react': ['reactjs', 'react.js'],
    'postgres': ['postgresql', 'pg'],
    # ... 50+ mappings
}

# Score = (matched_skills / total_required_skills) * 100
```

**Example:**
- Job requires: `['Python', 'AWS', 'Kubernetes', 'React', 'PostgreSQL']`
- Candidate has: `['Python', 'Amazon Web Services', 'k8s', 'ReactJS']`
- Matched: Python (exact), AWS (synonym), Kubernetes (synonym), React (synonym)
- Missing: PostgreSQL
- Score: `4/5 * 100 = 80%`

### 2. Experience Matching (25%)

Evaluates candidate's years against job requirements:

| Scenario | Score |
|----------|-------|
| Meets minimum requirement | 100% |
| 1 year below minimum | 85% |
| 2 years below minimum | 70% |
| 3 years below minimum | 55% |
| 4+ years below minimum | 40% |
| Slightly overqualified (1-2 years over max) | 95% |
| Moderately overqualified (3-5 years over) | 85% |
| Very overqualified (11+ years over) | 60% |

### 3. Location Matching (15%)

| Scenario | Score |
|----------|-------|
| Remote job + candidate wants remote | 100% |
| Remote job + candidate flexible | 90% |
| Same city and state | 100% |
| Same state, different city | 75% |
| Candidate wants remote, job is onsite | 40% |
| Different locations, not remote | 30% |
| Missing location data | 50% |

### 4. Salary Matching (10%)

Compares candidate's expected salary range with job's offered range:

| Scenario | Score |
|----------|-------|
| Ranges overlap fully | 100% |
| Job max slightly below candidate min (<10%) | 75% |
| Job max moderately below (10-20%) | 60% |
| Job max significantly below (20-30%) | 45% |
| Large salary gap (30%+) | 30% |
| Candidate has no expectations (flexible) | 80% |
| No salary data available | 50% |

### 5. Semantic Similarity (10%)

Cosine similarity between candidate and job embeddings:

```python
def calculate_semantic_similarity(self, candidate_embedding, job_embedding) -> float:
    # Cosine similarity = (A · B) / (||A|| * ||B||)
    
    dot_product = sum(a * b for a, b in zip(candidate_embedding, job_embedding))
    magnitude_candidate = sum(a * a for a in candidate_embedding) ** 0.5
    magnitude_job = sum(b * b for b in job_embedding) ** 0.5
    
    cosine_similarity = dot_product / (magnitude_candidate * magnitude_job)
    
    # Normalize to 0-100 scale
    return max(0.0, min(100.0, cosine_similarity * 100.0))
```

### Match Grades

| Grade | Score Range | Meaning |
|-------|-------------|---------|
| A+ | 90-100 | Excellent match |
| A | 80-89 | Very good match |
| B | 70-79 | Good match (recommended) |
| C | 60-69 | Fair match |
| D | 50-59 | Poor match |
| F | <50 | Not recommended |

---

## Workflows

### 1. Job Import Workflow

**Actors:** PM_ADMIN (Platform Administrator)

```
PM_ADMIN uploads JSON file
        │
        ▼
POST /api/jobs/import
        │
        ▼
┌─────────────────────────────────────────────┐
│           JobImportService                  │
├─────────────────────────────────────────────┤
│ 1. Create JobImportBatch record             │
│ 2. Parse JSON file                          │
│ 3. For each job:                            │
│    a. Parse salary (regex patterns)         │
│    b. Parse experience requirements         │
│    c. Normalize skills (synonym mapping)    │
│    d. Extract keywords from description     │
│    e. Detect remote work indicators         │
│    f. Upsert job (update if exists)         │
│ 4. Generate embeddings for new jobs         │
│ 5. Update batch statistics                  │
└─────────────────────────────────────────────┘
        │
        ▼
Jobs stored in job_postings table (GLOBAL)
```

**Supported Platforms:**
- Indeed
- Dice  
- TechFetch
- Glassdoor
- Monster

**JSON Format Example:**
```json
[
  {
    "job_id": "ABC123",
    "title": "Senior Python Developer",
    "company": "TechCorp",
    "location": "San Francisco, CA",
    "salary": "$150K - $180K",
    "description": "We are looking for...",
    "requirements": "5+ years Python experience...",
    "posted_date": "2025-11-15",
    "job_url": "https://indeed.com/job/ABC123"
  }
]
```

### 2. Candidate Match Generation Workflow

**Trigger:** Inngest event `job-match/generate-candidate`

```
Candidate onboarding approved
OR Profile updated
OR Manual trigger
        │
        ▼
Inngest Event: job-match/generate-candidate
{
  "candidate_id": 123,
  "tenant_id": 456,
  "trigger": "onboarding_approval"
}
        │
        ▼
┌─────────────────────────────────────────────┐
│     generate-candidate-matches workflow     │
├─────────────────────────────────────────────┤
│ Step 1: Validate candidate exists           │
│ Step 2: Ensure candidate has embedding      │
│         (generate via Gemini if missing)    │
│ Step 3: Fetch all ACTIVE job postings       │
│ Step 4: Calculate match score for each job  │
│ Step 5: Filter by min_score (default 50)    │
│ Step 6: Store top 50 matches                │
│ Step 7: Update candidate status to          │
│         'ready_for_assignment'              │
└─────────────────────────────────────────────┘
        │
        ▼
CandidateJobMatch records created
```

### 3. Nightly Refresh Workflow

**Schedule:** 2 AM daily (cron)

```
Cron Trigger: 0 2 * * *
        │
        ▼
┌─────────────────────────────────────────────┐
│       nightly-match-refresh workflow        │
├─────────────────────────────────────────────┤
│ Step 1: Fetch all active tenants            │
│ Step 2: For each tenant:                    │
│         - Fetch all active candidates       │
│         - Generate matches (batch_size=10)  │
│         - Rate limit: 5s between tenants    │
│ Step 3: Aggregate statistics                │
│ Step 4: Log results for monitoring          │
└─────────────────────────────────────────────┘
        │
        ▼
All matches refreshed with latest jobs
```

---

## API Endpoints

### Job Import (PM_ADMIN Only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/jobs/import` | Upload JSON file to import jobs |
| GET | `/api/jobs/batches` | List import batch history |
| GET | `/api/jobs/batches/:id` | Get batch details |
| GET | `/api/jobs/stats` | Get overall job statistics |

### Job Matching (Portal Users)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/job-matches/candidates/:id/generate` | Generate matches for candidate |
| POST | `/api/job-matches/generate-all` | Bulk generate for all candidates |
| GET | `/api/job-matches/candidates/:id` | Get candidate's matches |
| GET | `/api/job-matches/candidates/:id/matches/:matchId` | Get specific match details |
| PATCH | `/api/job-matches/:id/status` | Update match status |

### Job Postings (Portal Users)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/job-postings` | List job postings with filters |
| GET | `/api/job-postings/:id` | Get job posting details |
| GET | `/api/job-postings/search` | Search jobs by skills/keywords |
| GET | `/api/job-postings/stats` | Get job statistics |

---

## Configuration

### Environment Variables

```bash
# Google Gemini API (required for embeddings)
GOOGLE_API_KEY=your-gemini-api-key

# PostgreSQL with pgvector extension
DATABASE_URL=postgresql://user:pass@host:5432/blacklight

# Job matching thresholds
JOB_MATCH_MIN_SCORE=50.0
JOB_MATCH_LIMIT=50
```

### Database Setup

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create IVFFlat index for fast similarity search
CREATE INDEX idx_job_posting_embedding 
ON job_postings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

---

## Performance Considerations

### Embedding Generation
- **Rate Limiting:** 0.1s delay between batch requests
- **Batch Size:** Up to 100 texts per API call
- **Retry Logic:** 3 retries with exponential backoff

### Match Generation
- **Default Limit:** 50 matches per candidate
- **Minimum Score:** 50.0 (filters out poor matches)
- **Batch Processing:** 10 candidates per batch for bulk operations

### Vector Search Optimization
- **IVFFlat Index:** 100 lists for ~O(√n) search complexity
- **Cosine Ops:** Optimized for normalized vectors
- **Dimensions:** 768 (Gemini embedding-001 output)

---

## Files Reference

| File | Purpose |
|------|---------|
| `models/job_posting.py` | JobPosting model with embedding |
| `models/candidate_job_match.py` | Match results model |
| `models/job_import_batch.py` | Import tracking model |
| `models/job_application.py` | Application tracking model |
| `services/job_import_service.py` | JSON parsing and import logic |
| `services/job_matching_service.py` | Matching algorithm |
| `services/embedding_service.py` | Gemini embedding generation |
| `inngest/functions/job_matching_tasks.py` | Background workflows |
| `routes/job_import_routes.py` | Import API endpoints |
| `routes/job_match_routes.py` | Matching API endpoints |
| `routes/job_posting_routes.py` | Job listing API endpoints |

---

## Troubleshooting

### Common Issues

1. **"No active jobs found"**
   - Check `job_postings.status = 'ACTIVE'`
   - Verify jobs have been imported

2. **"Embedding generation failed"**
   - Verify `GOOGLE_API_KEY` is set
   - Check API quota limits

3. **Low match scores**
   - Ensure candidate has skills listed
   - Verify job postings have skills extracted
   - Check embedding generation completed

4. **Slow matching**
   - Verify IVFFlat index exists
   - Check number of active jobs (>10,000 may need optimization)
   - Consider increasing batch delay for API rate limits

### Monitoring

Check Inngest dashboard for:
- `nightly-match-refresh` completion status
- `generate-candidate-matches` success rate
- Error logs and retry patterns

---

## Future Improvements & Architecture Recommendations

### 1. Real-Time Job Ingestion Pipeline

**Current State:** Manual JSON upload by PM_ADMIN  
**Problem:** Jobs become stale, manual process doesn't scale

**Recommended Architecture:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                    REAL-TIME JOB INGESTION                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │   Indeed    │     │    Dice     │     │  LinkedIn   │           │
│  │   RSS/API   │     │    API      │     │    API      │           │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘           │
│         │                   │                   │                   │
│         └───────────────────┼───────────────────┘                   │
│                             ▼                                       │
│                  ┌─────────────────────┐                           │
│                  │   Apache Kafka /    │                           │
│                  │   Redis Streams     │                           │
│                  └──────────┬──────────┘                           │
│                             │                                       │
│         ┌───────────────────┼───────────────────┐                   │
│         ▼                   ▼                   ▼                   │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │  Dedup &    │     │  Embedding  │     │   Match     │           │
│  │  Normalize  │     │  Generator  │     │  Trigger    │           │
│  └─────────────┘     └─────────────┘     └─────────────┘           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- Jobs appear within minutes of posting
- Automatic deduplication across platforms
- Triggers re-matching for relevant candidates immediately

**Implementation:**
```python
# Scheduled scrapers (every 15 minutes)
@inngest_client.create_function(
    fn_id="scrape-indeed-jobs",
    trigger=inngest.TriggerCron(cron="*/15 * * * *"),
)
async def scrape_indeed_jobs(ctx):
    # 1. Fetch new jobs from Indeed RSS/API
    # 2. Push to Redis Stream
    # 3. Consumer processes and triggers matching
```

---

### 2. Intelligent Re-Matching (Event-Driven)

**Current State:** Nightly batch refresh for ALL candidates  
**Problem:** Wasteful - most candidates don't need daily refresh

**Recommended Approach: Smart Triggers**

| Event | Action |
|-------|--------|
| New job posted | Match against candidates with relevant skills |
| Candidate updates profile | Re-match only this candidate |
| Candidate views/rejects matches | Learn and adjust future matches |
| Job expires/closes | Remove from candidate matches |

```python
# Instead of nightly refresh for everyone:
@inngest_client.create_function(
    fn_id="smart-match-on-new-job",
    trigger=inngest.TriggerEvent(event="job/created"),
)
async def match_new_job_to_candidates(ctx):
    job = ctx.event.data["job"]
    
    # Find candidates with overlapping skills (using GIN index)
    relevant_candidates = db.session.execute(
        select(Candidate).where(
            Candidate.skills.overlap(job.skills),
            Candidate.status == 'ready_for_assignment'
        )
    ).scalars().all()
    
    # Only match relevant candidates (100s vs 10,000s)
    for candidate in relevant_candidates:
        generate_single_match(candidate, job)
```

---

### 3. Learning-to-Rank (LTR) Model

**Current State:** Static weighted scoring (40% skills, 25% experience, etc.)  
**Problem:** Weights are arbitrary, don't adapt to actual hiring outcomes

**Recommended Approach: ML-Based Ranking**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LEARNING-TO-RANK PIPELINE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Training Data (Historical)           Inference (Real-time)        │
│  ─────────────────────────           ──────────────────────        │
│                                                                     │
│  ┌─────────────────────┐             ┌─────────────────────┐       │
│  │ Positive Examples:  │             │  Candidate Profile  │       │
│  │ - Applied jobs      │             │  + Job Posting      │       │
│  │ - Shortlisted       │             └──────────┬──────────┘       │
│  │ - Hired             │                        │                   │
│  │                     │                        ▼                   │
│  │ Negative Examples:  │             ┌─────────────────────┐       │
│  │ - Rejected matches  │             │   Feature Vector    │       │
│  │ - Ignored matches   │             │   ───────────────   │       │
│  └──────────┬──────────┘             │   • skill_overlap   │       │
│             │                        │   • exp_delta       │       │
│             ▼                        │   • salary_gap      │       │
│  ┌─────────────────────┐             │   • semantic_sim    │       │
│  │   XGBoost / LambdaMART           │   • location_match  │       │
│  │   Ranking Model     │─────────────│   • title_similarity│       │
│  └─────────────────────┘             │   • recency_score   │       │
│                                      └──────────┬──────────┘       │
│                                                 │                   │
│                                                 ▼                   │
│                                      ┌─────────────────────┐       │
│                                      │  Predicted Score    │       │
│                                      │  (Hire Probability) │       │
│                                      └─────────────────────┘       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Feature Engineering:**
```python
def extract_features(candidate, job):
    return {
        # Current features
        'skill_overlap_ratio': len(matched_skills) / len(job.skills),
        'experience_delta': candidate.years - job.experience_min,
        'salary_gap_pct': (candidate.expected - job.salary_max) / job.salary_max,
        'semantic_similarity': cosine_sim(candidate.embedding, job.embedding),
        'location_match': 1 if same_location else 0,
        
        # New features to add
        'title_similarity': fuzzy_match(candidate.title, job.title),
        'job_recency_days': (now - job.posted_date).days,
        'candidate_activity_score': candidate.profile_completeness,
        'industry_match': 1 if same_industry else 0,
        'seniority_alignment': seniority_score(candidate, job),
        
        # Behavioral signals
        'similar_jobs_applied': count_similar_applications(candidate, job),
        'rejection_rate_for_role': historical_rejection_rate(job.title),
    }
```

---

### 4. Two-Stage Retrieval + Ranking

**Current State:** Calculate full match score for ALL jobs  
**Problem:** O(candidates × jobs) doesn't scale

**Recommended: ANN Retrieval → Precise Ranking**

```
Stage 1: Approximate Nearest Neighbor (ANN)           Stage 2: Precise Ranking
────────────────────────────────────────             ─────────────────────────

┌─────────────────────┐                              ┌─────────────────────┐
│ Candidate Embedding │                              │  Top 200 Candidates │
└──────────┬──────────┘                              │  (from Stage 1)     │
           │                                         └──────────┬──────────┘
           ▼                                                    │
┌─────────────────────┐                                         ▼
│   pgvector IVFFlat  │                              ┌─────────────────────┐
│   or Pinecone/Qdrant│──────────────────────────────│  Full Scoring       │
│                     │      Top 200 by              │  (5-factor weighted)│
│   O(√n) lookup      │      semantic similarity     │                     │
└─────────────────────┘                              │  O(200) precise     │
                                                     └──────────┬──────────┘
                                                                │
                                                                ▼
                                                     ┌─────────────────────┐
                                                     │  Top 50 Final       │
                                                     │  Recommendations    │
                                                     └─────────────────────┘
```

**Implementation:**
```python
def generate_matches_two_stage(candidate_id: int):
    candidate = db.session.get(Candidate, candidate_id)
    
    # Stage 1: ANN retrieval (fast, O(√n))
    # Get top 200 semantically similar jobs
    similar_jobs = db.session.execute(
        select(JobPosting)
        .where(JobPosting.status == 'ACTIVE')
        .order_by(JobPosting.embedding.cosine_distance(candidate.embedding))
        .limit(200)
    ).scalars().all()
    
    # Stage 2: Precise ranking (slower, but only 200 jobs)
    scored_matches = []
    for job in similar_jobs:
        score = calculate_full_match_score(candidate, job)  # 5-factor
        scored_matches.append((job, score))
    
    # Return top 50
    return sorted(scored_matches, key=lambda x: x[1], reverse=True)[:50]
```

---

### 5. Candidate-Job Fit Explanation (Explainable AI)

**Current State:** Generic explanations like "Good skills match (4/5 skills)"  
**Problem:** Not actionable for recruiters or candidates

**Recommended: Detailed Reasoning**

```json
{
  "match_score": 87.5,
  "grade": "A",
  "explanation": {
    "summary": "Strong technical fit with minor experience gap",
    
    "strengths": [
      "✅ Has 4 of 5 required skills (Python, AWS, React, PostgreSQL)",
      "✅ Current role 'Senior Engineer' aligns with job seniority",
      "✅ Salary expectation ($140K) within job range ($130K-$160K)",
      "✅ Profile mentions similar projects (microservices, cloud migration)"
    ],
    
    "gaps": [
      "⚠️ Missing Kubernetes experience (required skill)",
      "⚠️ 5 years experience vs 7+ years preferred"
    ],
    
    "recommendations": [
      "💡 Candidate could upskill in Kubernetes (many free resources)",
      "💡 Consider for interview - strong in 4/5 core areas"
    ],
    
    "similar_successful_hires": [
      "John D. - hired at TechCorp with similar profile (6 months ago)",
      "Sarah M. - hired at DataInc with 5 years exp (4 months ago)"
    ]
  }
}
```

---

### 6. Hybrid Search (Semantic + Keyword)

**Current State:** Semantic similarity is just 10% of score  
**Problem:** Missing keyword-based relevance (exact skill matches matter)

**Recommended: Reciprocal Rank Fusion (RRF)**

```python
def hybrid_search(candidate, top_k=100):
    # Query 1: Semantic search (embeddings)
    semantic_results = db.session.execute(
        select(JobPosting.id, JobPosting.embedding.cosine_distance(candidate.embedding).label('distance'))
        .where(JobPosting.status == 'ACTIVE')
        .order_by('distance')
        .limit(top_k)
    ).all()
    
    # Query 2: Keyword search (GIN index on skills)
    keyword_results = db.session.execute(
        select(JobPosting.id, func.array_length(
            func.array_intersect(JobPosting.skills, candidate.skills), 1
        ).label('overlap'))
        .where(JobPosting.status == 'ACTIVE')
        .order_by(desc('overlap'))
        .limit(top_k)
    ).all()
    
    # Reciprocal Rank Fusion
    rrf_scores = {}
    k = 60  # RRF constant
    
    for rank, (job_id, _) in enumerate(semantic_results):
        rrf_scores[job_id] = rrf_scores.get(job_id, 0) + 1 / (k + rank + 1)
    
    for rank, (job_id, _) in enumerate(keyword_results):
        rrf_scores[job_id] = rrf_scores.get(job_id, 0) + 1 / (k + rank + 1)
    
    # Sort by combined RRF score
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
```

---

### 7. Feedback Loop & Continuous Improvement

**Current State:** No feedback collection  
**Problem:** Can't improve without knowing what works

**Recommended: Track Outcomes**

```sql
-- New table: match_feedback
CREATE TABLE match_feedback (
    id SERIAL PRIMARY KEY,
    match_id INT REFERENCES candidate_job_matches(id),
    
    -- User actions
    was_viewed BOOLEAN DEFAULT FALSE,
    was_shortlisted BOOLEAN DEFAULT FALSE,
    was_applied BOOLEAN DEFAULT FALSE,
    was_interviewed BOOLEAN DEFAULT FALSE,
    was_hired BOOLEAN DEFAULT FALSE,
    was_rejected BOOLEAN DEFAULT FALSE,
    
    -- Explicit feedback
    recruiter_rating INT CHECK (rating BETWEEN 1 AND 5),
    candidate_rating INT CHECK (rating BETWEEN 1 AND 5),
    rejection_reason TEXT,
    
    -- Timing
    time_to_view_seconds INT,
    time_to_action_seconds INT,
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Metrics Dashboard:**
- **Precision@K:** Of top 10 recommendations, how many get shortlisted?
- **Recall:** Of all good matches, how many did we surface?
- **Time-to-hire:** Days from match to hire
- **Match-to-apply rate:** % of viewed matches that get applications

---

### 8. Multi-Tenant Job Customization

**Current State:** Jobs are global, all tenants see same jobs  
**Problem:** Different tenants have different focus areas

**Recommended: Tenant Job Preferences**

```python
class TenantJobPreferences(db.Model):
    tenant_id = db.Column(Integer, ForeignKey('tenants.id'))
    
    # Filter preferences
    preferred_platforms = db.Column(ARRAY(String))  # ['dice', 'linkedin']
    blocked_companies = db.Column(ARRAY(String))    # Competitors
    required_remote = db.Column(Boolean)            # Only remote jobs
    
    # Location preferences
    target_locations = db.Column(ARRAY(String))     # ['San Francisco', 'Remote']
    excluded_locations = db.Column(ARRAY(String))   # ['Overseas']
    
    # Salary preferences  
    min_salary_floor = db.Column(Integer)           # Don't show jobs below $80K
    
    # Industry focus
    target_industries = db.Column(ARRAY(String))    # ['Tech', 'Finance']
    target_job_titles = db.Column(ARRAY(String))    # ['Software Engineer', 'DevOps']

# Apply filters during matching
def get_jobs_for_tenant(tenant_id: int):
    prefs = TenantJobPreferences.query.get(tenant_id)
    
    query = select(JobPosting).where(JobPosting.status == 'ACTIVE')
    
    if prefs.preferred_platforms:
        query = query.where(JobPosting.platform.in_(prefs.preferred_platforms))
    
    if prefs.blocked_companies:
        query = query.where(~JobPosting.company.in_(prefs.blocked_companies))
    
    if prefs.min_salary_floor:
        query = query.where(JobPosting.salary_min >= prefs.min_salary_floor)
    
    return db.session.execute(query).scalars().all()
```

---

### 9. Resume-to-Job Direct Matching

**Current State:** Must create candidate profile first  
**Problem:** Slow onboarding, extra steps

**Recommended: Instant Resume Matching**

```
Recruiter uploads resume
         │
         ▼
┌─────────────────────────────────────────┐
│      INSTANT MATCH PREVIEW              │
├─────────────────────────────────────────┤
│                                         │
│  1. Parse resume (spaCy/LLM)            │
│  2. Extract: skills, experience, title  │
│  3. Generate embedding on-the-fly       │
│  4. Run ANN search against jobs         │
│  5. Show top 10 matches BEFORE          │
│     candidate is even created           │
│                                         │
│  "This candidate matches 47 jobs"       │
│  "Top match: Senior Python Dev @ Google"│
│                                         │
└─────────────────────────────────────────┘
         │
         ▼
Recruiter decides to onboard candidate
```

---

### 10. Scalability Roadmap

| Scale | Current | Recommended |
|-------|---------|-------------|
| <10K jobs | PostgreSQL pgvector | ✅ Current setup works |
| 10K-100K jobs | PostgreSQL pgvector + partitioning | Add table partitioning by platform |
| 100K-1M jobs | Dedicated vector DB | Migrate to Pinecone/Qdrant/Weaviate |
| 1M+ jobs | Distributed vector search | Elasticsearch + vector plugin, or Vespa |

**Vector DB Migration Path:**
```python
# Abstract the vector search behind an interface
class VectorSearchProvider(ABC):
    @abstractmethod
    def search(self, embedding: List[float], top_k: int) -> List[int]:
        pass

class PgVectorSearch(VectorSearchProvider):
    def search(self, embedding, top_k):
        return db.session.execute(
            select(JobPosting.id)
            .order_by(JobPosting.embedding.cosine_distance(embedding))
            .limit(top_k)
        ).scalars().all()

class PineconeSearch(VectorSearchProvider):
    def search(self, embedding, top_k):
        results = pinecone_index.query(vector=embedding, top_k=top_k)
        return [match.id for match in results.matches]

# Factory pattern for easy switching
def get_vector_search() -> VectorSearchProvider:
    if settings.VECTOR_DB == 'pinecone':
        return PineconeSearch()
    return PgVectorSearch()
```

---

### Summary: Priority Implementation Order

| Priority | Improvement | Effort | Impact |
|----------|-------------|--------|--------|
| 🔴 High | Event-driven re-matching | Medium | High - saves compute, fresher matches |
| 🔴 High | Two-stage retrieval | Low | High - 10x faster matching |
| 🟡 Medium | Feedback loop & metrics | Medium | High - enables continuous improvement |
| 🟡 Medium | Hybrid search (RRF) | Low | Medium - better keyword relevance |
| 🟡 Medium | Better explanations | Low | Medium - recruiter productivity |
| 🟢 Low | Real-time job ingestion | High | High - requires infrastructure |
| 🟢 Low | Learning-to-rank model | High | Very High - but needs training data |
| 🟢 Low | Tenant job preferences | Medium | Medium - better customization |

---

### Quick Wins (Implement This Week)

1. **Add job recency to scoring** - Penalize jobs older than 30 days
2. **Title similarity matching** - Fuzzy match candidate title to job title
3. **Track match views** - Simple analytics on which matches get clicked
4. **Batch embedding generation** - Generate embeddings for new jobs hourly, not on-demand
5. **Cache hot embeddings** - Redis cache for frequently matched candidates

---

## Phase 2: Candidate-Centric Scrape Queue System

### Overview

The Scrape Queue System is a candidate-driven job discovery engine. Instead of importing random jobs, the system scrapes jobs based on what candidates actually want (their preferred roles).

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Candidate-Centric** | Jobs are scraped based on candidate preferred roles, not random imports |
| **Rotating Queue** | Roles rotate continuously - completed roles go back to end of queue |
| **External Scraping** | Scraping happens outside the server via API (avoids IP blocks) |
| **Sequential Processing** | Jobs processed one at a time with 5s delay (prevents API rate limits) |
| **Layered Matching** | Filter by role → hard filters → soft scoring |

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  CANDIDATE-CENTRIC SCRAPE QUEUE SYSTEM                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. CANDIDATE ONBOARDING                                                    │
│  ───────────────────────                                                    │
│                                                                             │
│  Candidate submits preferred roles during onboarding:                       │
│  ["Python Developer", "Backend Engineer", "Data Engineer"]                  │
│                           │                                                 │
│                           ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │ candidate_preferred_roles                                       │       │
│  │ ──────────────────────────                                      │       │
│  │ tenant_id | candidate_id | role              | normalized_role  │       │
│  │ 7         | 123          | Python Developer  | python_developer │       │
│  │ 7         | 123          | Backend Engineer  | backend_engineer │       │
│  │ 7         | 124          | Data Engineer     | data_engineer    │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                           │                                                 │
│                           ▼ (auto-populates)                               │
│  2. ROTATING SCRAPE QUEUE                                                   │
│  ────────────────────────                                                   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │ scrape_queue (FIFO, Rotating)                                   │       │
│  │ ─────────────────────────────                                   │       │
│  │                                                                 │       │
│  │ id  | normalized_role    | status   | candidate_count          │       │
│  │ 1   | python_developer   | scraping | 15                       │       │
│  │ 2   | backend_engineer   | pending  | 8                        │       │
│  │ 3   | data_engineer      | pending  | 12                       │       │
│  │ ... │ ...                │ pending  │ ...                      │       │
│  │                                                                 │       │
│  │ Queue rotates: completed → goes back to end as pending          │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                           │                                                 │
│                           ▼                                                 │
│  3. EXTERNAL SCRAPER BOT                                                    │
│  ───────────────────────                                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │ Your Scraper Script (Python/Node - runs externally)             │       │
│  │ ──────────────────────────────────────────────────              │       │
│  │                                                                 │       │
│  │ while True:                                                     │       │
│  │     # 1. Get next role from queue                               │       │
│  │     role = GET /api/scrape-queue/next                           │       │
│  │     # Headers: X-Scraper-API-Key: your-key                      │       │
│  │                                                                 │       │
│  │     # 2. Scrape each platform                                   │       │
│  │     for platform in ['linkedin', 'indeed', 'dice', ...]:        │       │
│  │         jobs = scrape_platform(platform, role)                  │       │
│  │                                                                 │       │
│  │         # 3. Upload jobs                                        │       │
│  │         POST /api/scrape-queue/{id}/jobs                        │       │
│  │         Body: { "platform": platform, "jobs": jobs }            │       │
│  │                                                                 │       │
│  │     # 4. Mark complete (or auto-completes when all platforms)   │       │
│  │     POST /api/scrape-queue/{id}/complete                        │       │
│  │                                                                 │       │
│  │     sleep(60)  # Rate limiting between roles                    │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                           │                                                 │
│                           ▼                                                 │
│  4. PROCESSING QUEUE (Sequential with 5s delay)                            │
│  ──────────────────────────────────────────────                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │ Inngest Processing Queue                                        │       │
│  │ ────────────────────────                                        │       │
│  │                                                                 │       │
│  │ Jobs arrive (can be simultaneous):                              │       │
│  │   T+0s: Python Developer (LinkedIn) ──┐                         │       │
│  │   T+2s: Java Developer (Indeed)    ───┼──► Queue                │       │
│  │   T+3s: Python Developer (Dice)    ───┘                         │       │
│  │                                                                 │       │
│  │ Processing (sequential, 5s gap):                                │       │
│  │   T+0s:  Process Python Developer (LinkedIn)                    │       │
│  │   T+10s: [5s delay]                                             │       │
│  │   T+15s: Process Java Developer (Indeed)                        │       │
│  │   T+25s: [5s delay]                                             │       │
│  │   T+30s: Process Python Developer (Dice)                        │       │
│  │                                                                 │       │
│  │ Each process:                                                   │       │
│  │   → Parse & validate jobs                                       │       │
│  │   → Deduplicate against existing                                │       │
│  │   → Store in job_postings                                       │       │
│  │   → Generate embeddings (Gemini API)                            │       │
│  │   → Link to role (role_job_mapping)                             │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                           │                                                 │
│                           ▼                                                 │
│  5. LAYERED MATCHING (When role scraping completes)                        │
│  ──────────────────────────────────────────────────                        │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │ LAYER 1: Role Relevance                                         │       │
│  │ ──────────────────────                                          │       │
│  │ Only jobs from candidate's preferred roles                      │       │
│  │ Input: 500 total jobs → Output: 80 relevant jobs                │       │
│  └────────────────────────────┬────────────────────────────────────┘       │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │ LAYER 2: Hard Filters                                           │       │
│  │ ────────────────────                                            │       │
│  │ • Salary: Job pays within 15% of candidate expectation          │       │
│  │ • Location: Matches preference or remote                        │       │
│  │ • Experience: Candidate qualifies (within range)                │       │
│  │ Input: 80 jobs → Output: 35 jobs                                │       │
│  └────────────────────────────┬────────────────────────────────────┘       │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │ LAYER 3: Soft Scoring                                           │       │
│  │ ───────────────────                                             │       │
│  │ • Skill match score (normalized skills)                         │       │
│  │ • Semantic similarity (embeddings)                              │       │
│  │ • Keyword relevance                                             │       │
│  │ • Remote preference bonus                                       │       │
│  │ • Job recency bonus                                             │       │
│  │ Input: 35 jobs → Output: Ranked top 50 matches                  │       │
│  └────────────────────────────┬────────────────────────────────────┘       │
│                               ▼                                             │
│  6. MATCHES STORED (Silent - no notification)                              │
│  ────────────────────────────────────────────                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │ candidate_job_matches                                           │       │
│  │ ─────────────────────                                           │       │
│  │ candidate_id | job_posting_id | match_score | matched_skills    │       │
│  │ 123          | 456            | 87.5        | [Python, AWS...]  │       │
│  │ 123          | 457            | 82.3        | [Python, React...] │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│  7. QUEUE ROTATION                                                          │
│  ─────────────────                                                          │
│                                                                             │
│  Role "python_developer" completed → Moves back to end of queue            │
│  Queue continues forever, always scraping fresh jobs                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Database Schema

#### Table 1: `candidate_preferred_roles`

Stores preferred roles from candidate onboarding.

```sql
CREATE TABLE candidate_preferred_roles (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    
    -- Role data
    role VARCHAR(255) NOT NULL,              -- Original: "Python Developer"
    normalized_role VARCHAR(255) NOT NULL,   -- Normalized: "python_developer"
    priority INTEGER DEFAULT 1,              -- 1 = primary, 2 = secondary
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(candidate_id, normalized_role)
);

CREATE INDEX idx_cpr_normalized ON candidate_preferred_roles(normalized_role);
CREATE INDEX idx_cpr_tenant ON candidate_preferred_roles(tenant_id);
CREATE INDEX idx_cpr_candidate ON candidate_preferred_roles(candidate_id);
```

#### Table 2: `scrape_queue`

The rotating queue of roles to scrape.

```sql
CREATE TABLE scrape_queue (
    id SERIAL PRIMARY KEY,
    
    -- Role identification
    normalized_role VARCHAR(255) NOT NULL UNIQUE,
    display_role VARCHAR(255) NOT NULL,      -- "Python Developer"
    
    -- Queue status: pending → scraping → completed → (rotates back to pending)
    status VARCHAR(50) DEFAULT 'pending',
    
    -- Platform tracking (which platforms have been scraped this cycle)
    platforms_status JSONB DEFAULT '{
        "linkedin": "pending",
        "glassdoor": "pending",
        "indeed": "pending",
        "techfetch": "pending",
        "monster": "pending",
        "dice": "pending"
    }',
    
    -- Priority & stats
    candidate_count INTEGER DEFAULT 0,       -- How many candidates want this role
    
    -- Location hints (aggregated from candidates)
    location_hints TEXT[],
    
    -- Timing
    last_scraped_at TIMESTAMP,               -- When last full cycle completed
    scrape_started_at TIMESTAMP,             -- When current scrape cycle started
    
    -- Stats
    total_jobs_found INTEGER DEFAULT 0,
    last_error TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sq_status ON scrape_queue(status);
CREATE INDEX idx_sq_pending_fifo ON scrape_queue(status, last_scraped_at ASC NULLS FIRST);
```

#### Table 3: `role_job_mapping`

Links jobs to the role that triggered their scrape.

```sql
CREATE TABLE role_job_mapping (
    id SERIAL PRIMARY KEY,
    scrape_queue_id INTEGER NOT NULL REFERENCES scrape_queue(id) ON DELETE CASCADE,
    job_posting_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    scraped_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(scrape_queue_id, job_posting_id)
);

CREATE INDEX idx_rjm_queue ON role_job_mapping(scrape_queue_id);
CREATE INDEX idx_rjm_job ON role_job_mapping(job_posting_id);
```

#### Table 4: `scraper_api_keys`

API keys for scraper bots (managed by PM_ADMIN).

```sql
CREATE TABLE scraper_api_keys (
    id SERIAL PRIMARY KEY,
    
    -- Key data
    key_hash VARCHAR(255) NOT NULL UNIQUE,   -- SHA256 hash of API key
    key_prefix VARCHAR(10) NOT NULL,         -- First 8 chars for identification
    name VARCHAR(100) NOT NULL,              -- "production-scraper", "backup-scraper"
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Rate limiting
    requests_per_minute INTEGER DEFAULT 60,
    
    -- Stats
    last_used_at TIMESTAMP,
    total_requests INTEGER DEFAULT 0,
    
    -- Audit
    created_by INTEGER REFERENCES pm_admin_users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    revoked_at TIMESTAMP
);
```

#### Table 5: `job_processing_queue`

Queue for sequential job processing with 5s delay.

```sql
CREATE TABLE job_processing_queue (
    id SERIAL PRIMARY KEY,
    
    -- Reference
    scrape_queue_id INTEGER NOT NULL REFERENCES scrape_queue(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',    -- pending, processing, completed, failed
    
    -- Data (stored temporarily)
    jobs_data JSONB NOT NULL,
    jobs_count INTEGER NOT NULL,
    
    -- Timing
    queued_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Error tracking
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

CREATE INDEX idx_jpq_status ON job_processing_queue(status, queued_at ASC);
```

---

### API Endpoints

#### Authentication

All scrape queue endpoints require API key authentication:

```
Header: X-Scraper-API-Key: sk_live_abc123...
```

#### Endpoint 1: `GET /api/scrape-queue/next`

Get the next role to scrape (FIFO - oldest first).

**Response (200):**
```json
{
  "queue_id": 123,
  "normalized_role": "python_developer",
  "display_role": "Python Developer",
  "platforms": {
    "linkedin": "pending",
    "glassdoor": "pending",
    "indeed": "pending",
    "techfetch": "pending",
    "monster": "pending",
    "dice": "pending"
  },
  "location_hints": ["San Francisco, CA", "Remote", "New York, NY"],
  "candidate_count": 15,
  "scrape_started_at": "2025-12-01T10:30:00Z"
}
```

**Response (204 - Queue Empty):**
```json
{
  "message": "No roles pending in queue"
}
```

**Behavior:**
1. Find oldest `pending` role (ORDER BY last_scraped_at ASC NULLS FIRST)
2. Mark status = `scraping`
3. Set scrape_started_at = NOW()
4. Reset platforms_status to all "pending"
5. Return role details

---

#### Endpoint 2: `POST /api/scrape-queue/:id/jobs`

Upload scraped jobs for ONE platform.

**Request:**
```json
{
  "platform": "linkedin",
  "jobs": [
    {
      "external_job_id": "linkedin_abc123",
      "title": "Senior Python Developer",
      "company": "TechCorp",
      "location": "San Francisco, CA",
      "salary_range": "$150K - $180K",
      "description": "We are looking for a senior Python developer...",
      "requirements": "5+ years Python, AWS experience...",
      "job_url": "https://linkedin.com/jobs/abc123",
      "apply_url": "https://linkedin.com/jobs/abc123/apply",
      "posted_date": "2025-11-28",
      "job_type": "Full-time",
      "is_remote": false,
      "experience_required": "5-7 years",
      "skills": ["Python", "AWS", "PostgreSQL", "Docker"]
    }
  ]
}
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "message": "Queued 47 jobs for processing",
  "queue_id": 123,
  "platform": "linkedin",
  "jobs_received": 47,
  "processing_queue_position": 3,
  "platforms_remaining": ["glassdoor", "indeed", "techfetch", "monster", "dice"]
}
```

**Behavior:**
1. Validate queue_id exists and is "scraping"
2. Store jobs in job_processing_queue (for sequential processing)
3. Update platforms_status[platform] = "uploaded"
4. Return queue position

---

#### Endpoint 3: `POST /api/scrape-queue/:id/complete`

Manually mark role scraping as complete.

**Request:**
```json
{
  "total_jobs_found": 127,
  "notes": "All platforms scraped successfully"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Role completed and rotated back to queue",
  "queue_id": 123,
  "next_scrape_position": "end of queue",
  "candidates_to_match": 15
}
```

**Behavior:**
1. Mark status = "completed"
2. Set last_scraped_at = NOW()
3. Trigger candidate matching for this role
4. Rotate: status = "pending" (goes to end of FIFO queue)

---

#### Endpoint 4: `POST /api/scrape-queue/:id/fail`

Report scraping failure.

**Request:**
```json
{
  "platform": "linkedin",
  "error": "IP blocked - rate limited",
  "retry": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Failure recorded, role will retry",
  "queue_id": 123,
  "retry_count": 1,
  "will_retry": true
}
```

**Behavior:**
1. Update platforms_status[platform] = "failed"
2. Set last_error
3. Increment retry_count
4. If retry=true: Keep in queue for retry
5. Send email alert to PM_ADMIN

---

#### Endpoint 5: `GET /api/scrape-queue/status`

Get queue overview (for monitoring).

**Response:**
```json
{
  "queue_stats": {
    "total_roles": 25,
    "pending": 20,
    "scraping": 3,
    "failed": 2
  },
  "processing_queue": {
    "pending": 5,
    "processing": 1,
    "completed_today": 47
  },
  "recent_activity": [
    {
      "queue_id": 123,
      "role": "Python Developer",
      "status": "scraping",
      "platforms_status": {
        "linkedin": "completed",
        "indeed": "processing",
        "dice": "pending"
      },
      "candidate_count": 15
    }
  ]
}
```

---

#### PM_ADMIN Endpoints: API Key Management

**`GET /api/pm-admin/scraper-keys`** - List all API keys

```json
{
  "keys": [
    {
      "id": 1,
      "name": "production-scraper",
      "key_prefix": "sk_live_",
      "is_active": true,
      "last_used_at": "2025-12-01T10:30:00Z",
      "total_requests": 1547,
      "created_at": "2025-11-01T00:00:00Z"
    }
  ]
}
```

**`POST /api/pm-admin/scraper-keys`** - Create new API key

```json
// Request
{ "name": "backup-scraper" }

// Response
{
  "id": 2,
  "name": "backup-scraper",
  "api_key": "sk_live_abc123xyz789...",  // Only shown ONCE
  "message": "Save this key - it won't be shown again"
}
```

**`DELETE /api/pm-admin/scraper-keys/:id`** - Revoke API key

```json
{
  "success": true,
  "message": "API key revoked"
}
```

---

### Inngest Workflows

#### Workflow 1: `process-job-queue`

Processes jobs sequentially with 5s delay.

```python
@inngest_client.create_function(
    fn_id="process-job-queue",
    trigger=inngest.TriggerCron(cron="* * * * *"),  # Every minute
    name="Process Job Queue (Sequential)"
)
async def process_job_queue(ctx):
    """
    Processes pending jobs in queue one at a time with 5s delay.
    Runs every minute, processes as many as possible.
    """
    
    while True:
        # Get next pending job
        next_job = await ctx.step.run(
            "get-next-job",
            get_next_pending_job_step
        )
        
        if not next_job:
            return {"message": "Queue empty", "processed": 0}
        
        # Process the job
        result = await ctx.step.run(
            f"process-{next_job['id']}",
            process_single_job_batch_step,
            next_job
        )
        
        # 5 second delay before next
        await ctx.step.sleep("delay", 5)
        
        # Check if all platforms done for this role
        if result.get("all_platforms_done"):
            await ctx.step.run(
                "trigger-matching",
                trigger_candidate_matching_step,
                next_job["scrape_queue_id"]
            )
```

#### Workflow 2: `match-candidates-for-role`

Matches candidates when a role completes all platforms.

```python
@inngest_client.create_function(
    fn_id="match-candidates-for-role",
    trigger=inngest.TriggerEvent(event="scrape-queue/role-completed"),
    name="Match Candidates for Completed Role"
)
async def match_candidates_for_role(ctx):
    """
    When a role finishes scraping all platforms:
    1. Get all candidates who want this role
    2. Get all jobs scraped for this role
    3. Run layered matching
    4. Store matches (silently)
    5. Rotate role back to queue
    """
    queue_id = ctx.event.data["queue_id"]
    normalized_role = ctx.event.data["normalized_role"]
    
    # Step 1: Get candidates for this role
    candidates = await ctx.step.run("get-candidates", get_candidates_for_role_step, normalized_role)
    
    # Step 2: Get jobs for this role
    jobs = await ctx.step.run("get-jobs", get_jobs_for_role_step, queue_id)
    
    # Step 3: Match each candidate (layered matching)
    total_matches = 0
    for candidate in candidates:
        result = await ctx.step.run(
            f"match-{candidate['id']}",
            run_layered_matching_step,
            candidate,
            jobs
        )
        total_matches += result["matches_created"]
    
    # Step 4: Rotate queue item back to pending
    await ctx.step.run("rotate-queue", rotate_queue_item_step, queue_id)
    
    return {
        "queue_id": queue_id,
        "role": normalized_role,
        "candidates_matched": len(candidates),
        "total_matches_created": total_matches
    }
```

#### Workflow 3: `expire-old-jobs`

Auto-expires jobs older than 30 days.

```python
@inngest_client.create_function(
    fn_id="expire-old-jobs",
    trigger=inngest.TriggerCron(cron="0 3 * * *"),  # 3 AM daily
    name="Auto-Expire Old Jobs"
)
async def expire_old_jobs(ctx):
    """
    Mark jobs as EXPIRED based on WHICHEVER COMES FIRST:
    - 30 days from posted_date (when job was originally posted), OR
    - 30 days from imported_at (when we scraped it)
    
    Logic: expire_date = MIN(posted_date + 30, imported_at + 30)
    If posted_date is NULL, use imported_at only.
    """
    expired_count = await ctx.step.run("expire-jobs", expire_old_jobs_step)
    
    return {
        "jobs_expired": expired_count,
        "expired_at": datetime.utcnow().isoformat()
    }
```

#### Workflow 4: `alert-zero-jobs`

Sends email to PM_ADMIN when scraping returns zero jobs.

```python
@inngest_client.create_function(
    fn_id="alert-zero-jobs-scraped",
    trigger=inngest.TriggerEvent(event="scrape-queue/zero-jobs"),
    name="Alert PM_ADMIN on Zero Jobs"
)
async def alert_zero_jobs(ctx):
    """
    Send email alert when a role scrape returns 0 jobs.
    """
    data = ctx.event.data
    
    await ctx.step.run("send-alert", send_pm_admin_email_step, {
        "subject": f"⚠️ Scrape Alert: Zero jobs for {data['role']}",
        "body": f"""
        Role: {data['role']}
        Platform: {data['platform']}
        Queue ID: {data['queue_id']}
        Time: {datetime.utcnow().isoformat()}
        
        The scraper returned 0 jobs. This may indicate:
        - Platform blocked our scraper
        - Role has very few listings
        - Scraper configuration issue
        
        The role will remain in the queue for retry.
        """
    })
    
    return {"alert_sent": True}
```

---

### Layered Matching Algorithm

```python
class LayeredMatchingService:
    """
    Three-layer matching:
    Layer 1: Role Relevance (filter by preferred role)
    Layer 2: Hard Filters (salary, location, experience)
    Layer 3: Soft Scoring (skills, semantics, keywords)
    """
    
    def match_candidate_to_jobs(
        self, 
        candidate: dict, 
        jobs: list,
        normalized_role: str
    ) -> list:
        """
        Run layered matching for a single candidate.
        
        Args:
            candidate: Candidate data with preferences
            jobs: Jobs scraped for this role
            normalized_role: The role being matched
        
        Returns:
            List of top 50 matches with scores
        """
        
        # LAYER 1: Role Relevance
        # Jobs are already filtered by role (came from role-specific scrape)
        relevant_jobs = jobs
        logger.info(f"Layer 1: {len(relevant_jobs)} jobs for role {normalized_role}")
        
        # LAYER 2: Hard Filters
        filtered_jobs = []
        for job in relevant_jobs:
            if not self._passes_hard_filters(candidate, job):
                continue
            filtered_jobs.append(job)
        
        logger.info(f"Layer 2: {len(filtered_jobs)} jobs passed hard filters")
        
        # LAYER 3: Soft Scoring
        scored_jobs = []
        for job in filtered_jobs:
            score = self._calculate_soft_score(candidate, job)
            scored_jobs.append({
                "job": job,
                "overall_score": score["overall"],
                "skill_match_score": score["skills"],
                "semantic_similarity": score["semantic"],
                "location_score": score["location"],
                "salary_score": score["salary"],
                "recency_score": score["recency"],
                "matched_skills": score["matched_skills"],
                "missing_skills": score["missing_skills"]
            })
        
        # Sort by score, return top 50
        scored_jobs.sort(key=lambda x: x["overall_score"], reverse=True)
        return scored_jobs[:50]
    
    def _passes_hard_filters(self, candidate: dict, job: dict) -> bool:
        """Layer 2: Hard filters (must pass ALL)"""
        
        # Salary filter (15% tolerance)
        if candidate.get("expected_salary_min") and job.get("salary_max"):
            if job["salary_max"] < candidate["expected_salary_min"] * 0.85:
                return False
        
        # Location filter
        if not self._location_matches(candidate, job):
            return False
        
        # Experience filter
        if not self._experience_matches(candidate, job):
            return False
        
        return True
    
    def _location_matches(self, candidate: dict, job: dict) -> bool:
        """Check if job location matches candidate preference"""
        
        # Remote job matches everyone
        if job.get("is_remote"):
            return True
        
        # Candidate wants remote only
        candidate_locations = candidate.get("preferred_locations", [])
        if candidate_locations:
            wants_remote = any("remote" in loc.lower() for loc in candidate_locations)
            if wants_remote and not job.get("is_remote"):
                # Check if job is in any of their other preferred locations
                job_location = (job.get("location") or "").lower()
                for pref_loc in candidate_locations:
                    if pref_loc.lower() != "remote" and pref_loc.lower() in job_location:
                        return True
                return False
        
        return True  # No preference = matches all
    
    def _experience_matches(self, candidate: dict, job: dict) -> bool:
        """Check if candidate experience matches job requirements"""
        
        candidate_years = candidate.get("total_experience_years") or 0
        job_min = job.get("experience_min") or 0
        job_max = job.get("experience_max")
        
        # Candidate below minimum (allow 1 year grace)
        if candidate_years < job_min - 1:
            return False
        
        # No max or candidate within range
        if job_max is None or candidate_years <= job_max + 2:
            return True
        
        return False
    
    def _calculate_soft_score(self, candidate: dict, job: dict) -> dict:
        """Layer 3: Soft scoring (weighted combination)"""
        
        # Weights
        W_SKILLS = 0.35
        W_SEMANTIC = 0.25
        W_LOCATION = 0.15
        W_SALARY = 0.15
        W_RECENCY = 0.10
        
        # Skill match
        skill_score, matched, missing = self._calculate_skill_match(
            candidate.get("skills", []),
            job.get("skills", [])
        )
        
        # Semantic similarity
        semantic_score = self._calculate_semantic_similarity(
            candidate.get("embedding"),
            job.get("embedding")
        )
        
        # Location score
        location_score = self._calculate_location_score(candidate, job)
        
        # Salary score
        salary_score = self._calculate_salary_score(candidate, job)
        
        # Recency score (newer jobs score higher)
        recency_score = self._calculate_recency_score(job)
        
        # Weighted overall
        overall = (
            skill_score * W_SKILLS +
            semantic_score * W_SEMANTIC +
            location_score * W_LOCATION +
            salary_score * W_SALARY +
            recency_score * W_RECENCY
        )
        
        return {
            "overall": round(overall, 2),
            "skills": round(skill_score, 2),
            "semantic": round(semantic_score, 2),
            "location": round(location_score, 2),
            "salary": round(salary_score, 2),
            "recency": round(recency_score, 2),
            "matched_skills": matched,
            "missing_skills": missing
        }
    
    def _calculate_recency_score(self, job: dict) -> float:
        """Newer jobs score higher"""
        posted_date = job.get("posted_date")
        if not posted_date:
            return 50.0
        
        days_old = (datetime.utcnow().date() - posted_date).days
        
        if days_old <= 3:
            return 100.0
        elif days_old <= 7:
            return 90.0
        elif days_old <= 14:
            return 75.0
        elif days_old <= 21:
            return 60.0
        else:
            return 40.0
```

---

### Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| LinkedIn | ✅ Supported | Most restrictive, requires careful rate limiting |
| Glassdoor | ✅ Supported | Good for salary data |
| Indeed | ✅ Supported | Largest job board |
| TechFetch | ✅ Supported | Tech-focused |
| Monster | ✅ Supported | General jobs |
| Dice | ✅ Supported | Tech-focused |

---

### Configuration

#### Environment Variables

```bash
# Job expiration
JOB_EXPIRATION_DAYS=30

# Processing queue
PROCESSING_QUEUE_DELAY_SECONDS=5

# PM_ADMIN email for alerts
PM_ADMIN_ALERT_EMAIL=admin@company.com

# Gemini API (for embeddings)
GOOGLE_API_KEY=your-gemini-api-key
```

---

### File Structure

```
server/app/
├── models/
│   ├── candidate_preferred_role.py    # NEW
│   ├── scrape_queue.py                # NEW
│   ├── role_job_mapping.py            # NEW
│   ├── scraper_api_key.py             # NEW
│   └── job_processing_queue.py        # NEW
├── routes/
│   ├── scrape_queue_routes.py         # NEW: /api/scrape-queue/*
│   └── pm_admin_scraper_routes.py     # NEW: /api/pm-admin/scraper-keys/*
├── services/
│   ├── scrape_queue_service.py        # NEW
│   ├── layered_matching_service.py    # NEW
│   └── role_normalization_service.py  # NEW
├── middleware/
│   └── scraper_auth.py                # NEW: API key validation
├── inngest/functions/
│   ├── scrape_queue_tasks.py          # NEW
│   └── job_expiration_tasks.py        # NEW
└── schemas/
    └── scrape_queue_schema.py         # NEW
```

---

### Monitoring & Alerts

| Event | Action |
|-------|--------|
| Zero jobs scraped | Email PM_ADMIN |
| Scraper API key used after revocation | Log security event |
| Processing queue backlog > 100 | Email PM_ADMIN |
| Role stuck in "scraping" > 1 hour | Email PM_ADMIN |
| Embedding generation failure | Retry 3x, then alert |

---

### Summary

| Feature | Implementation |
|---------|----------------|
| Queue Type | FIFO (oldest first), rotating |
| Platforms | 6: LinkedIn, Glassdoor, Indeed, TechFetch, Monster, Dice |
| Processing | Sequential with 5s delay |
| Matching Trigger | Immediate after role completes |
| Authentication | API keys (PM_ADMIN managed) |
| Zero Jobs | Email alert, keep in queue |
| Notifications | Silent (no candidate notification) |
| Job Expiration | Auto-expire after 30 days |

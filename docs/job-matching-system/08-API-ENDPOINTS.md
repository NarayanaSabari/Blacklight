# Phase 5: API Reference

## Overview

This document covers all REST API endpoints for the Job Matching System, organized by access level and functionality.

---

## Authentication

### Portal Endpoints
- **Header**: `Authorization: Bearer <jwt_token>`
- **Middleware**: `@require_portal_auth`, `@with_tenant_context`

### PM_ADMIN Endpoints
- **Header**: `Authorization: Bearer <jwt_token>`
- **Middleware**: `@require_pm_admin`

### Scraper Endpoints
- **Header**: `X-Scraper-API-Key: <api_key>`
- **Middleware**: `@require_scraper_auth`

---

## Job Import (PM_ADMIN)

### Import Jobs from JSON

```
POST /api/jobs/import
```

Upload JSON file with jobs from external platforms.

**Headers:**
```
Authorization: Bearer <pm_admin_token>
Content-Type: multipart/form-data
```

**Request Body:**
```
file: <JSON file>
platform: "indeed" | "dice" | "linkedin" | "techfetch" | "glassdoor" | "monster"
```

**JSON File Format:**
```json
[
  {
    "job_id": "ABC123",
    "title": "Senior Python Developer",
    "company": "TechCorp",
    "location": "San Francisco, CA",
    "salary": "$150K - $180K",
    "description": "We are looking for a senior Python developer...",
    "requirements": "5+ years Python, AWS experience...",
    "posted_date": "2025-11-15",
    "job_url": "https://indeed.com/job/ABC123",
    "skills": ["Python", "AWS", "PostgreSQL"]
  }
]
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "batch_id": "batch_20251208_143022_abc123",
  "message": "Import started",
  "jobs_received": 47,
  "status_url": "/api/jobs/batches/batch_20251208_143022_abc123"
}
```

---

### Get Import Batch Status

```
GET /api/jobs/batches/{batch_id}
```

**Response (200):**
```json
{
  "batch_id": "batch_20251208_143022_abc123",
  "platform": "indeed",
  "import_status": "completed",
  "total_jobs": 47,
  "new_jobs": 42,
  "updated_jobs": 3,
  "failed_jobs": 2,
  "started_at": "2025-12-08T14:30:22Z",
  "completed_at": "2025-12-08T14:32:15Z",
  "errors": [
    {"job_id": "XYZ789", "error": "Missing required field: title"},
    {"job_id": "DEF456", "error": "Invalid salary format"}
  ]
}
```

---

### List Import Batches

```
GET /api/jobs/batches
```

**Query Parameters:**
- `platform` (optional): Filter by platform
- `status` (optional): Filter by status
- `page` (default: 1)
- `per_page` (default: 20)

**Response (200):**
```json
{
  "batches": [
    {
      "batch_id": "batch_20251208_143022_abc123",
      "platform": "indeed",
      "import_status": "completed",
      "total_jobs": 47,
      "new_jobs": 42,
      "started_at": "2025-12-08T14:30:22Z"
    }
  ],
  "total": 15,
  "page": 1,
  "per_page": 20
}
```

---

### Get Job Statistics

```
GET /api/jobs/stats
```

**Response (200):**
```json
{
  "total_jobs": 12547,
  "active_jobs": 10234,
  "expired_jobs": 2313,
  "by_platform": {
    "indeed": 4521,
    "dice": 3102,
    "linkedin": 2845,
    "techfetch": 1203,
    "glassdoor": 576,
    "monster": 300
  },
  "jobs_with_embedding": 10150,
  "jobs_without_embedding": 84,
  "last_import": "2025-12-08T10:30:00Z"
}
```

---

## Job Postings (Portal)

### List Job Postings

```
GET /api/job-postings
```

**Query Parameters:**
- `status` (default: "active"): Filter by status
- `platform` (optional): Filter by platform
- `skills` (optional): Comma-separated skills
- `location` (optional): Location filter
- `is_remote` (optional): true/false
- `salary_min` (optional): Minimum salary
- `search` (optional): Full-text search
- `page` (default: 1)
- `per_page` (default: 20)

**Response (200):**
```json
{
  "jobs": [
    {
      "id": 456,
      "title": "Senior Python Developer",
      "company": "TechCorp",
      "location": "San Francisco, CA",
      "is_remote": false,
      "salary_range": "$150K - $180K",
      "salary_min": 150000,
      "salary_max": 180000,
      "experience_min": 5,
      "experience_max": 8,
      "skills": ["Python", "AWS", "PostgreSQL", "Docker"],
      "platform": "indeed",
      "posted_date": "2025-12-01",
      "job_url": "https://indeed.com/job/456"
    }
  ],
  "total": 1024,
  "page": 1,
  "per_page": 20
}
```

---

### Get Job Posting Details

```
GET /api/job-postings/{job_id}
```

**Response (200):**
```json
{
  "id": 456,
  "title": "Senior Python Developer",
  "company": "TechCorp",
  "location": "San Francisco, CA",
  "description": "We are looking for a senior Python developer...",
  "requirements": "5+ years Python, AWS experience...",
  "salary_range": "$150K - $180K",
  "salary_min": 150000,
  "salary_max": 180000,
  "experience_required": "5+ years",
  "experience_min": 5,
  "experience_max": null,
  "skills": ["Python", "AWS", "PostgreSQL", "Docker"],
  "keywords": ["backend", "api", "microservices"],
  "is_remote": false,
  "platform": "indeed",
  "external_job_id": "ABC123",
  "job_url": "https://indeed.com/job/456",
  "posted_date": "2025-12-01",
  "imported_at": "2025-12-02T10:30:00Z",
  "status": "active"
}
```

---

### Search Jobs

```
GET /api/job-postings/search
```

**Query Parameters:**
- `q` (required): Search query
- `skills` (optional): Required skills (comma-separated)
- `location` (optional): Location preference
- `page` (default: 1)
- `per_page` (default: 20)

**Response (200):**
```json
{
  "jobs": [...],
  "total": 156,
  "query": "python developer",
  "filters_applied": {
    "skills": ["Python"],
    "location": "San Francisco"
  }
}
```

---

## Job Matching (Portal)

### Generate Matches for Candidate

```
POST /api/job-matches/candidates/{candidate_id}/generate
```

Trigger match generation for a specific candidate.

**Response (202 Accepted):**
```json
{
  "success": true,
  "message": "Match generation started",
  "candidate_id": 123,
  "event_id": "evt_abc123xyz"
}
```

---

### Bulk Generate Matches

```
POST /api/job-matches/generate-all
```

Trigger match generation for all candidates in tenant.

**Request Body (optional):**
```json
{
  "candidate_ids": [123, 456, 789],
  "status_filter": ["approved", "ready_for_assignment"]
}
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "message": "Bulk generation started",
  "candidates_queued": 47
}
```

---

### Get Candidate Matches

```
GET /api/job-matches/candidates/{candidate_id}
```

**Query Parameters:**
- `min_score` (default: 0): Minimum match score
- `status` (optional): Match status filter
- `is_recommended` (optional): true for 70+ scores
- `sort_by` (default: "match_score"): Sorting field
- `sort_order` (default: "desc")
- `page` (default: 1)
- `per_page` (default: 20)

**Response (200):**
```json
{
  "candidate_id": 123,
  "candidate_name": "John Doe",
  "total_matches": 47,
  "matches": [
    {
      "id": 789,
      "job": {
        "id": 456,
        "title": "Senior Python Developer",
        "company": "TechCorp",
        "location": "San Francisco, CA",
        "salary_range": "$150K - $180K",
        "skills": ["Python", "AWS", "PostgreSQL"]
      },
      "match_score": 87.5,
      "grade": "A",
      "skill_match_score": 80.0,
      "experience_match_score": 100.0,
      "location_match_score": 100.0,
      "salary_match_score": 85.0,
      "semantic_similarity": 78.0,
      "matched_skills": ["Python", "AWS"],
      "missing_skills": ["PostgreSQL"],
      "match_reasons": [
        "✅ Strong skill match (2/3 skills)",
        "✅ Experience level matches well",
        "✅ Location match"
      ],
      "is_recommended": true,
      "status": "suggested",
      "matched_at": "2025-12-08T10:30:00Z"
    }
  ],
  "page": 1,
  "per_page": 20
}
```

---

### Get Match Details

```
GET /api/job-matches/candidates/{candidate_id}/matches/{match_id}
```

**Response (200):**
```json
{
  "id": 789,
  "candidate": {
    "id": 123,
    "name": "John Doe",
    "skills": ["Python", "AWS", "React"],
    "experience_years": 5,
    "location": "San Francisco, CA",
    "expected_salary": "$150K - $170K"
  },
  "job": {
    "id": 456,
    "title": "Senior Python Developer",
    "company": "TechCorp",
    "location": "San Francisco, CA",
    "description": "...",
    "requirements": "...",
    "skills": ["Python", "AWS", "PostgreSQL"],
    "salary_min": 150000,
    "salary_max": 180000,
    "experience_min": 5,
    "job_url": "https://indeed.com/job/456"
  },
  "match_score": 87.5,
  "grade": "A",
  "score_breakdown": {
    "skill_match_score": 80.0,
    "experience_match_score": 100.0,
    "location_match_score": 100.0,
    "salary_match_score": 85.0,
    "semantic_similarity": 78.0
  },
  "skill_analysis": {
    "matched": ["Python", "AWS"],
    "missing": ["PostgreSQL"],
    "match_details": {
      "Python": "exact",
      "AWS": "exact"
    }
  },
  "match_reasons": [...],
  "is_recommended": true,
  "status": "suggested",
  "matched_at": "2025-12-08T10:30:00Z",
  "viewed_at": null
}
```

---

### Update Match Status

```
PATCH /api/job-matches/{match_id}/status
```

**Request Body:**
```json
{
  "status": "shortlisted" | "viewed" | "rejected" | "applied"
}
```

**Response (200):**
```json
{
  "id": 789,
  "status": "shortlisted",
  "updated_at": "2025-12-08T11:00:00Z"
}
```

---

## Candidate Jobs (Scrape Queue Mode)

### Get Jobs for Candidate (No Scoring)

```
GET /api/candidates/{candidate_id}/jobs
```

Returns all jobs for candidate's preferred roles without scoring.

**Query Parameters:**
- `page` (default: 1)
- `per_page` (default: 50)

**Response (200):**
```json
{
  "candidate_id": 123,
  "preferred_roles": ["Python Developer", "DevOps Engineer"],
  "total_jobs": 127,
  "jobs": [
    {
      "id": 456,
      "title": "Senior Python Developer",
      "company": "Google",
      "location": "San Francisco, CA",
      "salary_range": "$150K - $180K",
      "posted_date": "2025-12-01",
      "is_remote": false,
      "job_url": "https://linkedin.com/jobs/456",
      "scraped_for_role": "Python Developer"
    }
  ],
  "page": 1,
  "per_page": 50
}
```

---

### Get Matched Jobs for Candidate (With Scoring)

```
GET /api/candidates/{candidate_id}/job-matches
```

Returns all jobs with match scores calculated on-the-fly.

**Query Parameters:**
- `min_score` (default: 0): Filter by minimum score
- `sort_by` (default: "match_score")
- `page` (default: 1)
- `per_page` (default: 50)

**Response (200):**
```json
{
  "candidate_id": 123,
  "total_matches": 127,
  "matches": [
    {
      "job": {
        "id": 456,
        "title": "Senior Python Developer",
        "company": "Google",
        "location": "San Francisco, CA",
        "salary_range": "$150K - $180K",
        "skills": ["Python", "AWS", "PostgreSQL"],
        "job_url": "https://linkedin.com/jobs/456"
      },
      "match_score": 87.5,
      "grade": "A",
      "skill_match_score": 90.0,
      "location_match_score": 100.0,
      "salary_match_score": 85.0,
      "semantic_similarity": 78.5,
      "matched_skills": ["Python", "AWS"],
      "missing_skills": ["PostgreSQL"]
    }
  ],
  "page": 1,
  "per_page": 50
}
```

---

## Scrape Queue (Scraper)

### Get Next Role to Scrape

```
GET /api/scrape-queue/next
```

**Headers:**
```
X-Scraper-API-Key: <api_key>
```

**Response (200):**
```json
{
  "queue_id": 123,
  "canonical_role": "Python Developer",
  "candidate_count": 47,
  "last_scraped_at": "2025-12-06T10:00:00Z"
}
```

**Response (204):** Queue empty

---

### Upload Scraped Jobs

```
POST /api/scrape-queue/{queue_id}/jobs
```

**Headers:**
```
X-Scraper-API-Key: <api_key>
Content-Type: application/json
```

**Request Body:**
```json
{
  "jobs": [
    {
      "external_job_id": "linkedin_abc123",
      "platform": "linkedin",
      "title": "Senior Python Developer",
      "company": "TechCorp",
      "location": "San Francisco, CA",
      "salary_range": "$150K - $180K",
      "description": "We are looking for...",
      "requirements": "5+ years Python...",
      "job_url": "https://linkedin.com/jobs/abc123",
      "posted_date": "2025-12-01",
      "is_remote": false,
      "skills": ["Python", "AWS", "PostgreSQL"]
    }
  ]
}
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "queue_id": 123,
  "jobs_received": 47,
  "new_jobs": 42,
  "updated_jobs": 3,
  "duplicates_skipped": 2,
  "message": "Jobs queued for processing"
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": "Error Type",
  "message": "Human-readable error message",
  "status": 400,
  "details": {
    "field": "Additional context"
  }
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async processing) |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Rate Limited |
| 500 | Server Error |

---

## Rate Limits

| Endpoint Type | Limit |
|---------------|-------|
| Portal API | 100 requests/minute |
| PM_ADMIN API | 60 requests/minute |
| Scraper API | 10 requests/minute |

---

## Next: [09-SCRAPE-QUEUE-SYSTEM.md](./09-SCRAPE-QUEUE-SYSTEM.md) - Scrape Queue Architecture

# Resume Tailor Integration - API Design

## API Overview

All Resume Tailor endpoints are prefixed with `/api/resume-tailor` and require portal authentication.

### Authentication
- **Header**: `Authorization: Bearer <jwt_token>`
- **Middleware**: `@require_portal_auth`, `@with_tenant_context`
- **Permissions**: `resume_tailor.view`, `resume_tailor.create`

---

## Endpoints

### 1. Analyze Resume Against Job

**Start Analysis**

```http
POST /api/resume-tailor/analyze
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "candidate_id": 123,
  "job_posting_id": 456
}
```

**Response (202 Accepted):**
```json
{
  "analysis_id": "uuid-v4",
  "status": "processing",
  "message": "Analysis started",
  "polling_url": "/api/resume-tailor/analyze/uuid-v4"
}
```

---

**Get Analysis Result**

```http
GET /api/resume-tailor/analyze/{analysis_id}
Authorization: Bearer <token>
```

**Response (200 OK - Processing):**
```json
{
  "analysis_id": "uuid-v4",
  "status": "processing",
  "progress": 45,
  "current_step": "extracting_keywords"
}
```

**Response (200 OK - Completed):**
```json
{
  "analysis_id": "uuid-v4",
  "status": "completed",
  "candidate_id": 123,
  "job_posting_id": 456,
  "result": {
    "match_score": 0.72,
    "resume_keywords": ["python", "fastapi", "postgresql", "docker"],
    "job_keywords": ["python", "django", "aws", "kubernetes"],
    "matched_keywords": ["python"],
    "missing_keywords": ["django", "aws", "kubernetes"],
    "extra_keywords": ["fastapi", "postgresql", "docker"],
    "skill_comparison": [
      {
        "skill": "python",
        "resume_count": 8,
        "job_count": 5,
        "status": "matched"
      },
      {
        "skill": "django",
        "resume_count": 0,
        "job_count": 4,
        "status": "missing"
      }
    ],
    "improvement_potential": "high",
    "estimated_improvement": 0.15
  },
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

### 2. Tailor Resume

**Start Tailoring**

```http
POST /api/resume-tailor/tailor
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "candidate_id": 123,
  "job_posting_id": 456,
  "options": {
    "preserve_experience": true,
    "max_iterations": 5,
    "target_score": 0.85,
    "ai_provider": "openai",
    "ai_model": "gpt-4o-mini"
  }
}
```

**Response (202 Accepted):**
```json
{
  "tailor_id": "uuid-v4",
  "status": "processing",
  "message": "Resume tailoring started",
  "stream_url": "/api/resume-tailor/tailor/uuid-v4/stream"
}
```

---

**Get Tailoring Result**

```http
GET /api/resume-tailor/tailor/{tailor_id}
Authorization: Bearer <token>
```

**Response (200 OK - Completed):**
```json
{
  "tailor_id": "uuid-v4",
  "status": "completed",
  "candidate_id": 123,
  "job_posting_id": 456,
  "original": {
    "content_markdown": "# John Doe\n\n## Experience\n...",
    "match_score": 0.72,
    "keywords": ["python", "fastapi", "postgresql"]
  },
  "tailored": {
    "content_markdown": "# John Doe\n\n## Experience\n...(improved)",
    "content_html": "<h1>John Doe</h1>...",
    "match_score": 0.89,
    "keywords": ["python", "django", "aws", "fastapi"]
  },
  "improvements": [
    {
      "section": "Experience",
      "type": "keyword_addition",
      "description": "Added Django framework reference based on prior FastAPI experience",
      "before": "Built REST APIs using FastAPI",
      "after": "Built REST APIs using FastAPI and Django REST Framework"
    },
    {
      "section": "Skills",
      "type": "skill_reorganization",
      "description": "Prioritized AWS and cloud skills to match job requirements",
      "before": "Docker, PostgreSQL, AWS",
      "after": "AWS, Docker, PostgreSQL, Kubernetes basics"
    }
  ],
  "score_improvement": 0.17,
  "iterations_used": 3,
  "processing_duration_seconds": 45,
  "ai_provider": "openai",
  "ai_model": "gpt-4o-mini",
  "created_at": "2025-01-15T10:30:00Z",
  "completed_at": "2025-01-15T10:30:45Z"
}
```

---

**Stream Tailoring Progress (SSE)**

```http
GET /api/resume-tailor/tailor/{tailor_id}/stream
Authorization: Bearer <token>
Accept: text/event-stream
```

**SSE Events:**
```
event: progress
data: {"status": "processing", "step": "parsing_resume", "progress": 10}

event: progress
data: {"status": "processing", "step": "parsing_job", "progress": 20}

event: progress
data: {"status": "processing", "step": "extracting_keywords", "progress": 30}

event: progress
data: {"status": "processing", "step": "calculating_score", "progress": 40, "initial_score": 0.72}

event: progress
data: {"status": "processing", "step": "improving", "progress": 60, "iteration": 1}

event: progress
data: {"status": "processing", "step": "improving", "progress": 70, "iteration": 2}

event: progress
data: {"status": "processing", "step": "calculating_final_score", "progress": 90}

event: completed
data: {"status": "completed", "tailor_id": "uuid-v4", "final_score": 0.89}

event: close
data: {}
```

---

### 3. List Tailored Resumes for Candidate

```http
GET /api/candidates/{candidate_id}/tailored-resumes
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| per_page | int | 10 | Items per page |
| status | string | all | Filter by status (completed, processing, failed) |

**Response (200 OK):**
```json
{
  "tailored_resumes": [
    {
      "id": 1,
      "tailor_id": "uuid-v4",
      "job_posting": {
        "id": 456,
        "title": "Senior Python Developer",
        "company": "TechCorp Inc"
      },
      "original_score": 0.72,
      "tailored_score": 0.89,
      "score_improvement": 0.17,
      "status": "completed",
      "created_at": "2025-01-15T10:30:00Z",
      "created_by": {
        "id": 10,
        "name": "HR Manager"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 5,
    "pages": 1
  }
}
```

---

### 4. Get Tailored Resume Details

```http
GET /api/resume-tailor/{tailor_id}
Authorization: Bearer <token>
```

**Response:** Same as "Get Tailoring Result" above.

---

### 5. Export Tailored Resume

```http
GET /api/resume-tailor/{tailor_id}/export
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| format | string | Yes | Export format: `pdf`, `docx`, `md`, `html` |

**Response (200 OK):**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="john_doe_tailored_resume.pdf"

<binary file content>
```

---

### 6. Apply Tailored Resume

Replace candidate's original resume with tailored version.

```http
POST /api/resume-tailor/{tailor_id}/apply
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "update_parsed_data": true,
  "update_embedding": true,
  "archive_original": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Tailored resume applied to candidate profile",
  "candidate_id": 123,
  "changes": {
    "parsed_data_updated": true,
    "embedding_updated": true,
    "original_archived": true,
    "archived_resume_id": 789
  }
}
```

---

### 7. Delete Tailored Resume

```http
DELETE /api/resume-tailor/{tailor_id}
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Tailored resume deleted"
}
```

---

### 8. Bulk Tailor for Job

Tailor multiple candidates for a single job.

```http
POST /api/resume-tailor/bulk
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "job_posting_id": 456,
  "candidate_ids": [123, 124, 125, 126],
  "options": {
    "max_iterations": 3,
    "ai_provider": "gemini"
  }
}
```

**Response (202 Accepted):**
```json
{
  "bulk_id": "uuid-v4",
  "status": "processing",
  "total_candidates": 4,
  "jobs": [
    { "candidate_id": 123, "tailor_id": "uuid-1", "status": "queued" },
    { "candidate_id": 124, "tailor_id": "uuid-2", "status": "queued" },
    { "candidate_id": 125, "tailor_id": "uuid-3", "status": "queued" },
    { "candidate_id": 126, "tailor_id": "uuid-4", "status": "queued" }
  ],
  "stream_url": "/api/resume-tailor/bulk/uuid-v4/stream"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Bad Request",
  "message": "Candidate does not have a resume uploaded",
  "status": 400,
  "details": {
    "candidate_id": 123,
    "field": "resume_content"
  }
}
```

### 404 Not Found
```json
{
  "error": "Not Found",
  "message": "Tailored resume not found",
  "status": 404,
  "details": {
    "tailor_id": "uuid-v4"
  }
}
```

### 409 Conflict
```json
{
  "error": "Conflict",
  "message": "Tailoring already in progress for this candidate-job pair",
  "status": 409,
  "details": {
    "existing_tailor_id": "uuid-existing",
    "status": "processing"
  }
}
```

### 422 Unprocessable Entity
```json
{
  "error": "Unprocessable Entity",
  "message": "Resume format not supported",
  "status": 422,
  "details": {
    "supported_formats": ["pdf", "docx", "txt", "md"],
    "received_format": "xlsx"
  }
}
```

### 503 Service Unavailable
```json
{
  "error": "Service Unavailable",
  "message": "AI provider is currently unavailable",
  "status": 503,
  "details": {
    "provider": "openai",
    "retry_after_seconds": 30
  }
}
```

---

## Rate Limits

| Endpoint | Rate Limit | Window |
|----------|------------|--------|
| POST /analyze | 30/minute | Per user |
| POST /tailor | 10/minute | Per user |
| POST /bulk | 5/minute | Per tenant |
| GET /stream | 50/minute | Per user |
| GET /export | 20/minute | Per user |

**Rate Limit Response (429 Too Many Requests):**
```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded",
  "status": 429,
  "details": {
    "limit": 10,
    "window_seconds": 60,
    "retry_after_seconds": 45
  }
}
```

---

## Pydantic Schemas

```python
# server/app/schemas/resume_tailor.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class AnalyzeRequest(BaseModel):
    candidate_id: int
    job_posting_id: int

class TailorOptions(BaseModel):
    preserve_experience: bool = True
    max_iterations: int = Field(default=5, ge=1, le=10)
    target_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ai_provider: Optional[str] = Field(default=None, pattern="^(openai|ollama|gemini)$")
    ai_model: Optional[str] = None

class TailorRequest(BaseModel):
    candidate_id: int
    job_posting_id: int
    options: Optional[TailorOptions] = None

class BulkTailorRequest(BaseModel):
    job_posting_id: int
    candidate_ids: List[int] = Field(min_length=1, max_length=50)
    options: Optional[TailorOptions] = None

class SkillComparison(BaseModel):
    skill: str
    resume_count: int
    job_count: int
    status: str  # matched, missing, extra

class Improvement(BaseModel):
    section: str
    type: str  # keyword_addition, skill_reorganization, content_enhancement
    description: str
    before: Optional[str] = None
    after: Optional[str] = None

class TailorResult(BaseModel):
    tailor_id: str
    status: str
    candidate_id: int
    job_posting_id: int
    original: dict
    tailored: dict
    improvements: List[Improvement]
    score_improvement: float
    iterations_used: int
    processing_duration_seconds: int
    ai_provider: str
    ai_model: str
    created_at: datetime
    completed_at: Optional[datetime] = None

class ApplyRequest(BaseModel):
    update_parsed_data: bool = True
    update_embedding: bool = True
    archive_original: bool = True
```

---

**Document Status**: Draft - Pending Approval  
**Last Updated**: 2025-12-14

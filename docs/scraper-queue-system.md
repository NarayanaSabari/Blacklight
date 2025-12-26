# Blacklight Scraper Queue System

## Overview

The Blacklight Scraper Queue is a location-targeted job scraping system designed to efficiently gather job postings from multiple platforms. Instead of scraping per-candidate (which would cause massive duplication), the system scrapes **per-role+location**, benefiting all candidates who need that role in that location.

> **Default Mode**: Role+Location scraping is the primary and recommended mode. Every scrape targets a specific role in a specific location (e.g., "Python Developer in New York").

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SCRAPER QUEUE ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  Candidate   │    │  Candidate   │    │  Candidate   │                  │
│  │  "DevOps"    │    │  "DevOps"    │    │  "DevOps"    │                  │
│  │  NY Location │    │  LA Location │    │  NY Location │                  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                  │
│         │                   │                   │                           │
│         └────────┬──────────┴──────────┬────────┘                           │
│                  ▼                     ▼                                    │
│         ┌───────────────┐     ┌───────────────┐                            │
│         │ DevOps + NY   │     │ DevOps + LA   │   ◄── RoleLocationQueue    │
│         │ (2 candidates)│     │ (1 candidate) │                            │
│         └───────┬───────┘     └───────┬───────┘                            │
│                 │                     │                                     │
│                 └──────────┬──────────┘                                     │
│                            ▼                                                │
│                  ┌──────────────────┐                                       │
│                  │  External Scraper │                                      │
│                  │  (API Key Auth)   │                                      │
│                  └────────┬─────────┘                                       │
│                           │                                                 │
│         ┌─────────────────┼─────────────────┐                              │
│         ▼                 ▼                 ▼                              │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐                          │
│   │ LinkedIn │     │  Indeed  │     │ Monster  │   ◄── ScraperPlatform    │
│   │  Jobs    │     │   Jobs   │     │   Jobs   │                          │
│   └────┬─────┘     └────┬─────┘     └────┬─────┘                          │
│        │                │                │                                  │
│        └────────────────┼────────────────┘                                  │
│                         ▼                                                   │
│              ┌─────────────────────┐                                       │
│              │    Job Postings     │                                       │
│              │  (Deduplicated)     │                                       │
│              └──────────┬──────────┘                                       │
│                         ▼                                                   │
│              ┌─────────────────────┐                                       │
│              │   Job Matching      │   ◄── Triggered via Inngest           │
│              │   (AI-Powered)      │                                       │
│              └─────────────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### 1. Queue Modes

| Mode | Endpoint | Default | Use Case |
|------|----------|---------|----------|
| **Role+Location Queue** | `/api/scraper/queue/next-role-location` | ✅ Yes | Scrape jobs for a role in a specific location (e.g., "Python Developer in New York") |
| **Role Queue (Legacy)** | `/api/scraper/queue/next-role` | ❌ No | Legacy mode - scrapes role globally without location filter |

### 2. Queue Priority

Jobs are processed in order of priority, then by candidate count:

| Priority | Value | Use Case |
|----------|-------|----------|
| `urgent` | 4 | High-value roles, manually escalated |
| `high` | 3 | Roles with many candidates waiting |
| `normal` | 2 | Regular queue processing |
| `low` | 1 | Background refresh for stale roles |

### 3. Queue Status Flow

```
pending → approved → processing → completed
              ↓
           rejected
```

- **pending**: Newly created, awaiting PM_ADMIN approval
- **approved**: Ready for scraping
- **processing**: Currently being scraped
- **completed**: Scraping finished
- **rejected**: Will not be scraped

---

## API Endpoints

### Authentication

All endpoints require the `X-Scraper-API-Key` header:

```bash
curl -H "X-Scraper-API-Key: your-api-key" https://api.example.com/api/scraper/...
```

### Endpoint Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/scraper/queue/next-role-location` | Get next role+location with platform list |
| GET | `/api/scraper/queue/current-session` | Check if scraper has an active session |
| GET | `/api/scraper/queue/location-stats` | Get role+location queue statistics |
| POST | `/api/scraper/queue/jobs` | Submit scraped jobs for a platform |
| POST | `/api/scraper/queue/complete` | Complete the scraping session |

---

## Complete Workflow

### Step 1: Check for Active Session

Before requesting a new role, check if you have an existing session:

```bash
GET /api/scraper/queue/current-session
```

**Response (No Active Session):**
```json
{
    "has_active_session": false,
    "session": null
}
```

**Response (Has Active Session):**
```json
{
    "has_active_session": true,
    "session": {
        "session_id": "a1b2c3d4-...",
        "role_name": "Python Developer",
        "role_id": 42,
        "status": "in_progress",
        "platforms_total": 6,
        "platforms_completed": 2,
        "platforms_failed": 0
    }
}
```

> ⚠️ **Important**: A scraper can only have ONE active session at a time.

### Step 2: Get Next Role+Location from Queue

**Default: Role+Location Scraping**
```bash
GET /api/scraper/queue/next-role-location
```


**Response (200 OK):**
```json
{
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "role": {
        "id": 42,
        "name": "Python Developer",
        "aliases": ["Python Dev", "Python Engineer"],
        "category": "Engineering",
        "candidate_count": 15
    },
    "location": "New York, NY",
    "role_location_queue_id": 123,
    "platforms": [
        { "id": 1, "name": "linkedin", "display_name": "LinkedIn" },
        { "id": 2, "name": "indeed", "display_name": "Indeed" },
        { "id": 3, "name": "monster", "display_name": "Monster" }
    ]
}
```

**Response (204 No Content):** Queue is empty

**Response (409 Conflict):** Already has an active session

### Step 3: Scrape Each Platform

For each platform in the response, scrape jobs using the role name, aliases, and **location**.

**Search Parameters:**
- **Role name**: Primary search term (e.g., "Python Developer")
- **Aliases**: Alternative search terms (e.g., "Python Dev", "Python Engineer")
- **Location**: Geographic filter - always provided (e.g., "New York, NY")

### Step 4: Submit Jobs Per Platform

After scraping each platform, submit the jobs:

**Success Submission:**
```bash
POST /api/scraper/queue/jobs
Content-Type: application/json

{
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "platform": "linkedin",
    "jobs": [
        {
            "external_job_id": "linkedin-123456",
            "title": "Senior Python Developer",
            "company": "TechCorp",
            "location": "New York, NY",
            "job_type": "Full-time",
            "description": "We are looking for...",
            "requirements": ["5+ years Python", "AWS experience"],
            "salary_range": "$150K - $180K",
            "posted_date": "2025-12-25",
            "source_url": "https://linkedin.com/jobs/123456",
            "source_platform": "linkedin"
        }
    ]
}
```

**Failure Report:**
```bash
POST /api/scraper/queue/jobs
Content-Type: application/json

{
    "session_id": "a1b2c3d4-...",
    "platform": "indeed",
    "status": "failed",
    "error_message": "Rate limited - too many requests",
    "jobs": []
}
```

**Response (202 Accepted):**
```json
{
    "status": "accepted",
    "session_id": "a1b2c3d4-...",
    "platform": "linkedin",
    "platform_status": "processing",
    "jobs_count": 47,
    "progress": {
        "total_platforms": 6,
        "completed": 1,
        "pending": 5,
        "failed": 0
    }
}
```

### Step 5: Complete Session

After all platforms have been processed:

```bash
POST /api/scraper/queue/complete
Content-Type: application/json

{
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response (200 OK):**
```json
{
    "status": "completed",
    "session_id": "a1b2c3d4-...",
    "role_name": "Python Developer",
    "location": "New York, NY",
    "summary": {
        "total_platforms": 6,
        "successful_platforms": 5,
        "failed_platforms": 1,
        "failed_platform_details": [
            { "platform": "indeed", "error": "Rate limited" }
        ]
    },
    "jobs": {
        "total_found": 165,
        "total_imported": 158,
        "total_skipped": 7
    },
    "duration_seconds": 450,
    "matching_triggered": true
}
```

---

## Job Schema

When submitting jobs, use this schema:

```typescript
interface Job {
    // Required
    external_job_id: string;     // Unique ID from source platform
    title: string;               // Job title
    company: string;             // Company name
    source_platform: string;     // Platform name (e.g., "linkedin")
    
    // Recommended
    location: string;            // Job location
    description: string;         // Full job description
    source_url: string;          // URL to original posting
    
    // Optional
    job_type: string;            // "Full-time", "Contract", etc.
    salary_range: string;        // e.g., "$150K - $180K"
    requirements: string[];      // List of requirements
    posted_date: string;         // ISO date string
    experience_level: string;    // "Entry", "Mid", "Senior", etc.
}
```

---

## Deduplication

Jobs are deduplicated based on:

1. **External Job ID + Platform**: Same job from same platform is skipped
2. **Company + Title + Location**: Similar jobs from different platforms may be merged

---

## Queue Statistics

### Role+Location Queue Stats

```bash
GET /api/scraper/queue/location-stats
```

```json
{
    "by_status": {
        "pending": 10,
        "approved": 25,
        "processing": 2,
        "completed": 80
    },
    "by_priority": {
        "high": 10,
        "normal": 15
    },
    "total_location_entries": 117,
    "unique_roles": 23,
    "unique_locations": 15,
    "queue_depth": 25
}
```

---

## Error Handling

### Common Error Codes

| Status | Code | Description |
|--------|------|-------------|
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not Found | Session not found |
| 409 | Conflict | Already has an active session |
| 400 | Bad Request | Invalid request body |
| 204 | No Content | Queue is empty |

### Retry Strategy

Recommended retry logic:

```python
RETRY_DELAYS = [1, 2, 5, 10, 30]  # seconds

for attempt, delay in enumerate(RETRY_DELAYS):
    response = make_request()
    
    if response.status_code == 429:  # Rate limited
        time.sleep(delay)
        continue
    elif response.status_code >= 500:  # Server error
        time.sleep(delay)
        continue
    else:
        break
```

---

## Testing

Use the provided test script:

```bash
cd test_scraper/

# Set your API key
export SCRAPER_API_KEY="your-api-key"
export SCRAPER_API_URL="http://localhost"

# View queue stats
python test_scraper_queue.py


# Blacklight Scraper API Documentation

## Overview

The Blacklight Scraper API allows external job scrapers to:
1. Fetch the next role to scrape from the queue
2. Submit scraped jobs for each platform
3. Complete the scraping session

This document provides complete API specifications for integrating your job scraper with the Blacklight platform.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Base URL](#base-url)
3. [Workflow Overview](#workflow-overview)
4. [API Endpoints](#api-endpoints)
   - [Health Check](#1-health-check)
   - [Get Next Role](#2-get-next-role)
   - [Submit Jobs for Platform](#3-submit-jobs-for-platform)
   - [Complete Session](#4-complete-session)
   - [Report Session Failure](#5-report-session-failure)
   - [Get Queue Stats](#6-get-queue-stats)
5. [Admin Endpoints](#admin-endpoints)
   - [Terminate Session](#terminate-session)
6. [Job Object Schema](#job-object-schema)
7. [Error Handling](#error-handling)
8. [Example Implementation](#example-implementation)

---

## Authentication

All API endpoints (except health check) require authentication via the `X-Scraper-API-Key` header.

### Request Header

```
X-Scraper-API-Key: your_api_key_here
```

### Getting an API Key

API keys are created by the PM_ADMIN through the CentralD Dashboard:
1. Navigate to **Scraper Monitoring** → **API Keys**
2. Click **Create New Key**
3. **Store the key securely** - it's only shown once at creation

### Key Format

API keys are 64-character hex strings (e.g., `sk_live_a1b2c3d4e5f6...`).

### Authentication Errors

| HTTP Status | Error | Description |
|-------------|-------|-------------|
| 401 | Missing X-Scraper-API-Key header | No API key provided |
| 401 | Invalid or revoked API key | Key doesn't exist or has been revoked |

---

## Base URL

```
Production: https://your-domain.com/api/scraper
Development: http://localhost:5000/api/scraper
```

---

## Workflow Overview

The scraper follows a 4-step workflow for each role:

```
┌─────────────────────────────────────────────────────────────────┐
│                     SCRAPER WORKFLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. GET /queue/next-role                                        │
│     ↓                                                            │
│     Returns: session_id, role info, platform list                │
│                                                                  │
│  2. For each platform (linkedin, monster, indeed, etc.):        │
│     ├─ Scrape jobs from the platform                            │
│     └─ POST /queue/jobs with scraped jobs                       │
│                                                                  │
│  3. POST /queue/complete                                        │
│     ↓                                                            │
│     Triggers job matching workflow                               │
│                                                                  │
│  4. Repeat from step 1 for next role                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Session Flow Diagram

```
                    ┌─────────────┐
                    │  Start      │
                    └──────┬──────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │  GET /queue/next-role                 │
        │  → Returns session_id + platforms     │
        └──────────────────┬───────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  LinkedIn  │  │  Monster   │  │  Indeed    │  ... (parallel)
    │   Scrape   │  │   Scrape   │  │   Scrape   │
    └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
          │               │               │
          ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ POST /jobs │  │ POST /jobs │  │ POST /jobs │
    │ platform:  │  │ platform:  │  │ platform:  │
    │ "linkedin" │  │ "monster"  │  │ "indeed"   │
    └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
          │               │               │
          └───────────────┴───────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  POST /queue/complete   │
              │  → Triggers matching    │
              └────────────────────────┘
```

---

## API Endpoints

### 1. Health Check

Check if the scraper API is available.

**Endpoint:** `GET /health`

**Authentication:** Not required

**Response:**
```json
{
  "status": "healthy",
  "service": "scraper-api"
}
```

---

### 2. Get Next Role

Fetch the next role from the scraping queue with the list of platforms to scrape.

**Endpoint:** `GET /queue/next-role`

**Authentication:** Required

#### Success Response (200 OK)

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": {
    "id": 42,
    "name": "Python Developer",
    "aliases": ["Python Dev", "Python Engineer", "Python Programmer"],
    "category": "Engineering",
    "candidate_count": 15
  },
  "platforms": [
    { "id": 1, "name": "linkedin", "display_name": "LinkedIn" },
    { "id": 2, "name": "monster", "display_name": "Monster" },
    { "id": 3, "name": "indeed", "display_name": "Indeed" },
    { "id": 4, "name": "dice", "display_name": "Dice" },
    { "id": 5, "name": "glassdoor", "display_name": "Glassdoor" },
    { "id": 6, "name": "techfetch", "display_name": "TechFetch" }
  ]
}
```

#### Empty Queue Response (204 No Content)

Returns empty response with status 204 when no roles are available to scrape.

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | UUID | Unique session identifier - **use this for all subsequent requests** |
| `role.id` | integer | Global role ID |
| `role.name` | string | Role name to search for on job platforms |
| `role.aliases` | string[] | Alternative names for this role (optional search variations) |
| `role.category` | string | Role category (Engineering, Data Science, etc.) |
| `role.candidate_count` | integer | Number of candidates linked to this role |
| `platforms` | array | List of platforms to scrape |
| `platforms[].name` | string | Platform identifier (use in POST /queue/jobs) |
| `platforms[].display_name` | string | Human-readable platform name |

---

### 3. Submit Jobs for Platform

Submit scraped jobs for a specific platform. Call this endpoint once per platform.

**Endpoint:** `POST /queue/jobs`

**Authentication:** Required

#### Request Body (Success Case)

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "platform": "linkedin",
  "jobs": [
    {
      "external_job_id": "3456789012",
      "title": "Senior Python Developer",
      "company": "TechCorp Inc",
      "location": "San Francisco, CA",
      "description": "We are looking for an experienced Python developer...",
      "salary_range": "$120,000 - $180,000",
      "salary_min": 120000,
      "salary_max": 180000,
      "job_type": "Full-time",
      "is_remote": true,
      "posted_date": "2025-12-10",
      "job_url": "https://linkedin.com/jobs/view/3456789012",
      "apply_url": "https://linkedin.com/jobs/view/3456789012/apply",
      "skills": ["Python", "Django", "PostgreSQL", "AWS"],
      "experience_required": "5+ years",
      "requirements": "Bachelor's degree in Computer Science..."
    }
  ]
}
```

#### Request Body (Failure Case)

If scraping a platform fails, report it:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "platform": "indeed",
  "status": "failed",
  "error_message": "Connection timeout after 30 seconds",
  "jobs": []
}
```

#### Success Response (202 Accepted)

```json
{
  "status": "accepted",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "platform": "linkedin",
  "platform_status": "processing",
  "jobs_count": 47,
  "progress": {
    "total_platforms": 6,
    "completed": 0,
    "in_progress": 1,
    "pending": 5,
    "failed": 0
  }
}
```

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | UUID | Yes | Session ID from get-next-role |
| `platform` | string | Yes | Platform name (linkedin, monster, indeed, etc.) |
| `jobs` | array | Yes | Array of job objects (can be empty for failures) |
| `status` | string | No | Set to "failed" if platform scrape failed |
| `error_message` | string | No | Error details if status is "failed" |

---

### 4. Complete Session

Finalize the scraping session after all platforms have submitted. This triggers the job matching workflow.

**Endpoint:** `POST /queue/complete`

**Authentication:** Required

#### Request Body

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Response (200 OK)

```json
{
  "status": "completing",
  "message": "Session completion triggered",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "role_name": "Python Developer",
  "summary": {
    "total_platforms": 6,
    "successful_platforms": 5,
    "failed_platforms": 1,
    "failed_platform_details": [
      { "platform": "indeed", "error": "Connection timeout" }
    ]
  },
  "jobs": {
    "total_found": 165,
    "total_imported": 158,
    "total_skipped": 7
  },
  "matching_triggered": true
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always "completing" (async processing) |
| `summary.total_platforms` | integer | Total platforms in session |
| `summary.successful_platforms` | integer | Platforms that returned jobs |
| `summary.failed_platforms` | integer | Platforms that failed |
| `jobs.total_found` | integer | Total jobs received from scrapers |
| `jobs.total_imported` | integer | New jobs imported (non-duplicates) |
| `jobs.total_skipped` | integer | Duplicate jobs skipped |
| `matching_triggered` | boolean | Whether job matching was triggered |

---

### 5. Report Session Failure

Report a complete session failure (use when scraper cannot continue).

**Endpoint:** `POST /queue/fail`

**Authentication:** Required

#### Request Body

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "error_message": "Network error: Unable to connect to any platform"
}
```

#### Response (200 OK)

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error_message": "Network error: Unable to connect to any platform"
}
```

---

### 6. Get Queue Stats

Get current queue statistics (useful for monitoring).

**Endpoint:** `GET /queue/stats`

**Authentication:** Required

#### Response (200 OK)

```json
{
  "by_status": {
    "pending": 50,
    "processing": 3,
    "completed": 200
  },
  "by_priority": {
    "urgent": 5,
    "high": 15,
    "normal": 30
  },
  "total_pending_candidates": 1234,
  "queue_depth": 50
}
```

---

## Admin Endpoints

These endpoints are for PM_ADMIN users managing scrapers through the CentralD Dashboard.

### Terminate Session

Manually terminate a stuck/hanging session and return the role back to the queue.

**Endpoint:** `POST /api/scraper-monitoring/sessions/{session_id}/terminate`

**Authentication:** PM_ADMIN (via CentralD Dashboard)

**Use Cases:**
- Scraper is stuck or unresponsive
- Testing and debugging scrapers
- Manually clearing a session to allow another scraper to pick up the role

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | UUID | The session ID to terminate |

#### Response (200 OK)

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "terminated",
  "role_id": 42,
  "role_name": "Python Developer",
  "role_returned_to_queue": true,
  "message": "Session terminated. Role 'Python Developer' has been returned to the queue."
}
```

#### Error Responses

| Status | Error | Description |
|--------|-------|-------------|
| 400 | Invalid session ID format | UUID format is invalid |
| 400 | Cannot terminate session | Session is not in 'in_progress' or 'completing' status |
| 404 | Session not found | Session doesn't exist |

#### What Happens When You Terminate

1. The session status changes to `terminated`
2. The error message is set to "Manually terminated by PM_ADMIN"
3. The associated role's `queue_status` is reset to `approved`
4. The role immediately becomes available for another scraper to pick up

---

## Job Object Schema

When submitting jobs, use this schema:

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `external_job_id` | string | Unique job ID from the platform |
| `title` | string | Job title (max 500 chars) |
| `company` | string | Company name (max 255 chars) |
| `description` | string | Full job description |
| `job_url` | string | URL to the job posting |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `location` | string | Job location (e.g., "San Francisco, CA") |
| `salary_range` | string | Salary as displayed (e.g., "$100K - $150K") |
| `salary_min` | integer | Minimum salary (numeric) |
| `salary_max` | integer | Maximum salary (numeric) |
| `salary_currency` | string | Currency code (default: "USD") |
| `job_type` | string | "Full-time", "Contract", "Part-time" |
| `is_remote` | boolean | True if remote work allowed |
| `posted_date` | string | Date posted (ISO format: "YYYY-MM-DD") |
| `expires_at` | string | Expiry date (ISO format) |
| `apply_url` | string | Direct application URL |
| `skills` | string[] | Array of skill keywords |
| `keywords` | string[] | Additional keywords |
| `experience_required` | string | Experience as text (e.g., "3-5 years") |
| `experience_min` | integer | Minimum years (numeric) |
| `experience_max` | integer | Maximum years (numeric) |
| `requirements` | string | Job requirements text |
| `snippet` | string | Short description/snippet |

### Example Complete Job Object

```json
{
  "external_job_id": "monster-12345678",
  "title": "Full Stack Python Developer",
  "company": "Innovation Labs",
  "location": "Austin, TX",
  "description": "We are seeking a talented Full Stack Developer to join our team. You will work on exciting projects using Python, React, and cloud technologies...",
  "snippet": "Seeking a Full Stack Developer for exciting cloud projects...",
  "requirements": "- 5+ years of Python experience\n- Strong React skills\n- AWS certification preferred",
  "salary_range": "$130,000 - $170,000/year",
  "salary_min": 130000,
  "salary_max": 170000,
  "salary_currency": "USD",
  "job_type": "Full-time",
  "is_remote": true,
  "posted_date": "2025-12-10",
  "expires_at": "2026-01-10",
  "job_url": "https://monster.com/job/12345678",
  "apply_url": "https://monster.com/job/12345678/apply",
  "skills": ["Python", "React", "Django", "AWS", "PostgreSQL", "Docker"],
  "keywords": ["full stack", "backend", "frontend", "cloud"],
  "experience_required": "5+ years",
  "experience_min": 5,
  "experience_max": null
}
```

---

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "error": "Error Type",
  "message": "Detailed error message"
}
```

### Common HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Request completed |
| 201 | Created | Resource created |
| 202 | Accepted | Request accepted for async processing |
| 204 | No Content | Queue empty (get-next-role) |
| 400 | Bad Request | Fix request body/parameters |
| 401 | Unauthorized | Check API key |
| 404 | Not Found | Session not found or unauthorized |
| 500 | Internal Error | Retry with exponential backoff |

### Retry Strategy

For transient errors (500, network errors):

```python
import time

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait_time)
```

---

## Example Implementation

### Python Scraper Example

```python
"""
Blacklight Job Scraper - Example Implementation
"""
import requests
import time
from typing import Optional, List, Dict, Any

class BlacklightScraper:
    def __init__(self, api_key: str, base_url: str = "http://localhost:5000/api/scraper"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "X-Scraper-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def get_next_role(self) -> Optional[Dict]:
        """Fetch next role from queue."""
        response = requests.get(
            f"{self.base_url}/queue/next-role",
            headers=self.headers
        )
        
        if response.status_code == 204:
            print("Queue is empty")
            return None
        
        response.raise_for_status()
        return response.json()
    
    def submit_jobs(
        self,
        session_id: str,
        platform: str,
        jobs: List[Dict],
        failed: bool = False,
        error_message: str = None
    ) -> Dict:
        """Submit scraped jobs for a platform."""
        payload = {
            "session_id": session_id,
            "platform": platform,
            "jobs": jobs
        }
        
        if failed:
            payload["status"] = "failed"
            payload["error_message"] = error_message or "Unknown error"
        
        response = requests.post(
            f"{self.base_url}/queue/jobs",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def complete_session(self, session_id: str) -> Dict:
        """Complete the scraping session."""
        response = requests.post(
            f"{self.base_url}/queue/complete",
            headers=self.headers,
            json={"session_id": session_id}
        )
        response.raise_for_status()
        return response.json()
    
    def fail_session(self, session_id: str, error_message: str) -> Dict:
        """Report session failure."""
        response = requests.post(
            f"{self.base_url}/queue/fail",
            headers=self.headers,
            json={
                "session_id": session_id,
                "error_message": error_message
            }
        )
        response.raise_for_status()
        return response.json()


def scrape_platform(platform_name: str, role_name: str) -> List[Dict]:
    """
    Your platform-specific scraping logic goes here.
    This is a placeholder - implement your actual scraping logic.
    """
    # Example: Scrape LinkedIn, Monster, Indeed, etc.
    jobs = []
    
    # ... your scraping code ...
    
    return jobs


def main():
    # Initialize scraper
    scraper = BlacklightScraper(
        api_key="your_api_key_here",
        base_url="http://localhost:5000/api/scraper"
    )
    
    while True:
        # 1. Get next role from queue
        role_data = scraper.get_next_role()
        
        if not role_data:
            print("No more roles to scrape. Waiting 5 minutes...")
            time.sleep(300)
            continue
        
        session_id = role_data["session_id"]
        role = role_data["role"]
        platforms = role_data["platforms"]
        
        print(f"Scraping role: {role['name']} (Session: {session_id})")
        
        # 2. Scrape each platform
        for platform in platforms:
            platform_name = platform["name"]
            print(f"  Scraping {platform['display_name']}...")
            
            try:
                # Scrape jobs from this platform
                jobs = scrape_platform(platform_name, role["name"])
                
                # Submit jobs
                result = scraper.submit_jobs(
                    session_id=session_id,
                    platform=platform_name,
                    jobs=jobs
                )
                print(f"    Submitted {len(jobs)} jobs. Progress: {result['progress']}")
                
            except Exception as e:
                # Report platform failure
                print(f"    Failed: {str(e)}")
                scraper.submit_jobs(
                    session_id=session_id,
                    platform=platform_name,
                    jobs=[],
                    failed=True,
                    error_message=str(e)
                )
        
        # 3. Complete session
        result = scraper.complete_session(session_id)
        print(f"Session completed: {result['jobs']['total_imported']} jobs imported")
        
        # Brief pause before next role
        time.sleep(5)


if __name__ == "__main__":
    main()
```

### Node.js Scraper Example

```javascript
/**
 * Blacklight Job Scraper - Node.js Example
 */
const axios = require('axios');

class BlacklightScraper {
  constructor(apiKey, baseUrl = 'http://localhost:5000/api/scraper') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'X-Scraper-API-Key': apiKey,
        'Content-Type': 'application/json'
      }
    });
  }

  async getNextRole() {
    const response = await this.client.get('/queue/next-role');
    if (response.status === 204) {
      return null;
    }
    return response.data;
  }

  async submitJobs(sessionId, platform, jobs, failed = false, errorMessage = null) {
    const payload = {
      session_id: sessionId,
      platform: platform,
      jobs: jobs
    };

    if (failed) {
      payload.status = 'failed';
      payload.error_message = errorMessage || 'Unknown error';
    }

    const response = await this.client.post('/queue/jobs', payload);
    return response.data;
  }

  async completeSession(sessionId) {
    const response = await this.client.post('/queue/complete', {
      session_id: sessionId
    });
    return response.data;
  }

  async failSession(sessionId, errorMessage) {
    const response = await this.client.post('/queue/fail', {
      session_id: sessionId,
      error_message: errorMessage
    });
    return response.data;
  }
}

// Usage
async function main() {
  const scraper = new BlacklightScraper('your_api_key_here');

  while (true) {
    const roleData = await scraper.getNextRole();

    if (!roleData) {
      console.log('Queue empty. Waiting 5 minutes...');
      await new Promise(resolve => setTimeout(resolve, 300000));
      continue;
    }

    const { session_id, role, platforms } = roleData;
    console.log(`Scraping role: ${role.name}`);

    for (const platform of platforms) {
      try {
        const jobs = await scrapePlatform(platform.name, role.name);
        await scraper.submitJobs(session_id, platform.name, jobs);
        console.log(`  ${platform.display_name}: ${jobs.length} jobs`);
      } catch (error) {
        await scraper.submitJobs(session_id, platform.name, [], true, error.message);
        console.log(`  ${platform.display_name}: Failed - ${error.message}`);
      }
    }

    await scraper.completeSession(session_id);
    console.log('Session completed');
    
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
}

main().catch(console.error);
```

---

## Platform Names Reference

Use these exact platform names when submitting jobs:

| Platform Name | Display Name | Notes |
|---------------|--------------|-------|
| `linkedin` | LinkedIn | LinkedIn Jobs |
| `monster` | Monster | Monster.com |
| `indeed` | Indeed | Indeed.com |
| `dice` | Dice | Dice.com (tech jobs) |
| `glassdoor` | Glassdoor | Glassdoor Jobs |
| `techfetch` | TechFetch | TechFetch.com |

> **Note:** Platforms can be enabled/disabled by PM_ADMIN. Always use the platforms list returned by `GET /queue/next-role`.

---

## Rate Limiting

- Default rate limit: **60 requests per minute** per API key
- Rate limit is configurable per API key by PM_ADMIN
- Exceeding rate limit returns `429 Too Many Requests`

---

## Best Practices

1. **Always use the session_id** from `GET /queue/next-role` for all subsequent requests
2. **Report platform failures** rather than skipping them silently
3. **Submit jobs incrementally** - don't wait to submit all platforms at once
4. **Complete sessions** even if all platforms failed (for proper tracking)
5. **Implement retry logic** for transient network errors
6. **Respect rate limits** - add delays between requests if hitting limits
7. **Extract skills and salary data** when possible for better job matching
8. **Use posted_date** to enable freshness filtering in job matching

---

## Support

For API issues or questions:
- Check the CentralD Dashboard for scraper health metrics
- Review session logs in **Scraper Monitoring** → **Recent Sessions**
- Contact system administrator for API key issues

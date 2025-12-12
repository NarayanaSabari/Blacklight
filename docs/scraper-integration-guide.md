# Scraper Integration Guide

## Overview

This document describes how to build an external job scraper that integrates with the Blacklight job matching system. Scrapers fetch job listings from job boards (Monster, Indeed, LinkedIn, etc.) and submit them to Blacklight for candidate matching.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Job Boards    │         │  External Scraper │         │   Blacklight    │
│   (Monster,     │◀────────│   (Your Code)     │────────▶│   Backend       │
│    Indeed...)   │  Scrape │                   │  API    │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                    │
                                    ▼
                            ┌──────────────────┐
                            │   Workflow:      │
                            │ 1. Get next role │
                            │ 2. Scrape jobs   │
                            │ 3. Submit jobs   │
                            └──────────────────┘
```

## Authentication

All scraper API endpoints require authentication via API key.

### Getting an API Key

1. Login to CentralD Dashboard as PM_ADMIN
2. Navigate to Dashboard → API Keys Manager
3. Click "Create API Key"
4. **Save the key immediately** - it's only shown once!

### Using the API Key

Include the API key in all requests:

```
X-Scraper-API-Key: your-api-key-here
```

## API Endpoints

Base URL: `http://localhost/api/scraper` (or your production URL)

### 1. Get Next Role from Queue

Fetch the next role that needs job scraping.

```http
GET /api/scraper/queue/next-role
X-Scraper-API-Key: your-api-key-here
```

**Success Response (200 OK):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": {
    "id": 123,
    "name": "Python Developer",
    "aliases": ["Python Dev", "Python Engineer", "Senior Python Developer"],
    "category": "Engineering",
    "candidate_count": 50
  }
}
```

**Empty Queue Response (204 No Content):**
No body - queue is empty, wait and retry later.

**Error Response (401 Unauthorized):**
```json
{
  "error": "Unauthorized",
  "message": "Invalid or revoked API key"
}
```

### 2. Submit Jobs for a Role

After scraping jobs from job boards, submit them to Blacklight.

```http
POST /api/scraper/queue/jobs
Content-Type: application/json
X-Scraper-API-Key: your-api-key-here

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "jobs": [
    {
      "job_id": "monster-12345",
      "platform": "monster",
      "title": "Senior Python Developer",
      "company": "TechCorp Inc",
      "location": "San Francisco, CA",
      "description": "Full job description text here...",
      "requirements": "5+ years Python experience, AWS...",
      "salary": "$150,000 - $180,000",
      "job_url": "https://www.monster.com/job/12345",
      "posted_date": "2025-12-10",
      "skills": ["Python", "AWS", "PostgreSQL", "Django", "REST APIs"]
    }
  ]
}
```

**Success Response (200 OK):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "role_name": "Python Developer",
  "jobs_found": 47,
  "jobs_imported": 42,
  "jobs_skipped": 5,
  "duration_seconds": 125,
  "matching_triggered": true
}
```

### 3. Report Session Failure

If scraping fails, report the error so the role can be retried.

```http
POST /api/scraper/queue/fail
Content-Type: application/json
X-Scraper-API-Key: your-api-key-here

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "error_message": "Connection timeout to job board"
}
```

**Success Response (200 OK):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error_message": "Connection timeout to job board"
}
```

### 4. Get Queue Statistics

Check queue status and statistics.

```http
GET /api/scraper/queue/stats
X-Scraper-API-Key: your-api-key-here
```

**Response (200 OK):**
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
    "normal": 30,
    "low": 0
  },
  "total_pending_candidates": 1234,
  "queue_depth": 50
}
```

### 5. Health Check

Check if the scraper API is available (no auth required).

```http
GET /api/scraper/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "scraper-api"
}
```

## Job Object Schema

When submitting jobs, each job object should contain:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `job_id` | string | Yes | Unique ID from the job board (e.g., "monster-12345") |
| `platform` | string | Yes | Source platform: "monster", "indeed", "linkedin", "glassdoor", "dice", "techfetch" |
| `title` | string | Yes | Job title |
| `company` | string | Yes | Company name |
| `location` | string | Yes | Job location (city, state, remote, etc.) |
| `description` | string | Yes | Full job description |
| `requirements` | string | No | Requirements section (can be part of description) |
| `salary` | string | No | Salary range or information |
| `job_url` | string | Yes | Direct URL to the job posting |
| `posted_date` | string | No | Date job was posted (ISO format: YYYY-MM-DD) |
| `skills` | array | No | List of required skills extracted from the job |

## Sample Scraper Implementation (Python)

```python
#!/usr/bin/env python3
"""
Sample Blacklight Job Scraper

This is a template for building a job scraper that integrates with Blacklight.
"""

import requests
import time
import logging
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlacklightScraper:
    def __init__(self, api_key: str, base_url: str = "http://localhost"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "X-Scraper-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def get_next_role(self) -> Optional[Dict]:
        """Fetch the next role from the queue."""
        try:
            response = requests.get(
                f"{self.base_url}/api/scraper/queue/next-role",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 204:
                logger.info("Queue is empty")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get next role: {e}")
            raise
    
    def submit_jobs(self, session_id: str, jobs: List[Dict]) -> Dict:
        """Submit scraped jobs to Blacklight."""
        try:
            response = requests.post(
                f"{self.base_url}/api/scraper/queue/jobs",
                headers=self.headers,
                json={
                    "session_id": session_id,
                    "jobs": jobs
                },
                timeout=60
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to submit jobs: {e}")
            raise
    
    def report_failure(self, session_id: str, error_message: str) -> Dict:
        """Report a scraping failure."""
        try:
            response = requests.post(
                f"{self.base_url}/api/scraper/queue/fail",
                headers=self.headers,
                json={
                    "session_id": session_id,
                    "error_message": error_message
                },
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to report failure: {e}")
            raise
    
    def scrape_jobs_from_platform(self, role_name: str, aliases: List[str]) -> List[Dict]:
        """
        Scrape jobs from job boards.
        
        TODO: Implement your scraping logic here!
        
        This should:
        1. Search for the role name and aliases on job boards
        2. Extract job details (title, company, description, etc.)
        3. Return a list of job objects
        """
        # Example placeholder - replace with actual scraping logic
        jobs = []
        
        # Search using role name and aliases
        search_terms = [role_name] + aliases
        
        for search_term in search_terms[:3]:  # Limit searches
            logger.info(f"Searching for: {search_term}")
            
            # TODO: Add your job board scraping logic here
            # Example for Monster:
            # - Use requests or Selenium to search Monster
            # - Parse job listings
            # - Extract job details
            
            # Placeholder job for testing
            jobs.append({
                "job_id": f"test-{hash(search_term)}",
                "platform": "monster",
                "title": f"Senior {role_name}",
                "company": "Example Corp",
                "location": "Remote",
                "description": f"We are looking for a {role_name} to join our team...",
                "requirements": "5+ years of experience",
                "salary": "$120,000 - $150,000",
                "job_url": "https://example.com/job",
                "posted_date": "2025-12-10",
                "skills": ["Python", "AWS"]
            })
        
        return jobs
    
    def run(self, max_roles: int = 10, sleep_on_empty: int = 60):
        """
        Main scraper loop.
        
        Args:
            max_roles: Maximum number of roles to process before stopping
            sleep_on_empty: Seconds to sleep when queue is empty
        """
        roles_processed = 0
        
        while roles_processed < max_roles:
            try:
                # 1. Get next role from queue
                result = self.get_next_role()
                
                if not result:
                    logger.info(f"Queue empty, sleeping for {sleep_on_empty}s...")
                    time.sleep(sleep_on_empty)
                    continue
                
                session_id = result["session_id"]
                role = result["role"]
                
                logger.info(f"Processing role: {role['name']} (session: {session_id})")
                
                try:
                    # 2. Scrape jobs for this role
                    jobs = self.scrape_jobs_from_platform(
                        role_name=role["name"],
                        aliases=role.get("aliases", [])
                    )
                    
                    logger.info(f"Found {len(jobs)} jobs for {role['name']}")
                    
                    # 3. Submit jobs to Blacklight
                    if jobs:
                        result = self.submit_jobs(session_id, jobs)
                        logger.info(
                            f"Submitted: {result['jobs_imported']} imported, "
                            f"{result['jobs_skipped']} skipped"
                        )
                    else:
                        # Submit empty list to complete session
                        self.submit_jobs(session_id, [])
                        logger.info("No jobs found for this role")
                    
                except Exception as e:
                    # 4. Report failure if scraping fails
                    logger.error(f"Scraping failed: {e}")
                    self.report_failure(session_id, str(e))
                
                roles_processed += 1
                
                # Rate limiting - be nice to job boards
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("Scraper stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(30)
        
        logger.info(f"Scraper finished. Processed {roles_processed} roles.")


if __name__ == "__main__":
    import os
    
    API_KEY = os.environ.get("BLACKLIGHT_SCRAPER_KEY", "your-api-key-here")
    BASE_URL = os.environ.get("BLACKLIGHT_URL", "http://localhost")
    
    scraper = BlacklightScraper(api_key=API_KEY, base_url=BASE_URL)
    scraper.run(max_roles=5)
```

## Scraper Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         SCRAPER LOOP                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ GET /queue/     │
                    │ next-role       │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         204 Empty     200 OK w/ Role   Error
              │              │              │
              ▼              ▼              ▼
        Sleep & Retry   Scrape Jobs    Log & Retry
                             │
                             ▼
                    ┌─────────────────┐
                    │ Scrape job      │
                    │ boards for      │
                    │ role name       │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼                             ▼
         Success                        Failure
              │                             │
              ▼                             ▼
     ┌─────────────────┐          ┌─────────────────┐
     │ POST /queue/    │          │ POST /queue/    │
     │ jobs            │          │ fail            │
     └────────┬────────┘          └────────┬────────┘
              │                             │
              ▼                             ▼
     Jobs imported &              Role returned to
     matching triggered           queue for retry
```

## Best Practices

### 1. Rate Limiting
- Respect job board rate limits
- Add delays between requests (2-5 seconds minimum)
- Use exponential backoff on errors

### 2. Error Handling
- Always report failures via `/queue/fail`
- Include meaningful error messages
- Implement retry logic with backoff

### 3. Job Deduplication
- Use consistent `job_id` format: `{platform}-{board_job_id}`
- Blacklight handles deduplication server-side
- Don't worry about re-submitting the same job

### 4. Skills Extraction
- Extract skills from job descriptions
- Use NLP or keyword matching
- Better skills = better matching

### 5. Monitoring
- Log all API responses
- Monitor success/failure rates
- Set up alerts for failures

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BLACKLIGHT_SCRAPER_KEY` | Your scraper API key | Required |
| `BLACKLIGHT_URL` | Blacklight API base URL | `http://localhost` |

## Testing Your Scraper

### 1. Health Check
```bash
curl http://localhost/api/scraper/health
```

### 2. Get Queue Status
```bash
curl -H "X-Scraper-API-Key: your-key" \
     http://localhost/api/scraper/queue/stats
```

### 3. Test Full Workflow
```bash
# Get next role
curl -H "X-Scraper-API-Key: your-key" \
     http://localhost/api/scraper/queue/next-role

# Submit test jobs (use session_id from above)
curl -X POST \
     -H "X-Scraper-API-Key: your-key" \
     -H "Content-Type: application/json" \
     -d '{"session_id": "your-session-id", "jobs": [{"job_id": "test-1", "platform": "monster", "title": "Python Developer", "company": "Test Corp", "location": "Remote", "description": "Test job", "job_url": "https://example.com"}]}' \
     http://localhost/api/scraper/queue/jobs
```

## Support

For issues or questions:
1. Check backend logs: `docker logs blacklight-backend -f`
2. Check CentralD dashboard for session history
3. Verify API key is active and not revoked

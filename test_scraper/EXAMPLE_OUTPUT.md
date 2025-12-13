# Scraper Simulation - Example Output

This file shows what the scraper simulation produces.

## Example Run

```bash
$ python scraper_simulation.py
```

## Output

### Step 1: API Authentication

```
════════════════════════════════════════════════════════════════════════════════
                        Blacklight Scraper Simulation
════════════════════════════════════════════════════════════════════════════════


→ API Authentication
────────────────────────────────────────────────────────────────────────────────
Enter your Scraper API Key: sk_live_51234567890abcdefghij
✅ API key received: sk_live_...hijkl
```

### Step 2: Server Configuration

```
→ Server Configuration
────────────────────────────────────────────────────────────────────────────────
Enter server URL (default: http://localhost:5000): 
✅ Using server: http://localhost:5000
```

### Step 3: Simulation Configuration

```
→ Simulation Configuration
────────────────────────────────────────────────────────────────────────────────
ℹ️  Server URL: http://localhost:5000
ℹ️  API Key: sk_live_...hijkl
```

### Step 4: Fetch Next Role

```
→ Fetching Next Role from Queue
────────────────────────────────────────────────────────────────────────────────
ℹ️  Sending GET request to: http://localhost:5000/api/scraper/queue/next-role
✅ Successfully fetched next role
ℹ️  Response status: 200

Role Details:
  Session ID:       550e8400-e29b-41d4-a716-446655440000
  Role ID:          42
  Role Title:       Senior Full-Stack Engineer
  Keywords:         Python, JavaScript, React, PostgreSQL, Docker, Kubernetes
  Platforms Count:  3

Available Platforms:
  1. LinkedIn (name: linkedin, priority: 1)
  2. Monster (name: monster, priority: 2)
  3. Indeed (name: indeed, priority: 3)
```

### Step 5: Submit Jobs Per Platform

```
→ Submitting Jobs for All Platforms
────────────────────────────────────────────────────────────────────────────────
ℹ️  Submitting 3 jobs for platform: linkedin
✅ Platform linkedin: Submitted 3 jobs
  Status: completed
  Jobs recorded: 3

ℹ️  Submitting 3 jobs for platform: monster
✅ Platform monster: Submitted 3 jobs
  Status: completed
  Jobs recorded: 3

ℹ️  Submitting 3 jobs for platform: indeed
✅ Platform indeed: Submitted 3 jobs
  Status: completed
  Jobs recorded: 3

✅ Submitted jobs for 3/3 platforms
```

### Step 6: Complete Session

```
→ Completing Session
────────────────────────────────────────────────────────────────────────────────
ℹ️  Marking session as completed: 550e8400-e29b-41d4-a716-446655440000
✅ Session completed successfully
ℹ️  Response: {
  "message": "Session completed successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_jobs_imported": 0,
  "workflow_triggered": true
}
✅ Job matching workflow has been triggered
```

### Step 7: Summary

```
→ Simulation Complete
────────────────────────────────────────────────────────────────────────────────
✅ Scraper simulation workflow completed successfully!
ℹ️  Session ID: 550e8400-e29b-41d4-a716-446655440000
ℹ️  Role ID: 42
ℹ️  Platforms processed: 3
ℹ️  Total jobs submitted: 9

✨ Next Steps:
ℹ️  1. Check the Dashboard for the new session
ℹ️  2. Monitor the Inngest dashboard for workflow execution
ℹ️  3. Verify jobs were imported in the database
ℹ️  4. Check logs: ./deploy.sh logs

✨ Thank you for testing! 🎉
```

---

## Dummy Jobs Generated

Each platform gets 3 jobs like this:

### LinkedIn Job 1
```json
{
  "external_id": "linkedin_job_1702384923_0",
  "title": "Senior Full-Stack Engineer - linkedin",
  "company": "TechCorp",
  "location": "San Francisco, CA",
  "salary_min": 120000,
  "salary_max": 180000,
  "url": "https://linkedin.example.com/job/0",
  "description": "We are looking for a talented Senior Full-Stack Engineer with 5+ years of experience.",
  "posted_date": "2025-12-12T14:23:45.123456"
}
```

### LinkedIn Job 2
```json
{
  "external_id": "linkedin_job_1702384923_1",
  "title": "Senior Full-Stack Engineer - linkedin",
  "company": "Innovation Labs",
  "location": "New York, NY",
  "salary_min": 130000,
  "salary_max": 190000,
  "url": "https://linkedin.example.com/job/1",
  "description": "We are looking for a talented Senior Full-Stack Engineer with 5+ years of experience.",
  "posted_date": "2025-12-12T14:23:45.234567"
}
```

### LinkedIn Job 3
```json
{
  "external_id": "linkedin_job_1702384923_2",
  "title": "Senior Full-Stack Engineer - linkedin",
  "company": "CloudSys",
  "location": "Austin, TX",
  "salary_min": 140000,
  "salary_max": 200000,
  "url": "https://linkedin.example.com/job/2",
  "description": "We are looking for a talented Senior Full-Stack Engineer with 5+ years of experience.",
  "posted_date": "2025-12-12T14:23:45.345678"
}
```

*Similar jobs are generated for Monster and Indeed platforms*

---

## API Requests and Responses

### Request 1: GET /api/scraper/queue/next-role

**Request:**
```http
GET /api/scraper/queue/next-role HTTP/1.1
Host: localhost:5000
X-Scraper-API-Key: sk_live_51234567890abcdefghij
Content-Type: application/json
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "role_id": 42,
  "role_title": "Senior Full-Stack Engineer",
  "keywords": [
    "Python",
    "JavaScript",
    "React",
    "PostgreSQL",
    "Docker",
    "Kubernetes"
  ],
  "platforms": [
    {
      "id": 1,
      "name": "linkedin",
      "display_name": "LinkedIn",
      "icon": "briefcase",
      "priority": 1
    },
    {
      "id": 2,
      "name": "monster",
      "display_name": "Monster Jobs",
      "icon": "briefcase",
      "priority": 2
    },
    {
      "id": 3,
      "name": "indeed",
      "display_name": "Indeed",
      "icon": "briefcase",
      "priority": 3
    }
  ],
  "platform_count": 3
}
```

### Request 2: POST /api/scraper/queue/jobs (LinkedIn)

**Request:**
```http
POST /api/scraper/queue/jobs HTTP/1.1
Host: localhost:5000
X-Scraper-API-Key: sk_live_51234567890abcdefghij
Content-Type: application/json

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "platform_id": 1,
  "platform_name": "linkedin",
  "jobs": [
    {
      "external_id": "linkedin_job_1702384923_0",
      "title": "Senior Full-Stack Engineer - linkedin",
      "company": "TechCorp",
      "location": "San Francisco, CA",
      "salary_min": 120000,
      "salary_max": 180000,
      "url": "https://linkedin.example.com/job/0",
      "description": "We are looking for a talented Senior Full-Stack Engineer with 5+ years of experience.",
      "posted_date": "2025-12-12T14:23:45.123456"
    },
    {
      "external_id": "linkedin_job_1702384923_1",
      "title": "Senior Full-Stack Engineer - linkedin",
      "company": "Innovation Labs",
      "location": "New York, NY",
      "salary_min": 130000,
      "salary_max": 190000,
      "url": "https://linkedin.example.com/job/1",
      "description": "We are looking for a talented Senior Full-Stack Engineer with 5+ years of experience.",
      "posted_date": "2025-12-12T14:23:45.234567"
    },
    {
      "external_id": "linkedin_job_1702384923_2",
      "title": "Senior Full-Stack Engineer - linkedin",
      "company": "CloudSys",
      "location": "Austin, TX",
      "salary_min": 140000,
      "salary_max": 200000,
      "url": "https://linkedin.example.com/job/2",
      "description": "We are looking for a talented Senior Full-Stack Engineer with 5+ years of experience.",
      "posted_date": "2025-12-12T14:23:45.345678"
    }
  ],
  "job_count": 3
}
```

**Response:**
```json
{
  "message": "Jobs submitted successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "platform_id": 1,
  "platform_name": "linkedin",
  "jobs_submitted": 3,
  "status": "completed"
}
```

### Request 3: POST /api/scraper/queue/complete

**Request:**
```http
POST /api/scraper/queue/complete HTTP/1.1
Host: localhost:5000
X-Scraper-API-Key: sk_live_51234567890abcdefghij
Content-Type: application/json

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_status": "completed"
}
```

**Response:**
```json
{
  "message": "Session completed successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_jobs_imported": 0,
  "workflow_triggered": true
}
```

---

## Timeline

```
T+0.0s:  Start simulation
T+0.1s:  Prompt for API key
T+0.5s:  Prompt for server URL
T+0.6s:  Fetch next role from queue
T+0.7s:  Receive role with 3 platforms
T+0.8s:  Generate dummy jobs for each platform
T+0.9s:  Submit jobs for LinkedIn (3 jobs)
T+1.0s:  Submit jobs for Monster (3 jobs)
T+1.1s:  Submit jobs for Indeed (3 jobs)
T+1.2s:  Complete session
T+1.3s:  Inngest workflow triggered
T+1.4s:  Complete!
```

**Total Execution Time:** ~1.4 seconds

---

## Error Scenarios

### Invalid API Key
```
Enter your Scraper API Key: invalid_key
✅ API key received: invalid_...
...
❌ Unauthorized - invalid API key
```

### Server Not Running
```
❌ Connection error - cannot connect to http://localhost:5000
```

### No Roles in Queue
```
⚠️  No roles in queue - check if queue has data
ℹ️  Response: {
  "error": "No roles",
  "message": "No roles available in the queue"
}
```

### Network Timeout
```
❌ Request timeout - server not responding
```

---

## Verification Steps

After running the simulation, verify success:

### 1. Check Logs
```bash
./deploy.sh logs | grep -i "job\|import\|session"
```

### 2. Check Database
```bash
psql -U blacklight -d blacklight -c "
  SELECT session_id, status, created_at FROM scrape_sessions 
  WHERE session_id = '550e8400-e29b-41d4-a716-446655440000';
"
```

### 3. Check Inngest Dashboard
```
http://localhost:8288
Look for: email/* and job-matching/* workflows
```

### 4. Check Dashboard UI
```
Open: http://localhost:3000
Navigate to: Dashboard → Recent Sessions
```

---

This example demonstrates a successful end-to-end test of the scraper queue system.

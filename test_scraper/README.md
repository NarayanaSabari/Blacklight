# Blacklight Scraper Simulation Test

This directory contains a test script that simulates a real job scraper for testing the Blacklight queue system.

## Overview

The `scraper_simulation.py` script:
1. **Authenticates** using a Scraper API Key
2. **Fetches** the next role from the queue
3. **Generates** dummy job listings for each platform
4. **Submits** jobs platform-by-platform
5. **Completes** the session and triggers job matching

## Quick Start

### Prerequisites
```bash
pip install requests
```

### Basic Usage (Interactive)
```bash
cd test_scraper
python scraper_simulation.py
# Then enter your API key when prompted
```

### Advanced Usage

**With API key as argument:**
```bash
python scraper_simulation.py --api-key your-scraper-api-key-here
```

**With custom server URL:**
```bash
python scraper_simulation.py --server http://api.example.com:5000
```

**Skip session completion:**
```bash
python scraper_simulation.py --skip-complete
```

**Combined options:**
```bash
python scraper_simulation.py \
  --api-key your-key \
  --server http://localhost:5000 \
  --skip-complete
```

## Getting Your API Key

1. Open CentralD Dashboard
2. Navigate to Settings → Scraper API Keys
3. Create a new key or copy an existing one
4. Use this key with the simulation script

## Workflow Simulation

### Step 1: Fetch Next Role
```
GET /api/scraper/queue/next-role
Headers: X-Scraper-API-Key: <your-key>

Returns:
- session_id (UUID for tracking)
- role_id (the job role to fill)
- role_title (human-readable title)
- keywords (search terms)
- platforms (list of active platforms to scrape)
```

**Output Example:**
```
Session ID:       550e8400-e29b-41d4-a716-446655440000
Role ID:          123
Role Title:       Senior Software Engineer
Keywords:         Python, Flask, PostgreSQL
Platforms Count:  3

Available Platforms:
  1. LinkedIn (name: linkedin, priority: 1)
  2. Monster (name: monster, priority: 2)
  3. Indeed (name: indeed, priority: 3)
```

### Step 2: Submit Jobs Per Platform
```
POST /api/scraper/queue/jobs
Headers: X-Scraper-API-Key: <your-key>

Payload:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "platform_id": 1,
  "platform_name": "linkedin",
  "jobs": [
    {
      "external_id": "linkedin_job_1234567_0",
      "title": "Senior Software Engineer - linkedin",
      "company": "TechCorp",
      "location": "San Francisco, CA",
      "salary_min": 120000,
      "salary_max": 180000,
      "url": "https://linkedin.example.com/job/0"
    }
    // ... more jobs
  ],
  "job_count": 3
}
```

**Output Example:**
```
✅ Platform linkedin: Submitted 3 jobs
ℹ️  Status: completed
ℹ️  Jobs recorded: 3
```

### Step 3: Complete Session
```
POST /api/scraper/queue/complete
Headers: X-Scraper-API-Key: <your-key>

Payload:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_status": "completed"
}

Response:
{
  "message": "Session completed successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_jobs_imported": 9,
  "workflow_triggered": true
}
```

## Dummy Data Generated

The script generates realistic-looking dummy jobs:

- **Job ID**: Platform-specific format with timestamp
- **Title**: Position title relevant to the role
- **Company**: Random from realistic company names
- **Location**: Various US locations or Remote
- **Salary**: Realistic range for the position
- **URL**: Platform-specific URL format
- **Description**: Generic job description
- **Posted Date**: Current timestamp

Example dummy job:
```json
{
  "external_id": "linkedin_job_1702384923_0",
  "title": "Senior Software Engineer - linkedin",
  "company": "TechCorp",
  "location": "San Francisco, CA",
  "salary_min": 120000,
  "salary_max": 180000,
  "url": "https://linkedin.example.com/job/0",
  "description": "We are looking for a talented Senior Software Engineer with 5+ years of experience.",
  "posted_date": "2025-12-12T14:15:23.123456"
}
```

## Output Colors

The script uses colored output for better readability:
- 🟢 **Green**: Success messages
- 🔵 **Blue**: Info messages
- 🟡 **Yellow**: Warnings and prompts
- 🔴 **Red**: Errors
- 🔷 **Cyan**: Data/values

## Database Verification

After running the simulation, verify in the database:

```bash
# Connect to database
psql -U blacklight -d blacklight -h localhost

# Check session was created
SELECT * FROM scrape_sessions WHERE session_id = '550e8400-e29b-41d4-a716-446655440000';

# Check platform statuses
SELECT * FROM session_platform_status WHERE session_id = '550e8400-e29b-41d4-a716-446655440000';

# Check jobs were imported
SELECT COUNT(*) FROM job_postings WHERE created_at > NOW() - INTERVAL '1 minute';
```

## Troubleshooting

### "Connection error - cannot connect to http://localhost:5000"
- Ensure backend server is running: `./deploy.sh start`
- Verify the server URL is correct
- Check logs: `./deploy.sh logs`

### "Unauthorized - invalid API key"
- Verify the API key is correct
- Generate a new key in CentralD Dashboard
- Check the key hasn't expired

### "No roles in queue"
- Create a role first via the Dashboard
- Or seed the database: `python manage.py seed-roles`
- Check the role status: `SELECT * FROM global_roles;`

### Request timeout
- Check if server is under heavy load
- Verify network connectivity
- Try increasing timeout in code

### Jobs not appearing in database
- Check if migration was applied: `python manage.py migrate`
- Verify Inngest workflows are running
- Check logs: `./deploy.sh logs`

## Monitoring

### Watch Backend Logs
```bash
./deploy.sh logs -f app
```

### Monitor Inngest Workflows
```
Open: http://localhost:8288
Look for: email/* and job-matching/* workflows
```

### Check Database
```bash
# Monitor session status
psql -U blacklight -d blacklight -c "
  SELECT id, session_id, status, created_at FROM scrape_sessions 
  ORDER BY created_at DESC LIMIT 10;
"

# Check platform status
psql -U blacklight -d blacklight -c "
  SELECT session_id, platform_name, status, jobs_submitted, created_at 
  FROM session_platform_status 
  ORDER BY created_at DESC LIMIT 20;
"
```

## Advanced Testing

### Test Multiple Platforms
Run the script multiple times to test with different platform combinations:
```bash
for i in {1..5}; do
  python scraper_simulation.py --api-key your-key
  sleep 2
done
```

### Test Error Handling
Try invalid inputs:
- Wrong API key
- Invalid server URL
- Non-existent session ID
- Malformed JSON

### Performance Testing
```bash
# Time how long submission takes
time python scraper_simulation.py --api-key your-key

# Run concurrent simulations
for i in {1..5}; do
  python scraper_simulation.py --api-key your-key &
done
wait
```

## API Endpoints Being Tested

1. **GET /api/scraper/queue/next-role**
   - Returns next role to scrape + active platforms
   - Authentication: X-Scraper-API-Key

2. **POST /api/scraper/queue/jobs**
   - Submit jobs for a specific platform
   - Authentication: X-Scraper-API-Key

3. **POST /api/scraper/queue/complete**
   - Mark session as complete
   - Triggers job matching
   - Authentication: X-Scraper-API-Key

## Expected Flow

```
Start
  ↓
Authenticate with API Key ✓
  ↓
Fetch Next Role (includes platforms) ✓
  ↓
For Each Platform:
  ├─ Generate Dummy Jobs
  ├─ Submit Jobs
  └─ Verify Success ✓
  ↓
Complete Session ✓
  ↓
Trigger Job Matching Workflow
  ↓
Success! 🎉
```

## Next Steps After Testing

1. **Verify in Dashboard**
   - Check CentralD Dashboard
   - Look for imported jobs
   - Verify job matching results

2. **Check Database**
   - Verify data integrity
   - Check relationships
   - Monitor performance

3. **Monitor Workflows**
   - Open Inngest dashboard
   - Watch job import workflow
   - Verify job matching triggered

4. **Run End-to-End Tests**
   - Test with real scraper
   - Test error scenarios
   - Test with multiple platforms

## Support

For issues or questions:
1. Check troubleshooting section
2. Review backend logs: `./deploy.sh logs`
3. Check Inngest dashboard: http://localhost:8288
4. Review code comments in `scraper_simulation.py`

---

**Test Directory**: `/Users/sabari/Developer/freelancing/Aravind/Blacklight/test_scraper/`

**Script**: `scraper_simulation.py`

**Requirements**: `requests` library (pip install requests)

**Last Updated**: December 12, 2025

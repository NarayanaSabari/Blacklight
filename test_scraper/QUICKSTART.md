# Quick Start: Testing the Scraper

## 60-Second Setup

### 1. Install Dependencies
```bash
cd test_scraper
pip install -r requirements.txt
```

### 2. Get Your API Key
1. Open CentralD Dashboard
2. Go to Settings → Scraper API Keys
3. Copy a key or create a new one

### 3. Run the Simulation
```bash
python scraper_simulation.py
# Enter your API key when prompted
```

## What Happens

1. **Fetch Next Role**: Gets a job role from the queue
2. **Get Platforms**: List of all active scraping platforms
3. **Generate Jobs**: Creates 3 dummy jobs per platform
4. **Submit Jobs**: Posts jobs for each platform
5. **Complete Session**: Finishes and triggers job matching

## Expected Output

```
════════════════════════════════════════════════════════════════════════════════
                        Blacklight Scraper Simulation
════════════════════════════════════════════════════════════════════════════════

→ API Authentication
────────────────────────────────────────────────────────────────────────────────
Enter your Scraper API Key: ••••••••••••••••••••••••••••••••••••••••••••••••••••
✅ API key received: 123456...abcde

→ Fetching Next Role from Queue
────────────────────────────────────────────────────────────────────────────────
ℹ️  Sending GET request to: http://localhost:5000/api/scraper/queue/next-role
✅ Successfully fetched next role

Role Details:
  Session ID:       550e8400-e29b-41d4-a716-446655440000
  Role ID:          123
  Role Title:       Senior Software Engineer
  Keywords:         Python, Flask, PostgreSQL
  Platforms Count:  3

Available Platforms:
  1. LinkedIn (name: linkedin, priority: 1)
  2. Monster (name: monster, priority: 2)
  3. Indeed (name: indeed, priority: 3)

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

→ Completing Session
────────────────────────────────────────────────────────────────────────────────
ℹ️  Marking session as completed: 550e8400-e29b-41d4-a716-446655440000
✅ Session completed successfully
✅ Job matching workflow has been triggered

→ Simulation Complete
────────────────────────────────────────────────────────────────────────────────
✅ Scraper simulation workflow completed successfully!

Next Steps:
1. Check the Dashboard for the new session
2. Monitor the Inngest dashboard for workflow execution
3. Verify jobs were imported in the database
4. Check logs: ./deploy.sh logs

✨ Thank you for testing! 🎉
```

## Command Options

### Interactive Mode (Recommended)
```bash
python scraper_simulation.py
```

### Provide API Key
```bash
python scraper_simulation.py --api-key your-key-here
```

### Custom Server
```bash
python scraper_simulation.py --server http://api.example.com:5000
```

### Skip Final Completion
```bash
python scraper_simulation.py --skip-complete
```

### Combined
```bash
python scraper_simulation.py \
  --api-key your-key \
  --server http://localhost:5000
```

## Verify It Worked

### 1. Check Backend Logs
```bash
./deploy.sh logs -f app
# Look for job import entries
```

### 2. Check Inngest Dashboard
```
http://localhost:8288
```

### 3. Check Database
```bash
psql -U blacklight -d blacklight -c "
  SELECT * FROM scrape_sessions ORDER BY created_at DESC LIMIT 1;
"
```

### 4. Check Dashboard UI
- Open CentralD Dashboard
- Look for imported jobs
- Verify session status

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection error | Check if `./deploy.sh start` is running |
| Unauthorized | Verify API key from Settings → Scraper API Keys |
| No roles | Create a role first in the Dashboard |
| Timeout | Server might be busy, try again |

## Files

- `scraper_simulation.py` - Main test script (600+ lines)
- `README.md` - Detailed documentation
- `requirements.txt` - Python dependencies
- `QUICKSTART.md` - This file

## Real-World Usage

This script demonstrates what a real scraper should do:

1. **Authenticate** with API key
2. **Fetch** next role and platforms
3. **Scrape** job data (we simulate with dummy data)
4. **Submit** jobs for each platform
5. **Complete** session to trigger matching

Your real scraper should follow this exact pattern!

## Next Steps

After successful test:

1. **Integration Test**: Run your real scraper
2. **Database Verify**: Check data integrity
3. **Workflow Monitor**: Watch Inngest execute
4. **Performance Test**: Load test with multiple runs
5. **Error Handling**: Test failure scenarios

---

**Ready? Run**: `python scraper_simulation.py`

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                    BLACKLIGHT SCRAPER SIMULATION TEST                       ║
║                                                                              ║
║  Simulate a real job scraper by fetching roles, generating jobs,           ║
║  and submitting them to the multi-platform queue system.                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## 🚀 Quick Start (60 Seconds)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the simulation
python scraper_simulation.py

# Enter your API key when prompted
```

**That's it!** The script will fetch a job role, generate dummy jobs for all active platforms, submit them, and complete the session.

---

## 📚 Documentation

| File | Purpose | Read Time |
|------|---------|-----------|
| **INDEX.md** | Navigation guide (START HERE) | 5 min |
| **QUICKSTART.md** | Get running in 60 seconds | 5 min |
| **README.md** | Complete documentation | 15 min |
| **EXAMPLE_OUTPUT.md** | See real examples & API calls | 10 min |
| **CONFIGURATION.md** | Advanced setup options | 15 min |
| **SUMMARY.md** | Directory overview | 5 min |

---

## ✨ What This Script Does

```
┌─────────────────────────────────────────────────────────────────┐
│                    Scraper Simulation Workflow                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1️⃣  Authenticate with API Key                                 │
│      └─ Manually enter key (or pass via --api-key)             │
│                                                                  │
│  2️⃣  Fetch Next Role from Queue                               │
│      └─ GET /api/scraper/queue/next-role                       │
│      └─ Receive: role_id, title, keywords, platforms           │
│                                                                  │
│  3️⃣  Generate Dummy Jobs                                       │
│      └─ Create 3 jobs per platform (realistic data)            │
│      └─ Includes: company, location, salary, URL, etc.         │
│                                                                  │
│  4️⃣  Submit Jobs Per Platform                                  │
│      ├─ POST /api/scraper/queue/jobs (Platform 1)              │
│      ├─ POST /api/scraper/queue/jobs (Platform 2)              │
│      └─ POST /api/scraper/queue/jobs (Platform N)              │
│                                                                  │
│  5️⃣  Complete Session & Trigger Matching                       │
│      └─ POST /api/scraper/queue/complete                       │
│      └─ Inngest workflow kicks off                             │
│      └─ Job matching begins                                     │
│                                                                  │
│  ✅ Success!                                                    │
│     └─ Session tracked, jobs submitted, workflow triggered     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Features

✅ **Interactive or Scripted**
- Manual API key input OR command-line arguments
- Works in pipelines, CI/CD, and manual testing

✅ **Color-Coded Output**
- 🟢 Green for success
- 🔵 Blue for info
- 🟡 Yellow for warnings
- 🔴 Red for errors

✅ **Complete Error Handling**
- Connection errors
- Timeout handling
- Invalid API keys
- Detailed error messages

✅ **Realistic Data**
- Generates realistic dummy jobs
- Includes company names, locations, salaries
- Per-platform variability

✅ **Full Documentation**
- 6 comprehensive guides
- 2000+ lines of documentation
- Examples and use cases

---

## 📋 Usage Examples

### Interactive (Recommended for First-Time)
```bash
python scraper_simulation.py
# Then enter your API key when prompted
```

### With API Key
```bash
python scraper_simulation.py --api-key your-scraper-key-here
```

### Custom Server
```bash
python scraper_simulation.py --server http://api.example.com:5000
```

### Skip Session Completion
```bash
python scraper_simulation.py --skip-complete
```

### Batch Testing
```bash
for i in {1..10}; do
  python scraper_simulation.py --api-key $KEY
done
```

---

## 📊 What You'll See

### Example Output
```
════════════════════════════════════════════════════════════════════════════════
                        Blacklight Scraper Simulation
════════════════════════════════════════════════════════════════════════════════

→ API Authentication
────────────────────────────────────────────────────────────────────────────────
Enter your Scraper API Key: ••••••••••••••••••••••••••••••••••••••••••••••••••••
✅ API key received: sk_live_...xyz

→ Fetching Next Role from Queue
────────────────────────────────────────────────────────────────────────────────
ℹ️  Sending GET request to: http://localhost:5000/api/scraper/queue/next-role
✅ Successfully fetched next role

Role Details:
  Session ID:       550e8400-e29b-41d4-a716-446655440000
  Role ID:          42
  Role Title:       Senior Software Engineer
  Keywords:         Python, Flask, PostgreSQL, Docker
  Platforms Count:  3

Available Platforms:
  1. LinkedIn (name: linkedin, priority: 1)
  2. Monster (name: monster, priority: 2)
  3. Indeed (name: indeed, priority: 3)

→ Submitting Jobs for All Platforms
────────────────────────────────────────────────────────────────────────────────
ℹ️  Submitting 3 jobs for platform: linkedin
✅ Platform linkedin: Submitted 3 jobs

ℹ️  Submitting 3 jobs for platform: monster
✅ Platform monster: Submitted 3 jobs

ℹ️  Submitting 3 jobs for platform: indeed
✅ Platform indeed: Submitted 3 jobs

✅ Submitted jobs for 3/3 platforms

→ Completing Session
────────────────────────────────────────────────────────────────────────────────
ℹ️  Marking session as completed: 550e8400-e29b-41d4-a716-446655440000
✅ Session completed successfully
✅ Job matching workflow has been triggered

→ Simulation Complete
────────────────────────────────────────────────────────────────────────────────
✅ Scraper simulation workflow completed successfully!
ℹ️  Session ID: 550e8400-e29b-41d4-a716-446655440000
ℹ️  Role ID: 42
ℹ️  Platforms processed: 3
ℹ️  Total jobs submitted: 9

✨ Thank you for testing! 🎉
```

---

## 🔍 Getting Your API Key

1. Open **CentralD Dashboard**
2. Go to **Settings** → **Scraper API Keys**
3. Click **Generate New Key** or copy existing
4. Use this key with the script

---

## ✅ Verification

After running, verify success:

### Check Backend Logs
```bash
./deploy.sh logs -f app | grep "job\|import\|session"
```

### Check Database
```bash
psql -U blacklight -d blacklight -c "
  SELECT * FROM scrape_sessions 
  WHERE session_id = '550e8400-e29b-41d4-a716-446655440000';
"
```

### Check Inngest Dashboard
```
http://localhost:8288
```

### Check CentralD Dashboard
```
http://localhost:3000
Dashboard → Recent Sessions
```

---

## 📁 Files in This Directory

```
test_scraper/
├── scraper_simulation.py ............ Main test script (600+ lines)
├── README.md ....................... Complete guide
├── QUICKSTART.md ................... 60-second start
├── EXAMPLE_OUTPUT.md ............... Real examples
├── CONFIGURATION.md ................ Setup options
├── SUMMARY.md ...................... Overview
├── INDEX.md ........................ Navigation
├── requirements.txt ................ Dependencies
└── START_HERE.md (THIS FILE) ....... Quick start
```

---

## 🚦 Getting Started

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Get API Key
- Open CentralD Dashboard
- Settings → Scraper API Keys → Generate or Copy

### Step 3: Run Script
```bash
python scraper_simulation.py
```

### Step 4: Enter API Key
When prompted, paste your API key and press Enter

### Step 5: Verify
Check the output, logs, and dashboard for success ✅

---

## 🎓 Next Steps

1. **Understand the Workflow**
   - Read: QUICKSTART.md or README.md

2. **Run the Script**
   - Execute: `python scraper_simulation.py`

3. **Verify Success**
   - Check logs: `./deploy.sh logs`
   - Check DB: psql queries
   - Check Dashboard: UI inspection

4. **Run Tests**
   - Try different API keys
   - Test batch submissions
   - Monitor performance

5. **Integrate Real Scraper**
   - Follow same workflow pattern
   - Replace dummy jobs with real ones
   - Extend as needed

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| **ModuleNotFoundError: requests** | Run: `pip install -r requirements.txt` |
| **Connection refused** | Start backend: `./deploy.sh start` |
| **Unauthorized** | Get valid API key from Dashboard Settings |
| **No roles in queue** | Create a role first via Dashboard |
| **Request timeout** | Server might be busy, try again |

See **README.md** for full troubleshooting guide.

---

## 📞 Documentation by Need

| I want to... | Read this | Time |
|-------------|-----------|------|
| Get started NOW | QUICKSTART.md | 5 min |
| Understand everything | README.md | 15 min |
| See examples | EXAMPLE_OUTPUT.md | 10 min |
| Configure advanced options | CONFIGURATION.md | 15 min |
| Find anything | INDEX.md | 5 min |

---

## 🎉 Summary

**What**: Simulate a job scraper for testing
**How**: Run `python scraper_simulation.py`
**Time**: ~2 minutes to complete
**What Happens**: Fetches role → Generates jobs → Submits for all platforms → Completes session
**Result**: Tests multi-platform job queue system end-to-end

---

## 🚀 Ready?

```bash
# One command to do it all:
pip install -r requirements.txt && python scraper_simulation.py
```

Or read **QUICKSTART.md** for detailed steps.

---

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                         Ready to test? 🚀                                   ║
║                                                                              ║
║                    python scraper_simulation.py                            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

**For more details:** Open `INDEX.md` or `QUICKSTART.md`

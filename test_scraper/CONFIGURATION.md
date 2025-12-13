# Configuration Guide

## Overview

The scraper simulation script can be configured in multiple ways.

## Configuration Methods

### 1. Interactive (Recommended for First-Time)

Simply run the script without arguments:

```bash
python scraper_simulation.py
```

You will be prompted for:
- **API Key** - Your Scraper API Key (required)
- **Server URL** - Backend server address (optional, default: http://localhost:5000)

### 2. Command-Line Arguments

Pass configuration as command-line arguments:

```bash
python scraper_simulation.py --api-key YOUR_KEY --server http://localhost:5000
```

#### Available Arguments

| Argument | Short | Type | Default | Required | Description |
|----------|-------|------|---------|----------|-------------|
| `--api-key` | - | string | prompt | No | Scraper API key |
| `--server` | - | URL | http://localhost:5000 | No | Backend server URL |
| `--skip-complete` | - | flag | false | No | Skip session completion |

### 3. Environment Variables

Create a `.env` file in the `test_scraper` directory:

```bash
# .env
SCRAPER_API_KEY=sk_live_123456789abcdefghij
SCRAPER_SERVER=http://localhost:5000
SKIP_COMPLETE=false
```

Then run:
```bash
python scraper_simulation.py
```

## Usage Examples

### Minimal Setup
```bash
# Interactive - prompts for API key
python scraper_simulation.py
```

### Production-Like Setup
```bash
# With all credentials
python scraper_simulation.py \
  --api-key sk_live_123456789abcdefghij \
  --server http://localhost:5000
```

### Development Setup
```bash
# Skip completion for faster iteration
python scraper_simulation.py \
  --api-key sk_live_123456789abcdefghij \
  --skip-complete
```

### Remote Server
```bash
# Test against production server
python scraper_simulation.py \
  --api-key sk_prod_xxx \
  --server https://api.example.com
```

### CI/CD Pipeline
```bash
# Fully automated
python scraper_simulation.py \
  --api-key $SCRAPER_API_KEY \
  --server $BACKEND_URL
```

## Getting API Keys

### Via Dashboard (Recommended)

1. Open CentralD Dashboard
2. Navigate to **Settings** → **Scraper API Keys**
3. Click **Generate New Key** or copy existing
4. Use the key with the simulation script

### Via Database

```bash
# Query database for API keys
psql -U blacklight -d blacklight -c "
  SELECT id, key, description, created_at FROM scraper_api_keys;
"
```

### Via API (If Enabled)

```bash
curl -X GET http://localhost:5000/api/scraper-api-keys \
  -H "Authorization: Bearer <PM_ADMIN_TOKEN>"
```

## Server Configuration

### Local Development
```bash
# Default configuration
python scraper_simulation.py --api-key your-key
# Uses: http://localhost:5000
```

### Docker Compose
```bash
# When using docker-compose
python scraper_simulation.py --api-key your-key --server http://app:5000
```

### Remote Server
```bash
# Testing against remote server
python scraper_simulation.py \
  --api-key your-key \
  --server https://api.example.com
```

### Custom Port
```bash
# If running on different port
python scraper_simulation.py \
  --api-key your-key \
  --server http://localhost:8000
```

## Advanced Configuration

### Custom Job Count

Currently hardcoded to 3 jobs per platform. To modify:

1. Edit `scraper_simulation.py`
2. Find the line: `dummy_jobs = generate_dummy_jobs(platform_name, count=3)`
3. Change `count=3` to desired number

Example:
```python
dummy_jobs = generate_dummy_jobs(platform_name, count=10)  # 10 jobs per platform
```

### Custom Dummy Data

To modify generated dummy data, edit the `generate_dummy_jobs()` function:

```python
def generate_dummy_jobs(platform_name: str, count: int = 5) -> List[Dict[str, Any]]:
    # Modify these lists to change generated data
    companies = ["TechCorp", "Innovation Labs", "CloudSys", "DataWare", "AI Solutions", "DevOps Pro"]
    locations = ["San Francisco, CA", "New York, NY", "Austin, TX", "Seattle, WA", "Remote"]
    
    # Customize job data here
    job = {
        "external_id": f"{platform_name}_job_{int(time.time())}_{i}",
        "title": f"Senior Software Engineer - {platform_name}",
        # ... more fields
    }
```

### Custom Timeouts

To modify request timeout (default 10 seconds):

Find and modify these lines:
```python
response = requests.get(url, headers=headers, timeout=10)  # Change 10 to desired seconds
response = requests.post(url, json=payload, headers=headers, timeout=10)
```

### Disable Color Output

To remove colored output (for CI/CD logs):

1. Edit `scraper_simulation.py`
2. Change all `Colors.ENDC` to empty strings
3. Or comment out the Color class

## Batch Testing

### Run Multiple Times
```bash
for i in {1..5}; do
  echo "Run $i"
  python scraper_simulation.py --api-key your-key
  sleep 1  # 1 second between runs
done
```

### Parallel Execution
```bash
# Run 5 simulations in parallel
for i in {1..5}; do
  python scraper_simulation.py --api-key your-key &
done
wait  # Wait for all to complete
```

### With Different Roles
```bash
# Assuming multiple roles exist
for role_id in 1 2 3 4 5; do
  echo "Testing role $role_id"
  python scraper_simulation.py --api-key your-key
done
```

## Performance Tuning

### Faster Submissions
Reduce delay between platform submissions:

Find and modify:
```python
time.sleep(0.5)  # Change 0.5 to smaller value like 0.1
```

### Larger Batch
Increase jobs per platform:

Find and modify:
```python
dummy_jobs = generate_dummy_jobs(platform_name, count=3)  # Change to 50 for bulk test
```

### Longer Timeout
For slow servers:

Find and modify:
```python
response = requests.get(url, headers=headers, timeout=10)  # Change to 30
```

## Logging and Debugging

### Verbose Output

The script already provides verbose output. To add more debugging:

1. Uncomment debug lines in code
2. Add print statements
3. Enable Python logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Capture Output

Save output to file:
```bash
python scraper_simulation.py --api-key your-key > output.log 2>&1
```

### Watch Network Traffic

Monitor requests:
```bash
# Install: pip install mitmproxy
mitmproxy -p 8080

# Then configure script to use proxy
# Add to requests.get/post calls:
# proxies={"http": "http://localhost:8080"}
```

## Security

### API Key Protection

**Never** hardcode API keys in scripts. Instead:

1. Use interactive mode (prompts for key)
2. Use command-line arguments
3. Use environment variables from `.env`
4. Use CI/CD secrets

Example `.gitignore`:
```
.env
*.key
credentials/
```

### TLS/SSL

For HTTPS servers:
```bash
python scraper_simulation.py \
  --api-key your-key \
  --server https://secure.example.com
```

To disable certificate verification (development only):
```python
# In scraper_simulation.py, modify requests:
response = requests.get(url, headers=headers, verify=False)  # ⚠️ Development only!
```

## Troubleshooting Configuration

### Script Not Finding API Key
```bash
# Check if key is valid
echo $SCRAPER_API_KEY  # If using env var

# Or provide explicitly
python scraper_simulation.py --api-key your-actual-key
```

### Server Not Responding
```bash
# Verify server URL
curl http://localhost:5000/health

# Or check if server is running
./deploy.sh status
```

### Wrong API Key Format
```bash
# API keys should look like:
# sk_live_xxx... or sk_test_xxx...

# If unsure, get from Dashboard Settings
```

## Configuration Presets

### Local Development
```bash
#!/bin/bash
# save as run_local.sh
python scraper_simulation.py \
  --api-key $(cat .env | grep SCRAPER_API_KEY | cut -d= -f2) \
  --server http://localhost:5000
```

### Staging
```bash
#!/bin/bash
# save as run_staging.sh
python scraper_simulation.py \
  --api-key $STAGING_API_KEY \
  --server https://staging-api.example.com
```

### Production
```bash
#!/bin/bash
# save as run_production.sh
python scraper_simulation.py \
  --api-key $PRODUCTION_API_KEY \
  --server https://api.example.com
```

Usage:
```bash
bash run_local.sh
bash run_staging.sh
bash run_production.sh
```

## Default Configuration

If no arguments provided:

```yaml
API Key: Prompt for input
Server: http://localhost:5000
Skip Complete: false
Jobs per Platform: 3
Timeout: 10 seconds
Retry: None (fail immediately)
```

## Environment Variables Reference

The script can read from these environment variables:

```bash
# Optional - if set, skips interactive prompt
SCRAPER_API_KEY=your-key

# Optional - backend server URL
SCRAPER_SERVER=http://localhost:5000

# Optional - skip session completion
SKIP_COMPLETE=true/false
```

Set these in your shell:
```bash
export SCRAPER_API_KEY=sk_live_123...
export SCRAPER_SERVER=http://localhost:5000
python scraper_simulation.py
```

Or in `.env` file:
```bash
SCRAPER_API_KEY=sk_live_123...
SCRAPER_SERVER=http://localhost:5000
```

Then run:
```bash
source .env
python scraper_simulation.py
```

---

## Quick Reference

```bash
# Interactive
python scraper_simulation.py

# With key
python scraper_simulation.py --api-key your-key

# Custom server
python scraper_simulation.py --server http://api.example.com

# Skip completion
python scraper_simulation.py --skip-complete

# Fully configured
python scraper_simulation.py --api-key key --server url --skip-complete

# From environment
export SCRAPER_API_KEY=your-key
python scraper_simulation.py
```

---

**Last Updated:** December 12, 2025

# Inngest Docker Configuration Notes

## ✅ Updated Configuration (Official Inngest Pattern)

The Docker Compose files have been updated to follow the official Inngest Docker configuration pattern.

### Key Changes:

1. **Inngest Dev Server Command**:
   ```yaml
   # docker-compose.yml (when using Docker for Flask)
   inngest:
     command: 'inngest dev -u http://app:5000/api/inngest'
   ```
   
   ```yaml
   # docker-compose.local.yml (when running Flask natively)
   inngest:
     command: 'inngest dev'  # No -u flag, Flask registers directly
   ```

2. **Service Order**:
   - Inngest starts **before** Flask app
   - Flask app URL passed to Inngest via `-u` flag (Docker mode only)

3. **Environment Variables**:
   ```yaml
   # Flask app needs to know Inngest URL
   INNGEST_BASE_URL: http://inngest:8288  # Docker network name
   INNGEST_SERVE_ORIGIN: http://app:5000  # Flask app URL in Docker
   ```

---

## 🚀 How to Use

### Option 1: All in Docker (docker-compose.yml)

```bash
# Start everything in Docker
docker-compose up -d

# Inngest will auto-discover Flask at: http://app:5000/api/inngest
# Access dashboard: http://localhost:8288
```

**Configuration**:
- Inngest command: `inngest dev -u http://app:5000/api/inngest`
- Flask registers automatically when it starts
- Functions sync happens automatically

### Option 2: Native Flask (docker-compose.local.yml + run-local.sh)

```bash
# Start only Docker services (DB, Redis, Inngest)
./run-local.sh

# Flask runs natively on your machine
# Inngest runs in Docker
```

**Configuration**:
- Inngest command: `inngest dev` (no -u flag)
- Flask URL: `http://localhost:5000/api/inngest`
- Your `.env` should have: `INNGEST_SERVE_ORIGIN=http://localhost:5000`

---

## 🔧 Troubleshooting

### If Inngest can't find Flask:

**Symptom**: Inngest dashboard shows no functions

**Check**:
1. Flask is running and accessible
2. Visit: http://localhost:5000/api/inngest (should return JSON)
3. Check Inngest logs: `docker-compose logs inngest`
4. Verify INNGEST_SERVE_ORIGIN matches Flask URL

**Fix for Docker mode**:
```yaml
# Flask must be accessible from Inngest container
INNGEST_SERVE_ORIGIN: http://app:5000  # Use Docker service name
```

**Fix for native mode**:
```bash
# .env file
INNGEST_SERVE_ORIGIN=http://localhost:5000  # Use localhost
```

### If you see "connection refused":

**Docker mode**: Use service names (`http://app:5000`, `http://inngest:8288`)
**Native mode**: Use `localhost` (`http://localhost:5000`, `http://localhost:8288`)

---

## 📊 Verify Setup

```bash
# 1. Check Inngest is running
curl http://localhost:8288/health

# 2. Check Flask Inngest endpoint
curl http://localhost:5000/api/inngest

# 3. Check Inngest dashboard
open http://localhost:8288

# 4. View logs
docker-compose logs inngest
docker-compose logs app
```

---

## 🎯 Expected Behavior

### Successful Startup:

**Inngest logs should show**:
```
Inngest dev server running on http://0.0.0.0:8288
Discovered app: blacklight-hr
Found 8 functions
```

**Flask logs should show**:
```
Inngest: Registered 8 functions
Inngest: Serving at /api/inngest
```

**Inngest Dashboard should show**:
- App: `blacklight-hr`
- Functions: 8 total
  - parse-resume
  - send-invitation-email
  - send-submission-confirmation
  - send-approval-email
  - send-rejection-email
  - send-hr-notification
  - check-expiring-invitations
  - generate-daily-stats

---

## 📝 Configuration Summary

| Mode | Inngest Command | Flask URL | INNGEST_SERVE_ORIGIN |
|------|----------------|-----------|---------------------|
| Docker (docker-compose.yml) | `inngest dev -u http://app:5000/api/inngest` | http://app:5000 | http://app:5000 |
| Native (docker-compose.local.yml) | `inngest dev` | http://localhost:5000 | http://localhost:5000 |
| Production | N/A (uses Inngest Cloud) | https://api.yourcompany.com | https://api.yourcompany.com |

---

**Last Updated**: November 10, 2025

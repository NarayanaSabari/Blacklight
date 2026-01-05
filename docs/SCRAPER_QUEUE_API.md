# Scraper Credentials Queue API

API documentation for scrapers to fetch credentials and report usage.

## Base URL

```
/api/scraper-credentials/queue
```

## Authentication

All endpoints require a Scraper API Key in the header:

```
X-Scraper-API-Key: <your_scraper_api_key>
```

---

## Endpoints

### 1. Get Next Available Credential

Fetches the next available credential for a platform. The credential is automatically marked as `in_use` and assigned to your scraper.

**You must call `/success`, `/failure`, or `/release` after using the credential.**

```http
GET /api/scraper-credentials/queue/{platform}/next
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `platform` | string | Yes | `linkedin`, `glassdoor`, or `techfetch` |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | No | Your scraper session ID for tracking |

**Response (200) - LinkedIn/Techfetch:**
```json
{
  "id": 1,
  "platform": "linkedin",
  "name": "Account 1",
  "email": "user@example.com",
  "password": "secret123"
}
```

**Response (200) - Glassdoor:**
```json
{
  "id": 1,
  "platform": "glassdoor",
  "name": "Cookie Set 1",
  "credentials": {
    "cookie": "session_id=abc123",
    "csrf_token": "xyz789"
  }
}
```

**Response (204):** No credentials available (empty body).

**Response (400):** Invalid platform.

**Example:**
```bash
curl -X GET "http://localhost:5000/api/scraper-credentials/queue/linkedin/next?session_id=scraper-001" \
  -H "X-Scraper-API-Key: sk_live_abc123"
```

---

### 2. Report Success

Call this after successfully using a credential. Releases the credential back to the available pool.

```http
POST /api/scraper-credentials/queue/{credential_id}/success
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `credential_id` | integer | Yes | The credential ID from the `/next` response |

**Request Body (optional):**
```json
{
  "message": "Scraped 50 jobs successfully"
}
```

**Response (200):**
```json
{
  "message": "Credential released successfully",
  "status": "available"
}
```

**Example:**
```bash
curl -X POST "http://localhost:5000/api/scraper-credentials/queue/1/success" \
  -H "X-Scraper-API-Key: sk_live_abc123"
```

---

### 3. Report Failure

Call this when a credential fails (login error, account locked, etc.). Marks the credential as failed or puts it on cooldown.

```http
POST /api/scraper-credentials/queue/{credential_id}/failure
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `credential_id` | integer | Yes | The credential ID |

**Request Body:**
```json
{
  "error_message": "Login failed: Invalid credentials",
  "cooldown_minutes": 0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error_message` | string | Yes | What went wrong |
| `cooldown_minutes` | integer | No | If > 0, credential goes on cooldown instead of being marked failed |

**Response (200):**
```json
{
  "message": "Credential failure recorded",
  "status": "failed",
  "failure_count": 3
}
```

**When to use `cooldown_minutes`:**
- Use `cooldown_minutes: 0` (default) for permanent failures like invalid password, account locked
- Use `cooldown_minutes: 60` for temporary issues like rate limiting

**Example - Permanent Failure:**
```bash
curl -X POST "http://localhost:5000/api/scraper-credentials/queue/1/failure" \
  -H "X-Scraper-API-Key: sk_live_abc123" \
  -H "Content-Type: application/json" \
  -d '{"error_message": "Account locked by LinkedIn"}'
```

**Example - Temporary Rate Limit:**
```bash
curl -X POST "http://localhost:5000/api/scraper-credentials/queue/1/failure" \
  -H "X-Scraper-API-Key: sk_live_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "error_message": "Rate limited",
    "cooldown_minutes": 60
  }'
```

---

### 4. Release Credential

Release a credential without reporting success or failure. Use this if you fetched a credential but didn't use it.

```http
POST /api/scraper-credentials/queue/{credential_id}/release
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `credential_id` | integer | Yes | The credential ID |

**Response (200):**
```json
{
  "message": "Credential released",
  "status": "available"
}
```

**Example:**
```bash
curl -X POST "http://localhost:5000/api/scraper-credentials/queue/1/release" \
  -H "X-Scraper-API-Key: sk_live_abc123"
```

---

## Credential Statuses

| Status | Description |
|--------|-------------|
| `available` | Ready to be fetched |
| `in_use` | Currently assigned to a scraper |
| `failed` | Permanently failed (needs admin reset) |
| `cooldown` | Temporarily unavailable (auto-recovers) |
| `disabled` | Manually disabled by admin |

---

## Error Responses

```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

| Code | Meaning |
|------|---------|
| 204 | No credentials available |
| 400 | Invalid platform |
| 401 | Missing or invalid API key |
| 404 | Credential not found |

---

## Python Example

```python
import requests

API_BASE = "http://localhost:5000/api/scraper-credentials/queue"
API_KEY = "sk_live_abc123"
HEADERS = {"X-Scraper-API-Key": API_KEY}


def get_credential(platform: str, session_id: str = None):
    """Fetch next available credential."""
    params = {"session_id": session_id} if session_id else {}
    response = requests.get(f"{API_BASE}/{platform}/next", headers=HEADERS, params=params)
    
    if response.status_code == 204:
        return None  # No credentials available
    
    response.raise_for_status()
    return response.json()


def report_success(credential_id: int):
    """Report successful use."""
    requests.post(f"{API_BASE}/{credential_id}/success", headers=HEADERS)


def report_failure(credential_id: int, error: str, cooldown_minutes: int = 0):
    """Report failure."""
    requests.post(
        f"{API_BASE}/{credential_id}/failure",
        headers=HEADERS,
        json={"error_message": error, "cooldown_minutes": cooldown_minutes}
    )


def release_credential(credential_id: int):
    """Release without reporting."""
    requests.post(f"{API_BASE}/{credential_id}/release", headers=HEADERS)


# Usage
credential = get_credential("linkedin", session_id="my-scraper-001")

if not credential:
    print("No credentials available")
    exit()

credential_id = credential["id"]

try:
    # Use the credential
    login(credential["email"], credential["password"])
    scrape_jobs()
    report_success(credential_id)
    
except LoginError as e:
    report_failure(credential_id, str(e))
    
except RateLimitError:
    report_failure(credential_id, "Rate limited", cooldown_minutes=60)
```

---

## Endpoint Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/queue/{platform}/next` | Get next available credential |
| POST | `/queue/{credential_id}/success` | Report successful use |
| POST | `/queue/{credential_id}/failure` | Report failure |
| POST | `/queue/{credential_id}/release` | Release without reporting |

# Scraper Credentials API

API documentation for managing scraper credentials for LinkedIn, Glassdoor, and Techfetch platforms.

## Overview

The Scraper Credentials API provides two sets of endpoints with different authentication:

| Endpoint Type | Purpose | Authentication |
|---------------|---------|----------------|
| **PM_ADMIN Dashboard** | CRUD operations for CentralD UI | JWT Token (`Authorization: Bearer <token>`) |
| **Scraper Queue** | Get credentials, report success/failure | Scraper API Key (`X-Scraper-API-Key: <key>`) |

## Base URL

```
/api/scraper-credentials
```

---

## Authentication

### PM_ADMIN Endpoints (Dashboard)
Requires JWT token in the `Authorization` header:
```
Authorization: Bearer <jwt_token>
```

### Scraper Endpoints (Queue)
Requires API key in the `X-Scraper-API-Key` header:
```
X-Scraper-API-Key: <scraper_api_key>
```

---

## PM_ADMIN Dashboard Endpoints

These endpoints are used by the CentralD dashboard to manage credentials.

### 1. List All Credentials

Get all credentials with optional filters.

```http
GET /api/scraper-credentials/
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `platform` | string | Filter by platform: `linkedin`, `glassdoor`, `techfetch` |
| `status` | string | Filter by status: `available`, `in_use`, `failed`, `disabled`, `cooldown` |

**Response (200):**
```json
{
  "credentials": [
    {
      "id": 1,
      "platform": "linkedin",
      "name": "Account 1",
      "email": "user@example.com",
      "status": "available",
      "failure_count": 0,
      "total_uses": 42,
      "last_used_at": "2025-01-05T10:30:00Z",
      "created_at": "2025-01-01T00:00:00Z",
      "notes": "Primary account"
    }
  ],
  "total": 1
}
```

**Example:**
```bash
curl -X GET "http://localhost:5000/api/scraper-credentials/?platform=linkedin&status=available" \
  -H "Authorization: Bearer <jwt_token>"
```

---

### 2. Get Credential Statistics

Get statistics for all platforms.

```http
GET /api/scraper-credentials/stats
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
  "linkedin": {
    "total": 10,
    "available": 7,
    "in_use": 2,
    "failed": 1,
    "disabled": 0,
    "cooldown": 0
  },
  "glassdoor": {
    "total": 5,
    "available": 5,
    "in_use": 0,
    "failed": 0,
    "disabled": 0,
    "cooldown": 0
  },
  "techfetch": {
    "total": 3,
    "available": 3,
    "in_use": 0,
    "failed": 0,
    "disabled": 0,
    "cooldown": 0
  }
}
```

**Example:**
```bash
curl -X GET "http://localhost:5000/api/scraper-credentials/stats" \
  -H "Authorization: Bearer <jwt_token>"
```

---

### 3. Get Platform Credentials

Get all credentials for a specific platform with stats.

```http
GET /api/scraper-credentials/platforms/{platform}
Authorization: Bearer <jwt_token>
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `platform` | string | Platform name: `linkedin`, `glassdoor`, `techfetch` |

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Optional status filter |

**Response (200):**
```json
{
  "platform": "linkedin",
  "credentials": [
    {
      "id": 1,
      "platform": "linkedin",
      "name": "Account 1",
      "email": "user@example.com",
      "status": "available",
      "failure_count": 0,
      "total_uses": 42,
      "last_used_at": "2025-01-05T10:30:00Z",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "stats": {
    "total": 10,
    "available": 7,
    "in_use": 2,
    "failed": 1,
    "disabled": 0,
    "cooldown": 0
  }
}
```

**Example:**
```bash
curl -X GET "http://localhost:5000/api/scraper-credentials/platforms/linkedin" \
  -H "Authorization: Bearer <jwt_token>"
```

---

### 4. Create Credential

Create a new scraper credential.

```http
POST /api/scraper-credentials/
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body for LinkedIn/Techfetch:**
```json
{
  "platform": "linkedin",
  "name": "Account 1",
  "email": "user@example.com",
  "password": "secret123",
  "notes": "Optional notes"
}
```

**Request Body for Glassdoor (uses cookies/JSON):**
```json
{
  "platform": "glassdoor",
  "name": "Cookie Set 1",
  "json_credentials": {
    "cookie": "session_id=abc123; token=xyz789",
    "user_agent": "Mozilla/5.0..."
  },
  "notes": "Optional notes"
}
```

**Response (201):**
```json
{
  "message": "Credential created successfully",
  "credential": {
    "id": 1,
    "platform": "linkedin",
    "name": "Account 1",
    "email": "user@example.com",
    "status": "available",
    "failure_count": 0,
    "total_uses": 0,
    "created_at": "2025-01-05T10:30:00Z"
  }
}
```

**Example (LinkedIn):**
```bash
curl -X POST "http://localhost:5000/api/scraper-credentials/" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "linkedin",
    "name": "LinkedIn Account 1",
    "email": "scraper@example.com",
    "password": "MySecurePassword123",
    "notes": "Main scraping account"
  }'
```

---

### 5. Get Credential by ID

Get a specific credential.

```http
GET /api/scraper-credentials/{credential_id}
Authorization: Bearer <jwt_token>
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `credential_id` | integer | Credential ID |

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `include_credentials` | string | Set to `true` to include decrypted password/credentials |

**Response (200):**
```json
{
  "credential": {
    "id": 1,
    "platform": "linkedin",
    "name": "Account 1",
    "email": "user@example.com",
    "password": "secret123",
    "status": "available",
    "failure_count": 0,
    "total_uses": 42,
    "last_used_at": "2025-01-05T10:30:00Z",
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

**Example:**
```bash
curl -X GET "http://localhost:5000/api/scraper-credentials/1?include_credentials=true" \
  -H "Authorization: Bearer <jwt_token>"
```

---

### 6. Update Credential

Update an existing credential.

```http
PUT /api/scraper-credentials/{credential_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body (all fields optional):**
```json
{
  "name": "New Name",
  "email": "new@example.com",
  "password": "newpassword",
  "json_credentials": { "cookie": "new_cookie" },
  "notes": "Updated notes"
}
```

**Response (200):**
```json
{
  "message": "Credential updated successfully",
  "credential": {
    "id": 1,
    "platform": "linkedin",
    "name": "New Name",
    "email": "new@example.com",
    "status": "available"
  }
}
```

**Example:**
```bash
curl -X PUT "http://localhost:5000/api/scraper-credentials/1" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "NewSecurePassword456",
    "notes": "Password updated on 2025-01-05"
  }'
```

---

### 7. Delete Credential

Delete a credential permanently.

```http
DELETE /api/scraper-credentials/{credential_id}
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
  "message": "Credential deleted successfully"
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:5000/api/scraper-credentials/1" \
  -H "Authorization: Bearer <jwt_token>"
```

---

### 8. Enable Credential

Enable a disabled or failed credential.

```http
POST /api/scraper-credentials/{credential_id}/enable
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
  "message": "Credential enabled",
  "credential": {
    "id": 1,
    "status": "available"
  }
}
```

---

### 9. Disable Credential

Disable a credential (prevents it from being assigned to scrapers).

```http
POST /api/scraper-credentials/{credential_id}/disable
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
  "message": "Credential disabled",
  "credential": {
    "id": 1,
    "status": "disabled"
  }
}
```

---

### 10. Reset Credential

Reset a failed credential back to available status (clears error state).

```http
POST /api/scraper-credentials/{credential_id}/reset
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
  "message": "Credential reset to available",
  "credential": {
    "id": 1,
    "status": "available",
    "failure_count": 0
  }
}
```

---

## Scraper Queue Endpoints

These endpoints are used by external scrapers to fetch credentials and report usage.

### 1. Get Next Available Credential

Get the next available credential for a platform. The credential is automatically marked as `in_use`.

```http
GET /api/scraper-credentials/queue/{platform}/next
X-Scraper-API-Key: <scraper_api_key>
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `platform` | string | Platform name: `linkedin`, `glassdoor`, `techfetch` |

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | Optional scraper session ID for tracking |

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

**Response (204):** No credentials available (empty response body).

**Example:**
```bash
curl -X GET "http://localhost:5000/api/scraper-credentials/queue/linkedin/next?session_id=scraper-001" \
  -H "X-Scraper-API-Key: <scraper_api_key>"
```

---

### 2. Report Success

Report that a credential was used successfully. Releases the credential back to the available pool.

```http
POST /api/scraper-credentials/queue/{credential_id}/success
X-Scraper-API-Key: <scraper_api_key>
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `credential_id` | integer | Credential ID |

**Request Body (optional):**
```json
{
  "message": "Optional success message"
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
  -H "X-Scraper-API-Key: <scraper_api_key>" \
  -H "Content-Type: application/json" \
  -d '{"message": "Scraped 50 jobs successfully"}'
```

---

### 3. Report Failure

Report that a credential failed. Marks the credential as failed.

```http
POST /api/scraper-credentials/queue/{credential_id}/failure
X-Scraper-API-Key: <scraper_api_key>
Content-Type: application/json
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `credential_id` | integer | Credential ID |

**Request Body:**
```json
{
  "error_message": "Login failed: Invalid credentials",
  "cooldown_minutes": 30
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error_message` | string | Yes | Error description |
| `cooldown_minutes` | integer | No | Put credential on cooldown instead of marking as failed |

**Response (200):**
```json
{
  "message": "Credential failure recorded",
  "status": "failed",
  "failure_count": 3
}
```

**Example:**
```bash
curl -X POST "http://localhost:5000/api/scraper-credentials/queue/1/failure" \
  -H "X-Scraper-API-Key: <scraper_api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "error_message": "Rate limited by LinkedIn",
    "cooldown_minutes": 60
  }'
```

---

### 4. Release Credential

Release a credential without reporting success or failure. Useful if the scraper needs to return a credential without using it.

```http
POST /api/scraper-credentials/queue/{credential_id}/release
X-Scraper-API-Key: <scraper_api_key>
```

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
  -H "X-Scraper-API-Key: <scraper_api_key>"
```

---

## Credential Statuses

| Status | Description |
|--------|-------------|
| `available` | Credential is ready to be used |
| `in_use` | Credential is currently assigned to a scraper |
| `failed` | Credential has failed (e.g., invalid password, account locked) |
| `disabled` | Credential is manually disabled by admin |
| `cooldown` | Credential is temporarily unavailable (rate limited) |

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

**Common HTTP Status Codes:**
| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing or invalid authentication |
| 404 | Not Found - Credential not found |
| 500 | Internal Server Error |

---

## Typical Scraper Workflow

```python
import requests

API_BASE = "http://localhost:5000/api/scraper-credentials"
SCRAPER_API_KEY = "your-scraper-api-key"
HEADERS = {"X-Scraper-API-Key": SCRAPER_API_KEY}

# 1. Get a credential
response = requests.get(
    f"{API_BASE}/queue/linkedin/next",
    headers=HEADERS,
    params={"session_id": "my-scraper-001"}
)

if response.status_code == 204:
    print("No credentials available")
    exit()

credential = response.json()
credential_id = credential["id"]

try:
    # 2. Use the credential for scraping
    login_to_linkedin(credential["email"], credential["password"])
    scrape_jobs()
    
    # 3. Report success
    requests.post(
        f"{API_BASE}/queue/{credential_id}/success",
        headers=HEADERS
    )
    
except LoginError as e:
    # 3. Report failure (marks credential as failed)
    requests.post(
        f"{API_BASE}/queue/{credential_id}/failure",
        headers=HEADERS,
        json={"error_message": str(e)}
    )

except RateLimitError:
    # 3. Report failure with cooldown (credential available after cooldown)
    requests.post(
        f"{API_BASE}/queue/{credential_id}/failure",
        headers=HEADERS,
        json={
            "error_message": "Rate limited",
            "cooldown_minutes": 60
        }
    )
```

---

## Endpoint Summary

### PM_ADMIN Endpoints (JWT Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all credentials |
| GET | `/stats` | Get platform statistics |
| GET | `/platforms/{platform}` | Get platform credentials |
| POST | `/` | Create credential |
| GET | `/{id}` | Get credential by ID |
| PUT | `/{id}` | Update credential |
| DELETE | `/{id}` | Delete credential |
| POST | `/{id}/enable` | Enable credential |
| POST | `/{id}/disable` | Disable credential |
| POST | `/{id}/reset` | Reset failed credential |

### Scraper Endpoints (API Key Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/queue/{platform}/next` | Get next available credential |
| POST | `/queue/{id}/success` | Report successful use |
| POST | `/queue/{id}/failure` | Report failure |
| POST | `/queue/{id}/release` | Release without reporting |

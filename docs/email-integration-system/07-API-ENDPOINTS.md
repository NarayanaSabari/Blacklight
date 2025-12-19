# API Endpoints

## Overview

This document describes all REST API endpoints for the Email Integration feature.

## Base URL

```
/api/integrations
```

## Authentication

All endpoints require Portal authentication:
- Header: `Authorization: Bearer <jwt_token>`
- Middleware: `@require_portal_auth`, `@with_tenant_context`

---

## Integration Management Endpoints

### 1. Initiate OAuth Flow

Start the OAuth flow for Gmail or Outlook.

**Endpoint**: `POST /api/integrations/email/initiate`

**Request**:
```json
{
    "provider": "gmail" | "outlook"
}
```

**Response** (200):
```json
{
    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

**Errors**:
- `400`: Invalid provider

---

### 2. OAuth Callback (Internal)

Handles OAuth redirect from Google/Microsoft.

**Endpoint**: `GET /api/integrations/email/callback/{provider}`

**Query Parameters**:
- `code`: Authorization code
- `state`: State token for CSRF protection

**Response**: Redirect to frontend with status

Success:
```
{frontend_url}/settings/integrations?status=success&provider=gmail
```

Error:
```
{frontend_url}/settings/integrations?status=error&message=token_exchange_failed
```

---

### 3. List User Integrations

Get all email integrations for the current user.

**Endpoint**: `GET /api/integrations/email`

**Response** (200):
```json
{
    "integrations": [
        {
            "id": 1,
            "provider": "gmail",
            "email_address": "recruiter@company.com",
            "is_active": true,
            "last_synced_at": "2025-12-17T10:00:00Z",
            "last_sync_status": "success",
            "emails_processed_count": 150,
            "jobs_created_count": 23,
            "created_at": "2025-12-01T09:00:00Z"
        },
        {
            "id": 2,
            "provider": "outlook",
            "email_address": "recruiter@outlook.com",
            "is_active": false,
            "last_synced_at": "2025-12-15T08:00:00Z",
            "last_sync_status": "failed",
            "last_sync_error": "Token expired - please reconnect",
            "emails_processed_count": 50,
            "jobs_created_count": 8,
            "created_at": "2025-11-15T14:00:00Z"
        }
    ]
}
```

---

### 4. Get Integration Details

Get detailed information about a specific integration.

**Endpoint**: `GET /api/integrations/email/{integration_id}`

**Response** (200):
```json
{
    "id": 1,
    "provider": "gmail",
    "email_address": "recruiter@company.com",
    "is_active": true,
    "last_synced_at": "2025-12-17T10:00:00Z",
    "last_sync_status": "success",
    "last_sync_error": null,
    "sync_frequency_minutes": 15,
    "sync_lookback_days": 7,
    "emails_processed_count": 150,
    "jobs_created_count": 23,
    "created_at": "2025-12-01T09:00:00Z",
    "updated_at": "2025-12-17T10:00:00Z"
}
```

**Errors**:
- `404`: Integration not found

---

### 5. Disconnect Integration

Remove an email integration.

**Endpoint**: `DELETE /api/integrations/email/{integration_id}`

**Response** (200):
```json
{
    "message": "Integration disconnected successfully"
}
```

**Errors**:
- `404`: Integration not found

---

### 6. Trigger Manual Sync

Manually trigger email sync for an integration.

**Endpoint**: `POST /api/integrations/email/{integration_id}/sync`

**Response** (200):
```json
{
    "message": "Sync triggered successfully"
}
```

**Errors**:
- `404`: Integration not found
- `400`: Integration is inactive

---

### 7. Update Integration Settings

Update sync settings for an integration.

**Endpoint**: `PATCH /api/integrations/email/{integration_id}`

**Request**:
```json
{
    "sync_frequency_minutes": 30,
    "sync_lookback_days": 14,
    "is_active": true
}
```

**Response** (200):
```json
{
    "id": 1,
    "provider": "gmail",
    "sync_frequency_minutes": 30,
    "sync_lookback_days": 14,
    "is_active": true,
    "updated_at": "2025-12-17T10:30:00Z"
}
```

---

## Email Jobs Endpoints

### 8. List Email-Sourced Jobs

Get jobs sourced from emails for the tenant.

**Endpoint**: `GET /api/email-jobs`

**Query Parameters**:
- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 20, max: 100)
- `sourced_by_user_id` (int): Filter by user who sourced the job
- `date_from` (string): Filter by email date (ISO format)
- `date_to` (string): Filter by email date (ISO format)
- `search` (string): Search in title, company, description

**Response** (200):
```json
{
    "jobs": [
        {
            "id": 101,
            "title": "Senior Python Developer",
            "company": "Fortune 500 Tech Company",
            "location": "Remote",
            "is_remote": true,
            "job_type": "Contract",
            "salary_range": "$70-80/hr",
            "salary_min": 145600,
            "salary_max": 166400,
            "description": "Looking for a Senior Python Developer...",
            "skills": ["Python", "FastAPI", "AWS"],
            "status": "ACTIVE",
            "posted_date": "2025-12-16",
            
            "source_email_subject": "Urgent - Python Dev - Remote - C2C",
            "source_email_sender": "vendor@staffing.com",
            "source_email_date": "2025-12-16T09:30:00Z",
            
            "sourced_by": {
                "id": 5,
                "first_name": "John",
                "last_name": "Smith",
                "email": "john.smith@company.com"
            },
            
            "created_at": "2025-12-16T10:00:00Z"
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 45,
        "pages": 3
    }
}
```

---

### 9. Get Email Job Details

Get detailed information about an email-sourced job.

**Endpoint**: `GET /api/email-jobs/{job_id}`

**Response** (200):
```json
{
    "id": 101,
    "title": "Senior Python Developer",
    "company": "Fortune 500 Tech Company",
    "location": "Remote",
    "is_remote": true,
    "job_type": "Contract",
    "salary_range": "$70-80/hr",
    "salary_min": 145600,
    "salary_max": 166400,
    "description": "Full job description...",
    "skills": ["Python", "FastAPI", "AWS", "PostgreSQL"],
    "status": "ACTIVE",
    "posted_date": "2025-12-16",
    
    "source_email_id": "<abc123@mail.gmail.com>",
    "source_email_subject": "Urgent - Python Dev - Remote - C2C",
    "source_email_sender": "John Doe <vendor@staffing.com>",
    "source_email_date": "2025-12-16T09:30:00Z",
    
    "sourced_by": {
        "id": 5,
        "first_name": "John",
        "last_name": "Smith",
        "email": "john.smith@company.com",
        "phone": "+1-555-0123"
    },
    
    "created_at": "2025-12-16T10:00:00Z",
    "updated_at": "2025-12-16T10:00:00Z"
}
```

**Errors**:
- `404`: Job not found or not accessible

---

### 10. Get Email Jobs Statistics

Get statistics about email-sourced jobs.

**Endpoint**: `GET /api/email-jobs/stats`

**Response** (200):
```json
{
    "total_jobs": 45,
    "jobs_today": 5,
    "jobs_this_week": 23,
    "jobs_by_user": [
        {
            "user_id": 5,
            "user_name": "John Smith",
            "job_count": 18
        },
        {
            "user_id": 8,
            "user_name": "Jane Doe",
            "job_count": 15
        }
    ],
    "jobs_by_provider": {
        "gmail": 30,
        "outlook": 15
    },
    "active_integrations": 3,
    "last_sync_at": "2025-12-17T10:00:00Z"
}
```

---

### 11. Delete Email Job

Delete an email-sourced job.

**Endpoint**: `DELETE /api/email-jobs/{job_id}`

**Response** (200):
```json
{
    "message": "Job deleted successfully"
}
```

**Errors**:
- `404`: Job not found
- `403`: Not authorized to delete

---

## Processed Emails Endpoints (Admin)

### 12. List Processed Emails

View emails that have been processed by the system.

**Endpoint**: `GET /api/integrations/email/{integration_id}/processed`

**Query Parameters**:
- `page` (int): Page number
- `per_page` (int): Items per page
- `result` (string): Filter by result (job_created, skipped, failed)

**Response** (200):
```json
{
    "emails": [
        {
            "id": 1,
            "email_message_id": "<abc123@mail.gmail.com>",
            "email_subject": "Python Developer - Remote",
            "email_sender": "vendor@staffing.com",
            "processed_at": "2025-12-17T10:00:00Z",
            "processing_result": "job_created",
            "job_id": 101
        },
        {
            "id": 2,
            "email_message_id": "<def456@mail.gmail.com>",
            "email_subject": "Weekly Newsletter",
            "email_sender": "news@tech.com",
            "processed_at": "2025-12-17T10:01:00Z",
            "processing_result": "skipped",
            "skip_reason": "Not identified as a job requirement"
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 150,
        "pages": 8
    }
}
```

---

## Routes Implementation

```python
# app/routes/email_jobs_routes.py
from flask import Blueprint, request, jsonify, g
from app.middleware.auth import require_portal_auth, with_tenant_context
from app.models import JobPosting, PortalUser
from app import db
from sqlalchemy import select, and_, or_

email_jobs_bp = Blueprint('email_jobs', __name__, url_prefix='/api/email-jobs')


@email_jobs_bp.route('', methods=['GET'])
@require_portal_auth
@with_tenant_context
def list_email_jobs():
    """List email-sourced jobs for tenant."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    sourced_by = request.args.get('sourced_by_user_id', type=int)
    search = request.args.get('search', '')
    
    # Base query for email-sourced jobs in this tenant
    query = (
        select(JobPosting)
        .where(JobPosting.is_email_sourced == True)
        .where(JobPosting.source_tenant_id == g.tenant_id)
        .order_by(JobPosting.created_at.desc())
    )
    
    # Apply filters
    if sourced_by:
        query = query.where(JobPosting.sourced_by_user_id == sourced_by)
    
    if search:
        search_filter = or_(
            JobPosting.title.ilike(f'%{search}%'),
            JobPosting.company.ilike(f'%{search}%'),
            JobPosting.description.ilike(f'%{search}%')
        )
        query = query.where(search_filter)
    
    # Paginate
    pagination = db.paginate(query, page=page, per_page=per_page)
    
    # Build response with user info
    jobs = []
    for job in pagination.items:
        job_dict = job.to_dict()
        
        # Add sourced_by user info
        if job.sourced_by_user_id:
            user = db.session.get(PortalUser, job.sourced_by_user_id)
            if user:
                job_dict['sourced_by'] = {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email
                }
        
        jobs.append(job_dict)
    
    return jsonify({
        'jobs': jobs,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@email_jobs_bp.route('/<int:job_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
def get_email_job(job_id: int):
    """Get email-sourced job details."""
    job = db.session.get(JobPosting, job_id)
    
    if not job or not job.is_email_sourced:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.source_tenant_id != g.tenant_id:
        return jsonify({'error': 'Not authorized'}), 403
    
    job_dict = job.to_dict()
    
    # Add sourced_by user info
    if job.sourced_by_user_id:
        user = db.session.get(PortalUser, job.sourced_by_user_id)
        if user:
            job_dict['sourced_by'] = {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': user.phone
            }
    
    return jsonify(job_dict)


@email_jobs_bp.route('/stats', methods=['GET'])
@require_portal_auth
@with_tenant_context
def get_email_jobs_stats():
    """Get email jobs statistics for tenant."""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    tenant_id = g.tenant_id
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    
    # Total jobs
    total = db.session.scalar(
        select(func.count(JobPosting.id))
        .where(JobPosting.is_email_sourced == True)
        .where(JobPosting.source_tenant_id == tenant_id)
    )
    
    # Jobs today
    today_count = db.session.scalar(
        select(func.count(JobPosting.id))
        .where(JobPosting.is_email_sourced == True)
        .where(JobPosting.source_tenant_id == tenant_id)
        .where(JobPosting.created_at >= today_start)
    )
    
    # Jobs this week
    week_count = db.session.scalar(
        select(func.count(JobPosting.id))
        .where(JobPosting.is_email_sourced == True)
        .where(JobPosting.source_tenant_id == tenant_id)
        .where(JobPosting.created_at >= week_start)
    )
    
    # Jobs by user
    jobs_by_user_query = (
        select(
            JobPosting.sourced_by_user_id,
            func.count(JobPosting.id).label('count')
        )
        .where(JobPosting.is_email_sourced == True)
        .where(JobPosting.source_tenant_id == tenant_id)
        .group_by(JobPosting.sourced_by_user_id)
        .order_by(func.count(JobPosting.id).desc())
    )
    
    jobs_by_user = []
    for user_id, count in db.session.execute(jobs_by_user_query):
        if user_id:
            user = db.session.get(PortalUser, user_id)
            if user:
                jobs_by_user.append({
                    'user_id': user_id,
                    'user_name': f"{user.first_name} {user.last_name}",
                    'job_count': count
                })
    
    return jsonify({
        'total_jobs': total or 0,
        'jobs_today': today_count or 0,
        'jobs_this_week': week_count or 0,
        'jobs_by_user': jobs_by_user
    })


@email_jobs_bp.route('/<int:job_id>', methods=['DELETE'])
@require_portal_auth
@with_tenant_context
def delete_email_job(job_id: int):
    """Delete an email-sourced job."""
    job = db.session.get(JobPosting, job_id)
    
    if not job or not job.is_email_sourced:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.source_tenant_id != g.tenant_id:
        return jsonify({'error': 'Not authorized'}), 403
    
    db.session.delete(job)
    db.session.commit()
    
    return jsonify({'message': 'Job deleted successfully'})
```

## Error Responses

All errors follow this format:

```json
{
    "error": "Error type",
    "message": "Detailed error message",
    "status": 400
}
```

Common status codes:
- `400`: Bad request (invalid input)
- `401`: Unauthorized (missing/invalid token)
- `403`: Forbidden (not authorized for resource)
- `404`: Not found
- `500`: Internal server error

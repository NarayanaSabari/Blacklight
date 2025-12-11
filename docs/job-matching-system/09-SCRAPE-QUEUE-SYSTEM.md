# Scrape Queue System

The scrape queue system provides **role-based job scraping** with external scraper integration, FIFO queue management, and simplified session tracking for observability.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ROLE-BASED SCRAPE QUEUE SYSTEM                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐  │
│  │   Candidates    │    │  Global Roles   │    │    External    │  │
│  │   (Onboarding)  │───▶│   Queue (DB)    │◀───│    Scraper     │  │
│  └─────────────────┘    └─────────────────┘    └────────────────┘  │
│           │                      │                      │          │
│           │ AI Normalize         │ GET /next-role       │          │
│           ▼                      ▼                      ▼          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐  │
│  │ candidate_      │    │ Session Started │    │ POST /jobs     │  │
│  │ global_roles    │    │ (Observability) │    │ + jobs/imported│  │
│  └─────────────────┘    └─────────────────┘    └────────────────┘  │
│                                                         │          │
│                                                         ▼          │
│                                                ┌────────────────┐  │
│                                                │ Match to ALL   │  │
│                                                │ linked         │  │
│                                                │ candidates     │  │
│                                                └────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Design: Role-Based (Not Candidate-Based)

**Critical Architecture Decision**: The scrape queue is **ROLE-based**, not candidate-based:

| Approach | Queue Entity | Problem |
|----------|--------------|---------|
| ❌ Candidate-Based | Each candidate gets queued | Duplicate scrapes if 100 candidates want "Python Developer" |
| ✅ Role-Based | Each unique role gets queued | Scrape "Python Developer" ONCE, match to ALL 100 candidates |

### How It Works

1. **Candidate Onboarding**: Candidate selects "Senior Python Developer"
2. **AI Normalization**: Maps to canonical `GlobalRole("Python Developer")`
3. **Link Created**: `candidate_global_roles` record links candidate → role
4. **Queue Check**: If role is `pending`, it's already in queue - no duplicate
5. **Scraper Fetches**: Gets "Python Developer" (highest candidate_count first)
6. **Jobs Posted**: Jobs for "Python Developer" are imported
7. **Event Triggered**: `jobs/imported` → match to ALL candidates with that role

## Scraper Session Tracking (Simplified)

### Overview
Session tracking is **simplified** to two key events:
1. **Session Start**: When scraper fetches a role (`GET /api/scraper/queue/next-role`)
2. **Session Complete**: When scraper posts jobs (`POST /api/scraper/queue/jobs`)

No intermediate progress updates needed - this keeps the scraper implementation simple.

### Session Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      SIMPLIFIED SESSION TRACKING                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   1. Scraper Authenticates      2. Fetch Next Role      3. Session Start │
│   ┌─────────────────┐           ┌────────────────┐      ┌────────────┐  │
│   │ X-Scraper-API-  │──────────▶│ GET /api/      │─────▶│ Session    │  │
│   │ Key: abc123...  │           │ scraper/queue/ │      │ Created    │  │
│   └─────────────────┘           │ next-role      │      │ status=    │  │
│                                 └────────────────┘      │ in_progress│  │
│                                                         └────────────┘  │
│                                                                          │
│   4. Scraper Works (External)   5. Post Jobs            6. Session Done  │
│   ┌─────────────────┐           ┌────────────────┐      ┌────────────┐  │
│   │ Scrapes Monster │           │ POST /api/     │─────▶│ status=    │  │
│   │ Indeed, Dice... │──────────▶│ scraper/queue/ │      │ completed  │  │
│   │ (No callbacks)  │           │ jobs           │      │ Trigger    │  │
│   └─────────────────┘           └────────────────┘      │ jobs/      │  │
│                                                         │ imported   │  │
│                                                         └────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```
        
        db.session.commit()
```

## Candidate-Centric Approach

### Search Keywords Generation
The system generates search keywords from candidate data:

```python
def generate_search_keywords(candidate: Candidate) -> List[str]:
    """Generate search keywords from candidate profile."""
    keywords = []
    
    # 1. Primary: Job Title / Role
    if candidate.current_title:
        keywords.append(candidate.current_title)
    
    # 2. Secondary: Top Skills (limit to 5)
    if candidate.skills:
        top_skills = candidate.skills[:5]
        keywords.extend(top_skills)
    
    # 3. Tertiary: Technology Stack
    if candidate.tech_stack:
        keywords.extend(candidate.tech_stack[:3])
    
    # 4. Specializations
    if candidate.specializations:
        keywords.append(candidate.specializations)
    
    return list(set(keywords))  # Deduplicate
```

## Role Queue Service

### Simplified Service Implementation

```python
# app/services/scrape_queue_service.py

import uuid
from datetime import datetime
from app import db
from app.models import GlobalRole, ScrapeSession, ScraperApiKey

class ScrapeQueueService:
    """Service for managing the role-based scrape queue."""
    
    @staticmethod
    def get_next_role(scraper_key: ScraperApiKey) -> dict:
        """
        Get next role from queue and start session.
        Called by: GET /api/scraper/queue/next-role
        """
        # Find next pending role, prioritized by candidate_count
        role = GlobalRole.query.filter_by(
            queue_status="pending"
        ).order_by(
            case(
                (GlobalRole.priority == "urgent", 4),
                (GlobalRole.priority == "high", 3),
                (GlobalRole.priority == "normal", 2),
                (GlobalRole.priority == "low", 1),
            ).desc(),
            GlobalRole.candidate_count.desc()  # Higher demand = higher priority
        ).first()
        
        if not role:
            return None
        
        # Mark role as processing
        role.queue_status = "processing"
        role.updated_at = datetime.utcnow()
        
        # Create session for tracking
        session = ScrapeSession(
            session_id=uuid.uuid4(),
            scraper_key_id=scraper_key.id,
            scraper_name=scraper_key.name,
            global_role_id=role.id,
            role_name=role.name,
            started_at=datetime.utcnow(),
            status="in_progress"
        )
        db.session.add(session)
        db.session.commit()
        
        return {
            "session_id": str(session.session_id),
            "role": {
                "id": role.id,
                "name": role.name,
                "aliases": role.aliases or [],
                "candidate_count": role.candidate_count
            }
        }
    
    @staticmethod
    def complete_session(
        session_id: str,
        jobs_data: list,
        scraper_key: ScraperApiKey
    ) -> dict:
        """
        Complete session and import jobs.
        Called by: POST /api/scraper/queue/jobs
        """
        from app.services.job_import_service import JobImportService
        from app.inngest import inngest_client
        import inngest
        
        session = ScrapeSession.query.filter_by(
            session_id=uuid.UUID(session_id),
            scraper_key_id=scraper_key.id
        ).first()
        
        if not session:
            raise ValueError("Session not found or unauthorized")
        
        # Import jobs
        import_result = JobImportService.import_jobs(
            jobs_data=jobs_data,
            scraper_key_id=scraper_key.id,
            scrape_session_id=session.session_id,
            normalized_role_id=session.global_role_id
        )
        
        # Update session
        session.completed_at = datetime.utcnow()
        session.duration_seconds = int(
            (session.completed_at - session.started_at).total_seconds()
        )
        session.jobs_found = len(jobs_data)
        session.jobs_imported = import_result["imported"]
        session.jobs_skipped = import_result["skipped"]
        session.status = "completed"
        
        # Update role status
        role = db.session.get(GlobalRole, session.global_role_id)
        if role:
            role.queue_status = "completed"
            role.last_scraped_at = datetime.utcnow()
            role.total_jobs_scraped += import_result["imported"]
        
        db.session.commit()
        
        # Trigger job matching event
        if import_result["job_ids"]:
            inngest_client.send_sync(
                inngest.Event(
                    name="jobs/imported",
                    data={
                        "job_ids": import_result["job_ids"],
                        "global_role_id": session.global_role_id,
                        "role_name": session.role_name,
                        "session_id": str(session.session_id),
                        "source": "scraper"
                    }
                )
            )
        
        return {
            "session_id": str(session.session_id),
            "jobs_found": session.jobs_found,
            "jobs_imported": session.jobs_imported,
            "jobs_skipped": session.jobs_skipped,
            "duration_seconds": session.duration_seconds,
            "matching_triggered": len(import_result["job_ids"]) > 0
        }
```

## Role Queue Priority

### Priority Levels

| Priority | Weight | Use Case |
|----------|--------|----------|
| `urgent` | 4 | High-value roles, manual escalation |
| `high` | 3 | Roles with many candidates waiting |
| `normal` | 2 | Regular queue processing |
| `low` | 1 | Background refresh (stale roles) |

### Queue Ordering Logic

```python
# Within same priority, higher candidate_count = scraped first
# This ensures roles with most candidates get jobs soonest

ORDER BY:
    1. priority DESC (urgent > high > normal > low)
    2. candidate_count DESC (100 candidates > 10 candidates)
```

### Queue Status Transitions

```
┌─────────┐    GET /next-role   ┌────────────┐    POST /jobs    ┌───────────┐
│ pending │──────────────────▶│ processing │─────────────────▶│ completed │
└─────────┘                    └────────────┘                  └───────────┘
                                      │
                                      │ Timeout (no jobs posted in 1h)
                                      ▼
                                ┌──────────┐    Auto-retry
                                │ pending  │◀───────────────────
                                └──────────┘
```

## External Scraper Integration

### API Key Authentication

```python
# app/middleware/scraper_auth.py

from functools import wraps
from flask import request, g, jsonify
from app.services.scraper_api_key_service import ScraperApiKeyService

def require_scraper_api_key(f):
    """Decorator to require valid scraper API key."""
    
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-Scraper-API-Key")
        
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        
        key_record = ScraperApiKeyService.validate_api_key(api_key)
        
        if not key_record:
            return jsonify({"error": "Invalid or expired API key"}), 401
        
        g.scraper_key = key_record
        return f(*args, **kwargs)
    
    return decorated
```

### Scraper API Routes

**New modular route structure**: `/api/scraper/queue/`

```python
# app/routes/scraper_routes.py

from flask import Blueprint, request, jsonify, g
from app.middleware.scraper_auth import require_scraper_api_key
from app.services.scrape_queue_service import ScrapeQueueService

scraper_bp = Blueprint("scraper", __name__, url_prefix="/api/scraper")


@scraper_bp.route('/queue/next-role', methods=['GET'])
@require_scraper_api_key
def get_next_role():
    """
    Get next role from queue to scrape.
    
    Response:
    {
        "session_id": "uuid-string",
        "role": {
            "id": 123,
            "name": "Python Developer",
            "aliases": ["Python Dev", "Python Engineer"],
            "candidate_count": 45
        }
    }
    """
    result = ScrapeQueueService.get_next_role(g.scraper_key)
    
    if not result:
        return jsonify({"message": "Queue empty"}), 204
    
    return jsonify(result), 200


@scraper_bp.route('/queue/jobs', methods=['POST'])
@require_scraper_api_key
def post_jobs():
    """
    Submit scraped jobs and complete session.
    
    Request Body:
    {
        "session_id": "uuid-from-get-next-role",
        "jobs": [
            {
                "external_job_id": "monster-123456",
                "platform": "monster",
                "title": "Senior Python Developer",
                "company": "TechCorp",
                "location": "San Francisco, CA",
                "description": "...",
                "skills": ["Python", "Django", "AWS"],
                "salary_min": 120000,
                "salary_max": 180000,
                "job_url": "https://monster.com/...",
                "posted_date": "2024-01-15"
            },
            ...
        ]
    }
    
    Response:
    {
        "session_id": "uuid",
        "jobs_found": 25,
        "jobs_imported": 20,
        "jobs_skipped": 5,
        "duration_seconds": 45,
        "matching_triggered": true
    }
    """
    data = request.get_json()
    
    session_id = data.get("session_id")
    jobs = data.get("jobs", [])
    
    if not session_id:
        return jsonify({"error": "session_id required"}), 400
    
    try:
        result = ScrapeQueueService.complete_session(
            session_id=session_id,
            jobs_data=jobs,
            scraper_key=g.scraper_key
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@scraper_bp.route('/queue/stats', methods=['GET'])
@require_scraper_api_key
def get_queue_stats():
    """Get queue statistics (for scraper health checks)."""
    
```

## Data Models

### ScraperApiKey Model

```python
# app/models/scraper_api_key.py

class ScraperApiKey(BaseModel):
    """API key for external job scrapers."""
    
    __tablename__ = "scraper_api_keys"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # e.g., "Production Scraper 1"
    key_hash = Column(String(255), unique=True, nullable=False, index=True)  # SHA256 hash
    
    # Permissions
    is_active = Column(Boolean, default=True)
    allowed_sources = Column(ARRAY(String), nullable=True)  # null = all sources
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("pm_admins.id"), nullable=True)
    
    # Relationships
    sessions = relationship("ScrapeSession", back_populates="scraper_key")
```

### ScrapeSession Model (Simplified Observability)

```python
# app/models/scrape_session.py

class ScrapeSession(BaseModel):
    """Simplified session tracking for scraper observability."""
    
    __tablename__ = "scrape_sessions"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Scraper Identification
    scraper_key_id = Column(Integer, ForeignKey("scraper_api_keys.id"), nullable=False)
    scraper_name = Column(String(100))  # Cached from API key for reporting
    
    # What's Being Scraped (links to role queue)
    global_role_id = Column(Integer, ForeignKey("global_roles.id"), nullable=True)
    role_name = Column(String(255))  # Cached for reporting
    
    # Timing (Session starts on GET /next-role, completes on POST /jobs)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Results (populated on POST /jobs)
    jobs_found = Column(Integer, default=0)
    jobs_imported = Column(Integer, default=0)
    jobs_skipped = Column(Integer, default=0)
    
    # Status
    status = Column(String(20), default="in_progress")  # in_progress, completed, failed, timeout
    error_message = Column(Text, nullable=True)
    
    # Relationships
    scraper_key = relationship("ScraperApiKey", back_populates="sessions")
    role = relationship("GlobalRole")
    
    __table_args__ = (
        Index("idx_session_scraper_key", "scraper_key_id"),
        Index("idx_session_started", "started_at"),
        Index("idx_session_status", "status"),
    )
```

## CentralD Observability API (PM_ADMIN)

### Scraper Monitoring Routes

```python
# app/routes/scraper_monitoring_routes.py

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func
from app.middleware.pm_admin import require_pm_admin
from app.models import ScrapeSession, GlobalRole, ScraperApiKey
from app import db

scraper_monitoring_bp = Blueprint(
    "scraper_monitoring", 
    __name__, 
    url_prefix="/api/scraper-monitoring"
)


@scraper_monitoring_bp.route('/sessions', methods=['GET'])
@require_pm_admin
def get_recent_sessions():
    """Get recent scrape sessions for dashboard monitoring."""
    
    scraper_key_id = request.args.get("scraper_key_id", type=int)
    status = request.args.get("status")
    hours = request.args.get("hours", 24, type=int)
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    query = ScrapeSession.query.filter(
        ScrapeSession.started_at >= since
    )
    
    if scraper_key_id:
        query = query.filter_by(scraper_key_id=scraper_key_id)
    if status:
        query = query.filter_by(status=status)
    
    sessions = query.order_by(
        ScrapeSession.started_at.desc()
    ).limit(100).all()
    
    return jsonify({
        "sessions": [{
            "id": s.id,
            "session_id": str(s.session_id),
            "scraper_name": s.scraper_name,
            "role_name": s.role_name,
            "status": s.status,
            "started_at": s.started_at.isoformat(),
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "duration_seconds": s.duration_seconds,
            "jobs_found": s.jobs_found,
            "jobs_imported": s.jobs_imported,
            "jobs_skipped": s.jobs_skipped,
            "error_message": s.error_message
        } for s in sessions]
    }), 200


@scraper_monitoring_bp.route('/stats', methods=['GET'])
@require_pm_admin
def get_scraper_stats():
    """Get aggregated scraper statistics for dashboard."""
    
    hours = request.args.get("hours", 24, type=int)
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Active scrapers (with in_progress session)
    active_cutoff = datetime.utcnow() - timedelta(minutes=10)
    active_scrapers = db.session.query(
        func.count(func.distinct(ScrapeSession.scraper_key_id))
    ).filter(
        ScrapeSession.updated_at >= active_cutoff,
        ScrapeSession.status == "in_progress"
    ).scalar() or 0
    
    # Totals for time period
    totals = db.session.query(
        func.count(ScrapeSession.id).label("total_sessions"),
        func.sum(ScrapeSession.jobs_found).label("total_found"),
        func.sum(ScrapeSession.jobs_imported).label("total_imported"),
        func.avg(ScrapeSession.duration_seconds).label("avg_duration")
    ).filter(
        ScrapeSession.started_at >= since,
        ScrapeSession.status == "completed"
    ).first()
    
    # Per-scraper breakdown
    per_scraper = db.session.query(
        ScrapeSession.scraper_name,
        ScrapeSession.scraper_key_id,
        func.count(ScrapeSession.id).label("session_count"),
        func.sum(ScrapeSession.jobs_imported).label("jobs_imported"),
        func.max(ScrapeSession.role_name).label("last_role"),
        func.max(ScrapeSession.updated_at).label("last_activity")
    ).filter(
        ScrapeSession.started_at >= since
    ).group_by(
        ScrapeSession.scraper_key_id,
        ScrapeSession.scraper_name
    ).all()
    
    return jsonify({
        "active_scrapers": active_scrapers,
        "totals": {
            "total_sessions": totals.total_sessions or 0,
            "jobs_found": totals.total_found or 0,
            "jobs_imported": totals.total_imported or 0,
            "avg_duration_seconds": round(totals.avg_duration or 0, 2)
        },
        "per_scraper": [{
            "scraper_name": s.scraper_name,
            "scraper_key_id": s.scraper_key_id,
            "session_count": s.session_count,
            "jobs_imported": s.jobs_imported or 0,
            "last_role": s.last_role,
            "last_activity": s.last_activity.isoformat() if s.last_activity else None
        } for s in per_scraper]
    }), 200


@scraper_monitoring_bp.route('/queue', methods=['GET'])
@require_pm_admin
def get_role_queue():
    """Get current role queue status."""
    
    roles = GlobalRole.query.filter(
        GlobalRole.queue_status.in_(["pending", "processing"])
    ).order_by(
        case(
            (GlobalRole.priority == "urgent", 4),
            (GlobalRole.priority == "high", 3),
            (GlobalRole.priority == "normal", 2),
            (GlobalRole.priority == "low", 1),
        ).desc(),
        GlobalRole.candidate_count.desc()
    ).limit(50).all()
    
    return jsonify({
        "queue": [{
            "id": r.id,
            "name": r.name,
            "queue_status": r.queue_status,
            "priority": r.priority,
            "candidate_count": r.candidate_count,
            "last_scraped_at": r.last_scraped_at.isoformat() if r.last_scraped_at else None
        } for r in roles]
    }), 200
```

## Queue Statistics

### Queue Statistics Service

```python
# app/services/scrape_queue_service.py

@staticmethod
def get_queue_statistics() -> dict:
    """Get role queue statistics for monitoring."""
    
    stats = db.session.query(
        GlobalRole.queue_status,
        func.count(GlobalRole.id).label("count"),
        func.sum(GlobalRole.candidate_count).label("candidate_count")
    ).group_by(GlobalRole.queue_status).all()
    
    status_counts = {s.queue_status: {"roles": s.count, "candidates": s.candidate_count or 0} for s in stats}
    
    # Recent session stats
    last_24h = datetime.utcnow() - timedelta(hours=24)
    session_stats = db.session.query(
        func.count(ScrapeSession.id).label("total"),
        func.sum(ScrapeSession.jobs_imported).label("jobs_imported"),
        func.avg(ScrapeSession.duration_seconds).label("avg_duration")
    ).filter(
        ScrapeSession.started_at >= last_24h,
        ScrapeSession.status == "completed"
    ).first()
    
    return {
        "queue": {
            "pending": status_counts.get("pending", {"roles": 0, "candidates": 0}),
            "processing": status_counts.get("processing", {"roles": 0, "candidates": 0}),
            "completed": status_counts.get("completed", {"roles": 0, "candidates": 0})
        },
        "last_24h": {
            "sessions_completed": session_stats.total or 0,
            "jobs_imported": session_stats.jobs_imported or 0,
            "avg_duration_seconds": round(session_stats.avg_duration or 0, 2)
        }
    }
```

### Stale Session Cleanup

```python
@staticmethod
def cleanup_stale_sessions(timeout_minutes: int = 60):
    """Reset roles stuck in processing state (no jobs posted within timeout)."""
    
    cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    
    # Find stale sessions
    stale_sessions = ScrapeSession.query.filter(
        ScrapeSession.status == "in_progress",
        ScrapeSession.started_at < cutoff
    ).all()
    
    reset_count = 0
    for session in stale_sessions:
        # Mark session as timeout
        session.status = "timeout"
        session.error_message = f"No jobs posted within {timeout_minutes} minutes"
        
        # Reset the role to pending for retry
        if session.global_role_id:
            role = db.session.get(GlobalRole, session.global_role_id)
            if role and role.queue_status == "processing":
                role.queue_status = "pending"
        
        reset_count += 1
    
    db.session.commit()
    return reset_count
```

---

## Complete Integration Flow

### End-to-End Role-Based Scraping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE ROLE-BASED SCRAPING FLOW                        │
└─────────────────────────────────────────────────────────────────────────────┘

1. CANDIDATE ONBOARDING
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ Candidate selects: "Senior Python Developer", "Django Developer"       │
   │                              │                                          │
   │                              ▼                                          │
   │ AI Normalization (Option B): Check embedding similarity first          │
   │   - Generate embedding for "Senior Python Developer"                    │
   │   - Search global_roles for similar role (cosine > 0.85)               │
   │   - FOUND: "Python Developer" → use existing role                      │
   │   - NOT FOUND: Call Gemini AI to normalize → create new role           │
   │                              │                                          │
   │                              ▼                                          │
   │ Create candidate_global_roles link                                     │
   │ Increment global_role.candidate_count                                   │
   │ Set global_role.queue_status = "pending" (if not already)              │
   └─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
2. SCRAPER FETCHES ROLE
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ GET /api/scraper/queue/next-role                                        │
   │ Header: X-Scraper-API-Key: abc123...                                    │
   │                              │                                          │
   │ Response:                    │                                          │
   │ {                            ▼                                          │
   │   "session_id": "uuid",      ┌──────────────────────┐                  │
   │   "role": {                  │ Session Created      │                  │
   │     "id": 123,               │ status="in_progress" │                  │
   │     "name": "Python Dev",    │ Role status="proc"   │                  │
   │     "candidate_count": 45    └──────────────────────┘                  │
   │   }                                                                     │
   │ }                                                                       │
   └─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
3. SCRAPER WORKS (EXTERNAL)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ Scraper scrapes Monster, Indeed, Dice, etc. for "Python Developer"     │
   │ (No callbacks to Blacklight during this phase - simplified)             │
   └─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
4. SCRAPER POSTS JOBS
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ POST /api/scraper/queue/jobs                                            │
   │ {                                                                       │
   │   "session_id": "uuid-from-step-2",                                     │
   │   "jobs": [                                                             │
   │     { "platform": "monster", "title": "Python Dev", ... },              │
   │     { "platform": "indeed", "title": "Python Engineer", ... }          │
   │   ]                                                                     │
   │ }                                                                       │
   │                              │                                          │
   │                              ▼                                          │
   │ ┌────────────────────────────────────────────────────────────────────┐ │
   │ │ 1. Import jobs to job_postings (dedupe by external_job_id)        │ │
   │ │ 2. Link jobs to global_role via normalized_role_id                │ │
   │ │ 3. Complete session (status="completed", duration, counts)        │ │
   │ │ 4. Update role (queue_status="completed", last_scraped_at)        │ │
   │ │ 5. TRIGGER EVENT: "jobs/imported" with job_ids + role_id          │ │
   │ └────────────────────────────────────────────────────────────────────┘ │
   └─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
5. EVENT-DRIVEN MATCHING (Inngest)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ Event: "jobs/imported"                                                  │
   │ Data: { job_ids: [1,2,3], global_role_id: 123, role_name: "Python Dev" }│
   │                              │                                          │
   │                              ▼                                          │
   │ Workflow: match-jobs-to-candidates                                      │
   │   1. Find all candidates linked to global_role_id=123                  │
   │      (via candidate_global_roles)                                       │
   │   2. For each candidate:                                                │
   │      - Calculate multi-factor match score                               │
   │      - Store in candidate_job_matches if score >= 50                   │
   │   3. Return summary: { candidates_matched: 45, matches_created: 180 }  │
   └─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
6. CANDIDATES SEE NEW MATCHES (Portal)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ Recruiters view "Your Candidates" → "Job Matches" tab                  │
   │ New matches appear immediately after scraper posts jobs                 │
   └─────────────────────────────────────────────────────────────────────────┘
```

## Rate Limiting

### Per-API-Key Limits

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=lambda: g.scraper_key.id if hasattr(g, 'scraper_key') else get_remote_address()
)

@scraper_bp.route('/queue/next-role', methods=['GET'])
@require_scraper_api_key
@limiter.limit("60/minute")  # 60 requests per minute per API key
def get_next_role():
    ...
```

### Job Board-Specific Limits

| Source | Rate Limit | Reason |
|--------|------------|--------|
| Monster | 30/min | ToS compliance |
| Indeed | 20/min | More restrictive |
| Glassdoor | 15/min | Heavy rate limiting |
| TechFetch | 60/min | More permissive |
| Dice | 30/min | Standard |

## Scheduled Cleanup Tasks

### Stale Session Cleanup (Inngest)

```python
@inngest_client.create_function(
    fn_id="cleanup-stale-sessions",
    trigger=inngest.TriggerCron(cron="*/15 * * * *"),  # Every 15 minutes
    retries=1
)
async def cleanup_stale_sessions(ctx, step):
    """Reset roles stuck in processing state."""
    
    def cleanup():
        return ScrapeQueueService.cleanup_stale_sessions(timeout_minutes=60)
    
    reset_count = await step.run("cleanup", cleanup)
    
    return {"roles_reset": reset_count}
```

### Role Queue Reset (Daily)

```python
@inngest_client.create_function(
    fn_id="reset-completed-roles",
    trigger=inngest.TriggerCron(cron="0 0 * * *"),  # Midnight daily
    retries=1
)
async def reset_completed_roles(ctx, step):
    """Reset completed roles back to pending for re-scraping (stale data prevention)."""
    
    def reset_roles():
        from datetime import datetime, timedelta
        
        # Roles completed more than 24 hours ago
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        stale_roles = GlobalRole.query.filter(
            GlobalRole.queue_status == "completed",
            GlobalRole.last_scraped_at < cutoff,
            GlobalRole.candidate_count > 0  # Only if candidates still want it
        ).all()
        
        for role in stale_roles:
            role.queue_status = "pending"
        
        db.session.commit()
        return len(stale_roles)
    
    reset_count = await step.run("reset", reset_roles)
    
    return {"roles_reset_to_pending": reset_count}
```

---

## See Also

- [03-DATA-MODELS.md](./03-DATA-MODELS.md) - Database schemas for global_roles, scrape_sessions
- [07-INNGEST-WORKFLOWS.md](./07-INNGEST-WORKFLOWS.md) - Event-driven matching workflows
- [10-AI-ROLE-NORMALIZATION.md](./10-AI-ROLE-NORMALIZATION.md) - Option B: Embedding similarity + AI normalization
- [11-CENTRALD-DASHBOARD.md](./11-CENTRALD-DASHBOARD.md) - Scraper monitoring dashboard in CentralD
- [08-API-ENDPOINTS.md](./08-API-ENDPOINTS.md) - Complete API reference

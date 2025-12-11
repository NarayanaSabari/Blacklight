# Phase 4: Inngest Workflows

## Overview

Inngest handles all background job processing for the job matching system. This includes event-driven matching, scheduled cleanup tasks, and batch operations.

**Key Architecture Decision**: All matching is **event-driven** (no nightly batch refresh).

---

## Workflow Summary

| Workflow | Trigger | Purpose |
|----------|---------|--------|
| `match-jobs-to-candidates` | Event (`jobs/imported`) | Match new jobs to candidates with matching preferred roles |
| `generate-candidate-matches` | Event (`job-match/generate-candidate`) | Generate matches for single candidate (on approval) |
| `expire-old-jobs` | Cron (3 AM) | Mark expired jobs |
| `cleanup-stale-sessions` | Cron (every 15 min) | Reset stuck scraper sessions |
| `reset-completed-roles` | Cron (midnight) | Re-queue roles for fresh scraping |
| `update-job-embeddings` | Event | Regenerate embedding on job update |
| `backfill-embeddings` | Manual | Generate missing embeddings |

---

## ~~Nightly Refresh~~ (REMOVED)

> **The nightly-match-refresh workflow has been REMOVED.**
> 
> Matching is now fully event-driven:
> - Jobs imported → matches created for candidates with that preferred role
> - Candidate approved → matches created for that candidate

---

## Inngest Setup

### Configuration

```python
# server/app/inngest/__init__.py
import inngest
import os

inngest_client = inngest.Inngest(
    app_id="blacklight",
    event_key=os.getenv("INNGEST_EVENT_KEY"),
    signing_key=os.getenv("INNGEST_SIGNING_KEY")
)
```

### Flask Integration

```python
# server/app/__init__.py
from app.inngest import inngest_client

def create_app(config=None):
    app = Flask(__name__)
    
    # ... other setup ...
    
    # Register Inngest
    from app.inngest.functions import job_matching_tasks
    
    return app
```

---

## Workflow 1: Match New Jobs to Candidates (Primary)

### Event-Driven Job Matching

**This is the primary matching workflow.** When new jobs are imported from the scraper, this workflow automatically matches them to candidates who have matching preferred roles.

**Triggered when:**
- New jobs are imported via scraper API
- Batch job import completes

```python
# server/app/inngest/functions/job_matching_tasks.py
import inngest
from app.inngest import inngest_client
from app.services.job_matching_service import JobMatchingService
from app.services.embedding_service import EmbeddingService
from app import db

@inngest_client.create_function(
    fn_id="match-jobs-to-candidates",
    trigger=inngest.TriggerEvent(event="jobs/imported"),
    retries=3,
    name="Match New Jobs to Candidates"
)
async def match_jobs_to_candidates(ctx, step):
    """
    Match newly imported jobs to candidates with matching preferred roles.
    
    Event data:
    - job_ids: List[int] - IDs of newly imported jobs
    - batch_id: str - Import batch ID
    - source: str - Job source (monster, indeed, etc.)
    """
    job_ids = ctx.event.data.get("job_ids", [])
    batch_id = ctx.event.data.get("batch_id")
    source = ctx.event.data.get("source")
    
    if not job_ids:
        return {"message": "No jobs to process", "matches_created": 0}
    
    # Step 1: Get jobs with their normalized roles
    def get_jobs_with_roles():
        from app.models import JobPosting, GlobalRole
        
        jobs_data = []
        jobs = JobPosting.query.filter(JobPosting.id.in_(job_ids)).all()
        
        for job in jobs:
            job_info = {
                "id": job.id,
                "title": job.title,
                "normalized_role_id": job.normalized_role_id,
                "has_embedding": job.embedding is not None
            }
            
            # Get the normalized role name
            if job.normalized_role_id:
                role = db.session.get(GlobalRole, job.normalized_role_id)
                if role:
                    job_info["role_name"] = role.name
            
            jobs_data.append(job_info)
        
        return jobs_data
    
    jobs_data = await step.run("get-jobs-with-roles", get_jobs_with_roles)
    
    # Step 2: Generate embeddings for jobs without them
    def ensure_job_embeddings():
        from app.models import JobPosting
        embedding_service = EmbeddingService()
        
        jobs_without_embedding = [j for j in jobs_data if not j["has_embedding"]]
        generated_count = 0
        
        for job_info in jobs_without_embedding:
            job = db.session.get(JobPosting, job_info["id"])
            if job:
                embedding = embedding_service.generate_job_embedding(job)
                job.embedding = embedding
                generated_count += 1
        
        db.session.commit()
        return {"embeddings_generated": generated_count}
    
    embedding_result = await step.run("ensure-job-embeddings", ensure_job_embeddings)
    
    # Step 3: Find candidates with matching preferred roles
    def find_matching_candidates():
        from app.models import Candidate, JobPosting, GlobalRole
        
        # Get unique role IDs from the imported jobs
        role_ids = set()
        for job_info in jobs_data:
            if job_info.get("normalized_role_id"):
                role_ids.add(job_info["normalized_role_id"])
        
        if not role_ids:
            return {"candidates": [], "role_ids": []}
        
        # Find candidates whose preferred_roles match these roles
        # preferred_roles is stored as array of role names or role IDs
        candidates = Candidate.query.filter(
            Candidate.status.in_(['approved', 'ready_for_assignment']),
            Candidate.embedding.isnot(None)
        ).all()
        
        # Filter candidates by preferred roles
        matching_candidates = []
        for candidate in candidates:
            if not candidate.preferred_roles:
                continue
            
            # Check if any preferred role matches
            for preferred_role in candidate.preferred_roles:
                # preferred_role could be a role name or role ID
                if isinstance(preferred_role, int) and preferred_role in role_ids:
                    matching_candidates.append({
                        "id": candidate.id,
                        "tenant_id": candidate.tenant_id,
                        "preferred_roles": candidate.preferred_roles
                    })
                    break
                elif isinstance(preferred_role, str):
                    # Check by role name
                    for job_info in jobs_data:
                        if job_info.get("role_name", "").lower() == preferred_role.lower():
                            matching_candidates.append({
                                "id": candidate.id,
                                "tenant_id": candidate.tenant_id,
                                "preferred_roles": candidate.preferred_roles
                            })
                            break
        
        return {
            "candidates": matching_candidates,
            "role_ids": list(role_ids)
        }
    
    candidate_result = await step.run("find-matching-candidates", find_matching_candidates)
    matching_candidates = candidate_result["candidates"]
    
    if not matching_candidates:
        return {
            "batch_id": batch_id,
            "source": source,
            "jobs_processed": len(job_ids),
            "embeddings_generated": embedding_result["embeddings_generated"],
            "candidates_found": 0,
            "matches_created": 0,
            "message": "No candidates found with matching preferred roles"
        }
    
    # Step 4: Generate matches for each candidate-job pair
    def generate_matches():
        from app.models import Candidate, JobPosting, CandidateJobMatch
        matching_service = JobMatchingService()
        
        matches_created = 0
        
        for candidate_info in matching_candidates:
            candidate = db.session.get(Candidate, candidate_info["id"])
            if not candidate or candidate.embedding is None:
                continue
            
            # Match against the newly imported jobs only
            for job_id in job_ids:
                job = db.session.get(JobPosting, job_id)
                if not job or job.embedding is None:
                    continue
                
                # Check if match already exists
                existing = CandidateJobMatch.query.filter_by(
                    candidate_id=candidate.id,
                    job_posting_id=job.id
                ).first()
                
                if existing:
                    continue
                
                # Calculate match score
                result = matching_service.calculate_match_score(
                    candidate, job,
                    list(candidate.embedding),
                    list(job.embedding)
                )
                
                # Only store matches above threshold
                if result['match_score'] >= 50.0:
                    match = CandidateJobMatch(
                        candidate_id=candidate.id,
                        job_posting_id=job.id,
                        match_score=result['match_score'],
                        skill_match_score=result['skill_match_score'],
                        experience_match_score=result['experience_match_score'],
                        location_match_score=result['location_match_score'],
                        salary_match_score=result['salary_match_score'],
                        semantic_similarity=result['semantic_similarity'],
                        matched_skills=result['matched_skills'],
                        missing_skills=result['missing_skills'],
                        match_reasons=result['match_reasons'],
                        is_recommended=result['match_score'] >= 70.0
                    )
                    db.session.add(match)
                    matches_created += 1
        
        db.session.commit()
        return {"matches_created": matches_created}
    
    match_result = await step.run("generate-matches", generate_matches)
    
    return {
        "batch_id": batch_id,
        "source": source,
        "jobs_processed": len(job_ids),
        "embeddings_generated": embedding_result["embeddings_generated"],
        "candidates_found": len(matching_candidates),
        "matches_created": match_result["matches_created"]
    }
```

### Triggering from Job Import

```python
# From job import service
from app.inngest import inngest_client
import inngest

def import_jobs(jobs_data: list, source: str, batch_id: str):
    # ... import logic, store jobs in DB ...
    
    # Get IDs of newly created jobs
    job_ids = [job.id for job in created_jobs]
    
    # Trigger matching workflow
    inngest_client.send_sync(
        inngest.Event(
            name="jobs/imported",
            data={
                "job_ids": job_ids,
                "batch_id": batch_id,
                "source": source
            }
        )
    )
```

---

## Workflow 2: Generate Candidate Matches (On Onboarding)

### Event-Driven Matching

Triggered when:
- Candidate onboarding is approved
- Candidate updates their profile
- Manual trigger from UI

```python
# server/app/inngest/functions/job_matching_tasks.py
import inngest
from app.inngest import inngest_client
from app.services.job_matching_service import JobMatchingService
from app.services.embedding_service import EmbeddingService
from app import db

@inngest_client.create_function(
    fn_id="generate-candidate-matches",
    trigger=inngest.TriggerEvent(event="job-match/generate-candidate"),
    retries=3,
    name="Generate Candidate Matches"
)
async def generate_candidate_matches(ctx, step):
    """
    Generate job matches for a single candidate.
    
    Event data:
    - candidate_id: int
    - tenant_id: int
    - trigger: str (onboarding_approval, profile_update, manual)
    """
    candidate_id = ctx.event.data.get("candidate_id")
    tenant_id = ctx.event.data.get("tenant_id")
    trigger = ctx.event.data.get("trigger", "manual")
    
    # Step 1: Validate candidate exists
    def validate_candidate():
        from app.models import Candidate
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")
        if candidate.tenant_id != tenant_id:
            raise ValueError(f"Tenant mismatch for candidate {candidate_id}")
        return {
            "id": candidate.id,
            "name": f"{candidate.first_name} {candidate.last_name}",
            "skills": candidate.skills or [],
            "status": candidate.status
        }
    
    candidate_data = await step.run("validate-candidate", validate_candidate)
    
    # Step 2: Ensure candidate has embedding
    def ensure_embedding():
        from app.models import Candidate
        candidate = db.session.get(Candidate, candidate_id)
        
        if candidate.embedding is None:
            embedding_service = EmbeddingService()
            embedding = embedding_service.generate_candidate_embedding(candidate)
            candidate.embedding = embedding
            db.session.commit()
            return {"generated": True}
        return {"generated": False}
    
    embedding_result = await step.run("ensure-embedding", ensure_embedding)
    
    # Step 3: Generate matches
    def generate_matches():
        from app.models import Candidate, JobPosting, CandidateJobMatch
        
        candidate = db.session.get(Candidate, candidate_id)
        matching_service = JobMatchingService()
        
        # Get all active jobs
        jobs = JobPosting.query.filter(
            JobPosting.status == 'active'
        ).all()
        
        # Delete existing matches
        CandidateJobMatch.query.filter(
            CandidateJobMatch.candidate_id == candidate_id
        ).delete()
        
        matches_created = 0
        for job in jobs:
            if job.embedding is None:
                continue
            
            result = matching_service.calculate_match_score(
                candidate, job,
                list(candidate.embedding),
                list(job.embedding)
            )
            
            # Only store matches above threshold
            if result['match_score'] >= 50.0:
                match = CandidateJobMatch(
                    candidate_id=candidate_id,
                    job_posting_id=job.id,
                    match_score=result['match_score'],
                    skill_match_score=result['skill_match_score'],
                    experience_match_score=result['experience_match_score'],
                    location_match_score=result['location_match_score'],
                    salary_match_score=result['salary_match_score'],
                    semantic_similarity=result['semantic_similarity'],
                    matched_skills=result['matched_skills'],
                    missing_skills=result['missing_skills'],
                    match_reasons=result['match_reasons'],
                    is_recommended=result['match_score'] >= 70.0
                )
                db.session.add(match)
                matches_created += 1
        
        db.session.commit()
        return {"matches_created": matches_created, "jobs_processed": len(jobs)}
    
    match_result = await step.run("generate-matches", generate_matches)
    
    # Step 4: Update candidate status (if onboarding)
    if trigger == "onboarding_approval":
        def update_status():
            from app.models import Candidate
            candidate = db.session.get(Candidate, candidate_id)
            candidate.status = 'ready_for_assignment'
            db.session.commit()
            return {"new_status": candidate.status}
        
        await step.run("update-status", update_status)
    
    return {
        "candidate_id": candidate_id,
        "candidate_name": candidate_data['name'],
        "embedding_generated": embedding_result['generated'],
        "matches_created": match_result['matches_created'],
        "jobs_processed": match_result['jobs_processed'],
        "trigger": trigger
    }
```

### Triggering the Event

```python
# From onboarding approval service (existing code)
from app.inngest import inngest_client
import inngest

def approve_candidate_onboarding(invitation_id: int, tenant_id: int):
    # ... approval logic ...
    
    # Trigger match generation
    inngest_client.send_sync(
        inngest.Event(
            name="job-match/generate-candidate",
            data={
                "candidate_id": candidate.id,
                "tenant_id": tenant_id,
                "trigger": "onboarding_approval"
            }
        )
    )
```

---

## ~~Workflow 2: Nightly Match Refresh~~ (REMOVED)

> **⚠️ DEPRECATED - DO NOT IMPLEMENT**
> 
> The nightly match refresh workflow has been **permanently removed** in favor of event-driven matching.
> 
> **Why Removed:**
> - Inefficient: Recomputes ALL matches even if nothing changed
> - Wasteful: Most matches don't change day-to-day
> - Delayed: Users wait until 2 AM to see new job matches
> - Resource heavy: Processing all tenants/candidates is expensive
>
> **Replaced By:**
> 1. `jobs/imported` event → Matches created immediately when scraper posts jobs
> 2. `job-match/generate-candidate` event → Matches created when candidate approved
>
> **Benefits of Event-Driven:**
> - Real-time: Matches appear within seconds of job import
> - Efficient: Only processes relevant candidates (those with matching preferred roles)
> - Incremental: No full recomputation needed
> - Scalable: Processing distributed across events, not batched

---

## Workflow 3: Expire Old Jobs

### Daily Cleanup

```python
@inngest_client.create_function(
    fn_id="expire-old-jobs",
    trigger=inngest.TriggerCron(cron="0 3 * * *"),  # 3 AM daily
    retries=1,
    name="Expire Old Jobs"
)
async def expire_old_jobs(ctx, step):
    """
    Mark jobs as expired if older than 30 days.
    Runs at 3 AM daily.
    """
    def expire_jobs():
        from app.models import JobPosting
        from datetime import datetime, timedelta
        from sqlalchemy import or_
        
        cutoff = datetime.utcnow() - timedelta(days=30)
        
        # Expire based on posted_date or imported_at (whichever is earlier)
        expired_count = JobPosting.query.filter(
            JobPosting.status == 'active',
            or_(
                JobPosting.posted_date <= cutoff.date(),
                JobPosting.imported_at <= cutoff
            )
        ).update({'status': 'expired'}, synchronize_session=False)
        
        db.session.commit()
        
        return expired_count
    
    expired_count = await step.run("expire-jobs", expire_jobs)
    
    # Clean up orphaned matches
    def cleanup_matches():
        from app.models import CandidateJobMatch, JobPosting
        
        # Delete matches for expired jobs
        deleted = db.session.execute(
            db.delete(CandidateJobMatch).where(
                CandidateJobMatch.job_posting_id.in_(
                    db.select(JobPosting.id).where(JobPosting.status == 'expired')
                )
            )
        )
        db.session.commit()
        return deleted.rowcount
    
    matches_deleted = await step.run("cleanup-matches", cleanup_matches)
    
    return {
        "jobs_expired": expired_count,
        "matches_deleted": matches_deleted
    }
```

---

## Workflow 4: Update Job Embeddings

### On Job Content Change

```python
@inngest_client.create_function(
    fn_id="update-job-embedding",
    trigger=inngest.TriggerEvent(event="job-posting/updated"),
    retries=3,
    name="Update Job Embedding"
)
async def update_job_embedding(ctx, step):
    """
    Regenerate embedding when job content changes.
    
    Event data:
    - job_id: int
    - changed_fields: list (title, description, skills, etc.)
    """
    job_id = ctx.event.data.get("job_id")
    changed_fields = ctx.event.data.get("changed_fields", [])
    
    # Only regenerate if content fields changed
    content_fields = {'title', 'description', 'skills', 'requirements'}
    if not content_fields.intersection(changed_fields):
        return {"skipped": True, "reason": "No content fields changed"}
    
    def regenerate_embedding():
        from app.models import JobPosting
        
        job = db.session.get(JobPosting, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        embedding_service = EmbeddingService()
        embedding = embedding_service.generate_job_embedding(job)
        job.embedding = embedding
        db.session.commit()
        
        return {"embedding_updated": True}
    
    result = await step.run("regenerate-embedding", regenerate_embedding)
    
    return {
        "job_id": job_id,
        "changed_fields": changed_fields,
        **result
    }
```

---

## Workflow 5: Backfill Embeddings

### Manual Batch Processing

```python
@inngest_client.create_function(
    fn_id="backfill-embeddings",
    trigger=inngest.TriggerEvent(event="system/backfill-embeddings"),
    retries=1,
    name="Backfill Missing Embeddings"
)
async def backfill_embeddings(ctx, step):
    """
    Generate embeddings for entities missing them.
    
    Event data:
    - entity_type: 'jobs' or 'candidates'
    - batch_size: int (default 100)
    """
    entity_type = ctx.event.data.get("entity_type", "jobs")
    batch_size = ctx.event.data.get("batch_size", 100)
    
    if entity_type == "jobs":
        def backfill_jobs():
            from app.models import JobPosting
            
            jobs = JobPosting.query.filter(
                JobPosting.embedding.is_(None),
                JobPosting.status == 'active'
            ).limit(batch_size).all()
            
            embedding_service = EmbeddingService()
            
            for job in jobs:
                try:
                    embedding = embedding_service.generate_job_embedding(job)
                    job.embedding = embedding
                except Exception as e:
                    continue  # Skip failures
            
            db.session.commit()
            return {"processed": len(jobs)}
        
        result = await step.run("backfill-jobs", backfill_jobs)
        
    elif entity_type == "candidates":
        def backfill_candidates():
            from app.models import Candidate
            
            candidates = Candidate.query.filter(
                Candidate.embedding.is_(None),
                Candidate.status.in_(['approved', 'ready_for_assignment'])
            ).limit(batch_size).all()
            
            embedding_service = EmbeddingService()
            
            for candidate in candidates:
                try:
                    embedding = embedding_service.generate_candidate_embedding(candidate)
                    candidate.embedding = embedding
                except Exception as e:
                    continue
            
            db.session.commit()
            return {"processed": len(candidates)}
        
        result = await step.run("backfill-candidates", backfill_candidates)
    
    return {
        "entity_type": entity_type,
        "batch_size": batch_size,
        **result
    }
```

---

## Event Types Reference

### Job Matching Events

| Event Name | Data | Description |
|------------|------|-------------|
| `job-match/generate-candidate` | `{candidate_id, tenant_id, trigger}` | Generate matches for one candidate |
| `job-match/refresh-candidate` | `{candidate_id, tenant_id}` | Refresh existing matches |
| `job-posting/updated` | `{job_id, changed_fields}` | Job content changed |
| `system/backfill-embeddings` | `{entity_type, batch_size}` | Backfill missing embeddings |

### Sending Events

```python
from app.inngest import inngest_client
import inngest

# Async (fire and forget)
inngest_client.send_sync(
    inngest.Event(
        name="job-match/generate-candidate",
        data={
            "candidate_id": 123,
            "tenant_id": 456,
            "trigger": "manual"
        }
    )
)

# Multiple events
inngest_client.send_sync([
    inngest.Event(name="event1", data={...}),
    inngest.Event(name="event2", data={...}),
])
```

---

## Monitoring & Debugging

### Inngest Dashboard

Access at: `http://localhost:8288` (dev server)

Monitor:
- Running functions
- Failed executions
- Retry attempts
- Event history

### Logging

```python
import logging

logger = logging.getLogger(__name__)

@inngest_client.create_function(...)
async def my_function(ctx, step):
    logger.info(f"Starting function with event: {ctx.event.data}")
    
    # ... function logic ...
    
    logger.info(f"Function completed successfully")
```

### Error Handling

```python
@inngest_client.create_function(
    fn_id="my-function",
    trigger=inngest.TriggerEvent(event="my/event"),
    retries=3,  # Automatic retries
    name="My Function"
)
async def my_function(ctx, step):
    try:
        result = await step.run("my-step", do_work)
    except Exception as e:
        logger.error(f"Step failed: {e}")
        raise  # Re-raise to trigger retry
```

---

## Environment Variables

```bash
# Inngest configuration
INNGEST_EVENT_KEY=your-event-key
INNGEST_SIGNING_KEY=your-signing-key

# For local development
INNGEST_DEV=1
INNGEST_DEV_SERVER_URL=http://localhost:8288
```

---

## Next: [08-API-ENDPOINTS.md](./08-API-ENDPOINTS.md) - REST API Reference

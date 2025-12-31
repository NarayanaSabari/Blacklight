"""
Job Matching Background Tasks
Automated job matching and recommendation generation
"""
import logging
import time
from datetime import datetime
from typing import Dict, Any, List

import inngest
from sqlalchemy import select

from app import db
from app.inngest import inngest_client
from app.models.tenant import Tenant
from app.models.candidate import Candidate
from app.models.job_posting import JobPosting
from app.models.global_role import GlobalRole
from app.models.candidate_global_role import CandidateGlobalRole
from app.models.candidate_job_match import CandidateJobMatch
from app.services.job_matching_service import JobMatchingService
from app.services.unified_scorer_service import UnifiedScorerService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@inngest_client.create_function(
    fn_id="nightly-match-refresh",
    trigger=inngest.TriggerCron(cron="0 2 * * *"),  # 2 AM daily
    name="Nightly Job Match Refresh"
)
async def nightly_match_refresh_workflow(ctx: inngest.Context):
    """
    Regenerate job matches for all active candidates across all tenants.
    Runs nightly at 2 AM to ensure matches stay fresh with latest jobs.
    
    Workflow:
    1. Fetch all active tenants
    2. For each tenant, generate matches for all active candidates
    3. Track statistics and performance metrics
    4. Log results for monitoring
    """
    logger.info("[INNGEST] Starting nightly job match refresh")
    start_time = time.time()
    
    # Step 1: Fetch active tenants
    active_tenants = await ctx.step.run(
        "fetch-active-tenants",
        fetch_active_tenants_step
    )
    
    logger.info(f"[INNGEST] Found {len(active_tenants)} active tenants to process")
    
    if not active_tenants:
        return {
            "status": "completed",
            "tenants_processed": 0,
            "total_candidates": 0,
            "total_matches": 0,
            "processing_time_seconds": 0
        }
    
    # Step 2: Process each tenant
    all_results = []
    
    for tenant in active_tenants:
        result = await ctx.step.run(
            f"process-tenant-{tenant['id']}",
            process_tenant_matches_step,
            tenant
        )
        all_results.append(result)
        
        # Rate limiting: 5 second delay between tenants to avoid API overload
        if len(all_results) < len(active_tenants):  # Not the last tenant
            await ctx.step.sleep("rate-limit-delay", 5)
    
    # Step 3: Aggregate statistics
    total_stats = await ctx.step.run(
        "aggregate-stats",
        aggregate_match_stats_step,
        all_results
    )
    
    processing_time = time.time() - start_time
    total_stats["processing_time_seconds"] = round(processing_time, 2)
    
    logger.info(
        f"[INNGEST] Nightly match refresh complete. "
        f"Tenants: {total_stats['tenants_processed']}, "
        f"Candidates: {total_stats['total_candidates']}, "
        f"Matches: {total_stats['total_matches']}, "
        f"Time: {processing_time:.2f}s"
    )
    
    return total_stats


@inngest_client.create_function(
    fn_id="generate-candidate-matches",
    trigger=inngest.TriggerEvent(event="job-match/generate-candidate"),
    name="Generate Matches for Single Candidate"
)
async def generate_candidate_matches_workflow(ctx: inngest.Context):
    """
    Generate job matches for a single candidate.
    Triggered by events: new candidate onboarding, profile update, manual trigger.
    
    Event data:
    {
        "candidate_id": 123,
        "tenant_id": 456,
        "min_score": 50.0,
        "trigger": "onboarding" | "profile_update" | "manual"
    }
    """
    event_data = ctx.event.data
    candidate_id = event_data.get("candidate_id")
    tenant_id = event_data.get("tenant_id")
    min_score = event_data.get("min_score", 50.0)
    trigger = event_data.get("trigger", "manual")
    
    logger.info(
        f"[INNGEST] Generating matches for candidate {candidate_id} "
        f"(tenant {tenant_id}, trigger: {trigger})"
    )
    
    # Step 1: Validate candidate exists
    candidate_data = await ctx.step.run(
        "validate-candidate",
        validate_candidate_step,
        candidate_id,
        tenant_id
    )
    
    if not candidate_data:
        logger.error(f"[INNGEST] Candidate {candidate_id} not found or invalid")
        return {
            "status": "failed",
            "error": "Candidate not found",
            "candidate_id": candidate_id
        }
    
    # Step 2: Ensure candidate has embedding
    embedding_status = await ctx.step.run(
        "ensure-embedding",
        ensure_candidate_embedding_step,
        candidate_id,
        tenant_id
    )
    
    if not embedding_status["has_embedding"]:
        logger.warning(
            f"[INNGEST] Candidate {candidate_id} missing embedding, "
            f"generation {'succeeded' if embedding_status['generated'] else 'failed'}"
        )
    
    # Step 3: Generate matches
    match_result = await ctx.step.run(
        "generate-matches",
        generate_matches_step,
        candidate_id,
        tenant_id,
        min_score
    )
    
    logger.info(
        f"[INNGEST] Generated {match_result['total_matches']} matches "
        f"for candidate {candidate_id}"
    )
    
    # Step 4: Update candidate status to 'ready_for_assignment' if triggered by onboarding
    if trigger == "onboarding_approval":
        status_updated = await ctx.step.run(
            "update-candidate-status",
            update_candidate_status_step,
            candidate_id,
            "ready_for_assignment"
        )
        
        if status_updated:
            logger.info(
                f"[INNGEST] Candidate {candidate_id} status updated to 'ready_for_assignment' "
                f"after generating {match_result['total_matches']} matches"
            )
    
    return {
        "status": "completed",
        "candidate_id": candidate_id,
        "tenant_id": tenant_id,
        "total_matches": match_result["total_matches"],
        "trigger": trigger,
        "final_status": "ready_for_assignment" if trigger == "onboarding_approval" else None
    }


@inngest_client.create_function(
    fn_id="match-jobs-to-candidates",
    trigger=inngest.TriggerEvent(event="jobs/imported"),
    retries=3,
    name="Match New Jobs to Candidates"
)
async def match_jobs_to_candidates_workflow(ctx: inngest.Context) -> dict:
    """
    Match newly imported jobs to candidates with matching preferred roles.
    
    This is the PRIMARY matching workflow - triggered by scraper job imports.
    
    Event data:
    {
        "job_ids": [1, 2, 3],           - IDs of newly imported jobs
        "global_role_id": 5,            - Role that triggered the scrape
        "role_name": "Python Developer", - Role name for logging
        "session_id": "uuid",           - Scrape session ID
        "source": "scraper"             - Import source
    }
    """
    event_data = ctx.event.data
    job_ids = event_data.get("job_ids", [])
    global_role_id = event_data.get("global_role_id")
    role_name = event_data.get("role_name", "Unknown")
    source = event_data.get("source", "unknown")
    
    if not job_ids:
        logger.info("[INNGEST] No jobs to process in jobs/imported event")
        return {"status": "completed", "matches_created": 0, "message": "No jobs to process"}
    
    logger.info(
        f"[INNGEST] Processing {len(job_ids)} jobs for role '{role_name}' "
        f"(role_id={global_role_id}, source={source})"
    )
    
    # Step 1: Get jobs and ensure they have embeddings
    def ensure_job_embeddings():
        embedding_service = EmbeddingService()
        jobs_processed = 0
        embeddings_generated = 0
        
        for job_id in job_ids:
            job = db.session.get(JobPosting, job_id)
            if not job:
                continue
            
            jobs_processed += 1
            
            if job.embedding is None:
                try:
                    embedding = embedding_service.generate_job_embedding(job)
                    if embedding:
                        job.embedding = embedding
                        embeddings_generated += 1
                except Exception as e:
                    logger.error(f"[INNGEST] Failed to generate embedding for job {job_id}: {e}")
        
        db.session.commit()
        return {
            "jobs_processed": jobs_processed,
            "embeddings_generated": embeddings_generated
        }
    
    embedding_result = await ctx.step.run("ensure-job-embeddings", ensure_job_embeddings)
    
    # Step 2: Find candidates with matching preferred roles
    def find_matching_candidates():
        if not global_role_id:
            logger.warning("[INNGEST] No global_role_id in event, cannot find candidates")
            return []
        
        # Find all candidates linked to this global role
        candidate_links = CandidateGlobalRole.query.filter_by(
            global_role_id=global_role_id
        ).all()
        
        candidates_info = []
        for link in candidate_links:
            candidate = link.candidate
            # Only match approved/ready candidates with embeddings
            if candidate and candidate.status in ['approved', 'ready_for_assignment']:
                if candidate.embedding is not None:
                    candidates_info.append({
                        "id": candidate.id,
                        "tenant_id": candidate.tenant_id,
                        "first_name": candidate.first_name,
                        "last_name": candidate.last_name
                    })
        
        return candidates_info
    
    matching_candidates = await ctx.step.run("find-matching-candidates", find_matching_candidates)
    
    if not matching_candidates:
        logger.info(f"[INNGEST] No candidates found for role '{role_name}'")
        return {
            "status": "completed",
            "role_name": role_name,
            "jobs_processed": embedding_result["jobs_processed"],
            "candidates_found": 0,
            "matches_created": 0
        }
    
    logger.info(f"[INNGEST] Found {len(matching_candidates)} candidates for role '{role_name}'")
    
    # Step 3: Generate matches for each candidate using UnifiedScorerService
    def generate_matches_for_candidates():
        total_matches = 0
        
        # Initialize unified scorer (tenant-agnostic)
        unified_scorer = UnifiedScorerService()
        
        for candidate_info in matching_candidates:
            candidate_id = candidate_info["id"]
            
            candidate = db.session.get(Candidate, candidate_id)
            if not candidate or candidate.embedding is None:
                continue
            
            for job_id in job_ids:
                job = db.session.get(JobPosting, job_id)
                if not job or job.embedding is None:
                    continue
                
                # Check if match already exists
                existing = CandidateJobMatch.query.filter_by(
                    candidate_id=candidate_id,
                    job_posting_id=job_id
                ).first()
                
                if existing:
                    continue
                
                # Calculate and store match using unified scorer
                try:
                    # This calculates score AND creates/updates CandidateJobMatch
                    match = unified_scorer.calculate_and_store_match(candidate, job)
                    
                    # Only count if score is above threshold
                    if match.match_score >= 50:
                        total_matches += 1
                    else:
                        # Remove match if below threshold
                        db.session.delete(match)
                        
                except Exception as e:
                    logger.error(
                        f"[INNGEST] Failed to calculate match for candidate {candidate_id}, "
                        f"job {job_id}: {e}"
                    )
        
        db.session.commit()
        return total_matches
    
    matches_created = await ctx.step.run("generate-matches", generate_matches_for_candidates)
    
    logger.info(
        f"[INNGEST] Job import matching complete: "
        f"role='{role_name}', jobs={len(job_ids)}, "
        f"candidates={len(matching_candidates)}, matches={matches_created}"
    )
    
    return {
        "status": "completed",
        "role_name": role_name,
        "global_role_id": global_role_id,
        "jobs_processed": embedding_result["jobs_processed"],
        "embeddings_generated": embedding_result["embeddings_generated"],
        "candidates_found": len(matching_candidates),
        "matches_created": matches_created
    }


@inngest_client.create_function(
    fn_id="update-job-embeddings",
    trigger=inngest.TriggerEvent(event="job-posting/updated"),
    name="Update Job Embeddings on Change"
)
async def update_job_embeddings_workflow(ctx: inngest.Context):
    """
    Regenerate embeddings when job posting is updated.
    Triggered automatically when job details change.
    
    Event data:
    {
        "job_posting_id": 789,
        "fields_changed": ["title", "description", "required_skills"]
    }
    """
    event_data = ctx.event.data
    job_id = event_data.get("job_posting_id")
    fields_changed = event_data.get("fields_changed", [])
    
    # Only regenerate if content fields changed
    content_fields = {"title", "description", "required_skills", "preferred_skills"}
    should_update = any(field in content_fields for field in fields_changed)
    
    if not should_update:
        logger.info(f"[INNGEST] Job {job_id} updated but no content changes, skipping embedding")
        return {"status": "skipped", "job_id": job_id}
    
    logger.info(f"[INNGEST] Regenerating embedding for job {job_id}")
    
    # Step 1: Generate new embedding
    embedding_result = await ctx.step.run(
        "generate-job-embedding",
        generate_job_embedding_step,
        job_id
    )
    
    if not embedding_result["success"]:
        logger.error(f"[INNGEST] Failed to generate embedding for job {job_id}")
        return {
            "status": "failed",
            "job_id": job_id,
            "error": embedding_result.get("error")
        }
    
    logger.info(f"[INNGEST] Successfully updated embedding for job {job_id}")
    
    return {
        "status": "completed",
        "job_id": job_id,
        "embedding_generated": True
    }


# Step Functions

def fetch_active_tenants_step() -> List[Dict[str, Any]]:
    """Fetch all active tenants"""
    query = select(Tenant).where(Tenant.is_active == True)
    tenants = db.session.execute(query).scalars().all()
    
    return [
        {
            "id": tenant.id,
            "company_name": tenant.company_name,
            "subdomain": tenant.subdomain
        }
        for tenant in tenants
    ]


def process_tenant_matches_step(tenant: Dict[str, Any]) -> Dict[str, Any]:
    """Process job matches for all candidates in a tenant using UnifiedScorerService"""
    tenant_id = tenant["id"]
    
    try:
        logger.info(f"[INNGEST] Processing matches for tenant {tenant_id} ({tenant['company_name']})")
        
        # Get all active candidates for this tenant
        candidates = Candidate.query.filter(
            Candidate.tenant_id == tenant_id,
            Candidate.status.in_(['approved', 'ready_for_assignment']),
            Candidate.embedding.isnot(None)
        ).all()
        
        # Get all active jobs with embeddings
        jobs = JobPosting.query.filter(
            JobPosting.embedding.isnot(None),
            JobPosting.status == 'ACTIVE'
        ).all()
        
        # Initialize unified scorer
        unified_scorer = UnifiedScorerService()
        
        total_candidates = len(candidates)
        successful_candidates = 0
        failed_candidates = 0
        total_matches = 0
        
        for candidate in candidates:
            try:
                candidate_matches = 0
                for job in jobs:
                    # Check if match already exists
                    existing = CandidateJobMatch.query.filter_by(
                        candidate_id=candidate.id,
                        job_posting_id=job.id
                    ).first()
                    
                    if existing:
                        continue
                    
                    # Calculate and store match
                    match = unified_scorer.calculate_and_store_match(candidate, job)
                    if match.match_score >= 50:
                        candidate_matches += 1
                    else:
                        db.session.delete(match)
                
                total_matches += candidate_matches
                successful_candidates += 1
                
            except Exception as e:
                logger.error(f"[INNGEST] Error processing candidate {candidate.id}: {e}")
                failed_candidates += 1
        
        db.session.commit()
        
        logger.info(
            f"[INNGEST] Tenant {tenant_id} complete: "
            f"{successful_candidates}/{total_candidates} candidates, "
            f"{total_matches} matches generated"
        )
        
        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant["company_name"],
            "status": "success",
            "total_candidates": total_candidates,
            "successful_candidates": successful_candidates,
            "failed_candidates": failed_candidates,
            "total_matches": total_matches
        }
        
    except Exception as e:
        logger.error(f"[INNGEST] Error processing tenant {tenant_id}: {str(e)}")
        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant["company_name"],
            "status": "error",
            "error": str(e),
            "total_candidates": 0,
            "successful_candidates": 0,
            "total_matches": 0
        }


def aggregate_match_stats_step(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate statistics from all tenant processing"""
    total_tenants = len(results)
    successful_tenants = sum(1 for r in results if r.get("status") == "success")
    failed_tenants = total_tenants - successful_tenants
    
    total_candidates = sum(r.get("total_candidates", 0) for r in results)
    successful_candidates = sum(r.get("successful_candidates", 0) for r in results)
    failed_candidates = sum(r.get("failed_candidates", 0) for r in results)
    total_matches = sum(r.get("total_matches", 0) for r in results)
    
    # Calculate average matches per candidate
    avg_matches = (
        round(total_matches / successful_candidates, 2)
        if successful_candidates > 0
        else 0.0
    )
    
    return {
        "status": "completed",
        "tenants_processed": total_tenants,
        "successful_tenants": successful_tenants,
        "failed_tenants": failed_tenants,
        "total_candidates": total_candidates,
        "successful_candidates": successful_candidates,
        "failed_candidates": failed_candidates,
        "total_matches": total_matches,
        "avg_matches_per_candidate": avg_matches
    }


def validate_candidate_step(candidate_id: int, tenant_id: int) -> Dict[str, Any] | None:
    """Validate candidate exists and belongs to tenant"""
    candidate = db.session.get(Candidate, candidate_id)
    
    if not candidate or candidate.tenant_id != tenant_id:
        return None
    
    return {
        "id": candidate.id,
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "status": candidate.status
    }


def ensure_candidate_embedding_step(candidate_id: int, tenant_id: int) -> Dict[str, Any]:
    """Ensure candidate has embedding, generate if missing"""
    candidate = db.session.get(Candidate, candidate_id)
    
    if not candidate:
        return {"has_embedding": False, "generated": False, "error": "Candidate not found"}
    
    # Check if embedding exists
    if candidate.embedding is not None and len(candidate.embedding) > 0:
        return {"has_embedding": True, "generated": False}
    
    # Generate embedding
    try:
        embedding_service = EmbeddingService()
        embedding = embedding_service.generate_candidate_embedding(candidate)
        
        if embedding:
            candidate.embedding = embedding
            db.session.commit()
            logger.info(f"[INNGEST] Generated embedding for candidate {candidate_id}")
            return {"has_embedding": True, "generated": True}
        else:
            logger.warning(f"[INNGEST] Failed to generate embedding for candidate {candidate_id}")
            return {"has_embedding": False, "generated": False, "error": "Embedding generation returned None"}
            
    except Exception as e:
        logger.error(f"[INNGEST] Error generating embedding for candidate {candidate_id}: {str(e)}")
        return {"has_embedding": False, "generated": False, "error": str(e)}


def generate_matches_step(candidate_id: int, tenant_id: int, min_score: float) -> Dict[str, Any]:
    """Generate job matches for a candidate using UnifiedScorerService"""
    try:
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate or candidate.embedding is None:
            return {
                "success": False,
                "total_matches": 0,
                "error": "Candidate not found or has no embedding"
            }
        
        # Get all active jobs with embeddings
        jobs = JobPosting.query.filter(
            JobPosting.embedding.isnot(None),
            JobPosting.status == 'ACTIVE'
        ).all()
        
        # Initialize unified scorer
        unified_scorer = UnifiedScorerService()
        total_matches = 0
        
        for job in jobs:
            # Check if match already exists
            existing = CandidateJobMatch.query.filter_by(
                candidate_id=candidate_id,
                job_posting_id=job.id
            ).first()
            
            if existing:
                continue
            
            # Calculate and store match
            try:
                match = unified_scorer.calculate_and_store_match(candidate, job)
                if match.match_score >= min_score:
                    total_matches += 1
                else:
                    db.session.delete(match)
            except Exception as e:
                logger.error(f"[INNGEST] Error matching candidate {candidate_id} to job {job.id}: {e}")
        
        db.session.commit()
        
        return {
            "success": True,
            "total_matches": total_matches
        }
        
    except Exception as e:
        logger.error(f"[INNGEST] Error generating matches for candidate {candidate_id}: {str(e)}")
        return {
            "success": False,
            "total_matches": 0,
            "error": str(e)
        }


def update_candidate_status_step(candidate_id: int, status: str) -> bool:
    """
    Update candidate status after job matching completes
    Used to transition candidate to 'ready_for_assignment' after onboarding approval
    """
    try:
        from sqlalchemy import select
        from app.models.candidate import Candidate
        
        stmt = select(Candidate).where(Candidate.id == candidate_id)
        candidate = db.session.scalar(stmt)
        
        if not candidate:
            logger.error(f"[INNGEST] Cannot update status: Candidate {candidate_id} not found")
            return False
        
        old_status = candidate.status
        candidate.status = status
        db.session.commit()
        
        logger.info(
            f"[INNGEST] Candidate {candidate_id} status updated: "
            f"'{old_status}' → '{status}' (audit trail)"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"[INNGEST] Error updating candidate {candidate_id} status: {str(e)}")
        db.session.rollback()
        return False


def generate_job_embedding_step(job_id: int) -> Dict[str, Any]:
    """Generate embedding for a job posting"""
    try:
        job = db.session.get(JobPosting, job_id)
        
        if not job:
            return {"success": False, "error": "Job not found"}
        
        embedding_service = EmbeddingService()
        embedding = embedding_service.generate_job_embedding(job)
        
        if embedding:
            job.embedding = embedding
            db.session.commit()
            return {"success": True}
        else:
            return {"success": False, "error": "Embedding generation returned None"}
            
    except Exception as e:
        logger.error(f"[INNGEST] Error generating job embedding {job_id}: {str(e)}")
        return {"success": False, "error": str(e)}

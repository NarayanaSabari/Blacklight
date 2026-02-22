"""
Email Sync Inngest Workflows (Large Scale Redesign)

Background jobs for syncing emails from connected accounts
and parsing job postings from matching emails.

Architecture:
  sync-all-email-integrations (cron, every 15 min)
    └─ Pages through integrations in chunks of 100
    └─ Batch-sends "email/sync-user-inbox" events per page

  sync-user-inbox (per integration, CONCURRENCY LIMITED)
    ├─ Step 1: fetch-and-filter — fetch + filter, store in Redis
    ├─ Step 2..N: process-email-chunk-{N} — pull chunk, parse via Gemini
    ├─ Step N+1: trigger-matching — fan-out matching per batch of jobs
    └─ Step N+2: update-sync-timestamp — idempotent cursor update

  match-email-jobs-to-candidates (CHUNKED by candidates)
    ├─ Step 1: generate embeddings (per job)
    └─ Step 2..N: match candidates in pages of 200

  manual-email-sync — user-triggered, delegates to sync-user-inbox
  cleanup-old-processed-emails — daily data retention
  check-circuit-breaker-status — monitoring
"""

import logging
import math
from datetime import datetime, timedelta, timezone

import inngest

from app.inngest import inngest_client
from config.settings import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Scheduled Sync — All Integrations (PAGINATED)
# ============================================================================

@inngest_client.create_function(
    fn_id="sync-all-email-integrations",
    trigger=inngest.TriggerCron(cron="*/15 * * * *"),
    name="Sync All Email Integrations",
    retries=1,
)
async def sync_all_integrations_workflow(ctx):
    """
    Scheduled job to sync all active email integrations.

    Large Scale: Pages through integrations in chunks instead of loading
    all integrations into memory at once. Each page sends a batch of
    sync events, preventing memory/event-size blow-ups.
    """
    logger.info("[INNGEST] Starting sync-all-email-integrations (paginated)")

    if not settings.email_sync_enabled:
        logger.info("[INNGEST] Email sync is disabled, skipping")
        return {"status": "disabled", "message": "Email sync is disabled"}

    page_size = settings.email_sync_integration_page_size

    # Step 1: Get first page + total count to know how many pages we need
    def get_first_page():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app.services.email_sync_service import email_sync_service
            integrations, total = email_sync_service.get_active_integrations_page(
                offset=0, limit=page_size
            )
            return {
                "integrations": integrations,
                "total": total,
                "page_size": page_size,
            }

    first_page = await ctx.step.run("get-integrations-page-0", get_first_page)

    total = first_page["total"]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    logger.info(
        f"[INNGEST] Found {total} active integrations, "
        f"{total_pages} page(s) of {page_size}"
    )

    if total == 0:
        return {
            "status": "completed",
            "integrations_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Send events for page 0
    def send_page_events(integrations):
        events = [
            inngest.Event(
                name="email/sync-user-inbox",
                data={
                    "integration_id": i["id"],
                    "user_id": i["user_id"],
                    "tenant_id": i["tenant_id"],
                    "scheduled": True,
                },
            )
            for i in integrations
        ]
        if events:
            inngest_client.send_sync(events)
        return len(events)

    total_events = await ctx.step.run(
        "send-events-page-0",
        lambda: send_page_events(first_page["integrations"]),
    )

    # Process remaining pages
    for page_num in range(1, total_pages):
        offset = page_num * page_size

        def get_page(pg=page_num, off=offset):
            from app import create_app
            app = create_app()
            with app.app_context():
                from app.services.email_sync_service import email_sync_service
                integrations, _ = email_sync_service.get_active_integrations_page(
                    offset=off, limit=page_size
                )
                return integrations

        page_integrations = await ctx.step.run(
            f"get-integrations-page-{page_num}", get_page
        )

        events_sent = await ctx.step.run(
            f"send-events-page-{page_num}",
            lambda ints=page_integrations: send_page_events(ints),
        )
        total_events += events_sent

    logger.info(f"[INNGEST] Batch sent {total_events} sync events across {total_pages} pages")

    return {
        "status": "triggered",
        "integrations_count": total,
        "pages": total_pages,
        "events_sent": total_events,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Single Integration Sync (CONCURRENCY LIMITED, CHUNKED)
# ============================================================================

@inngest_client.create_function(
    fn_id="sync-user-inbox",
    trigger=inngest.TriggerEvent(event="email/sync-user-inbox"),
    name="Sync User Email Inbox",
    retries=3,
    concurrency=[
        # Global concurrency: max 25 concurrent sync functions total
        inngest.Concurrency(
            limit=settings.email_sync_concurrency_limit,
        ),
        # Per-tenant fairness: max 5 concurrent syncs per tenant
        inngest.Concurrency(
            limit=settings.email_sync_tenant_concurrency,
            key="event.data.tenant_id",
        ),
    ],
)
async def sync_user_inbox_workflow(ctx):
    """
    Sync emails for a single user's integration.

    Large Scale changes:
    - Concurrency limited (25 global, 5 per tenant)
    - Email bodies stored in Redis, not in step output
    - Emails processed in chunks (20 per step)
    - Each step is independently retryable

    Event data:
        integration_id: int
        user_id: int
        tenant_id: int
        manual_trigger: bool (optional)
    """
    event_data = ctx.event.data
    integration_id = event_data.get("integration_id")
    manual_trigger = event_data.get("manual_trigger", False)

    logger.info(
        f"[INNGEST] Syncing inbox for integration {integration_id} "
        f"(manual={manual_trigger})"
    )

    # Step 1: Fetch and filter emails, store matched emails in Redis
    def fetch_and_filter():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app.services.email_sync_service import email_sync_service
            return email_sync_service.fetch_and_filter_emails(integration_id)

    sync_result = await ctx.step.run("fetch-and-filter", fetch_and_filter)

    if sync_result.get("error"):
        logger.error(f"[INNGEST] Sync failed: {sync_result['error']}")
        return sync_result

    if sync_result.get("skipped") is True:
        logger.info(
            f"[INNGEST] Sync skipped: {sync_result.get('reason', 'unknown')}"
        )
        return sync_result

    matched_count = sync_result.get("matched", 0)
    redis_key = sync_result.get("redis_key")

    if matched_count == 0:
        logger.debug("[INNGEST] No matched emails to process")
        # Still update sync timestamp
        def update_ts_no_emails():
            from app import create_app
            app = create_app()
            with app.app_context():
                from app.services.email_sync_service import email_sync_service
                new_history_id = sync_result.get("new_history_id")
                email_sync_service.update_sync_timestamp(
                    integration_id, new_history_id
                )
                return {"updated": True}

        await ctx.step.run("update-sync-timestamp", update_ts_no_emails)
        return {
            "status": "completed",
            "fetched": sync_result.get("fetched", 0),
            "matched": 0,
            "jobs_created": 0,
        }

    # Step 2: Retrieve emails from Redis and process in chunks
    chunk_size = settings.email_sync_email_chunk_size
    total_chunks = math.ceil(matched_count / chunk_size)
    jobs_created = 0
    created_job_ids = []

    logger.info(
        f"[INNGEST] Processing {matched_count} matched emails in "
        f"{total_chunks} chunk(s) of {chunk_size}"
    )

    for chunk_idx in range(total_chunks):
        start = chunk_idx * chunk_size
        end = start + chunk_size

        def process_email_chunk(
            r_key=redis_key,
            s=start,
            e=end,
            chunk_num=chunk_idx + 1,
        ):
            from app import create_app
            app = create_app()
            with app.app_context():
                from app import db
                from app.models.user_email_integration import UserEmailIntegration
                from app.services.email_sync_service import email_sync_service
                from app.services.email_job_parser_service import (
                    email_job_parser_service,
                )

                # Retrieve emails from Redis
                all_emails = email_sync_service.get_emails_from_redis(r_key)
                if not all_emails:
                    return {
                        "error": "Redis key expired — emails lost",
                        "chunk": chunk_num,
                    }

                chunk_emails = all_emails[s:e]
                if not chunk_emails:
                    return {"jobs": [], "chunk": chunk_num, "chunk_size": 0}

                integration = db.session.get(
                    UserEmailIntegration, integration_id
                )
                if not integration:
                    return {"error": "Integration not found", "chunk": chunk_num}

                # Parse emails into jobs using batch Gemini
                results = email_job_parser_service.parse_emails_to_jobs_batch(
                    integration, chunk_emails
                )

                batch_jobs = []
                for job, email_data in results:
                    if job:
                        batch_jobs.append({
                            "job_id": job.id,
                            "title": job.title,
                            "tenant_id": integration.tenant_id,
                        })

                return {
                    "jobs": batch_jobs,
                    "chunk": chunk_num,
                    "chunk_size": len(chunk_emails),
                    "jobs_created": len(batch_jobs),
                }

        result = await ctx.step.run(
            f"process-email-chunk-{chunk_idx + 1}",
            process_email_chunk,
        )

        if result.get("error"):
            logger.error(
                f"[INNGEST] Chunk {chunk_idx + 1} error: {result['error']}"
            )
            continue

        if result.get("jobs"):
            for job_info in result["jobs"]:
                jobs_created += 1
                created_job_ids.append(job_info["job_id"])
                logger.info(
                    f"[INNGEST] Chunk {chunk_idx + 1} created job "
                    f"{job_info['job_id']}: {job_info['title']}"
                )

    # Step 3: Clean up Redis email data
    if redis_key:
        def cleanup_redis(r_key=redis_key):
            from app import create_app
            app = create_app()
            with app.app_context():
                from app.services.email_sync_service import email_sync_service
                email_sync_service.delete_emails_from_redis(r_key)
                return {"cleaned": True}

        await ctx.step.run("cleanup-redis", cleanup_redis)

    # Step 4: Trigger job matching for created jobs
    if created_job_ids:
        def trigger_matching(
            job_ids=created_job_ids,
            tenant_id=event_data.get("tenant_id"),
        ):
            inngest_client.send_sync(
                inngest.Event(
                    name="email-jobs/match-to-candidates",
                    data={
                        "job_ids": job_ids,
                        "tenant_id": tenant_id,
                        "source": "email",
                    },
                )
            )
            return {"triggered": True, "job_count": len(job_ids)}

        await ctx.step.run("trigger-matching", trigger_matching)

    # Step 5: Update sync timestamp (idempotent cursor)
    def update_sync_ts():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app.services.email_sync_service import email_sync_service
            new_history_id = sync_result.get("new_history_id")
            email_sync_service.update_sync_timestamp(
                integration_id, new_history_id
            )
            return {"updated": True}

    await ctx.step.run("update-sync-timestamp", update_sync_ts)

    return {
        "status": "completed",
        "fetched": sync_result.get("fetched", 0),
        "matched": sync_result.get("matched", 0),
        "already_processed": sync_result.get("already_processed", 0),
        "jobs_created": jobs_created,
        "job_ids": created_job_ids,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Manual Sync Trigger
# ============================================================================

@inngest_client.create_function(
    fn_id="manual-email-sync",
    trigger=inngest.TriggerEvent(event="email/manual-sync"),
    name="Manual Email Sync",
    retries=2,
)
async def manual_sync_workflow(ctx):
    """
    Manually triggered sync for a specific user.

    Event data:
        user_id: int
        tenant_id: int
        provider: str (optional)
    """
    event_data = ctx.event.data
    user_id = event_data.get("user_id")
    tenant_id = event_data.get("tenant_id")
    provider = event_data.get("provider")

    logger.info(
        f"[INNGEST] Manual sync triggered for user {user_id}, "
        f"provider={provider}"
    )

    def get_user_integrations():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app.services.email_integration_service import (
                email_integration_service,
            )
            integrations = email_integration_service.get_integrations_for_user(
                user_id, tenant_id
            )
            result = []
            for i in integrations:
                if provider and i.provider != provider:
                    continue
                if i.is_active:
                    result.append({"id": i.id, "provider": i.provider})
            return result

    integrations = await ctx.step.run(
        "get-user-integrations", get_user_integrations
    )

    # Trigger sync for each integration (inside step for retry safety)
    def send_sync_events(ints=None):
        events = [
            inngest.Event(
                name="email/sync-user-inbox",
                data={
                    "integration_id": integration["id"],
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "manual_trigger": True,
                },
            )
            for integration in ints
        ]
        if events:
            inngest_client.send_sync(events)
        return len(events)

    events_sent = await ctx.step.run(
        "send-sync-events",
        lambda: send_sync_events(integrations),
    )

    return {
        "status": "triggered",
        "integrations_synced": len(integrations),
    }


# ============================================================================
# Email Job Matching — CHUNKED by candidates
# ============================================================================

@inngest_client.create_function(
    fn_id="match-email-jobs-to-candidates",
    trigger=inngest.TriggerEvent(event="email-jobs/match-to-candidates"),
    name="Match Email Jobs to Candidates",
    retries=3,
    concurrency=[
        # Limit concurrent matching to avoid DB pressure
        inngest.Concurrency(limit=10),
    ],
)
async def match_email_jobs_to_candidates_workflow(ctx):
    """
    Generate embeddings for email-sourced jobs and match to candidates.

    Large Scale changes:
    - Embeddings generated one step per job (independently retryable)
    - Candidate matching paginated in chunks of 200
    - Concurrency limited to 10

    Event data:
        job_ids: list[int]
        tenant_id: int
        source: str
    """
    event_data = ctx.event.data
    job_ids = event_data.get("job_ids", [])
    tenant_id = event_data.get("tenant_id")

    if not job_ids:
        logger.debug("[INNGEST] No email jobs to process for matching")
        return {"status": "completed", "matches_created": 0}

    logger.info(
        f"[INNGEST] Processing {len(job_ids)} email jobs for matching "
        f"in tenant {tenant_id}"
    )

    # Step 1: Generate embeddings for all jobs
    def generate_job_embeddings():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app import db
            from app.models.job_posting import JobPosting
            from app.services.embedding_service import EmbeddingService

            embedding_service = EmbeddingService()
            embeddings_generated = 0
            job_infos = []
            embedding_errors = []

            for job_id in job_ids:
                job = db.session.get(JobPosting, job_id)
                if not job:
                    embedding_errors.append({
                        "job_id": job_id,
                        "error": "Job not found",
                    })
                    continue

                if job.embedding is None:
                    try:
                        logger.info(
                            f"[INNGEST] Generating embedding for job "
                            f"{job_id}: {job.title}"
                        )
                        embedding = embedding_service.generate_job_embedding(job)
                        if embedding:
                            job.embedding = embedding
                            embeddings_generated += 1
                        else:
                            embedding_errors.append({
                                "job_id": job_id,
                                "title": job.title,
                                "error": "Embedding service returned None",
                            })
                    except Exception as e:
                        import traceback
                        logger.error(
                            f"[INNGEST] Failed to generate embedding "
                            f"for job {job_id}: {e}"
                        )
                        embedding_errors.append({
                            "job_id": job_id,
                            "title": job.title,
                            "error": str(e),
                            "traceback": traceback.format_exc()[:500],
                        })
                        continue

                job_infos.append({
                    "id": job.id,
                    "title": job.title,
                    "has_embedding": job.embedding is not None,
                })

            db.session.commit()
            return {
                "embeddings_generated": embeddings_generated,
                "jobs_processed": len(job_infos),
                "job_infos": job_infos,
                "embedding_errors": embedding_errors,
            }

    embedding_result = await ctx.step.run(
        "generate-email-job-embeddings", generate_job_embeddings
    )

    logger.info(
        f"[INNGEST] Generated {embedding_result['embeddings_generated']} "
        f"embeddings for {embedding_result['jobs_processed']} email jobs"
    )

    # Step 2: Find role-filtered candidate-job pairs
    def find_role_filtered_pairs():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app import db
            from app.models.job_posting import JobPosting
            from app.models.candidate import Candidate
            from app.models.candidate_global_role import CandidateGlobalRole
            from sqlalchemy import select

            matchable_statuses = ['approved', 'ready_for_assignment']

            # Load jobs and their normalized_role_ids
            jobs = list(db.session.scalars(
                select(JobPosting).where(
                    JobPosting.id.in_(job_ids),
                    JobPosting.embedding.isnot(None),
                )
            ).all())

            if not jobs:
                return {"pairs": [], "total_candidates": 0, "jobs_with_roles": 0}

            # Build mapping: role_id -> list of job_ids
            role_to_jobs = {}
            jobs_without_role = []
            for job in jobs:
                if job.normalized_role_id:
                    role_to_jobs.setdefault(job.normalized_role_id, []).append(job.id)
                else:
                    jobs_without_role.append(job.id)

            if not role_to_jobs:
                logger.warning(
                    f"[INNGEST] None of the {len(jobs)} email jobs have "
                    f"normalized_role_id, cannot match to candidates"
                )
                return {"pairs": [], "total_candidates": 0, "jobs_with_roles": 0}

            # Find candidates whose preferred roles match the jobs' roles
            role_ids = list(role_to_jobs.keys())
            candidate_role_links = db.session.execute(
                select(
                    CandidateGlobalRole.candidate_id,
                    CandidateGlobalRole.global_role_id,
                ).where(
                    CandidateGlobalRole.global_role_id.in_(role_ids),
                )
            ).all()

            if not candidate_role_links:
                return {"pairs": [], "total_candidates": 0, "jobs_with_roles": len(role_to_jobs)}

            # Get candidate IDs and verify they're matchable
            candidate_ids = list(set(link[0] for link in candidate_role_links))
            matchable_candidates = {
                c.id: c for c in db.session.scalars(
                    select(Candidate).where(
                        Candidate.id.in_(candidate_ids),
                        Candidate.tenant_id == tenant_id,
                        Candidate.status.in_(matchable_statuses),
                        Candidate.embedding.isnot(None),
                    )
                ).all()
            }

            # Build pairs: (candidate_id, job_id) based on role matching
            pairs = []
            for link in candidate_role_links:
                cand_id, role_id = link[0], link[1]
                if cand_id not in matchable_candidates:
                    continue
                for jid in role_to_jobs.get(role_id, []):
                    pairs.append({"candidate_id": cand_id, "job_id": jid})

            # Deduplicate pairs (candidate may have multiple roles matching same job)
            seen = set()
            unique_pairs = []
            for p in pairs:
                key = (p["candidate_id"], p["job_id"])
                if key not in seen:
                    seen.add(key)
                    unique_pairs.append(p)

            logger.info(
                f"[INNGEST] Role-filtered matching: {len(unique_pairs)} pairs "
                f"({len(matchable_candidates)} candidates x {len(role_to_jobs)} roles), "
                f"{len(jobs_without_role)} jobs skipped (no role)"
            )

            return {
                "pairs": unique_pairs,
                "total_candidates": len(matchable_candidates),
                "jobs_with_roles": len(role_to_jobs),
                "jobs_without_roles": len(jobs_without_role),
            }

    pair_info = await ctx.step.run("find-role-filtered-pairs", find_role_filtered_pairs)

    total_candidates = pair_info["total_candidates"]
    pairs = pair_info["pairs"]

    if not pairs:
        logger.warning(
            f"[INNGEST] No role-filtered candidate-job pairs in tenant {tenant_id}"
        )
        return {
            "status": "completed",
            "jobs_processed": embedding_result["jobs_processed"],
            "embeddings_generated": embedding_result["embeddings_generated"],
            "candidates_found": total_candidates,
            "matches_created": 0,
        }

    # Step 3: Score all role-filtered pairs in chunks
    chunk_size = 200  # pairs per step
    total_chunks = math.ceil(len(pairs) / chunk_size)
    total_matches_created = 0
    total_low_score = 0
    total_skipped = 0
    job_match_summaries = []

    logger.info(
        f"[INNGEST] Scoring {len(pairs)} role-filtered pairs "
        f"in {total_chunks} chunk(s) of {chunk_size}"
    )

    for chunk_idx in range(total_chunks):
        start = chunk_idx * chunk_size
        end = start + chunk_size
        chunk_pairs = pairs[start:end]

        def match_pair_chunk(
            c_pairs=chunk_pairs,
            pg=chunk_idx + 1,
        ):
            from app import create_app
            app = create_app()
            with app.app_context():
                from app import db
                from app.models.job_posting import JobPosting
                from app.models.candidate import Candidate
                from app.models.candidate_job_match import CandidateJobMatch
                from app.services.unified_scorer_service import UnifiedScorerService
                from sqlalchemy import select

                # Collect unique IDs
                cand_ids = list(set(p["candidate_id"] for p in c_pairs))
                jb_ids = list(set(p["job_id"] for p in c_pairs))

                # Load all needed candidates and jobs
                candidates_map = {
                    c.id: c for c in db.session.scalars(
                        select(Candidate).where(Candidate.id.in_(cand_ids))
                    ).all()
                }
                jobs_map = {
                    j.id: j for j in db.session.scalars(
                        select(JobPosting).where(JobPosting.id.in_(jb_ids))
                    ).all()
                }

                # Get existing matches in one query
                existing = set()
                existing_stmt = select(
                    CandidateJobMatch.candidate_id,
                    CandidateJobMatch.job_posting_id,
                ).where(
                    CandidateJobMatch.candidate_id.in_(cand_ids),
                    CandidateJobMatch.job_posting_id.in_(jb_ids),
                )
                for row in db.session.execute(existing_stmt).all():
                    existing.add((row[0], row[1]))

                unified_scorer = UnifiedScorerService()
                chunk_matches = 0
                chunk_low_score = 0
                chunk_skipped = 0
                chunk_job_details = {}

                for pair in c_pairs:
                    cid = pair["candidate_id"]
                    jid = pair["job_id"]

                    candidate = candidates_map.get(cid)
                    job = jobs_map.get(jid)

                    if not candidate or not job:
                        continue
                    if candidate.embedding is None or job.embedding is None:
                        continue

                    if (cid, jid) in existing:
                        chunk_skipped += 1
                        continue

                    try:
                        match = (
                            unified_scorer
                            .calculate_and_store_match_no_commit(
                                candidate, job
                            )
                        )

                        if match:
                            if match.match_score >= 50:
                                chunk_matches += 1
                                if jid not in chunk_job_details:
                                    chunk_job_details[jid] = {
                                        "job_id": jid,
                                        "job_title": job.title,
                                        "matches_in_chunk": 0,
                                    }
                                chunk_job_details[jid]["matches_in_chunk"] += 1
                            else:
                                chunk_low_score += 1

                    except Exception as e:
                        logger.error(
                            f"[INNGEST] Match error: candidate "
                            f"{cid} x job {jid}: {e}"
                        )
                        continue

                db.session.commit()

                return {
                    "chunk": pg,
                    "pairs_in_chunk": len(c_pairs),
                    "matches_created": chunk_matches,
                    "low_score": chunk_low_score,
                    "skipped_existing": chunk_skipped,
                    "job_details": list(chunk_job_details.values()),
                }

        chunk_result = await ctx.step.run(
            f"match-pairs-chunk-{chunk_idx + 1}",
            match_pair_chunk,
        )

        total_matches_created += chunk_result.get("matches_created", 0)
        total_low_score += chunk_result.get("low_score", 0)
        total_skipped += chunk_result.get("skipped_existing", 0)

        if chunk_result.get("job_details"):
            job_match_summaries.extend(chunk_result["job_details"])

        logger.info(
            f"[INNGEST] Chunk {chunk_idx + 1}/{total_chunks}: "
            f"{chunk_result.get('matches_created', 0)} matches from "
            f"{chunk_result.get('pairs_in_chunk', 0)} pairs"
        )

    return {
        "status": "completed",
        "jobs_processed": embedding_result["jobs_processed"],
        "embeddings_generated": embedding_result["embeddings_generated"],
        "embedding_errors": embedding_result.get("embedding_errors", []),
        "candidates_found": total_candidates,
        "role_filtered_pairs": len(pairs),
        "matches_created": total_matches_created,
        "low_score_matches": total_low_score,
        "skipped_existing": total_skipped,
        "job_match_summaries": job_match_summaries,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# ProcessedEmail Cleanup — Data Retention
# ============================================================================

@inngest_client.create_function(
    fn_id="cleanup-old-processed-emails",
    trigger=inngest.TriggerCron(cron="0 3 * * *"),
    name="Cleanup Old Processed Emails",
    retries=2,
)
async def cleanup_old_processed_emails_workflow(ctx):
    """
    Clean up old ProcessedEmail records to control table growth.

    Runs daily at 3 AM. Deletes records older than 90 days.
    """
    logger.info("[INNGEST] Starting processed emails cleanup")

    RETENTION_DAYS = 90

    def cleanup_old_records():
        from app import create_app
        app = create_app()
        with app.app_context():
            from app import db
            from app.models.processed_email import ProcessedEmail
            from sqlalchemy import delete, select

            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=RETENTION_DAYS
            )

            # Count records to be deleted
            count_to_delete = db.session.scalar(
                select(db.func.count(ProcessedEmail.id)).where(
                    ProcessedEmail.created_at < cutoff_date
                )
            ) or 0

            if count_to_delete == 0:
                return {"deleted": 0, "message": "No old records to delete"}

            # Delete in batches to avoid long locks
            batch_size = 10000
            total_deleted = 0

            while True:
                # Get batch of IDs to delete
                subquery = (
                    select(ProcessedEmail.id)
                    .where(ProcessedEmail.created_at < cutoff_date)
                    .limit(batch_size)
                    .subquery()
                )

                result = db.session.execute(
                    delete(ProcessedEmail).where(
                        ProcessedEmail.id.in_(
                            select(subquery.c.id)
                        )
                    )
                )

                deleted_count = result.rowcount
                total_deleted += deleted_count
                db.session.commit()

                logger.info(
                    f"[INNGEST] Deleted batch of {deleted_count} processed emails"
                )

                if deleted_count < batch_size:
                    break

            return {
                "deleted": total_deleted,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": RETENTION_DAYS,
            }

    result = await ctx.step.run("cleanup-processed-emails", cleanup_old_records)

    logger.info(
        f"[INNGEST] Cleanup completed: deleted {result.get('deleted', 0)} old records"
    )

    return {
        "status": "completed",
        **result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Circuit Breaker Status Check (for monitoring)
# ============================================================================

@inngest_client.create_function(
    fn_id="check-circuit-breaker-status",
    trigger=inngest.TriggerEvent(event="email/check-circuit-status"),
    name="Check Circuit Breaker Status",
    retries=1,
)
async def check_circuit_breaker_status_workflow(ctx):
    """
    Check and report distributed circuit breaker status.
    """
    from app.utils.circuit_breaker import (
        gmail_circuit_breaker,
        outlook_circuit_breaker,
        gemini_circuit_breaker,
    )

    return {
        "status": "completed",
        "circuit_breakers": {
            "gmail": gmail_circuit_breaker.get_status(),
            "outlook": outlook_circuit_breaker.get_status(),
            "gemini": gemini_circuit_breaker.get_status(),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

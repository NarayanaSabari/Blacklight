"""
Job Match Routes
API endpoints for AI-powered job matching and recommendations.
"""
import logging
from flask import Blueprint, request, jsonify, g
from sqlalchemy import select, and_, or_, func

from app import db
from app.models.candidate import Candidate
from app.models.candidate_job_match import CandidateJobMatch
from app.models.job_posting import JobPosting
from app.models.candidate_assignment import CandidateAssignment
from app.services.job_matching_service import JobMatchingService
from app.services.unified_scorer_service import UnifiedScorerService
from app.middleware.portal_auth import require_portal_auth
from app.middleware.tenant_context import with_tenant_context
from app.middleware.portal_auth import require_permission

logger = logging.getLogger(__name__)

job_match_bp = Blueprint('job_matches', __name__, url_prefix='/api/job-matches')


def error_response(message: str, status: int = 400, details: dict = None):
    """Helper to create error responses"""
    response = {
        'error': 'Error',
        'message': message,
        'status': status
    }
    if details:
        response['details'] = details
    return jsonify(response), status


@job_match_bp.route('/candidates/<int:candidate_id>/generate', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def generate_matches_for_candidate(candidate_id: int):
    """
    Generate job matches for a specific candidate using UnifiedScorerService.
    
    Finds jobs via RoleJobMapping (candidate's preferred roles) and scores
    each pair, storing results in candidate_job_matches table.
    
    POST /api/job-matches/candidates/:id/generate
    
    Request body:
    {
        "min_score": 50.0,  // Optional, default 50
        "limit": 50         // Optional, default 50
    }
    
    Permissions: candidates.view
    """
    from app.models.candidate_global_role import CandidateGlobalRole
    from app.models.role_job_mapping import RoleJobMapping
    
    try:
        tenant_id = g.tenant_id
        
        # Verify candidate exists and belongs to tenant
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return error_response(f"Candidate {candidate_id} not found", 404)
        
        if candidate.tenant_id != tenant_id:
            return error_response("Access denied", 403)
        
        # Parse request body
        data = request.get_json() or {}
        min_score = data.get('min_score', 50.0)
        limit = data.get('limit', 50)
        
        # Validate parameters
        if not isinstance(min_score, (int, float)) or min_score < 0 or min_score > 100:
            return error_response("min_score must be between 0 and 100")
        
        if not isinstance(limit, int) or limit < 1 or limit > 200:
            return error_response("limit must be between 1 and 200")
        
        # Get candidate's preferred role IDs for role-based filtering
        role_ids = [
            row[0] for row in db.session.execute(
                select(CandidateGlobalRole.global_role_id).where(
                    CandidateGlobalRole.candidate_id == candidate_id
                )
            ).all()
        ]
        
        if not role_ids:
            return jsonify({
                'message': 'No preferred roles assigned. Cannot generate matches.',
                'candidate_id': candidate_id,
                'total_matches': 0,
                'matches': []
            }), 200
        
        # Get jobs via RoleJobMapping (standardized join path)
        job_ids = [
            row[0] for row in db.session.execute(
                select(RoleJobMapping.job_posting_id).where(
                    RoleJobMapping.global_role_id.in_(role_ids)
                ).distinct()
            ).all()
        ]
        
        jobs = db.session.scalars(
            select(JobPosting).where(
                JobPosting.id.in_(job_ids),
                JobPosting.embedding.isnot(None),
                JobPosting.status == 'ACTIVE'
            )
        ).all() if job_ids else []
        
        # Score using UnifiedScorerService
        scorer = UnifiedScorerService()
        matches = []
        
        for job in jobs:
            try:
                match = scorer.calculate_and_store_match(candidate, job)
                if float(match.match_score) >= min_score:
                    matches.append(match)
                else:
                    db.session.delete(match)
            except Exception as e:
                logger.error(f"Error scoring candidate {candidate_id} vs job {job.id}: {e}")
        
        db.session.commit()
        db.session.expire_all()
        
        # Sort by score descending and limit
        matches.sort(key=lambda m: float(m.match_score), reverse=True)
        matches = matches[:limit]
        
        return jsonify({
            'message': 'Matches generated successfully',
            'candidate_id': candidate_id,
            'total_matches': len(matches),
            'matches': [match.to_dict(include_job=True) for match in matches[:10]]  # First 10
        }), 200
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error generating matches for candidate {candidate_id}: {str(e)}")
        return error_response("Failed to generate matches", 500)


@job_match_bp.route('/generate-all', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def generate_matches_for_all():
    """
    Generate job matches for all active candidates in tenant using UnifiedScorerService.
    
    Uses role-based filtering via RoleJobMapping for each candidate.
    
    POST /api/job-matches/generate-all
    
    Request body:
    {
        "min_score": 50.0,   // Optional, default 50
        "batch_size": 10     // Optional, default 10
    }
    
    Permissions: candidates.view
    """
    import time
    from app.models.candidate_global_role import CandidateGlobalRole
    from app.models.role_job_mapping import RoleJobMapping
    
    try:
        tenant_id = g.tenant_id
        
        # Parse request body
        data = request.get_json() or {}
        min_score = data.get('min_score', 50.0)
        batch_size = data.get('batch_size', 10)
        
        # Validate parameters
        if not isinstance(min_score, (int, float)) or min_score < 0 or min_score > 100:
            return error_response("min_score must be between 0 and 100")
        
        if not isinstance(batch_size, int) or batch_size < 1 or batch_size > 50:
            return error_response("batch_size must be between 1 and 50")
        
        start_time = time.time()
        
        # Fetch all active candidates for this tenant
        candidates = db.session.scalars(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status.in_(['approved', 'ready_for_assignment', 'new', 'screening']),
            )
        ).all()
        
        total_candidates = len(candidates)
        if total_candidates == 0:
            return jsonify({
                'message': 'Bulk match generation complete',
                'stats': {
                    'total_candidates': 0,
                    'successful_candidates': 0,
                    'failed_candidates': 0,
                    'total_matches': 0,
                    'avg_matches_per_candidate': 0.0,
                    'processing_time_seconds': 0.0
                }
            }), 200
        
        scorer = UnifiedScorerService()
        successful_count = 0
        failed_count = 0
        total_matches = 0
        
        for i in range(0, total_candidates, batch_size):
            batch = candidates[i:i + batch_size]
            
            for candidate in batch:
                try:
                    # Get candidate's role IDs
                    role_ids = [
                        row[0] for row in db.session.execute(
                            select(CandidateGlobalRole.global_role_id).where(
                                CandidateGlobalRole.candidate_id == candidate.id
                            )
                        ).all()
                    ]
                    
                    if not role_ids:
                        successful_count += 1
                        continue
                    
                    # Get jobs via RoleJobMapping
                    job_ids = [
                        row[0] for row in db.session.execute(
                            select(RoleJobMapping.job_posting_id).where(
                                RoleJobMapping.global_role_id.in_(role_ids)
                            ).distinct()
                        ).all()
                    ]
                    
                    jobs = db.session.scalars(
                        select(JobPosting).where(
                            JobPosting.id.in_(job_ids),
                            JobPosting.embedding.isnot(None),
                            JobPosting.status == 'ACTIVE'
                        )
                    ).all() if job_ids else []
                    
                    candidate_matches = 0
                    for job in jobs:
                        try:
                            match = scorer.calculate_and_store_match(candidate, job)
                            if float(match.match_score) >= min_score:
                                candidate_matches += 1
                            else:
                                db.session.delete(match)
                        except Exception as e:
                            logger.error(f"Error scoring candidate {candidate.id} vs job {job.id}: {e}")
                    
                    total_matches += candidate_matches
                    successful_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to generate matches for candidate {candidate.id}: {e}")
            
            db.session.commit()
            
            # Small delay between batches
            if i + batch_size < total_candidates:
                time.sleep(0.1)
        
        db.session.expire_all()
        processing_time = time.time() - start_time
        avg_matches = total_matches / successful_count if successful_count > 0 else 0.0
        
        return jsonify({
            'message': 'Bulk match generation complete',
            'stats': {
                'total_candidates': total_candidates,
                'successful_candidates': successful_count,
                'failed_candidates': failed_count,
                'total_matches': total_matches,
                'avg_matches_per_candidate': round(avg_matches, 2),
                'processing_time_seconds': round(processing_time, 2)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in bulk match generation: {str(e)}")
        return error_response("Failed to generate matches", 500)


@job_match_bp.route('/candidates/<int:candidate_id>/refresh', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def refresh_candidate_matches(candidate_id: int):
    """
    Refresh/regenerate job matches for a specific candidate.
    Triggers Inngest background job to regenerate all matches.
    
    POST /api/job-matches/candidates/:id/refresh
    
    Request body (optional):
    {
        "min_score": 50.0  // Optional, default 50
    }
    
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        
        # Verify candidate exists and belongs to tenant
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return error_response(f"Candidate {candidate_id} not found", 404)
        
        if candidate.tenant_id != tenant_id:
            return error_response("Access denied", 403)
        
        # Parse request body
        data = request.get_json() or {}
        min_score = data.get('min_score', 50.0)
        
        # Validate parameters
        if not isinstance(min_score, (int, float)) or min_score < 0 or min_score > 100:
            return error_response("min_score must be between 0 and 100")
        
        # Trigger Inngest workflow
        from app.inngest import inngest_client
        import inngest
        
        inngest_client.send_sync(
            inngest.Event(
                name="job-match/generate-candidate",
                data={
                    "candidate_id": candidate_id,
                    "tenant_id": tenant_id,
                    "min_score": min_score
                }
            )
        )
        
        logger.info(f"Triggered match refresh for candidate {candidate_id}")
        
        return jsonify({
            'message': 'Match refresh initiated',
            'candidate_id': candidate_id,
            'status': 'processing'
        }), 202
        
    except Exception as e:
        logger.error(f"Error refreshing matches for candidate {candidate_id}: {str(e)}")
        return error_response("Failed to refresh matches", 500)


@job_match_bp.route('/candidates/<int:candidate_id>/stats', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_candidate_match_stats(candidate_id: int):
    """
    Get match statistics for a specific candidate.
    
    GET /api/job-matches/candidates/:id/stats
    
    Permissions: candidates.view
    
    Returns:
    - total: Total number of matches
    - by_grade: Distribution of matches by grade (A+, A, B, C, D, F)
    - by_status: Distribution by match status (SUGGESTED, VIEWED, APPLIED, etc.)
    - avg_score: Average match score
    - top_score: Highest match score
    - last_updated: When matches were last generated
    """
    try:
        tenant_id = g.tenant_id
        
        # Verify candidate exists and belongs to tenant
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return error_response(f"Candidate {candidate_id} not found", 404)
        
        if candidate.tenant_id != tenant_id:
            return error_response("Access denied", 403)
        
        # Get all matches for this candidate
        matches_query = select(CandidateJobMatch).where(
            CandidateJobMatch.candidate_id == candidate_id
        )
        matches = db.session.execute(matches_query).scalars().all()
        
        if not matches:
            return jsonify({
                'candidate_id': candidate_id,
                'total': 0,
                'by_grade': {'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0},
                'by_status': {},
                'avg_score': 0.0,
                'top_score': 0.0,
                'last_updated': None
            }), 200
        
        # Calculate statistics
        total = len(matches)
        scores = [float(m.match_score) for m in matches]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        top_score = max(scores) if scores else 0.0
        
        # Grade distribution
        grade_dist = {'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        for score in scores:
            if score >= 90:
                grade_dist['A+'] += 1
            elif score >= 80:
                grade_dist['A'] += 1
            elif score >= 70:
                grade_dist['B'] += 1
            elif score >= 60:
                grade_dist['C'] += 1
            elif score >= 50:
                grade_dist['D'] += 1
            else:
                grade_dist['F'] += 1
        
        # Status distribution
        status_dist = {}
        for match in matches:
            status = match.status
            status_dist[status] = status_dist.get(status, 0) + 1
        
        # Last updated (most recent match creation)
        last_updated = max(m.created_at for m in matches)
        
        return jsonify({
            'candidate_id': candidate_id,
            'total': total,
            'by_grade': grade_dist,
            'by_status': status_dist,
            'avg_score': round(avg_score, 2),
            'top_score': round(top_score, 2),
            'last_updated': last_updated.isoformat() if last_updated else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching stats for candidate {candidate_id}: {str(e)}")
        return error_response("Failed to fetch statistics", 500)


@job_match_bp.route('/candidates/<int:candidate_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_candidate_matches(candidate_id: int):
    """
    Get job matches for a specific candidate.
    
    Reads pre-computed scores from candidate_job_matches table (populated by
    nightly refresh and job-import events). Falls back to on-the-fly scoring
    only for jobs that have no stored match yet.
    
    GET /api/job-matches/candidates/:id?page=1&per_page=20&min_score=0
    
    Query params:
    - page: Page number (default 1)
    - per_page: Matches per page (default 20, max 500)
    - min_score: Minimum match score filter (default 0)
    - sort_by: Sort field (created_at, match_score, posted_date, default: created_at)
    - sort_order: Sort order (asc, desc, default: desc)
    - platforms: Comma-separated list of platforms to filter by (e.g., "linkedin,glassdoor")
    - grades: Comma-separated list of grades to filter by (e.g., "A+,A,B")
    - source: Filter by job source (all, email, scraped) - default: all
    
    Permissions: candidates.view
    """
    from app.models.candidate_global_role import CandidateGlobalRole
    from app.models.role_job_mapping import RoleJobMapping
    from app.models.portal_user import PortalUser
    
    try:
        tenant_id = g.tenant_id
        
        # Verify candidate exists and belongs to tenant
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return error_response(f"Candidate {candidate_id} not found", 404)
        
        if candidate.tenant_id != tenant_id:
            return error_response("Access denied", 403)
        
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)  # Default 25 for pagination
        min_score = request.args.get('min_score', 0, type=float)
        sort_by = request.args.get('sort_by', 'created_at')  # Default: latest first
        sort_order = request.args.get('sort_order', 'desc')
        platforms_param = request.args.get('platforms', '')
        grades_param = request.args.get('grades', '')
        source_filter = request.args.get('source', 'all').lower()  # all, email, scraped
        
        # Validate source filter
        if source_filter not in ('all', 'email', 'scraped'):
            source_filter = 'all'
        
        # Parse platforms filter (comma-separated list)
        platforms_filter = [p.strip().lower() for p in platforms_param.split(',') if p.strip()] if platforms_param else []
        
        # Parse grades filter (comma-separated list)
        grades_filter = [g.strip() for g in grades_param.split(',') if g.strip()] if grades_param else []
        
        # Validate parameters
        if per_page < 1 or per_page > 500:
            return error_response("per_page must be between 1 and 500")
        if page < 1:
            return error_response("page must be >= 1")
        
        # Get candidate's global roles
        global_role_query = select(CandidateGlobalRole.global_role_id).where(
            CandidateGlobalRole.candidate_id == candidate_id
        )
        global_role_ids = [row[0] for row in db.session.execute(global_role_query).all()]
        
        logger.info(
            f"[JOB-MATCHES] Candidate {candidate_id}: global_role_ids={global_role_ids}"
        )
        
        if not global_role_ids:
            # Check if candidate has preferred_roles that haven't been normalized yet
            preferred_roles = candidate.preferred_roles or []
            
            logger.warning(
                f"[JOB-MATCHES] Candidate {candidate_id} has no CandidateGlobalRole links. "
                f"preferred_roles={preferred_roles}"
            )
            
            return jsonify({
                'candidate_id': candidate_id,
                'total_matches': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'matches': [],
                'message': 'No preferred roles assigned to this candidate. Assign roles to see job matches.',
                'debug': {
                    'preferred_roles': preferred_roles,
                    'global_role_ids': [],
                    'hint': 'Roles need to be normalized first. This happens on candidate approval.'
                }
            }), 200
        
        # Get all job IDs mapped to these roles via RoleJobMapping
        job_mapping_query = select(RoleJobMapping.job_posting_id).where(
            RoleJobMapping.global_role_id.in_(global_role_ids)
        ).distinct()
        job_ids = [row[0] for row in db.session.execute(job_mapping_query).all()]
        
        logger.info(
            f"[JOB-MATCHES] Candidate {candidate_id}: Found {len(job_ids)} jobs for roles {global_role_ids}"
        )
        
        if not job_ids:
            # Get role names for debug
            from app.models.global_role import GlobalRole
            role_names = []
            for role_id in global_role_ids:
                role = db.session.get(GlobalRole, role_id)
                if role:
                    role_names.append(role.name)
            
            return jsonify({
                'candidate_id': candidate_id,
                'total_matches': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'matches': [],
                'message': 'No jobs found for assigned roles. Jobs will appear here when scraped or received via email.',
                'debug': {
                    'global_role_ids': global_role_ids,
                    'global_role_names': role_names,
                    'hint': 'Jobs are linked to roles via RoleJobMapping. Check if scraper/email imported jobs for these roles.'
                }
            }), 200
        
        # ------------------------------------------------------------------
        # Read pre-computed scores from CandidateJobMatch table.
        # Join with JobPosting to apply visibility/status/platform/source filters.
        # ------------------------------------------------------------------
        
        # Base query: join CandidateJobMatch with JobPosting
        match_query = (
            select(CandidateJobMatch, JobPosting)
            .join(JobPosting, CandidateJobMatch.job_posting_id == JobPosting.id)
            .where(
                CandidateJobMatch.candidate_id == candidate_id,
                CandidateJobMatch.job_posting_id.in_(job_ids),
                JobPosting.status == 'ACTIVE',
                # Email job visibility: scraped jobs visible to all, email jobs only to source tenant
                or_(
                    JobPosting.is_email_sourced == False,
                    and_(
                        JobPosting.is_email_sourced == True,
                        JobPosting.source_tenant_id == tenant_id
                    )
                )
            )
        )
        
        # Apply min_score filter
        if min_score > 0:
            match_query = match_query.where(
                CandidateJobMatch.match_score >= min_score
            )
        
        # Apply grade filter
        if grades_filter:
            match_query = match_query.where(
                CandidateJobMatch.match_grade.in_(grades_filter)
            )
        
        # Apply source filter
        if source_filter == 'email':
            match_query = match_query.where(JobPosting.is_email_sourced == True)
        elif source_filter == 'scraped':
            match_query = match_query.where(JobPosting.is_email_sourced == False)
        
        # Apply platform filter
        if platforms_filter:
            match_query = match_query.where(
                func.lower(JobPosting.platform).in_(platforms_filter)
            )
        
        # Sorting
        reverse_order = (sort_order != 'asc')
        if sort_by == 'match_score':
            order_col = CandidateJobMatch.match_score.desc() if reverse_order else CandidateJobMatch.match_score.asc()
        elif sort_by == 'posted_date':
            order_col = JobPosting.posted_date.desc() if reverse_order else JobPosting.posted_date.asc()
        else:  # default: created_at
            order_col = JobPosting.created_at.desc() if reverse_order else JobPosting.created_at.asc()
        
        match_query = match_query.order_by(order_col)
        
        # ------------------------------------------------------------------
        # Collect available_platforms and available_sources BEFORE pagination
        # (lightweight aggregation over the filtered set)
        # ------------------------------------------------------------------
        
        # We need unfiltered-by-platform query for available_platforms
        base_visibility_filter = and_(
            CandidateJobMatch.candidate_id == candidate_id,
            CandidateJobMatch.job_posting_id.in_(job_ids),
            JobPosting.status == 'ACTIVE',
            or_(
                JobPosting.is_email_sourced == False,
                and_(
                    JobPosting.is_email_sourced == True,
                    JobPosting.source_tenant_id == tenant_id
                )
            )
        )
        
        # Available platforms
        platform_query = (
            select(func.lower(JobPosting.platform))
            .join(CandidateJobMatch, CandidateJobMatch.job_posting_id == JobPosting.id)
            .where(base_visibility_filter)
            .where(JobPosting.platform.isnot(None))
            .distinct()
        )
        available_platforms = sorted([row[0] for row in db.session.execute(platform_query).all()])
        
        # Available sources
        source_query = (
            select(JobPosting.is_email_sourced)
            .join(CandidateJobMatch, CandidateJobMatch.job_posting_id == JobPosting.id)
            .where(base_visibility_filter)
            .distinct()
        )
        source_rows = [row[0] for row in db.session.execute(source_query).all()]
        available_sources = []
        if False in source_rows:
            available_sources.append('scraped')
        if True in source_rows:
            available_sources.append('email')
        
        # ------------------------------------------------------------------
        # Get total count (for pagination) and paginated results
        # ------------------------------------------------------------------
        
        # Total count
        from sqlalchemy import func as sqla_func
        count_query = (
            select(sqla_func.count())
            .select_from(CandidateJobMatch)
            .join(JobPosting, CandidateJobMatch.job_posting_id == JobPosting.id)
            .where(
                CandidateJobMatch.candidate_id == candidate_id,
                CandidateJobMatch.job_posting_id.in_(job_ids),
                JobPosting.status == 'ACTIVE',
                or_(
                    JobPosting.is_email_sourced == False,
                    and_(
                        JobPosting.is_email_sourced == True,
                        JobPosting.source_tenant_id == tenant_id
                    )
                )
            )
        )
        if min_score > 0:
            count_query = count_query.where(CandidateJobMatch.match_score >= min_score)
        if grades_filter:
            count_query = count_query.where(CandidateJobMatch.match_grade.in_(grades_filter))
        if source_filter == 'email':
            count_query = count_query.where(JobPosting.is_email_sourced == True)
        elif source_filter == 'scraped':
            count_query = count_query.where(JobPosting.is_email_sourced == False)
        if platforms_filter:
            count_query = count_query.where(func.lower(JobPosting.platform).in_(platforms_filter))
        
        total_matches = db.session.scalar(count_query) or 0
        total_pages = (total_matches + per_page - 1) // per_page if total_matches > 0 else 0
        
        # Paginated results
        offset = (page - 1) * per_page
        paginated_query = match_query.offset(offset).limit(per_page)
        paginated_rows = db.session.execute(paginated_query).all()
        
        # Format response to match expected JobMatch interface
        matches_response = []
        for row in paginated_rows:
            match = row[0]  # CandidateJobMatch
            job = row[1]    # JobPosting
            
            # Get sourced_by user info for email jobs
            sourced_by_info = None
            if job.is_email_sourced and job.sourced_by_user_id:
                sourced_by_user = db.session.get(PortalUser, job.sourced_by_user_id)
                if sourced_by_user:
                    sourced_by_info = {
                        'id': sourced_by_user.id,
                        'first_name': sourced_by_user.first_name,
                        'last_name': sourced_by_user.last_name,
                        'email': sourced_by_user.email,
                    }
            
            matches_response.append({
                'id': match.id,
                'candidate_id': candidate_id,
                'job_posting_id': job.id,
                'match_score': float(match.match_score) if match.match_score else 0.0,
                'match_grade': match.match_grade,
                'skill_match_score': float(match.skill_match_score) if match.skill_match_score else 0.0,
                'keyword_match_score': None,  # DEPRECATED - no longer used
                'experience_match_score': float(match.experience_match_score) if match.experience_match_score else 0.0,
                'semantic_similarity': float(match.semantic_similarity) if match.semantic_similarity else 0.0,
                'matched_skills': match.matched_skills or [],
                'missing_skills': match.missing_skills or [],
                'matched_keywords': None,  # DEPRECATED - no longer used
                'missing_keywords': None,  # DEPRECATED - no longer used
                'status': match.status or 'SUGGESTED',
                'is_recommended': match.is_recommended,
                'job_posting': {
                    'id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'location': job.location,
                    'salary_range': job.salary_range,
                    'salary_min': job.salary_min,
                    'salary_max': job.salary_max,
                    'job_type': job.job_type,
                    'is_remote': job.is_remote,
                    'skills': job.skills or [],
                    'description': job.description[:500] if job.description else None,
                    'job_url': job.job_url,
                    'platform': job.platform,
                    'posted_date': job.posted_date.isoformat() if job.posted_date else None,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'status': job.status,
                    # Email source info
                    'is_email_sourced': job.is_email_sourced,
                    'sourced_by': sourced_by_info,
                    'source_email_sender': job.source_email_sender if job.is_email_sourced else None,
                }
            })
        
        return jsonify({
            'candidate_id': candidate_id,
            'total_matches': total_matches,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'matches': matches_response,
            'available_platforms': available_platforms,
            'available_sources': available_sources
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching matches for candidate {candidate_id}: {str(e)}")
        return error_response("Failed to fetch matches", 500)


@job_match_bp.route('/assigned-candidates', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_assigned_candidates_matches():
    """
    Get job matches for candidates assigned to the current user.
    
    GET /api/job-matches/assigned-candidates?limit=20&min_score=70
    
    Query params:
    - limit: Max matches per candidate (default 5, max 20)
    - min_score: Minimum match score filter (default 60)
    - recommended_only: Only show recommended matches (default false)
    
    Permissions: candidates.view
    
    Returns matches for:
    - Recruiters: Candidates assigned to them
    - Team Leads: Candidates assigned to them or their team recruiters
    - Managers: All candidates they manage
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Parse query parameters
        limit = request.args.get('limit', 5, type=int)
        min_score = request.args.get('min_score', 60.0, type=float)
        recommended_only = request.args.get('recommended_only', 'false').lower() == 'true'
        
        # Validate parameters
        if limit < 1 or limit > 20:
            return error_response("limit must be between 1 and 20")
        
        # Get candidates assigned to this user (explicit assignments)
        assignments_query = select(CandidateAssignment).where(
            and_(
                CandidateAssignment.assigned_to_user_id == user_id,
                CandidateAssignment.status.in_(['PENDING', 'ACCEPTED'])
            )
        )
        assignments = db.session.execute(assignments_query).scalars().all()
        candidate_ids = [assignment.candidate_id for assignment in assignments]
        
        # Also include broadcast candidates (visible to all team)
        broadcast_query = select(Candidate.id).where(
            and_(
                Candidate.tenant_id == tenant_id,
                Candidate.is_visible_to_all_team == True
            )
        )
        broadcast_candidate_ids = [row for row in db.session.execute(broadcast_query).scalars().all()]
        
        # Merge both sets of candidate IDs (avoiding duplicates)
        all_candidate_ids = list(set(candidate_ids + broadcast_candidate_ids))
        
        if not all_candidate_ids:
            return jsonify({
                'message': 'No candidates assigned to you',
                'candidates': []
            }), 200
        
        candidate_ids = all_candidate_ids
        
        # Fetch matches for assigned candidates
        results = []
        
        for candidate_id in candidate_ids:
            # Build query for this candidate's matches
            match_query = select(CandidateJobMatch).where(
                CandidateJobMatch.candidate_id == candidate_id
            )
            
            if min_score:
                match_query = match_query.where(CandidateJobMatch.match_score >= min_score)
            
            if recommended_only:
                match_query = match_query.where(CandidateJobMatch.is_recommended == True)
            
            match_query = match_query.order_by(CandidateJobMatch.match_score.desc()).limit(limit)
            
            matches = db.session.execute(match_query).scalars().all()
            
            if matches:
                candidate = db.session.get(Candidate, candidate_id)
                results.append({
                    'candidate': {
                        'id': candidate.id,
                        'first_name': candidate.first_name,
                        'last_name': candidate.last_name,
                        'email': candidate.email,
                        'current_title': candidate.current_title,
                        'skills': candidate.skills,
                        'total_experience_years': candidate.total_experience_years
                    },
                    'top_matches': [match.to_dict(include_job=True) for match in matches]
                })
        
        return jsonify({
            'total_candidates': len(results),
            'candidates': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching assigned candidates matches: {str(e)}")
        return error_response("Failed to fetch matches", 500)


@job_match_bp.route('/<int:match_id>/update-status', methods=['PATCH'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def update_match_status(match_id: int):
    """
    Update match status (viewed, applied, rejected, etc.).
    
    PATCH /api/job-matches/:id/update-status
    
    Request body:
    {
        "status": "APPLIED",           // Required: VIEWED, APPLIED, REJECTED, SHORTLISTED
        "notes": "Applied via email",  // Optional
        "rejection_reason": "..."      // Optional, for REJECTED status
    }
    
    Permissions: candidates.view
    """
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return error_response("status is required")
        
        match = JobMatchingService.update_match_status(
            match_id=match_id,
            tenant_id=g.tenant_id,
            status=data['status'],
            notes=data.get('notes'),
            rejection_reason=data.get('rejection_reason')
        )
        
        return jsonify({
            'message': 'Match status updated',
            'match': match.to_dict(include_job=True)
        }), 200
        
    except ValueError as e:
        return error_response(str(e), 400 if "Invalid status" in str(e) else 404)
    except Exception as e:
        logger.error(f"Error updating match {match_id}: {str(e)}")
        return error_response("Failed to update match", 500)


@job_match_bp.route('/stats', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_match_stats():
    """
    Get matching statistics for the tenant.
    
    GET /api/job-matches/stats
    
    Permissions: candidates.view
    
    Returns:
    - total_candidates_with_matches
    - total_matches
    - avg_match_score
    - grade_distribution (A+, A, B, C, D)
    - top_matched_jobs (jobs with most matches)
    """
    try:
        tenant_id = g.tenant_id
        
        # Get all candidates for this tenant
        candidate_ids_query = select(Candidate.id).where(Candidate.tenant_id == tenant_id)
        candidate_ids = [row[0] for row in db.session.execute(candidate_ids_query).all()]
        
        if not candidate_ids:
            return jsonify({
                'total_candidates_with_matches': 0,
                'total_matches': 0,
                'avg_match_score': 0.0,
                'grade_distribution': {},
                'top_matched_jobs': []
            }), 200
        
        # Total matches
        total_matches = db.session.query(func.count(CandidateJobMatch.id)).filter(
            CandidateJobMatch.candidate_id.in_(candidate_ids)
        ).scalar()
        
        # Average match score
        avg_score = db.session.query(func.avg(CandidateJobMatch.match_score)).filter(
            CandidateJobMatch.candidate_id.in_(candidate_ids)
        ).scalar() or 0.0
        
        # Grade distribution
        matches = db.session.execute(
            select(CandidateJobMatch.match_score).where(
                CandidateJobMatch.candidate_id.in_(candidate_ids)
            )
        ).scalars().all()
        
        grade_dist = {'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        for score in matches:
            score_val = float(score)
            if score_val >= 90:
                grade_dist['A+'] += 1
            elif score_val >= 80:
                grade_dist['A'] += 1
            elif score_val >= 70:
                grade_dist['B'] += 1
            elif score_val >= 60:
                grade_dist['C'] += 1
            elif score_val >= 50:
                grade_dist['D'] += 1
            else:
                grade_dist['F'] += 1
        
        # Top matched jobs
        top_jobs_query = select(
            CandidateJobMatch.job_posting_id,
            func.count(CandidateJobMatch.id).label('match_count')
        ).where(
            CandidateJobMatch.candidate_id.in_(candidate_ids)
        ).group_by(
            CandidateJobMatch.job_posting_id
        ).order_by(
            func.count(CandidateJobMatch.id).desc()
        ).limit(10)
        
        top_jobs_data = db.session.execute(top_jobs_query).all()
        top_matched_jobs = []
        
        for job_id, match_count in top_jobs_data:
            job = db.session.get(JobPosting, job_id)
            if job:
                top_matched_jobs.append({
                    'job_id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'match_count': match_count
                })
        
        # Candidates with matches
        candidates_with_matches = db.session.query(
            func.count(func.distinct(CandidateJobMatch.candidate_id))
        ).filter(
            CandidateJobMatch.candidate_id.in_(candidate_ids)
        ).scalar()
        
        return jsonify({
            'total_candidates_with_matches': candidates_with_matches,
            'total_matches': total_matches,
            'avg_match_score': round(float(avg_score), 2),
            'grade_distribution': grade_dist,
            'top_matched_jobs': top_matched_jobs
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching match stats: {str(e)}")
        return error_response("Failed to fetch statistics", 500)


@job_match_bp.route('/candidates/<int:candidate_id>/job/<int:job_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_match_by_candidate_and_job(candidate_id: int, job_id: int):
    """
    Get match data for a specific candidate-job pair.
    Calculates match score on-the-fly if no stored match exists.
    
    GET /api/job-matches/candidates/:candidate_id/job/:job_id
    
    Permissions: candidates.view
    
    Returns match data including score, grade, and skills analysis.
    """
    try:
        tenant_id = g.tenant_id
        
        # Verify candidate exists and belongs to tenant
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return error_response(f"Candidate {candidate_id} not found", 404)
        
        if candidate.tenant_id != tenant_id:
            return error_response("Access denied", 403)
        
        # Verify job exists
        job = db.session.get(JobPosting, job_id)
        if not job:
            return error_response(f"Job {job_id} not found", 404)
        
        # Check if job is active
        if job.status != 'ACTIVE':
            return error_response(f"Job {job_id} is not active", 400)
        
        # First check if there's a stored match
        stored_match_query = select(CandidateJobMatch).where(
            and_(
                CandidateJobMatch.candidate_id == candidate_id,
                CandidateJobMatch.job_posting_id == job_id
            )
        )
        stored_match = db.session.execute(stored_match_query).scalar_one_or_none()
        
        if stored_match:
            # Return stored match with job info
            return jsonify({
                'id': stored_match.id,
                'candidate_id': candidate_id,
                'job_posting_id': job_id,
                'match_score': float(stored_match.match_score),
                'match_grade': stored_match.match_grade,
                'skill_match_score': float(stored_match.skill_match_score) if stored_match.skill_match_score else 0,
                'experience_match_score': float(stored_match.experience_match_score) if stored_match.experience_match_score else 0,
                'semantic_similarity': float(stored_match.semantic_similarity) if stored_match.semantic_similarity else 0,
                'matched_skills': stored_match.matched_skills or [],
                'missing_skills': stored_match.missing_skills or [],
                'status': stored_match.status,
                'is_recommended': stored_match.is_recommended,
                'explanation': stored_match.recommendation_reason,
                'created_at': stored_match.created_at.isoformat() if stored_match.created_at else None,
                'job_posting': {
                    'id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'location': job.location,
                    'salary_range': job.salary_range,
                    'salary_min': job.salary_min,
                    'salary_max': job.salary_max,
                    'job_type': job.job_type,
                    'is_remote': job.is_remote,
                    'skills': job.skills or [],
                    'description': job.description[:500] if job.description else None,
                    'job_url': job.job_url,
                    'platform': job.platform,
                    'posted_date': job.posted_date.isoformat() if job.posted_date else None,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'status': job.status,
                }
            }), 200
        
        # No stored match - calculate on-the-fly
        # We allow calculating match scores for any candidate-job pair
        # The frontend already filters which jobs are shown to the user
        
        # Calculate score on-the-fly using unified scorer
        service = UnifiedScorerService()
        result = service.calculate_score(candidate, job)
        
        return jsonify({
            'id': None,  # No stored match ID
            'candidate_id': candidate_id,
            'job_posting_id': job_id,
            'match_score': round(result.overall_score, 2),
            'match_grade': result.match_grade,
            'skill_match_score': round(result.skill_score, 2),
            'experience_match_score': round(result.experience_score, 2),
            'semantic_similarity': round(result.semantic_score, 2),
            'matched_skills': result.matched_skills,
            'missing_skills': result.missing_skills,
            'status': 'SUGGESTED',
            'is_recommended': True,
            'explanation': None,
            'created_at': None,
            'job_posting': {
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'location': job.location,
                'salary_range': job.salary_range,
                'salary_min': job.salary_min,
                'salary_max': job.salary_max,
                'job_type': job.job_type,
                'is_remote': job.is_remote,
                'skills': job.skills or [],
                'description': job.description[:500] if job.description else None,
                'job_url': job.job_url,
                'platform': job.platform,
                'posted_date': job.posted_date.isoformat() if job.posted_date else None,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'status': job.status,
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching match for candidate {candidate_id}, job {job_id}: {str(e)}")
        return error_response("Failed to fetch match data", 500)


@job_match_bp.route('/<int:match_id>/ai-analysis', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_ai_compatibility_analysis(match_id: int):
    """
    Get AI-powered detailed compatibility analysis for a match.
    Results are cached for 24 hours.
    
    POST /api/job-matches/:id/ai-analysis
    
    Request body (optional):
    {
        "force_refresh": false  // Optional: Force re-analysis even if cached
    }
    
    Returns:
    - compatibility_score: AI-calculated score
    - strengths: List of candidate strengths for this role
    - gaps: List of skill/experience gaps
    - recommendations: Actionable recommendations
    - experience_analysis: Detailed experience analysis
    - culture_fit_indicators: Cultural fit observations
    - cached: Whether result was from cache
    """
    from datetime import datetime, timedelta
    
    try:
        tenant_id = g.tenant_id
        
        match = db.session.get(CandidateJobMatch, match_id)
        if not match:
            return error_response(f"Match {match_id} not found", 404)
        
        candidate = db.session.get(Candidate, match.candidate_id)
        if not candidate:
            return error_response("Candidate not found", 404)
        
        if candidate.tenant_id != tenant_id:
            return error_response("Access denied", 403)
        
        job_posting = db.session.get(JobPosting, match.job_posting_id)
        if not job_posting:
            return error_response("Job posting not found", 404)
        
        data = request.get_json() or {}
        force_refresh = data.get('force_refresh', False)
        
        cache_valid = False
        if match.ai_scored_at and not force_refresh:
            cache_expiry = match.ai_scored_at + timedelta(hours=24)
            if datetime.utcnow() < cache_expiry:
                cache_valid = True
        
        if cache_valid and match.ai_compatibility_score is not None:
            logger.info(f"Returning cached AI analysis for match {match_id}")
            return jsonify({
                'match_id': match_id,
                'candidate_id': candidate.id,
                'job_posting_id': job_posting.id,
                'compatibility_score': float(match.ai_compatibility_score),
                'details': match.ai_compatibility_details or {},
                'analyzed_at': match.ai_scored_at.isoformat() if match.ai_scored_at else None,
                'cached': True
            }), 200
        
        logger.info(f"Calculating AI analysis for match {match_id}")
        
        service = UnifiedScorerService()
        ai_result = service.calculate_ai_compatibility(candidate, job_posting)
        
        match = JobMatchingService.update_ai_analysis(
            match_id=match_id,
            tenant_id=tenant_id,
            compatibility_score=ai_result.compatibility_score,
            strengths=ai_result.strengths,
            gaps=ai_result.gaps,
            recommendations=ai_result.recommendations,
            experience_analysis=ai_result.experience_analysis,
            culture_fit_indicators=ai_result.culture_fit_indicators
        )
        
        logger.info(f"AI analysis complete for match {match_id}, score: {ai_result.compatibility_score}")
        
        return jsonify({
            'match_id': match_id,
            'candidate_id': candidate.id,
            'job_posting_id': job_posting.id,
            'compatibility_score': ai_result.compatibility_score,
            'details': {
                'strengths': ai_result.strengths,
                'gaps': ai_result.gaps,
                'recommendations': ai_result.recommendations,
                'experience_analysis': ai_result.experience_analysis,
                'culture_fit_indicators': ai_result.culture_fit_indicators
            },
            'analyzed_at': match.ai_scored_at.isoformat(),
            'cached': False
        }), 200
        
    except ValueError as e:
        logger.error(f"AI analysis error for match {match_id}: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error getting AI analysis for match {match_id}: {str(e)}")
        return error_response("Failed to get AI analysis", 500)

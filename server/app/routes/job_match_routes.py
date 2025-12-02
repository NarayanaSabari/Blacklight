"""
Job Match Routes
API endpoints for AI-powered job matching and recommendations.
"""
import logging
from flask import Blueprint, request, jsonify, g
from sqlalchemy import select, and_, func

from app import db
from app.models.candidate import Candidate
from app.models.candidate_job_match import CandidateJobMatch
from app.models.job_posting import JobPosting
from app.models.candidate_assignment import CandidateAssignment
from app.services.job_matching_service import JobMatchingService
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
    Generate job matches for a specific candidate.
    
    POST /api/job-matches/candidates/:id/generate
    
    Request body:
    {
        "min_score": 50.0,  // Optional, default 50
        "limit": 50         // Optional, default 50
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
        limit = data.get('limit', 50)
        
        # Validate parameters
        if not isinstance(min_score, (int, float)) or min_score < 0 or min_score > 100:
            return error_response("min_score must be between 0 and 100")
        
        if not isinstance(limit, int) or limit < 1 or limit > 200:
            return error_response("limit must be between 1 and 200")
        
        # Generate matches
        service = JobMatchingService(tenant_id=tenant_id)
        matches = service.generate_matches_for_candidate(
            candidate_id=candidate_id,
            min_score=min_score,
            limit=limit
        )
        
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
    Generate job matches for all active candidates in tenant.
    
    POST /api/job-matches/generate-all
    
    Request body:
    {
        "min_score": 50.0,   // Optional, default 50
        "batch_size": 10     // Optional, default 10
    }
    
    Permissions: candidates.view
    """
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
        
        # Generate matches for all candidates
        service = JobMatchingService(tenant_id=tenant_id)
        stats = service.generate_matches_for_all_candidates(
            batch_size=batch_size,
            min_score=min_score
        )
        
        return jsonify({
            'message': 'Bulk match generation complete',
            'stats': stats
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
    
    GET /api/job-matches/candidates/:id?page=1&per_page=20&status=SUGGESTED&job_status=ACTIVE
    
    Query params:
    - page: Page number (default 1)
    - per_page: Matches per page (default 20, max 100)
    - status: Filter by match status (SUGGESTED, VIEWED, APPLIED, etc.)
    - job_status: Filter by job posting status (ACTIVE, EXPIRED, etc.)
    - min_score: Minimum match score filter
    - sort_by: Sort field (match_score, created_at, default: match_score)
    - sort_order: Sort order (asc, desc, default: desc)
    
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
        
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        match_status = request.args.get('status')
        job_status = request.args.get('job_status')
        min_score = request.args.get('min_score', type=float)
        sort_by = request.args.get('sort_by', 'match_score')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Validate parameters
        if per_page < 1 or per_page > 100:
            return error_response("per_page must be between 1 and 100")
        if page < 1:
            return error_response("page must be >= 1")
        
        # Build query for total count
        count_query = select(func.count(CandidateJobMatch.id)).where(
            CandidateJobMatch.candidate_id == candidate_id
        )
        
        if match_status:
            count_query = count_query.where(CandidateJobMatch.status == match_status)
        
        if min_score is not None:
            count_query = count_query.where(CandidateJobMatch.match_score >= min_score)
        
        if job_status:
            count_query = count_query.join(JobPosting).where(JobPosting.status == job_status)
        
        total_matches = db.session.execute(count_query).scalar()
        
        # Build query for matches
        query = select(CandidateJobMatch).where(
            CandidateJobMatch.candidate_id == candidate_id
        )
        
        if match_status:
            query = query.where(CandidateJobMatch.status == match_status)
        
        if min_score is not None:
            query = query.where(CandidateJobMatch.match_score >= min_score)
        
        if job_status:
            query = query.join(JobPosting).where(JobPosting.status == job_status)
        
        # Sorting
        if sort_by == 'match_score':
            sort_column = CandidateJobMatch.match_score
        elif sort_by == 'created_at':
            sort_column = CandidateJobMatch.created_at
        else:
            sort_column = CandidateJobMatch.match_score
        
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        matches = db.session.execute(query).scalars().all()
        
        return jsonify({
            'candidate_id': candidate_id,
            'total_matches': total_matches,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_matches + per_page - 1) // per_page if total_matches > 0 else 0,
            'matches': [match.to_dict(include_job=True) for match in matches]
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
        
        # Get candidates assigned to this user
        assignments_query = select(CandidateAssignment).where(
            and_(
                CandidateAssignment.assigned_to_user_id == user_id,
                CandidateAssignment.status == 'ACTIVE'
            )
        )
        assignments = db.session.execute(assignments_query).scalars().all()
        candidate_ids = [assignment.candidate_id for assignment in assignments]
        
        if not candidate_ids:
            return jsonify({
                'message': 'No candidates assigned to you',
                'candidates': []
            }), 200
        
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
        tenant_id = g.tenant_id
        
        # Fetch match
        match = db.session.get(CandidateJobMatch, match_id)
        if not match:
            return error_response(f"Match {match_id} not found", 404)
        
        # Verify candidate belongs to tenant
        candidate = db.session.get(Candidate, match.candidate_id)
        if candidate.tenant_id != tenant_id:
            return error_response("Access denied", 403)
        
        # Parse request body
        data = request.get_json()
        if not data or 'status' not in data:
            return error_response("status is required")
        
        new_status = data['status']
        valid_statuses = ['SUGGESTED', 'VIEWED', 'APPLIED', 'REJECTED', 'SHORTLISTED']
        
        if new_status not in valid_statuses:
            return error_response(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        # Update match
        match.status = new_status
        
        if new_status == 'VIEWED' and not match.viewed_at:
            match.viewed_at = db.func.now()
        elif new_status == 'APPLIED':
            match.applied_at = db.func.now()
        elif new_status == 'REJECTED':
            match.rejected_at = db.func.now()
            if 'rejection_reason' in data:
                match.rejection_reason = data['rejection_reason']
        
        if 'notes' in data:
            match.notes = data['notes']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Match status updated',
            'match': match.to_dict(include_job=True)
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating match {match_id}: {str(e)}")
        db.session.rollback()
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

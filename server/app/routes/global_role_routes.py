"""
Global Role API Routes

Admin endpoints for managing global roles (PM_ADMIN only):
1. List all roles with statistics (GET /api/roles)
2. Get role details (GET /api/roles/{id})
3. Update role priority (PUT /api/roles/{id}/priority)
4. Merge roles (POST /api/roles/merge)
5. Add role to queue (POST /api/roles/{id}/queue)
6. Get role candidates (GET /api/roles/{id}/candidates)
"""
import logging
from flask import Blueprint, request, jsonify, g
from sqlalchemy import func

from app import db
from app.models.global_role import GlobalRole
from app.models.candidate_global_role import CandidateGlobalRole
from app.models.candidate import Candidate
from app.models.scrape_session import ScrapeSession
from app.middleware import require_pm_admin
from app.services.ai_role_normalization_service import AIRoleNormalizationService
from app.services.scrape_queue_service import ScrapeQueueService

logger = logging.getLogger(__name__)

global_role_bp = Blueprint('global_roles', __name__, url_prefix='/api/roles')


@global_role_bp.route('', methods=['GET'])
@require_pm_admin
def list_roles():
    """
    List all global roles with statistics.
    
    Query params:
    - status: Filter by queue_status (pending, processing, completed)
    - priority: Filter by priority (urgent, high, normal, low)
    - search: Search by name or aliases
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    - sort_by: Sort field (name, candidate_count, priority, queue_status)
    - sort_order: asc or desc
    
    Response:
    {
        "roles": [...],
        "total": 100,
        "page": 1,
        "per_page": 50,
        "total_pages": 2
    }
    """
    try:
        # Query params
        status = request.args.get('status')
        priority = request.args.get('priority')
        search = request.args.get('search')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        sort_by = request.args.get('sort_by', 'candidate_count')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Build query
        query = db.select(GlobalRole)
        
        if status:
            query = query.where(GlobalRole.queue_status == status)
        
        if priority:
            query = query.where(GlobalRole.priority == priority)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                GlobalRole.name.ilike(search_term) |
                GlobalRole.aliases.op('@>')(f'["{search}"]')  # JSON contains
            )
        
        # Sorting
        sort_column = getattr(GlobalRole, sort_by, GlobalRole.candidate_count)
        if sort_order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Pagination
        pagination = db.paginate(query, page=page, per_page=per_page)
        
        roles_data = []
        for role in pagination.items:
            # Get job count for this role
            from app.models.role_job_mapping import RoleJobMapping
            job_count = db.session.scalar(
                db.select(func.count(RoleJobMapping.id))
                .where(RoleJobMapping.global_role_id == role.id)
            ) or 0
            
            roles_data.append({
                "id": role.id,
                "name": role.name,
                "normalized_name": role.name,  # Same as name for now (normalized form)
                "aliases": role.aliases or [],
                "category": role.category,
                "seniority_level": None,  # Not stored in model yet, can be derived from name
                "candidate_count": role.candidate_count,
                "job_count": job_count,
                # Frontend expects 'status' and 'queue_priority' (aliases for backend fields)
                "status": role.queue_status,  # pending, processing, completed
                "queue_status": role.queue_status,  # Keep original for backward compatibility
                "queue_priority": role.priority,  # urgent, high, normal, low
                "priority": role.priority,  # Keep original for backward compatibility
                "last_scraped_at": role.last_scraped_at.isoformat() if role.last_scraped_at else None,
                "created_at": role.created_at.isoformat(),
                "similar_roles": None  # Can be computed on demand if needed
            })
        
        return jsonify({
            "roles": roles_data,
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing roles: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@global_role_bp.route('/<int:role_id>', methods=['GET'])
@require_pm_admin
def get_role(role_id: int):
    """
    Get role details including recent scrape sessions.
    """
    try:
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            return jsonify({
                "error": "Not Found",
                "message": f"Role {role_id} not found"
            }), 404
        
        # Get recent scrape sessions
        recent_sessions = db.session.scalars(
            db.select(ScrapeSession)
            .where(ScrapeSession.global_role_id == role_id)
            .order_by(ScrapeSession.created_at.desc())
            .limit(10)
        ).all()
        
        sessions_data = [{
            "id": s.id,
            "session_id": s.session_id,
            "status": s.status,
            "jobs_found": s.jobs_found,
            "jobs_imported": s.jobs_imported,
            "jobs_skipped": s.jobs_skipped,
            "error_message": s.error_message,
            "duration_seconds": s.duration_seconds,
            "created_at": s.created_at.isoformat()
        } for s in recent_sessions]
        
        return jsonify({
            "id": role.id,
            "name": role.name,
            "aliases": role.aliases or [],
            "category": role.category,
            "candidate_count": role.candidate_count,
            "queue_status": role.queue_status,
            "priority": role.priority,
            "last_scraped_at": role.last_scraped_at.isoformat() if role.last_scraped_at else None,
            "created_at": role.created_at.isoformat(),
            "recent_sessions": sessions_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting role {role_id}: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@global_role_bp.route('/<int:role_id>/priority', methods=['PUT'])
@require_pm_admin
def update_priority(role_id: int):
    """
    Update role priority.
    
    Request body:
    {
        "priority": "urgent" | "high" | "normal" | "low"
    }
    """
    data = request.get_json()
    
    if not data or 'priority' not in data:
        return jsonify({
            "error": "Bad Request",
            "message": "priority required"
        }), 400
    
    priority = data['priority']
    valid_priorities = ['urgent', 'high', 'normal', 'low']
    
    if priority not in valid_priorities:
        return jsonify({
            "error": "Bad Request",
            "message": f"priority must be one of: {valid_priorities}"
        }), 400
    
    try:
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            return jsonify({
                "error": "Not Found",
                "message": f"Role {role_id} not found"
            }), 404
        
        role.priority = priority
        db.session.commit()
        
        return jsonify({
            "id": role.id,
            "name": role.name,
            "priority": role.priority,
            "message": f"Priority updated to {priority}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating priority for role {role_id}: {e}")
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@global_role_bp.route('/<int:role_id>/approve', methods=['POST'])
@require_pm_admin
def approve_role(role_id: int):
    """
    Approve a pending role for scraping.
    
    Changes queue_status from 'pending' to 'approved' (ready for scraping).
    The scraper will pick up roles with status 'approved' or 'pending'.
    """
    try:
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            return jsonify({
                "error": "Not Found",
                "message": f"Role {role_id} not found"
            }), 404
        
        # Set status to 'approved' - reviewed and ready for scrape queue
        # This removes it from the "pending review" list in the dashboard
        role.queue_status = 'approved'
        db.session.commit()
        
        # Get job count for response
        from app.models.role_job_mapping import RoleJobMapping
        job_count = db.session.scalar(
            db.select(func.count(RoleJobMapping.id))
            .where(RoleJobMapping.global_role_id == role.id)
        ) or 0
        
        logger.info(f"Role {role_id} ({role.name}) approved by PM_ADMIN")
        
        return jsonify({
            "role": {
                "id": role.id,
                "name": role.name,
                "normalized_name": role.name,
                "aliases": role.aliases or [],
                "category": role.category,
                "seniority_level": None,
                "candidate_count": role.candidate_count,
                "job_count": job_count,
                "status": role.queue_status,
                "queue_status": role.queue_status,
                "queue_priority": role.priority,
                "priority": role.priority,
                "last_scraped_at": role.last_scraped_at.isoformat() if role.last_scraped_at else None,
                "created_at": role.created_at.isoformat(),
                "similar_roles": None
            },
            "message": f"Role '{role.name}' approved and added to scrape queue"
        }), 200
        
    except Exception as e:
        logger.error(f"Error approving role {role_id}: {e}")
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@global_role_bp.route('/<int:role_id>/reject', methods=['POST'])
@require_pm_admin
def reject_role(role_id: int):
    """
    Reject a role - permanently delete from database.
    
    This will hard-delete the role from the database.
    Use this to reject pending roles that should not be scraped.
    """
    data = request.get_json() or {}
    reason = data.get('reason', 'No reason provided')
    
    try:
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            return jsonify({
                "error": "Not Found",
                "message": f"Role {role_id} not found"
            }), 404
        
        role_name = role.name
        
        # Delete any candidate links first
        from app.models.candidate_global_role import CandidateGlobalRole
        db.session.query(CandidateGlobalRole).filter(
            CandidateGlobalRole.global_role_id == role_id
        ).delete()
        
        # Delete any job mappings
        from app.models.role_job_mapping import RoleJobMapping
        db.session.query(RoleJobMapping).filter(
            RoleJobMapping.global_role_id == role_id
        ).delete()
        
        # Hard delete the role
        db.session.delete(role)
        db.session.commit()
        
        logger.info(f"Role {role_id} ({role_name}) rejected and deleted by PM_ADMIN. Reason: {reason}")
        
        return jsonify({
            "message": f"Role '{role_name}' rejected and deleted",
            "reason": reason
        }), 200
        
    except Exception as e:
        logger.error(f"Error rejecting role {role_id}: {e}")
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@global_role_bp.route('/<int:role_id>', methods=['DELETE'])
@require_pm_admin
def delete_role(role_id: int):
    """
    Delete a role from the database.
    
    Only allowed if no candidates are linked to this role (candidate_count = 0).
    Use this to clean up approved roles that are no longer needed.
    """
    try:
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            return jsonify({
                "error": "Not Found",
                "message": f"Role {role_id} not found"
            }), 404
        
        # Check if any candidates are linked
        from app.models.candidate_global_role import CandidateGlobalRole
        linked_candidates = db.session.query(CandidateGlobalRole).filter(
            CandidateGlobalRole.global_role_id == role_id
        ).count()
        
        if linked_candidates > 0:
            return jsonify({
                "error": "Cannot Delete",
                "message": f"Role '{role.name}' has {linked_candidates} candidate(s) linked. Remove candidate links first."
            }), 400
        
        role_name = role.name
        
        # Delete any job mappings
        from app.models.role_job_mapping import RoleJobMapping
        db.session.query(RoleJobMapping).filter(
            RoleJobMapping.global_role_id == role_id
        ).delete()
        
        # Hard delete the role
        db.session.delete(role)
        db.session.commit()
        
        logger.info(f"Role {role_id} ({role_name}) deleted by PM_ADMIN")
        
        return jsonify({
            "message": f"Role '{role_name}' deleted successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting role {role_id}: {e}")
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@global_role_bp.route('/<int:role_id>/merge', methods=['POST'])
@require_pm_admin
def merge_single_role(role_id: int):
    """
    Merge this role into another role.
    
    Request body:
    {
        "target_role_id": 1
    }
    
    All candidates linked to this role will be relinked to target role.
    This role will be deleted after merge.
    """
    data = request.get_json()
    
    if not data or 'target_role_id' not in data:
        return jsonify({
            "error": "Bad Request",
            "message": "target_role_id required"
        }), 400
    
    target_id = data['target_role_id']
    
    if target_id == role_id:
        return jsonify({
            "error": "Bad Request",
            "message": "Cannot merge role into itself"
        }), 400
    
    try:
        result = AIRoleNormalizationService.merge_roles([role_id], target_id)
        
        # Get updated target role for response
        target_role = db.session.get(GlobalRole, target_id)
        
        from app.models.role_job_mapping import RoleJobMapping
        job_count = db.session.scalar(
            db.select(func.count(RoleJobMapping.id))
            .where(RoleJobMapping.global_role_id == target_id)
        ) or 0
        
        return jsonify({
            "role": {
                "id": target_role.id,
                "name": target_role.name,
                "normalized_name": target_role.name,
                "aliases": target_role.aliases or [],
                "category": target_role.category,
                "seniority_level": None,
                "candidate_count": target_role.candidate_count,
                "job_count": job_count,
                "status": target_role.queue_status,
                "queue_status": target_role.queue_status,
                "queue_priority": target_role.priority,
                "priority": target_role.priority,
                "last_scraped_at": target_role.last_scraped_at.isoformat() if target_role.last_scraped_at else None,
                "created_at": target_role.created_at.isoformat(),
                "similar_roles": None
            },
            "message": result.get('message', 'Roles merged successfully'),
            "candidates_moved": result.get('candidates_moved', 0)
        }), 200
        
    except ValueError as e:
        return jsonify({
            "error": "Bad Request",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error merging role {role_id}: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@global_role_bp.route('/merge', methods=['POST'])
@require_pm_admin
def merge_roles():
    """
    Merge multiple roles into one.
    
    Request body:
    {
        "source_role_ids": [2, 3, 4],
        "target_role_id": 1
    }
    
    All candidates linked to source roles will be relinked to target role.
    Source roles will be deleted after merge.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            "error": "Bad Request",
            "message": "Request body required"
        }), 400
    
    source_ids = data.get('source_role_ids', [])
    target_id = data.get('target_role_id')
    
    if not source_ids or not target_id:
        return jsonify({
            "error": "Bad Request",
            "message": "source_role_ids and target_role_id required"
        }), 400
    
    if target_id in source_ids:
        return jsonify({
            "error": "Bad Request",
            "message": "target_role_id cannot be in source_role_ids"
        }), 400
    
    try:
        result = AIRoleNormalizationService.merge_roles(source_ids, target_id)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({
            "error": "Bad Request",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error merging roles: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@global_role_bp.route('/<int:role_id>/queue', methods=['POST'])
@require_pm_admin
def add_to_queue(role_id: int):
    """
    Add role to scrape queue (set status to pending).
    """
    try:
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            return jsonify({
                "error": "Not Found",
                "message": f"Role {role_id} not found"
            }), 404
        
        if role.queue_status == 'processing':
            return jsonify({
                "error": "Bad Request",
                "message": "Role is currently being processed"
            }), 400
        
        role.queue_status = 'approved'
        db.session.commit()
        
        return jsonify({
            "id": role.id,
            "name": role.name,
            "queue_status": role.queue_status,
            "message": "Role added to scrape queue"
        }), 200
        
    except Exception as e:
        logger.error(f"Error adding role {role_id} to queue: {e}")
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@global_role_bp.route('/<int:role_id>/candidates', methods=['GET'])
@require_pm_admin
def get_role_candidates(role_id: int):
    """
    Get candidates linked to a role.
    
    Query params:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    """
    try:
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            return jsonify({
                "error": "Not Found",
                "message": f"Role {role_id} not found"
            }), 404
        
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        # Query candidates via CandidateGlobalRole
        query = (
            db.select(Candidate)
            .join(CandidateGlobalRole, CandidateGlobalRole.candidate_id == Candidate.id)
            .where(CandidateGlobalRole.global_role_id == role_id)
            .order_by(Candidate.created_at.desc())
        )
        
        pagination = db.paginate(query, page=page, per_page=per_page)
        
        candidates_data = []
        for candidate in pagination.items:
            candidates_data.append({
                "id": candidate.id,
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "email": candidate.email,
                "preferred_role": candidate.preferred_role,
                "tenant_id": candidate.tenant_id,
                "created_at": candidate.created_at.isoformat()
            })
        
        return jsonify({
            "role": {
                "id": role.id,
                "name": role.name
            },
            "candidates": candidates_data,
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting candidates for role {role_id}: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@global_role_bp.route('/stats', methods=['GET'])
@require_pm_admin
def get_stats():
    """
    Get overall role statistics.
    
    Response:
    {
        "total_roles": 150,
        "by_status": {"pending": 50, "processing": 3, "completed": 97},
        "by_priority": {"urgent": 5, "high": 15, "normal": 100, "low": 30},
        "total_candidates_linked": 5000,
        "average_candidates_per_role": 33
    }
    """
    try:
        # Total roles
        total_roles = db.session.scalar(
            db.select(func.count(GlobalRole.id))
        )
        
        # By status
        status_counts = db.session.execute(
            db.select(GlobalRole.queue_status, func.count(GlobalRole.id))
            .group_by(GlobalRole.queue_status)
        ).all()
        by_status = {status: count for status, count in status_counts}
        
        # By priority
        priority_counts = db.session.execute(
            db.select(GlobalRole.priority, func.count(GlobalRole.id))
            .group_by(GlobalRole.priority)
        ).all()
        by_priority = {priority: count for priority, count in priority_counts}
        
        # Total candidates linked
        total_candidates = db.session.scalar(
            db.select(func.count(CandidateGlobalRole.id))
        )
        
        # Average per role
        avg_per_role = total_candidates / total_roles if total_roles > 0 else 0
        
        return jsonify({
            "total_roles": total_roles,
            "by_status": by_status,
            "by_priority": by_priority,
            "total_candidates_linked": total_candidates,
            "average_candidates_per_role": round(avg_per_role, 1)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting role stats: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


@global_role_bp.route('/queue/cleanup', methods=['POST'])
@require_pm_admin
def cleanup_queue():
    """
    Cleanup stale sessions (stuck in processing) and optionally reset completed roles.
    
    Request body:
    {
        "reset_completed": false,  // Set to true to reset completed roles to pending
        "force_reset": false,      // Set to true to force reset ALL completed roles immediately
        "hours_threshold": 24      // Optional: hours after which roles are considered stale
    }
    """
    data = request.get_json() or {}
    reset_completed = data.get('reset_completed', False)
    force_reset = data.get('force_reset', False)
    hours_threshold = data.get('hours_threshold', 24)
    
    try:
        # Cleanup stale sessions
        stale_cleaned = ScrapeQueueService.cleanup_stale_sessions()
        
        result = {
            "stale_sessions_cleaned": stale_cleaned,
            "completed_roles_reset": 0,
            "reset_details": None
        }
        
        if reset_completed or force_reset:
            reset_result = ScrapeQueueService.reset_completed_roles(
                force=force_reset,
                hours_threshold=hours_threshold
            )
            result["completed_roles_reset"] = reset_result.get("reset_count", 0)
            result["reset_details"] = reset_result
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error cleaning up queue: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500

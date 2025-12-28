"""
Dashboard Routes
Provides statistics and overview data for the portal dashboard
"""

import logging
from datetime import datetime, timedelta

from flask import Blueprint, g, jsonify

from app import db
from app.middleware.portal_auth import require_portal_auth, with_tenant_context
from app.models.candidate import Candidate
from app.models.candidate_assignment import CandidateAssignment
from app.models.candidate_invitation import CandidateInvitation
from sqlalchemy import select, func, case, and_

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/stats', methods=['GET'])
@require_portal_auth
@with_tenant_context
def get_dashboard_stats():
    """
    Get comprehensive dashboard statistics for the current user.
    
    Returns role-specific stats:
    - For Recruiters: Their assigned candidates and activity
    - For Managers/Team Leads: Team overview and candidate distribution
    - For Admins: Tenant-wide statistics
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user.id
        user_roles = [r.name for r in g.user.roles] if g.user.roles else []
        
        # Determine user's role for stats scope
        is_admin = 'TENANT_ADMIN' in user_roles
        is_manager = 'MANAGER' in user_roles or 'TEAM_LEAD' in user_roles
        
        # Time ranges
        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        
        # ========== MY CANDIDATES (assigned to current user) ==========
        my_candidates_query = select(func.count()).select_from(CandidateAssignment).where(
            and_(
                CandidateAssignment.assigned_to_user_id == user_id,
                CandidateAssignment.status.in_(['PENDING', 'ACCEPTED', 'ACTIVE'])
            )
        )
        my_candidates_count = db.session.scalar(my_candidates_query) or 0
        
        # My candidates by status
        my_candidates_by_status_query = select(
            Candidate.onboarding_status,
            func.count(Candidate.id)
        ).select_from(Candidate).join(
            CandidateAssignment,
            CandidateAssignment.candidate_id == Candidate.id
        ).where(
            and_(
                CandidateAssignment.assigned_to_user_id == user_id,
                CandidateAssignment.status.in_(['PENDING', 'ACCEPTED', 'ACTIVE'])
            )
        ).group_by(Candidate.onboarding_status)
        
        my_candidates_by_status = {}
        for status, count in db.session.execute(my_candidates_by_status_query):
            my_candidates_by_status[status or 'PENDING_ASSIGNMENT'] = count
        
        # Recent assignments to me (last 7 days)
        recent_assignments_query = select(func.count()).select_from(CandidateAssignment).where(
            and_(
                CandidateAssignment.assigned_to_user_id == user_id,
                CandidateAssignment.assigned_at >= seven_days_ago
            )
        )
        recent_assignments = db.session.scalar(recent_assignments_query) or 0
        
        # ========== TENANT-WIDE STATS ==========
        # Total candidates in tenant
        total_candidates_query = select(func.count()).select_from(Candidate).where(
            Candidate.tenant_id == tenant_id
        )
        total_candidates = db.session.scalar(total_candidates_query) or 0
        
        # Candidates by onboarding status
        candidates_by_status_query = select(
            Candidate.onboarding_status,
            func.count(Candidate.id)
        ).where(
            Candidate.tenant_id == tenant_id
        ).group_by(Candidate.onboarding_status)
        
        candidates_by_status = {}
        for status, count in db.session.execute(candidates_by_status_query):
            candidates_by_status[status or 'PENDING_ASSIGNMENT'] = count
        
        # ========== INVITATION STATS ==========
        # Pending invitations
        pending_invitations_query = select(func.count()).select_from(CandidateInvitation).where(
            and_(
                CandidateInvitation.tenant_id == tenant_id,
                CandidateInvitation.status == 'pending'
            )
        )
        pending_invitations = db.session.scalar(pending_invitations_query) or 0
        
        # Submissions waiting for review
        pending_review_query = select(func.count()).select_from(CandidateInvitation).where(
            and_(
                CandidateInvitation.tenant_id == tenant_id,
                CandidateInvitation.status == 'submitted'
            )
        )
        pending_review = db.session.scalar(pending_review_query) or 0
        
        # ========== RECENT ACTIVITY ==========
        # Candidates added in last 7 days
        new_candidates_7d_query = select(func.count()).select_from(Candidate).where(
            and_(
                Candidate.tenant_id == tenant_id,
                Candidate.created_at >= seven_days_ago
            )
        )
        new_candidates_7d = db.session.scalar(new_candidates_7d_query) or 0
        
        # Candidates approved in last 7 days
        approved_7d_query = select(func.count()).select_from(Candidate).where(
            and_(
                Candidate.tenant_id == tenant_id,
                Candidate.approved_at >= seven_days_ago
            )
        )
        approved_7d = db.session.scalar(approved_7d_query) or 0
        
        # ========== TEAM STATS (for managers) ==========
        team_stats = None
        if is_manager or is_admin:
            from app.models.portal_user import PortalUser
            
            # Get team members (users reporting to current user)
            team_members_query = select(func.count()).select_from(PortalUser).where(
                and_(
                    PortalUser.tenant_id == tenant_id,
                    PortalUser.manager_id == user_id
                )
            )
            team_member_count = db.session.scalar(team_members_query) or 0
            
            # Get candidates assigned to team members
            team_candidates_query = select(func.count()).select_from(CandidateAssignment).join(
                PortalUser,
                PortalUser.id == CandidateAssignment.assigned_to_user_id
            ).where(
                and_(
                    PortalUser.manager_id == user_id,
                    CandidateAssignment.status.in_(['PENDING', 'ACCEPTED', 'ACTIVE'])
                )
            )
            team_candidates = db.session.scalar(team_candidates_query) or 0
            
            team_stats = {
                'team_members': team_member_count,
                'team_candidates': team_candidates
            }
        
        # ========== BUILD RESPONSE ==========
        response = {
            'my_stats': {
                'assigned_candidates': my_candidates_count,
                'by_status': my_candidates_by_status,
                'recent_assignments': recent_assignments
            },
            'tenant_stats': {
                'total_candidates': total_candidates,
                'by_status': candidates_by_status,
                'pending_invitations': pending_invitations,
                'pending_review': pending_review,
                'new_candidates_7d': new_candidates_7d,
                'approved_7d': approved_7d
            },
            'user_role': user_roles[0] if user_roles else 'RECRUITER',
            'is_admin': is_admin,
            'is_manager': is_manager
        }
        
        if team_stats:
            response['team_stats'] = team_stats
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to get dashboard statistics',
            'message': str(e)
        }), 500


@dashboard_bp.route('/recent-activity', methods=['GET'])
@require_portal_auth
@with_tenant_context
def get_recent_activity():
    """
    Get recent activity for the dashboard.
    Shows recent candidates, assignments, and status changes.
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user.id
        
        # Get recent candidates (last 10)
        recent_candidates_query = select(
            Candidate.id,
            Candidate.first_name,
            Candidate.last_name,
            Candidate.email,
            Candidate.onboarding_status,
            Candidate.created_at
        ).where(
            Candidate.tenant_id == tenant_id
        ).order_by(Candidate.created_at.desc()).limit(10)
        
        recent_candidates = []
        for row in db.session.execute(recent_candidates_query):
            recent_candidates.append({
                'id': row.id,
                'name': f"{row.first_name} {row.last_name or ''}".strip(),
                'email': row.email,
                'status': row.onboarding_status or 'PENDING_ASSIGNMENT',
                'created_at': row.created_at.isoformat() if row.created_at else None
            })
        
        # Get my recent assignments (last 5)
        from app.models.portal_user import PortalUser
        
        my_assignments_query = select(
            CandidateAssignment.id,
            CandidateAssignment.assigned_at,
            CandidateAssignment.status,
            Candidate.id.label('candidate_id'),
            Candidate.first_name,
            Candidate.last_name,
            PortalUser.first_name.label('assigned_by_first'),
            PortalUser.last_name.label('assigned_by_last')
        ).select_from(CandidateAssignment).join(
            Candidate,
            Candidate.id == CandidateAssignment.candidate_id
        ).outerjoin(
            PortalUser,
            PortalUser.id == CandidateAssignment.assigned_by_user_id
        ).where(
            CandidateAssignment.assigned_to_user_id == user_id
        ).order_by(CandidateAssignment.assigned_at.desc()).limit(5)
        
        my_assignments = []
        for row in db.session.execute(my_assignments_query):
            my_assignments.append({
                'id': row.id,
                'candidate_id': row.candidate_id,
                'candidate_name': f"{row.first_name} {row.last_name or ''}".strip(),
                'assigned_by': f"{row.assigned_by_first or ''} {row.assigned_by_last or ''}".strip() if row.assigned_by_first else 'System',
                'assigned_at': row.assigned_at.isoformat() if row.assigned_at else None,
                'status': row.status
            })
        
        return jsonify({
            'recent_candidates': recent_candidates,
            'my_recent_assignments': my_assignments
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to get recent activity',
            'message': str(e)
        }), 500

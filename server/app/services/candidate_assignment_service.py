"""Candidate Assignment Service - Handle candidate assignments and notifications."""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import select, and_, or_

from app import db
from app.models import (
    Candidate,
    CandidateAssignment,
    AssignmentNotification,
    PortalUser,
)
from app.services import AuditLogService

logger = logging.getLogger(__name__)


class CandidateAssignmentService:
    """Service for candidate assignment operations."""

    @staticmethod
    def assign_candidate(
        candidate_id: int,
        assigned_to_user_id: int,
        assigned_by_user_id: int,
        assignment_reason: Optional[str] = None,
        changed_by: str = None,
        tenant_id: int = None
    ) -> Dict:
        """
        Assign a candidate to a manager or recruiter (initial assignment).

        Args:
            candidate_id: ID of candidate to assign
            assigned_to_user_id: ID of user to assign candidate to
            assigned_by_user_id: ID of user performing assignment (must be MANAGER)
            assignment_reason: Optional reason for assignment
            changed_by: Identifier for audit log (format: "portal_user:123")
            tenant_id: Tenant ID for validation (optional, will use candidate's tenant if not provided)

        Returns:
            Dictionary with assignment details

        Raises:
            ValueError: If validation fails or permissions denied
        """
        # Get the candidate
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found")

        # Get the assignee
        assignee = db.session.get(PortalUser, assigned_to_user_id)
        if not assignee:
            raise ValueError(f"User with ID {assigned_to_user_id} not found")

        # Get the assigner (must have candidates.assign permission)
        assigner = db.session.get(PortalUser, assigned_by_user_id)
        if not assigner:
            raise ValueError("Assigner user not found")

        # Verify assigner has permission
        if not assigner.has_permission("candidates.assign"):
            raise ValueError("Only users with 'candidates.assign' permission can assign candidates")

        # Verify all belong to same tenant
        if candidate.tenant_id != assignee.tenant_id or candidate.tenant_id != assigner.tenant_id:
            raise ValueError("Candidate, assignee, and assigner must be in the same tenant")

        # Check if candidate already has an active assignment
        existing_assignment = db.session.scalar(
            select(CandidateAssignment).where(
                CandidateAssignment.candidate_id == candidate_id,
                CandidateAssignment.status.in_(['PENDING', 'ACCEPTED'])
            ).order_by(CandidateAssignment.assigned_at.desc())
        )

        if existing_assignment:
            raise ValueError(
                f"Candidate already has an active assignment to user {existing_assignment.assigned_to_user_id}. "
                "Use reassign_candidate() instead."
            )

        # Determine assignment type based on assignee's role
        assignee_roles = [role.name for role in assignee.roles]
        is_manager = 'TEAM_LEAD' in assignee_roles or 'MANAGER' in assignee_roles

        # Create assignment
        assignment = CandidateAssignment(
            candidate_id=candidate_id,
            assigned_to_user_id=assigned_to_user_id,
            assigned_by_user_id=assigned_by_user_id,
            assignment_type='INITIAL',
            assignment_reason=assignment_reason,
            status='PENDING',
        )
        db.session.add(assignment)
        db.session.flush()  # Get assignment ID

        # Update candidate denormalized fields
        if is_manager:
            candidate.manager_id = assigned_to_user_id
        else:
            candidate.recruiter_id = assigned_to_user_id

        # Update candidate onboarding status
        if not candidate.onboarding_status or candidate.onboarding_status == 'PENDING_ASSIGNMENT':
            candidate.onboarding_status = 'ASSIGNED'

        db.session.commit()

        # Create notification for assignee
        notification = AssignmentNotification(
            assignment_id=assignment.id,
            user_id=assigned_to_user_id,
            notification_type='ASSIGNED',
            is_read=False,
        )
        db.session.add(notification)
        db.session.commit()

        # Log audit
        if not changed_by:
            changed_by = f"portal_user:{assigned_by_user_id}"

        AuditLogService.log_action(
            action="ASSIGN_CANDIDATE",
            entity_type="CandidateAssignment",
            entity_id=assignment.id,
            changed_by=changed_by,
            changes={
                "candidate_id": candidate_id,
                "candidate_name": f"{candidate.first_name} {candidate.last_name}",
                "assigned_to_user_id": assigned_to_user_id,
                "assigned_to_name": assignee.full_name,
                "assignment_type": "INITIAL",
                "assignment_reason": assignment_reason,
            },
        )

        logger.info(
            f"Candidate {candidate_id} assigned to user {assigned_to_user_id} by {assigned_by_user_id}"
        )

        return {
            "message": f"Candidate '{candidate.first_name} {candidate.last_name}' assigned to '{assignee.full_name}' successfully",
            "assignment": assignment.to_dict(include_users=True, include_candidate=True),
        }

    @staticmethod
    def reassign_candidate(
        candidate_id: int,
        new_assigned_to_user_id: int,
        assigned_by_user_id: int,
        assignment_reason: Optional[str] = None,
        changed_by: str = None
    ) -> Dict:
        """
        Reassign a candidate from one user to another.

        Args:
            candidate_id: ID of candidate to reassign
            new_assigned_to_user_id: ID of new user to assign candidate to
            assigned_by_user_id: ID of user performing reassignment (must be MANAGER)
            assignment_reason: Optional reason for reassignment
            changed_by: Identifier for audit log (format: "portal_user:123")

        Returns:
            Dictionary with reassignment details

        Raises:
            ValueError: If validation fails or permissions denied
        """
        # Get the candidate
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found")

        # Get the new assignee
        new_assignee = db.session.get(PortalUser, new_assigned_to_user_id)
        if not new_assignee:
            raise ValueError(f"User with ID {new_assigned_to_user_id} not found")

        # Get the assigner (must have candidates.reassign permission)
        assigner = db.session.get(PortalUser, assigned_by_user_id)
        if not assigner:
            raise ValueError("Assigner user not found")

        # Verify assigner has permission (check for either reassign or assign)
        if not (assigner.has_permission("candidates.reassign") or assigner.has_permission("candidates.assign")):
            raise ValueError("Only users with 'candidates.reassign' or 'candidates.assign' permission can reassign candidates")

        # Verify all belong to same tenant
        if candidate.tenant_id != new_assignee.tenant_id or candidate.tenant_id != assigner.tenant_id:
            raise ValueError("Candidate, assignee, and assigner must be in the same tenant")

        # Get current active assignment
        current_assignment = db.session.scalar(
            select(CandidateAssignment).where(
                CandidateAssignment.candidate_id == candidate_id,
                CandidateAssignment.status.in_(['PENDING', 'ACCEPTED'])
            ).order_by(CandidateAssignment.assigned_at.desc())
        )

        if not current_assignment:
            raise ValueError(
                f"Candidate has no active assignment. Use assign_candidate() instead."
            )

        previous_assignee_id = current_assignment.assigned_to_user_id

        # Check if reassigning to the same person
        if previous_assignee_id == new_assigned_to_user_id:
            raise ValueError("Candidate is already assigned to this user")

        # Complete the current assignment
        current_assignment.status = 'COMPLETED'
        current_assignment.completed_at = datetime.utcnow()

        # Determine assignment type based on new assignee's role
        new_assignee_roles = [role.name for role in new_assignee.roles]
        is_manager = 'TEAM_LEAD' in new_assignee_roles or 'MANAGER' in new_assignee_roles

        # Create new assignment
        new_assignment = CandidateAssignment(
            candidate_id=candidate_id,
            assigned_to_user_id=new_assigned_to_user_id,
            assigned_by_user_id=assigned_by_user_id,
            assignment_type='REASSIGNMENT',
            previous_assignee_id=previous_assignee_id,
            assignment_reason=assignment_reason,
            status='PENDING',
        )
        db.session.add(new_assignment)
        db.session.flush()  # Get assignment ID

        # Update candidate denormalized fields
        if is_manager:
            candidate.manager_id = new_assigned_to_user_id
        else:
            candidate.recruiter_id = new_assigned_to_user_id
        
        # Update onboarding status to ASSIGNED if it was NULL or PENDING_ASSIGNMENT
        if not candidate.onboarding_status or candidate.onboarding_status == 'PENDING_ASSIGNMENT':
            candidate.onboarding_status = 'ASSIGNED'

        db.session.commit()

        # Create notification for new assignee
        notification = AssignmentNotification(
            assignment_id=new_assignment.id,
            user_id=new_assigned_to_user_id,
            notification_type='REASSIGNED',
            is_read=False,
        )
        db.session.add(notification)
        db.session.commit()

        # Log audit
        if not changed_by:
            changed_by = f"portal_user:{assigned_by_user_id}"

        previous_assignee = db.session.get(PortalUser, previous_assignee_id)

        AuditLogService.log_action(
            action="REASSIGN_CANDIDATE",
            entity_type="CandidateAssignment",
            entity_id=new_assignment.id,
            changed_by=changed_by,
            changes={
                "candidate_id": candidate_id,
                "candidate_name": f"{candidate.first_name} {candidate.last_name}",
                "previous_assignee_id": previous_assignee_id,
                "previous_assignee_name": previous_assignee.full_name if previous_assignee else "Unknown",
                "new_assigned_to_user_id": new_assigned_to_user_id,
                "new_assigned_to_name": new_assignee.full_name,
                "assignment_reason": assignment_reason,
            },
        )

        logger.info(
            f"Candidate {candidate_id} reassigned from user {previous_assignee_id} to {new_assigned_to_user_id}"
        )

        return {
            "message": f"Candidate '{candidate.first_name} {candidate.last_name}' reassigned to '{new_assignee.full_name}' successfully",
            "assignment": new_assignment.to_dict(include_users=True, include_candidate=True),
        }

    @staticmethod
    def unassign_candidate(
        candidate_id: int,
        unassigned_by_user_id: int,
        reason: Optional[str] = None,
        changed_by: str = None
    ) -> Dict:
        """
        Unassign a candidate (remove current assignment).

        Args:
            candidate_id: ID of candidate to unassign
            unassigned_by_user_id: ID of user performing unassignment (must be MANAGER)
            reason: Optional reason for unassignment
            changed_by: Identifier for audit log (format: "portal_user:123")

        Returns:
            Dictionary with success message

        Raises:
            ValueError: If validation fails or permissions denied
        """
        # Get the candidate
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found")

        # Get the unassigner (must have candidates.unassign permission)
        unassigner = db.session.get(PortalUser, unassigned_by_user_id)
        if not unassigner:
            raise ValueError("Unassigner user not found")

        # Verify unassigner has permission
        if not unassigner.has_permission("candidates.unassign"):
            raise ValueError("Only users with 'candidates.unassign' permission can unassign candidates")

        # Verify same tenant
        if candidate.tenant_id != unassigner.tenant_id:
            raise ValueError("Cannot unassign candidates from other tenants")

        # Get current active assignment
        current_assignment = db.session.scalar(
            select(CandidateAssignment).where(
                CandidateAssignment.candidate_id == candidate_id,
                CandidateAssignment.status.in_(['PENDING', 'ACCEPTED'])
            ).order_by(CandidateAssignment.assigned_at.desc())
        )

        if not current_assignment:
            raise ValueError("Candidate has no active assignment to unassign")

        previous_assignee_id = current_assignment.assigned_to_user_id
        previous_assignee = db.session.get(PortalUser, previous_assignee_id)

        # Cancel the current assignment
        current_assignment.status = 'CANCELLED'
        current_assignment.completed_at = datetime.utcnow()
        current_assignment.notes = reason

        # Clear candidate denormalized fields
        candidate.manager_id = None
        candidate.recruiter_id = None

        # Update onboarding status back to PENDING_ASSIGNMENT
        if candidate.onboarding_status == 'ASSIGNED':
            candidate.onboarding_status = 'PENDING_ASSIGNMENT'

        db.session.commit()

        # Create notification
        notification = AssignmentNotification(
            assignment_id=current_assignment.id,
            user_id=previous_assignee_id,
            notification_type='CANCELLED',
            is_read=False,
        )
        db.session.add(notification)
        db.session.commit()

        # Log audit
        if not changed_by:
            changed_by = f"portal_user:{unassigned_by_user_id}"

        AuditLogService.log_action(
            action="UNASSIGN_CANDIDATE",
            entity_type="CandidateAssignment",
            entity_id=current_assignment.id,
            changed_by=changed_by,
            changes={
                "candidate_id": candidate_id,
                "candidate_name": f"{candidate.first_name} {candidate.last_name}",
                "previous_assignee_id": previous_assignee_id,
                "previous_assignee_name": previous_assignee.full_name if previous_assignee else "Unknown",
                "reason": reason,
            },
        )

        logger.info(f"Candidate {candidate_id} unassigned by user {unassigned_by_user_id}")

        return {
            "message": f"Candidate '{candidate.first_name} {candidate.last_name}' unassigned successfully",
            "candidate_id": candidate_id,
        }

    @staticmethod
    def get_candidate_assignments(
        candidate_id: int,
        tenant_id: int,
        include_notifications: bool = False
    ) -> List[Dict]:
        """
        Get assignment history for a candidate.

        Args:
            candidate_id: ID of candidate
            tenant_id: Tenant ID for security
            include_notifications: Whether to include notification data (default: False)

        Returns:
            List of assignment dictionaries ordered by assignment date (newest first)

        Raises:
            ValueError: If candidate not found or tenant mismatch
        """
        # Verify candidate exists and belongs to tenant
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found")

        if candidate.tenant_id != tenant_id:
            raise ValueError("Candidate does not belong to the specified tenant")

        # Get all assignments for this candidate
        query = select(CandidateAssignment).where(
            CandidateAssignment.candidate_id == candidate_id
        ).order_by(CandidateAssignment.assigned_at.desc())

        assignments = list(db.session.scalars(query))

        result = [
            assignment.to_dict(include_users=True, include_candidate=False)
            for assignment in assignments
        ]

        logger.debug(f"Retrieved {len(result)} assignments for candidate {candidate_id}")

        return result

    @staticmethod
    def get_user_assigned_candidates(
        user_id: int,
        tenant_id: int,
        status_filter: Optional[str] = None,
        include_completed: bool = False
    ) -> List[Dict]:
        """
        Get all candidates assigned to a user.
        Also includes candidates with is_visible_to_all_team=True (broadcast visible).

        Args:
            user_id: ID of user
            tenant_id: Tenant ID for security
            status_filter: Optional filter by assignment status
            include_completed: If True, include completed/cancelled assignments

        Returns:
            List of candidate dictionaries with assignment info

        Raises:
            ValueError: If user not found or tenant mismatch
        """
        # Verify user exists and belongs to tenant
        user = db.session.get(PortalUser, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        if user.tenant_id != tenant_id:
            raise ValueError("User does not belong to the specified tenant")

        result = []
        seen_candidate_ids = set()

        # Part 1: Get candidates with explicit assignments to this user
        query = select(CandidateAssignment).where(
            CandidateAssignment.assigned_to_user_id == user_id
        )

        # Filter by status
        # Frontend uses ACTIVE to mean PENDING, ACCEPTED, or ACTIVE (broadcast)
        if status_filter:
            if status_filter == 'ACTIVE':
                query = query.where(
                    CandidateAssignment.status.in_(['PENDING', 'ACCEPTED', 'ACTIVE'])
                )
            else:
                query = query.where(CandidateAssignment.status == status_filter)
        elif not include_completed:
            # By default, show only active assignments (including broadcast)
            query = query.where(
                CandidateAssignment.status.in_(['PENDING', 'ACCEPTED', 'ACTIVE'])
            )

        query = query.order_by(CandidateAssignment.assigned_at.desc())

        assignments = list(db.session.scalars(query))

        # Get candidate details with assignment info
        for assignment in assignments:
            if assignment.candidate:
                seen_candidate_ids.add(assignment.candidate.id)
                
                # Map PENDING/ACCEPTED/ACTIVE to ACTIVE for frontend compatibility
                display_status = assignment.status
                if assignment.status in ['PENDING', 'ACCEPTED', 'ACTIVE']:
                    display_status = 'ACTIVE'
                    
                candidate_dict = {
                    'id': assignment.candidate.id,
                    'first_name': assignment.candidate.first_name,
                    'last_name': assignment.candidate.last_name,
                    'email': assignment.candidate.email,
                    'phone': assignment.candidate.phone,
                    'onboarding_status': assignment.candidate.onboarding_status,
                    'is_visible_to_all_team': assignment.candidate.is_visible_to_all_team,
                    'current_assignment': {
                        'id': assignment.id,
                        'assigned_to_user_id': assignment.assigned_to_user_id,
                        'assigned_by_user_id': assignment.assigned_by_user_id,
                        'assignment_type': assignment.assignment_type,
                        'status': display_status,
                        'assignment_reason': assignment.assignment_reason,
                        'assigned_at': assignment.assigned_at.isoformat() if assignment.assigned_at else None,
                        'completed_at': assignment.completed_at.isoformat() if assignment.completed_at else None,
                    }
                }
                result.append(candidate_dict)

        # Part 2: Get candidates with is_visible_to_all_team=True (only if showing active)
        # These are automatically visible to all team members without explicit assignment
        if status_filter == 'ACTIVE' or (not status_filter and not include_completed):
            broadcast_candidates_query = select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.is_visible_to_all_team == True,
                ~Candidate.id.in_(seen_candidate_ids) if seen_candidate_ids else True
            ).order_by(Candidate.updated_at.desc())

            broadcast_candidates = list(db.session.scalars(broadcast_candidates_query))

            for candidate in broadcast_candidates:
                candidate_dict = {
                    'id': candidate.id,
                    'first_name': candidate.first_name,
                    'last_name': candidate.last_name,
                    'email': candidate.email,
                    'phone': candidate.phone,
                    'onboarding_status': candidate.onboarding_status,
                    'is_visible_to_all_team': candidate.is_visible_to_all_team,
                    'current_assignment': {
                        'id': None,  # No explicit assignment record
                        'assigned_to_user_id': None,
                        'assigned_by_user_id': None,
                        'assignment_type': 'BROADCAST',
                        'status': 'ACTIVE',
                        'assignment_reason': 'Visible to all team members',
                        'assigned_at': candidate.updated_at.isoformat() if candidate.updated_at else None,
                        'completed_at': None,
                    }
                }
                result.append(candidate_dict)

        logger.debug(f"Retrieved {len(result)} assigned candidates for user {user_id}")

        return result

    @staticmethod
    def get_assignment_history(
        tenant_id: int,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get recent assignment history for a tenant.

        Args:
            tenant_id: Tenant ID
            limit: Maximum number of assignments to return

        Returns:
            List of assignment dictionaries ordered by date (newest first)
        """
        # Get assignments for candidates in this tenant
        query = select(CandidateAssignment).join(
            Candidate,
            CandidateAssignment.candidate_id == Candidate.id
        ).where(
            Candidate.tenant_id == tenant_id
        ).order_by(CandidateAssignment.assigned_at.desc()).limit(limit)

        assignments = list(db.session.scalars(query))

        result = [
            assignment.to_dict(include_users=True, include_candidate=True)
            for assignment in assignments
        ]

        logger.debug(f"Retrieved {len(result)} assignment history records for tenant {tenant_id}")

        return result

    @staticmethod
    def get_user_notifications(
        user_id: int,
        tenant_id: int,
        unread_only: bool = False,
        limit: int = 20
    ) -> Dict:
        """
        Get assignment notifications for a user.

        Args:
            user_id: ID of user
            tenant_id: Tenant ID for security
            unread_only: If True, only return unread notifications
            limit: Maximum number of notifications to return (default: 20)

        Returns:
            Dictionary with notifications list, total count, and unread count

        Raises:
            ValueError: If user not found or tenant mismatch
        """
        # Verify user exists and belongs to tenant
        user = db.session.get(PortalUser, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        if user.tenant_id != tenant_id:
            raise ValueError("User does not belong to the specified tenant")

        # Build query for notifications
        query = select(AssignmentNotification).where(
            AssignmentNotification.user_id == user_id
        )

        if unread_only:
            query = query.where(AssignmentNotification.is_read == False)

        query = query.order_by(AssignmentNotification.created_at.desc()).limit(limit)

        notifications = list(db.session.scalars(query))

        # Get unread count
        unread_count_query = select(AssignmentNotification).where(
            AssignmentNotification.user_id == user_id,
            AssignmentNotification.is_read == False
        )
        unread_count = len(list(db.session.scalars(unread_count_query)))

        result = [
            notification.to_dict(include_assignment=True, include_user=False)
            for notification in notifications
        ]

        logger.debug(f"Retrieved {len(result)} notifications for user {user_id} (unread: {unread_count})")

        return {
            'notifications': result,
            'total': len(result),
            'unread_count': unread_count
        }

    @staticmethod
    def mark_notification_as_read(
        notification_id: int,
        user_id: int
    ) -> Dict:
        """
        Mark a notification as read.

        Args:
            notification_id: ID of notification
            user_id: ID of user (for security - must own the notification)

        Returns:
            Dictionary with success message

        Raises:
            ValueError: If notification not found or doesn't belong to user
        """
        notification = db.session.get(AssignmentNotification, notification_id)
        if not notification:
            raise ValueError(f"Notification with ID {notification_id} not found")

        if notification.user_id != user_id:
            raise ValueError("Notification does not belong to this user")

        notification.mark_as_read()
        db.session.commit()

        logger.debug(f"Notification {notification_id} marked as read by user {user_id}")

        return {
            "message": "Notification marked as read",
            "notification_id": notification_id,
        }

    @staticmethod
    def broadcast_assign_candidate(
        candidate_id: int,
        assigned_by_user_id: int,
        assignment_reason: Optional[str] = None,
        changed_by: str = None,
        tenant_id: int = None
    ) -> Dict:
        """
        Broadcast assign a candidate to ALL managers and recruiters in the tenant.
        This sets is_visible_to_all_team=True, making the candidate visible to all 
        current AND future users with TEAM_LEAD, MANAGER, or RECRUITER roles.

        Args:
            candidate_id: ID of candidate to assign
            assigned_by_user_id: ID of user performing assignment
            assignment_reason: Optional reason for broadcast assignment
            changed_by: Identifier for audit log (format: "portal_user:123")
            tenant_id: Tenant ID for validation

        Returns:
            Dictionary with assignment details

        Raises:
            ValueError: If validation fails or permissions denied
        """
        from app.models.role import Role
        
        # Get the candidate
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found")

        # Get the assigner
        assigner = db.session.get(PortalUser, assigned_by_user_id)
        if not assigner:
            raise ValueError("Assigner user not found")

        # Verify assigner has permission
        if not assigner.has_permission("candidates.assign"):
            raise ValueError("Only users with 'candidates.assign' permission can broadcast assign candidates")

        # Use candidate's tenant if not provided
        if tenant_id is None:
            tenant_id = candidate.tenant_id
        
        # Verify same tenant
        if candidate.tenant_id != tenant_id or assigner.tenant_id != tenant_id:
            raise ValueError("Candidate and assigner must be in the same tenant")

        # Check if already visible to all team
        if candidate.is_visible_to_all_team:
            raise ValueError("Candidate is already visible to all team members")

        # Cancel any existing active individual assignments for this candidate
        existing_assignments = db.session.scalars(
            select(CandidateAssignment).where(
                CandidateAssignment.candidate_id == candidate_id,
                CandidateAssignment.status.in_(['PENDING', 'ACCEPTED', 'ACTIVE'])
            )
        ).all()

        cancelled_count = 0
        for existing in existing_assignments:
            existing.status = 'CANCELLED'
            existing.completed_at = datetime.utcnow()
            existing.notes = 'Cancelled due to tenant-wide broadcast'
            cancelled_count += 1

        # Set the tenant-wide visibility flag
        candidate.is_visible_to_all_team = True

        # Update candidate status
        candidate.onboarding_status = 'ASSIGNED'

        # Get count of current team members for the response message
        target_roles = ['TEAM_LEAD', 'MANAGER', 'RECRUITER']
        team_count_query = (
            select(PortalUser)
            .join(PortalUser.roles)
            .where(
                PortalUser.tenant_id == tenant_id,
                PortalUser.is_active == True,
                Role.name.in_(target_roles)
            )
            .distinct()
        )
        current_team_count = len(list(db.session.scalars(team_count_query)))

        db.session.commit()

        # Log audit
        if not changed_by:
            changed_by = f"portal_user:{assigned_by_user_id}"

        AuditLogService.log_action(
            action="BROADCAST_ASSIGN_CANDIDATE",
            entity_type="Candidate",
            entity_id=candidate_id,
            changed_by=changed_by,
            changes={
                "candidate_id": candidate_id,
                "candidate_name": f"{candidate.first_name} {candidate.last_name}",
                "assignment_type": "BROADCAST",
                "is_visible_to_all_team": True,
                "current_team_count": current_team_count,
                "previous_assignments_cancelled": cancelled_count,
                "assignment_reason": assignment_reason,
            },
        )

        logger.info(
            f"Candidate {candidate_id} set to visible for all team by user {assigned_by_user_id} "
            f"(current team size: {current_team_count})"
        )

        return {
            "message": f"Candidate '{candidate.first_name} {candidate.last_name}' is now visible to all team members (currently {current_team_count} users, plus any future hires)",
            "candidate_id": candidate_id,
            "is_visible_to_all_team": True,
            "current_team_count": current_team_count,
            "previous_assignments_cancelled": cancelled_count,
        }

    @staticmethod
    def set_candidate_visibility(
        candidate_id: int,
        is_visible_to_all_team: bool,
        changed_by_user_id: int,
        changed_by: str = None
    ) -> Dict:
        """
        Set the tenant-wide visibility flag for a candidate.
        
        Args:
            candidate_id: ID of candidate
            is_visible_to_all_team: Whether candidate should be visible to all team
            changed_by_user_id: ID of user making the change
            changed_by: Identifier for audit log (format: "portal_user:123")
            
        Returns:
            Dictionary with updated candidate info
            
        Raises:
            ValueError: If validation fails or permissions denied
        """
        # Get the candidate
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found")

        # Get the user making the change
        user = db.session.get(PortalUser, changed_by_user_id)
        if not user:
            raise ValueError("User not found")

        # Verify permission
        if not user.has_permission("candidates.assign"):
            raise ValueError("Only users with 'candidates.assign' permission can change candidate visibility")

        # Verify same tenant
        if candidate.tenant_id != user.tenant_id:
            raise ValueError("Cannot modify candidates from other tenants")

        previous_value = candidate.is_visible_to_all_team
        
        if previous_value == is_visible_to_all_team:
            return {
                "message": f"Candidate visibility unchanged (already {'visible' if is_visible_to_all_team else 'not visible'} to all team)",
                "candidate_id": candidate_id,
                "is_visible_to_all_team": is_visible_to_all_team,
            }

        # Update the flag
        candidate.is_visible_to_all_team = is_visible_to_all_team
        
        db.session.commit()

        # Log audit
        if not changed_by:
            changed_by = f"portal_user:{changed_by_user_id}"

        AuditLogService.log_action(
            action="SET_CANDIDATE_VISIBILITY",
            entity_type="Candidate",
            entity_id=candidate_id,
            changed_by=changed_by,
            changes={
                "candidate_id": candidate_id,
                "candidate_name": f"{candidate.first_name} {candidate.last_name}",
                "is_visible_to_all_team": is_visible_to_all_team,
                "previous_value": previous_value,
            },
        )

        visibility_text = "visible to all team members" if is_visible_to_all_team else "no longer visible to all team members"
        logger.info(f"Candidate {candidate_id} is now {visibility_text}")

        return {
            "message": f"Candidate '{candidate.first_name} {candidate.last_name}' is now {visibility_text}",
            "candidate_id": candidate_id,
            "is_visible_to_all_team": is_visible_to_all_team,
        }

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
            assigned_by_user_id: ID of user performing assignment (must be HIRING_MANAGER)
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
        is_manager = 'MANAGER' in assignee_roles or 'HIRING_MANAGER' in assignee_roles

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
            assigned_by_user_id: ID of user performing reassignment (must be HIRING_MANAGER)
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
        is_manager = 'MANAGER' in new_assignee_roles or 'HIRING_MANAGER' in new_assignee_roles

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
            unassigned_by_user_id: ID of user performing unassignment (must be HIRING_MANAGER)
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

        # Build query
        query = select(CandidateAssignment).where(
            CandidateAssignment.assigned_to_user_id == user_id
        )

        # Filter by status
        # Frontend uses ACTIVE to mean PENDING or ACCEPTED
        if status_filter:
            if status_filter == 'ACTIVE':
                query = query.where(
                    CandidateAssignment.status.in_(['PENDING', 'ACCEPTED'])
                )
            else:
                query = query.where(CandidateAssignment.status == status_filter)
        elif not include_completed:
            # By default, show only active assignments
            query = query.where(
                CandidateAssignment.status.in_(['PENDING', 'ACCEPTED'])
            )

        query = query.order_by(CandidateAssignment.assigned_at.desc())

        assignments = list(db.session.scalars(query))

        # Get candidate details with assignment info
        # Transform to match frontend expectation: candidates with current_assignment nested
        result = []
        for assignment in assignments:
            if assignment.candidate:
                # Map PENDING/ACCEPTED to ACTIVE for frontend compatibility
                display_status = assignment.status
                if assignment.status in ['PENDING', 'ACCEPTED']:
                    display_status = 'ACTIVE'
                    
                candidate_dict = {
                    'id': assignment.candidate.id,
                    'first_name': assignment.candidate.first_name,
                    'last_name': assignment.candidate.last_name,
                    'email': assignment.candidate.email,
                    'phone': assignment.candidate.phone,
                    'onboarding_status': assignment.candidate.onboarding_status,
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

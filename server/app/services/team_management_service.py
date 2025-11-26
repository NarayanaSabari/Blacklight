"""Team Management Service - Handle team hierarchy and manager assignments."""

import logging
from typing import List, Dict, Optional
from sqlalchemy import select, or_

from app import db
from app.models import PortalUser, Role
from app.services import AuditLogService

logger = logging.getLogger(__name__)

# Role Hierarchy for Manager Assignment (System Roles Only)
# Higher level can manage lower levels (skip-level allowed)
ROLE_HIERARCHY = {
    'TENANT_ADMIN': 1,     # Can manage: HIRING_MANAGER, MANAGER, RECRUITER
    'HIRING_MANAGER': 2,   # Can manage: MANAGER, RECRUITER  
    'MANAGER': 3,          # Can manage: RECRUITER only
    'RECRUITER': 4,        # Cannot manage anyone
}


class TeamManagementService:
    """Service for team hierarchy and manager assignment operations."""
    
    @staticmethod
    def _get_user_role_level(user: PortalUser) -> Optional[int]:
        """
        Get the hierarchy level of a user's system role.
        
        Args:
            user: PortalUser instance
            
        Returns:
            Hierarchy level (lower number = higher authority) or None if no system role
        """
        # Users should have only one role
        if not user.roles:
            return None
        
        # Get the first (and should be only) role
        role = user.roles[0]
        
        # Only check hierarchy for system roles
        if not role.is_system_role:
            return None
        
        return ROLE_HIERARCHY.get(role.name)
    
    @staticmethod
    def _can_manage(manager: PortalUser, subordinate: PortalUser) -> tuple[bool, str]:
        """
        Check if manager's role allows them to manage subordinate's role.
        
        Hierarchy Rules (System Roles Only):
        - TENANT_ADMIN (1) can manage: HIRING_MANAGER (2), MANAGER (3), RECRUITER (4)
        - HIRING_MANAGER (2) can manage: MANAGER (3), RECRUITER (4)
        - MANAGER (3) can manage: RECRUITER (4) only
        - RECRUITER (4) cannot manage anyone
        
        Args:
            manager: Proposed manager user
            subordinate: User to be managed
            
        Returns:
            Tuple of (can_manage: bool, error_message: str)
        """
        manager_level = TeamManagementService._get_user_role_level(manager)
        subordinate_level = TeamManagementService._get_user_role_level(subordinate)
        
        # If either user doesn't have a system role, allow assignment
        # (custom roles don't have hierarchy restrictions)
        if manager_level is None or subordinate_level is None:
            return (True, "")
        
        # Manager must have a lower level number (higher authority) than subordinate
        if manager_level >= subordinate_level:
            manager_role_name = manager.roles[0].name if manager.roles else "Unknown"
            subordinate_role_name = subordinate.roles[0].name if subordinate.roles else "Unknown"
            
            if manager_level == subordinate_level:
                # Same level - peers cannot manage peers
                error_msg = f"{manager_role_name} cannot manage another {subordinate_role_name} (peers cannot manage each other)"
            else:
                # Lower authority trying to manage higher
                error_msg = f"{manager_role_name} cannot manage {subordinate_role_name} (insufficient authority in role hierarchy)"
            
            return (False, error_msg)
        
        return (True, "")

    @staticmethod
    def assign_manager_to_user(
        user_id: int,
        manager_id: int,
        assigned_by_user_id: int,
        changed_by: str,
        tenant_id: Optional[int] = None
    ) -> Dict:
        """
        Assign a manager to a user.

        Args:
            user_id: ID of user to assign manager to
            manager_id: ID of manager to assign
            assigned_by_user_id: ID of user performing assignment (must be HIRING_MANAGER)
            changed_by: Identifier for audit log (format: "portal_user:123")
            tenant_id: Optional tenant ID for validation

        Returns:
            Dictionary with success message and updated user info

        Raises:
            ValueError: If validation fails or permissions denied
        """
        # Get the user being assigned
        user = db.session.get(PortalUser, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Get the manager
        manager = db.session.get(PortalUser, manager_id)
        if not manager:
            raise ValueError(f"Manager with ID {manager_id} not found")

        # Get the assigner (must be HIRING_MANAGER)
        assigner = db.session.get(PortalUser, assigned_by_user_id)
        if not assigner:
            raise ValueError("Assigner user not found")

        # Verify assigner has HIRING_MANAGER role
        if not assigner.has_permission("users.assign_manager"):
            raise ValueError("Only users with 'users.assign_manager' permission can assign managers")

        # Verify all users are in the same tenant
        if user.tenant_id != manager.tenant_id:
            raise ValueError("User and manager must be in the same tenant")

        if user.tenant_id != assigner.tenant_id:
            raise ValueError("Cannot assign managers across tenants")

        # Verify tenant_id if provided
        if tenant_id and user.tenant_id != tenant_id:
            raise ValueError("User does not belong to the specified tenant")

        # Prevent self-assignment
        if user_id == manager_id:
            raise ValueError("A user cannot be their own manager")

        # Prevent circular hierarchy
        if TeamManagementService._would_create_cycle(user_id, manager_id):
            raise ValueError("This assignment would create a circular hierarchy")
        
        # Validate role hierarchy (System Roles Only)
        # Ensures manager's role has authority to manage user's role
        can_manage, error_message = TeamManagementService._can_manage(manager, user)
        if not can_manage:
            raise ValueError(error_message)

        # Store old manager for audit log
        old_manager_id = user.manager_id

        # Assign manager
        user.manager_id = manager_id
        db.session.commit()

        # Log audit
        AuditLogService.log_action(
            action="ASSIGN_MANAGER",
            entity_type="PortalUser",
            entity_id=user_id,
            changed_by=changed_by,
            changes={
                "old_manager_id": old_manager_id,
                "new_manager_id": manager_id,
                "manager_email": manager.email,
                "manager_name": manager.full_name,
            },
        )

        logger.info(
            f"Manager assigned: User {user_id} now reports to {manager_id} by {changed_by}"
        )

        return {
            "message": f"Manager '{manager.full_name}' assigned to '{user.full_name}' successfully",
            "user_id": user_id,
            "manager_id": manager_id,
            "user": user.to_dict(include_manager=True),
        }

    @staticmethod
    def _would_create_cycle(user_id: int, proposed_manager_id: int) -> bool:
        """
        Check if assigning proposed_manager_id as manager would create a circular hierarchy.

        Args:
            user_id: ID of user receiving manager assignment
            proposed_manager_id: ID of proposed manager

        Returns:
            True if assignment would create a cycle, False otherwise
        """
        # Walk up the proposed manager's chain to see if we encounter user_id
        current_id = proposed_manager_id
        visited = set()

        while current_id:
            if current_id == user_id:
                return True  # Found a cycle

            if current_id in visited:
                # Infinite loop detected (existing cycle in data)
                logger.warning(f"Existing cycle detected in manager hierarchy at user {current_id}")
                return True

            visited.add(current_id)

            # Get the manager's manager
            manager = db.session.get(PortalUser, current_id)
            if not manager:
                break

            current_id = manager.manager_id

        return False

    @staticmethod
    def remove_manager_assignment(
        user_id: int,
        removed_by_user_id: int,
        changed_by: str
    ) -> Dict:
        """
        Remove manager assignment from a user.

        Args:
            user_id: ID of user to remove manager from
            removed_by_user_id: ID of user performing removal (must be HIRING_MANAGER)
            changed_by: Identifier for audit log (format: "portal_user:123")

        Returns:
            Dictionary with success message

        Raises:
            ValueError: If validation fails or permissions denied
        """
        # Get the user
        user = db.session.get(PortalUser, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Get the remover (must be HIRING_MANAGER)
        remover = db.session.get(PortalUser, removed_by_user_id)
        if not remover:
            raise ValueError("Remover user not found")

        # Verify remover has permission
        if not remover.has_permission("users.assign_manager"):
            raise ValueError("Only users with 'users.assign_manager' permission can remove managers")

        # Verify same tenant
        if user.tenant_id != remover.tenant_id:
            raise ValueError("Cannot remove managers across tenants")

        # Check if user has a manager
        if not user.manager_id:
            raise ValueError(f"User '{user.full_name}' does not have a manager assigned")

        # Store old manager for audit log
        old_manager_id = user.manager_id
        old_manager = db.session.get(PortalUser, old_manager_id)
        old_manager_name = old_manager.full_name if old_manager else "Unknown"

        # Remove manager
        user.manager_id = None
        db.session.commit()

        # Log audit
        AuditLogService.log_action(
            action="REMOVE_MANAGER",
            entity_type="PortalUser",
            entity_id=user_id,
            changed_by=changed_by,
            changes={
                "old_manager_id": old_manager_id,
                "old_manager_name": old_manager_name,
            },
        )

        logger.info(f"Manager removed from user {user_id} by {changed_by}")

        return {
            "message": f"Manager removed from '{user.full_name}' successfully",
            "user_id": user_id,
            "user": user.to_dict(),
        }

    @staticmethod
    def get_user_team_members(
        manager_id: int,
        tenant_id: int,
        include_indirect: bool = False
    ) -> List[Dict]:
        """
        Get all team members for a manager.

        Args:
            manager_id: ID of manager
            tenant_id: Tenant ID for security
            include_indirect: If True, include indirect reports (team members of team members)

        Returns:
            List of team member dictionaries

        Raises:
            ValueError: If manager not found or tenant mismatch
        """
        # Verify manager exists and belongs to tenant
        manager = db.session.get(PortalUser, manager_id)
        if not manager:
            raise ValueError(f"Manager with ID {manager_id} not found")

        if manager.tenant_id != tenant_id:
            raise ValueError("Manager does not belong to the specified tenant")

        if include_indirect:
            # Get all descendants recursively
            team_members = TeamManagementService._get_all_descendants(manager_id, tenant_id)
        else:
            # Get only direct reports
            query = select(PortalUser).where(
                PortalUser.manager_id == manager_id,
                PortalUser.tenant_id == tenant_id
            )
            direct_reports = list(db.session.scalars(query))
            team_members = [
                user.to_dict(include_roles=True, include_team=False)
                for user in direct_reports
            ]

        logger.debug(f"Retrieved {len(team_members)} team members for manager {manager_id}")

        return team_members

    @staticmethod
    def _get_all_descendants(manager_id: int, tenant_id: int, level: int = 0) -> List[Dict]:
        """
        Recursively get all descendants (direct and indirect reports) of a manager.

        Args:
            manager_id: ID of manager
            tenant_id: Tenant ID for filtering
            level: Current recursion level (for hierarchy tracking)

        Returns:
            List of user dictionaries with hierarchy level
        """
        if level > 10:  # Prevent infinite recursion
            logger.warning(f"Maximum recursion depth reached for manager {manager_id}")
            return []

        # Get direct reports
        query = select(PortalUser).where(
            PortalUser.manager_id == manager_id,
            PortalUser.tenant_id == tenant_id
        )
        direct_reports = list(db.session.scalars(query))

        result = []
        for user in direct_reports:
            user_dict = user.to_dict(include_roles=True, include_team=False)
            user_dict['hierarchy_level'] = level + 1

            result.append(user_dict)

            # Recursively get this user's team members
            descendants = TeamManagementService._get_all_descendants(user.id, tenant_id, level + 1)
            result.extend(descendants)

        return result

    @staticmethod
    def get_team_hierarchy(tenant_id: int) -> List[Dict]:
        """
        Get complete team hierarchy for a tenant.
        Returns users organized in a hierarchical structure.

        Args:
            tenant_id: Tenant ID

        Returns:
            List of top-level users (those without managers) with nested team_members

        Raises:
            ValueError: If tenant not found
        """
        # Get all users in the tenant
        query = select(PortalUser).where(
            PortalUser.tenant_id == tenant_id,
            PortalUser.is_active == True
        ).order_by(PortalUser.first_name, PortalUser.last_name)

        all_users = list(db.session.scalars(query))

        # Build a map of user_id -> user data
        user_map = {}
        for user in all_users:
            user_dict = user.to_dict(include_roles=True, include_manager=False)
            user_dict['team_members'] = []
            user_map[user.id] = user_dict

        # Build the hierarchy by linking children to parents
        top_level_users = []
        for user in all_users:
            user_dict = user_map[user.id]

            if user.manager_id and user.manager_id in user_map:
                # Add this user to their manager's team_members
                user_map[user.manager_id]['team_members'].append(user_dict)
            else:
                # No manager or manager not in map - this is a top-level user
                top_level_users.append(user_dict)

        logger.info(f"Built team hierarchy for tenant {tenant_id}: {len(top_level_users)} top-level users")

        return top_level_users

    @staticmethod
    def get_managers_list(tenant_id: int, role_name: Optional[str] = None) -> List[Dict]:
        """
        Get list of all users who have team members (are managers).

        Args:
            tenant_id: Tenant ID
            role_name: Optional filter by role name (e.g., "MANAGER", "HIRING_MANAGER")

        Returns:
            List of manager dictionaries with team_member_count

        Raises:
            ValueError: If tenant not found
        """
        # Get all users in tenant who have team members
        query = select(PortalUser).where(
            PortalUser.tenant_id == tenant_id,
            PortalUser.is_active == True
        )

        all_users = list(db.session.scalars(query))

        # Find users who are managers (have at least one team member)
        managers = []
        for user in all_users:
            # Count team members
            team_member_count = len([u for u in all_users if u.manager_id == user.id])

            if team_member_count > 0:
                # This user is a manager
                user_dict = user.to_dict(include_roles=True, include_manager=True)
                user_dict['team_member_count'] = team_member_count

                # Filter by role if specified
                if role_name:
                    user_roles = [role.name for role in user.roles]
                    if role_name in user_roles:
                        managers.append(user_dict)
                else:
                    managers.append(user_dict)

        logger.info(f"Found {len(managers)} managers in tenant {tenant_id}")

        return managers

    @staticmethod
    def get_available_managers(
        tenant_id: int,
        exclude_user_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Get list of users who can be assigned as managers.
        Typically includes MANAGER and HIRING_MANAGER roles.

        Args:
            tenant_id: Tenant ID
            exclude_user_id: Optional user ID to exclude (useful when assigning to self)

        Returns:
            List of available manager dictionaries
        """
        # Get all active users with MANAGER or HIRING_MANAGER roles
        query = select(PortalUser).where(
            PortalUser.tenant_id == tenant_id,
            PortalUser.is_active == True
        )

        if exclude_user_id:
            query = query.where(PortalUser.id != exclude_user_id)

        all_users = list(db.session.scalars(query))

        # Filter to users with appropriate roles
        available_managers = []
        for user in all_users:
            user_roles = [role.name for role in user.roles]
            if 'MANAGER' in user_roles or 'HIRING_MANAGER' in user_roles:
                user_dict = user.to_dict(include_roles=True)
                available_managers.append(user_dict)

        logger.debug(f"Found {len(available_managers)} available managers in tenant {tenant_id}")

        return available_managers

    @staticmethod
    def get_hierarchical_team_members(user_id: int, tenant_id: int) -> List[Dict]:
        """
        Get current user's direct team members with candidate and sub-team counts.
        Used for hierarchical "Your Candidates" drill-down view.
        
        For TENANT_ADMIN: Returns all HR/HIRING_MANAGER users (top-level users without a manager)
        For other roles: Returns direct reports (users where manager_id = current user)
        
        Args:
            user_id: Current user's ID
            tenant_id: Tenant ID
            
        Returns:
            List of team members with structure:
            {
                'id': int,
                'full_name': str,
                'email': str,
                'role_name': str,
                'candidate_count': int,  # Candidates assigned to this user
                'team_member_count': int,  # Direct reports count
                'has_team_members': bool  # True if user has direct reports
            }
        """
        from app.models import Candidate, CandidateAssignment, Role
        from sqlalchemy import func, distinct
        
        # Get current user to check their role
        current_user = db.session.get(PortalUser, user_id)
        if not current_user:
            return []
        
        # Check if user is TENANT_ADMIN
        is_tenant_admin = any(role.name == 'TENANT_ADMIN' for role in current_user.roles)
        
        if is_tenant_admin:
            # TENANT_ADMIN sees all top-level users (HR/HIRING_MANAGER without managers)
            # Get HIRING_MANAGER role ID
            hiring_manager_role = db.session.scalar(
                select(Role).where(
                    Role.name == 'HIRING_MANAGER',
                    Role.tenant_id == tenant_id
                )
            )
            
            if hiring_manager_role:
                # Get all HR users (HIRING_MANAGER role) who have no manager
                direct_reports_query = select(PortalUser).where(
                    PortalUser.tenant_id == tenant_id,
                    PortalUser.is_active == True,
                    or_(
                        PortalUser.manager_id.is_(None),
                        PortalUser.manager_id == user_id
                    )
                ).join(PortalUser.roles).where(
                    Role.id == hiring_manager_role.id
                )
            else:
                # Fallback: get all users without a manager
                direct_reports_query = select(PortalUser).where(
                    PortalUser.tenant_id == tenant_id,
                    PortalUser.is_active == True,
                    PortalUser.manager_id.is_(None),
                    PortalUser.id != user_id  # Exclude self
                )
        else:
            # Regular users: get direct reports (users where manager_id = current user)
            direct_reports_query = select(PortalUser).where(
                PortalUser.manager_id == user_id,
                PortalUser.tenant_id == tenant_id,
                PortalUser.is_active == True
            )
        
        direct_reports = list(db.session.scalars(direct_reports_query))
        
        result = []
        for member in direct_reports:
            # Get primary role name
            role_name = member.roles[0].name if member.roles else 'USER'
            
            # Count candidates assigned to this member (via manager_id or recruiter_id)
            candidate_count = db.session.scalar(
                select(func.count(distinct(Candidate.id)))
                .where(
                    Candidate.tenant_id == tenant_id,
                    or_(
                        Candidate.manager_id == member.id,
                        Candidate.recruiter_id == member.id
                    )
                )
            ) or 0
            
            # Count this member's direct reports
            team_member_count = db.session.scalar(
                select(func.count(PortalUser.id))
                .where(
                    PortalUser.manager_id == member.id,
                    PortalUser.tenant_id == tenant_id,
                    PortalUser.is_active == True
                )
            ) or 0
            
            result.append({
                'id': member.id,
                'full_name': f"{member.first_name} {member.last_name}",
                'email': member.email,
                'role_name': role_name,
                'candidate_count': candidate_count,
                'team_member_count': team_member_count,
                'has_team_members': team_member_count > 0
            })
        
        return result

    @staticmethod
    def get_team_member_candidates(
        member_id: int,
        requester_id: int,
        tenant_id: int
    ) -> List[Dict]:
        """
        Get candidates assigned to a specific team member.
        Verifies the requester has permission to view these candidates (hierarchical access).
        
        Args:
            member_id: Team member's user ID whose candidates to fetch
            requester_id: User requesting the data (must be in hierarchy above member)
            tenant_id: Tenant ID
            
        Returns:
            List of candidate dictionaries
            
        Raises:
            ValueError: If requester doesn't have access to view member's candidates
        """
        from app.models import Candidate
        
        # Verify access: requester must be in the hierarchy above the member
        # This checks if requester is member's manager (direct or indirect)
        if not TeamManagementService._is_in_hierarchy(requester_id, member_id, tenant_id):
            raise ValueError("You don't have permission to view this team member's candidates")
        
        # Get candidates assigned to this member
        candidates_query = select(Candidate).where(
            Candidate.tenant_id == tenant_id,
            or_(
                Candidate.manager_id == member_id,
                Candidate.recruiter_id == member_id
            )
        ).order_by(Candidate.created_at.desc())
        
        candidates = list(db.session.scalars(candidates_query))
        
        return [c.to_dict(include_assignments=False) for c in candidates]

    @staticmethod
    def _is_in_hierarchy(manager_id: int, subordinate_id: int, tenant_id: int) -> bool:
        """
        Check if manager_id is in the hierarchy above subordinate_id.
        TENANT_ADMIN role has access to all users in their tenant.
        
        Args:
            manager_id: Potential manager/supervisor user ID
            subordinate_id: Subordinate user ID
            tenant_id: Tenant ID
            
        Returns:
            True if manager is above subordinate in hierarchy, False otherwise
        """
        # If same user, they can view their own
        if manager_id == subordinate_id:
            return True
        
        # Check if manager is TENANT_ADMIN - they can access anyone
        manager = db.session.get(PortalUser, manager_id)
        if manager and any(role.name == 'TENANT_ADMIN' for role in manager.roles):
            return True
        
        # Walk up the subordinate's management chain
        current_user = db.session.get(PortalUser, subordinate_id)
        if not current_user or current_user.tenant_id != tenant_id:
            return False
        
        # Check up to 10 levels (prevent infinite loops)
        for _ in range(10):
            if not current_user.manager_id:
                break
            
            if current_user.manager_id == manager_id:
                return True
            
            # Move up one level
            current_user = db.session.get(PortalUser, current_user.manager_id)
            if not current_user or current_user.tenant_id != tenant_id:
                break
        
        return False

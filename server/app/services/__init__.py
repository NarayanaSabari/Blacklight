"""Business logic services package."""

import logging
from typing import Optional, Dict, List
from sqlalchemy import select

from app import db
from app.models import AuditLog

logger = logging.getLogger(__name__)


class AuditLogService:
    """Service for audit logging."""
    
    @staticmethod
    def log_action(
        action: str,
        entity_type: str,
        entity_id: int,
        changed_by: str,
        changes: Optional[Dict] = None,
    ) -> AuditLog:
        """Log an action.
        
        Args:
            action: Action type (CREATE, UPDATE, DELETE, etc.)
            entity_type: Type of entity
            entity_id: Entity ID
            changed_by: Identifier of user performing action (format: "pm_admin:123" or "portal_user:456")
            changes: Dictionary of changes
        
        Returns:
            Created audit log
        """
        audit_log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            changed_by=changed_by,
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
        logger.debug(f"Audit log: {action} {entity_type} {entity_id} by {changed_by}")
        return audit_log
    
    @staticmethod
    def get_logs(
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs.
        
        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            limit: Maximum number of logs
        
        Returns:
            List of audit logs
        """
        query = select(AuditLog).order_by(AuditLog.created_at.desc())
        
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
        
        if entity_id:
            query = query.where(AuditLog.entity_id == entity_id)
        
        return list(db.session.scalars(query.limit(limit)))


# Import tenant management services (after AuditLogService is defined)
from app.services.subscription_plan_service import SubscriptionPlanService
from app.services.tenant_service import TenantService
from app.services.portal_user_service import PortalUserService
from app.services.pm_admin_service import PMAdminService
from app.services.pm_admin_auth_service import PMAdminAuthService
from app.services.portal_auth_service import PortalAuthService
from app.services.role_service import RoleService
from app.services.permission_service import PermissionService
from app.services.candidate_service import CandidateService
from app.services.invitation_service import InvitationService
from app.services.document_service import DocumentService
from app.services.email_service import EmailService
from app.services.team_management_service import TeamManagementService
from app.services.candidate_assignment_service import CandidateAssignmentService

__all__ = [
    "AuditLogService",
    "SubscriptionPlanService",
    "TenantService",
    "PortalUserService",
    "PMAdminService",
    "PMAdminAuthService",
    "PortalAuthService",
    "RoleService",
    "PermissionService",
    "CandidateService",
    "InvitationService",
    "DocumentService",
    "EmailService",
    "TeamManagementService",
    "CandidateAssignmentService",
]

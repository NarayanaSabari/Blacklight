"""SQLAlchemy models package."""

from datetime import datetime
from app import db


class BaseModel(db.Model):
    """Base model with common columns."""
    
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        """String representation."""
        return f"<{self.__class__.__name__} id={self.id}>"


class AuditLog(BaseModel):
    """Audit log model for tracking changes."""
    
    __tablename__ = "audit_logs"
    
    action = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(100), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    changes = db.Column(db.JSON, nullable=True)
    # Changed by: can be PM admin user ID or portal user ID (store as string with prefix)
    changed_by = db.Column(db.String(100), nullable=True)
    
    def to_dict(self):
        """Convert model to dictionary."""
        data = super().to_dict()
        data.update({
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "changes": self.changes,
            "changed_by": self.changed_by,
        })
        return data


# Import tenant management models to ensure they're registered with SQLAlchemy
from app.models.subscription_plan import SubscriptionPlan
from app.models.tenant import Tenant, TenantStatus, BillingCycle
from app.models.pm_admin_user import PMAdminUser
from app.models.portal_user import PortalUser
from app.models.tenant_subscription_history import TenantSubscriptionHistory
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole
from app.models.candidate import Candidate

# Import candidate onboarding models
from app.models.candidate_invitation import CandidateInvitation
from app.models.invitation_audit_log import InvitationAuditLog
from app.models.candidate_document import CandidateDocument

# Import candidate assignment models
from app.models.candidate_assignment import CandidateAssignment
from app.models.assignment_notification import AssignmentNotification

# Import job matching models
from app.models.job_posting import JobPosting
from app.models.candidate_job_match import CandidateJobMatch
from app.models.job_application import JobApplication
from app.models.job_import_batch import JobImportBatch

"""
Global Role Service
Business logic for global role management
"""
import logging

from app import db
from app.models.global_role import GlobalRole
from app.models.candidate_global_role import CandidateGlobalRole
from app.models.role_job_mapping import RoleJobMapping

logger = logging.getLogger(__name__)


class GlobalRoleService:
    """Service for global role operations"""
    
    def update_priority(self, role_id: int, priority: str) -> GlobalRole:
        """
        Update role priority.
        
        Args:
            role_id: Role ID
            priority: New priority value (urgent, high, normal, low)
            
        Returns:
            Updated GlobalRole
            
        Raises:
            ValueError: If role not found
        """
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        role.priority = priority
        db.session.commit()
        db.session.refresh(role)
        
        logger.info(f"Role {role_id} priority updated to {priority}")
        return role
    
    def approve_role(self, role_id: int) -> GlobalRole:
        """
        Approve role for scraping (set queue_status to 'approved').
        
        Args:
            role_id: Role ID
            
        Returns:
            Updated GlobalRole
            
        Raises:
            ValueError: If role not found
        """
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        role.queue_status = 'approved'
        db.session.commit()
        db.session.refresh(role)
        
        logger.info(f"Role {role_id} ({role.name}) approved by PM_ADMIN")
        return role
    
    def reject_role(self, role_id: int, reason: str) -> str:
        """
        Reject and delete role with all related data.
        
        Args:
            role_id: Role ID
            reason: Rejection reason
            
        Returns:
            Role name (for response message)
            
        Raises:
            ValueError: If role not found
        """
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        role_name = role.name
        
        # Delete candidate links
        db.session.query(CandidateGlobalRole).filter(
            CandidateGlobalRole.global_role_id == role_id
        ).delete()
        
        # Delete job mappings
        db.session.query(RoleJobMapping).filter(
            RoleJobMapping.global_role_id == role_id
        ).delete()
        
        # Delete role
        db.session.delete(role)
        db.session.commit()
        db.session.expire_all()
        
        logger.info(f"Role {role_id} ({role_name}) rejected and deleted by PM_ADMIN. Reason: {reason}")
        return role_name
    
    def delete_role(self, role_id: int) -> str:
        """
        Delete role with validation (no linked candidates).
        
        Args:
            role_id: Role ID
            
        Returns:
            Role name (for response message)
            
        Raises:
            ValueError: If role not found or has linked candidates
        """
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        # Check for linked candidates
        linked_candidates = db.session.query(CandidateGlobalRole).filter(
            CandidateGlobalRole.global_role_id == role_id
        ).count()
        
        if linked_candidates > 0:
            raise ValueError(
                f"Role '{role.name}' has {linked_candidates} candidate(s) linked. "
                "Remove candidate links first."
            )
        
        role_name = role.name
        
        # Delete job mappings
        db.session.query(RoleJobMapping).filter(
            RoleJobMapping.global_role_id == role_id
        ).delete()
        
        # Delete role
        db.session.delete(role)
        db.session.commit()
        db.session.expire_all()
        
        logger.info(f"Role {role_id} ({role_name}) deleted by PM_ADMIN")
        return role_name
    
    def add_to_queue(self, role_id: int) -> GlobalRole:
        """
        Add role to scrape queue (set status to 'approved').
        
        Args:
            role_id: Role ID
            
        Returns:
            Updated GlobalRole
            
        Raises:
            ValueError: If role not found or currently processing
        """
        role = db.session.get(GlobalRole, role_id)
        
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        if role.queue_status == 'processing':
            raise ValueError("Role is currently being processed")
        
        role.queue_status = 'approved'
        db.session.commit()
        db.session.refresh(role)
        
        logger.info(f"Role {role_id} ({role.name}) added to scrape queue")
        return role

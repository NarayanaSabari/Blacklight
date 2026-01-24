"""
Role Location Queue Service
Business logic for managing the role+location scraping queue.

Features:
- Approve/reject queue entries
- Update entry priority
- Delete entries
- Bulk operations
"""
import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select

from app import db
from app.models.role_location_queue import RoleLocationQueue

logger = logging.getLogger(__name__)


class RoleLocationQueueService:
    """Service for managing role location queue entries."""
    
    @staticmethod
    def approve_entry(entry_id: int) -> RoleLocationQueue:
        """
        Approve a role+location queue entry for scraping.
        
        Args:
            entry_id: ID of the queue entry
            
        Returns:
            Updated RoleLocationQueue instance
            
        Raises:
            ValueError: If entry not found or invalid status
        """
        entry = db.session.get(RoleLocationQueue, entry_id)
        
        if not entry:
            raise ValueError("Entry not found")
        
        if entry.queue_status not in ['pending', 'rejected']:
            raise ValueError(
                f"Cannot approve entry with status '{entry.queue_status}'"
            )
        
        entry.queue_status = 'approved'
        entry.updated_at = datetime.utcnow()
        
        db.session.commit()
        db.session.refresh(entry)
        
        role_name = entry.global_role.name if entry.global_role else "Unknown"
        logger.info(f"Approved role+location entry {entry_id}: {role_name} @ {entry.location}")
        
        return entry
    
    @staticmethod
    def reject_entry(entry_id: int) -> RoleLocationQueue:
        """
        Reject a role+location queue entry.
        
        Args:
            entry_id: ID of the queue entry
            
        Returns:
            Updated RoleLocationQueue instance
            
        Raises:
            ValueError: If entry not found or invalid status
        """
        entry = db.session.get(RoleLocationQueue, entry_id)
        
        if not entry:
            raise ValueError("Entry not found")
        
        if entry.queue_status not in ['pending', 'approved']:
            raise ValueError(
                f"Cannot reject entry with status '{entry.queue_status}'"
            )
        
        entry.queue_status = 'rejected'
        entry.updated_at = datetime.utcnow()
        
        db.session.commit()
        db.session.refresh(entry)
        
        role_name = entry.global_role.name if entry.global_role else "Unknown"
        logger.info(f"Rejected role+location entry {entry_id}: {role_name} @ {entry.location}")
        
        return entry
    
    @staticmethod
    def update_priority(entry_id: int, priority: str) -> RoleLocationQueue:
        """
        Update priority of a role+location queue entry.
        
        Args:
            entry_id: ID of the queue entry
            priority: New priority (urgent, high, normal, low)
            
        Returns:
            Updated RoleLocationQueue instance
            
        Raises:
            ValueError: If entry not found or invalid priority
        """
        if priority not in ['urgent', 'high', 'normal', 'low']:
            raise ValueError("Invalid priority. Must be: urgent, high, normal, low")
        
        entry = db.session.get(RoleLocationQueue, entry_id)
        
        if not entry:
            raise ValueError("Entry not found")
        
        entry.priority = priority
        entry.updated_at = datetime.utcnow()
        
        db.session.commit()
        db.session.refresh(entry)
        
        logger.info(f"Updated priority for role+location entry {entry_id} to {priority}")
        
        return entry
    
    @staticmethod
    def delete_entry(entry_id: int) -> tuple[int, str, str]:
        """
        Delete a role+location queue entry.
        
        Args:
            entry_id: ID of the queue entry
            
        Returns:
            Tuple of (entry_id, role_name, location) for logging
            
        Raises:
            ValueError: If entry not found
        """
        entry = db.session.get(RoleLocationQueue, entry_id)
        
        if not entry:
            raise ValueError("Entry not found")
        
        role_name = entry.global_role.name if entry.global_role else "Unknown"
        location = entry.location
        
        db.session.delete(entry)
        db.session.commit()
        db.session.expire_all()
        
        logger.info(f"Deleted role+location entry {entry_id}: {role_name} @ {location}")
        
        return entry_id, role_name, location
    
    @staticmethod
    def bulk_approve_entries(entry_ids: Optional[List[int]] = None) -> int:
        """
        Bulk approve pending role+location queue entries.
        
        Args:
            entry_ids: Optional list of specific entry IDs to approve.
                      If None, approves all pending entries.
            
        Returns:
            Number of entries approved
        """
        if not entry_ids:
            stmt = select(RoleLocationQueue).where(RoleLocationQueue.queue_status == 'pending')
            entries = db.session.scalars(stmt).all()
        else:
            stmt = select(RoleLocationQueue).where(
                RoleLocationQueue.id.in_(entry_ids),
                RoleLocationQueue.queue_status == 'pending'
            )
            entries = db.session.scalars(stmt).all()
        
        approved_count = 0
        for entry in entries:
            entry.queue_status = 'approved'
            entry.updated_at = datetime.utcnow()
            approved_count += 1
        
        db.session.commit()
        
        logger.info(f"Bulk approved {approved_count} role+location entries")
        
        return approved_count

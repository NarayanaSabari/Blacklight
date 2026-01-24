"""
Email Job Service

Business logic for managing email-sourced job postings.
Handles CRUD operations for jobs sourced from email integrations.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import select

from app import db
from app.models.job_posting import JobPosting

logger = logging.getLogger(__name__)


class EmailJobService:
    """Service for managing email-sourced job postings"""
    
    @staticmethod
    def update_email_job(
        job_id: int,
        tenant_id: int,
        update_data: Dict[str, Any]
    ) -> JobPosting:
        """
        Update an email-sourced job posting.
        
        Args:
            job_id: Job posting ID
            tenant_id: Tenant ID for multi-tenant scoping
            update_data: Dictionary of fields to update
            
        Returns:
            Updated JobPosting instance
            
        Raises:
            ValueError: If job not found or not email-sourced
        """
        # Query for email-sourced job in this tenant
        stmt = select(JobPosting).where(
            JobPosting.id == job_id,
            JobPosting.is_email_sourced == True,
            JobPosting.source_tenant_id == tenant_id,
        )
        job = db.session.scalar(stmt)
        
        if not job:
            raise ValueError("Email-sourced job not found")
        
        # Define allowed fields for update
        updateable_fields = [
            "title", "company", "location", "description", "job_type",
            "remote_type", "skills", "required_skills", "preferred_skills",
            "experience_years", "requirements", "min_rate", "max_rate",
            "min_salary", "max_salary", "employment_type", "duration_months",
            "status", "client_name",
        ]
        
        # Update allowed fields
        for field in updateable_fields:
            if field in update_data:
                setattr(job, field, update_data[field])
        
        # Update timestamp
        job.updated_at = datetime.utcnow()
        
        # Commit transaction
        db.session.commit()
        
        logger.info(f"Updated email job {job_id} for tenant {tenant_id}")
        
        return job
    
    @staticmethod
    def delete_email_job(job_id: int, tenant_id: int) -> bool:
        """
        Delete an email-sourced job posting.
        
        Args:
            job_id: Job posting ID
            tenant_id: Tenant ID for multi-tenant scoping
            
        Returns:
            True if deleted successfully
            
        Raises:
            ValueError: If job not found or not email-sourced
        """
        # Query for email-sourced job in this tenant
        stmt = select(JobPosting).where(
            JobPosting.id == job_id,
            JobPosting.is_email_sourced == True,
            JobPosting.source_tenant_id == tenant_id,
        )
        job = db.session.scalar(stmt)
        
        if not job:
            raise ValueError("Email-sourced job not found")
        
        # Delete job
        db.session.delete(job)
        db.session.commit()
        db.session.expire_all()  # Expire session after delete
        
        logger.info(f"Deleted email job {job_id} for tenant {tenant_id}")
        
        return True

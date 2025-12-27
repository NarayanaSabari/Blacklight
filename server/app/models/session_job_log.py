"""
Session Job Log Model

Logs all jobs received during a scrape session with their import status.
Used for detailed session analysis and debugging duplicate detection.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID as PyUUID
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app import db


class SessionJobLog(db.Model):
    """
    Logs each job received during a scrape session.
    
    Stores:
    - Raw job data as received from scraper
    - Import status (imported, skipped, error)
    - Skip reason with details
    - Reference to duplicate job if applicable
    """
    __tablename__ = "session_job_logs"
    
    id = db.Column(Integer, primary_key=True)
    
    # Session reference
    session_id = db.Column(
        PG_UUID(as_uuid=True),
        db.ForeignKey("scrape_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Platform info
    platform_name = db.Column(db.String(50), nullable=False, index=True)
    platform_status_id = db.Column(db.Integer, nullable=True)
    
    # Job identification
    external_job_id = db.Column(db.String(255), nullable=True)
    job_index = db.Column(db.Integer, nullable=False)  # Order in the batch
    
    # Raw job data from scraper
    raw_job_data = db.Column(db.JSON, nullable=False, default=dict)
    
    # Extracted key fields for quick filtering
    title = db.Column(db.String(500), nullable=True)
    company = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    
    # Import result
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        index=True
    )  # pending, imported, skipped, error
    
    # For imported jobs
    imported_job_id = db.Column(
        db.Integer,
        db.ForeignKey("job_postings.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # For skipped jobs - reason details
    skip_reason = db.Column(db.String(50), nullable=True)
    # duplicate_platform_id, duplicate_title_company_location, 
    # duplicate_title_company_description, missing_required, error
    
    skip_reason_detail = db.Column(db.Text, nullable=True)  # Human-readable explanation
    
    # Reference to the duplicate job that caused the skip
    duplicate_job_id = db.Column(
        db.Integer,
        db.ForeignKey("job_postings.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Error message if status is 'error'
    error_message = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    session = db.relationship(
        "ScrapeSession",
        backref=db.backref("job_logs", lazy="dynamic", cascade="all, delete-orphan")
    )
    
    imported_job = db.relationship(
        "JobPosting",
        foreign_keys=[imported_job_id],
        backref=db.backref("import_log", uselist=False)
    )
    
    duplicate_job = db.relationship(
        "JobPosting",
        foreign_keys=[duplicate_job_id],
        backref=db.backref("duplicate_logs", lazy="dynamic")
    )
    
    def __repr__(self):
        return f"<SessionJobLog {self.id} session={self.session_id} status={self.status}>"
    
    def to_dict(self, include_raw_data: bool = False, include_duplicate: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "id": self.id,
            "session_id": str(self.session_id),
            "platform_name": self.platform_name,
            "job_index": self.job_index,
            "external_job_id": self.external_job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "status": self.status,
            "imported_job_id": self.imported_job_id,
            "skip_reason": self.skip_reason,
            "skip_reason_detail": self.skip_reason_detail,
            "duplicate_job_id": self.duplicate_job_id,
            "error_message": self.error_message,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        if include_raw_data:
            result["raw_job_data"] = self.raw_job_data
        
        if include_duplicate and self.duplicate_job:
            result["duplicate_job"] = {
                "id": self.duplicate_job.id,
                "title": self.duplicate_job.title,
                "company": self.duplicate_job.company,
                "location": self.duplicate_job.location,
                "platform": self.duplicate_job.platform,
                "external_job_id": self.duplicate_job.external_job_id,
                "description": self.duplicate_job.description,
                "posted_date": self.duplicate_job.posted_date.isoformat() if self.duplicate_job.posted_date else None,
                "created_at": self.duplicate_job.created_at.isoformat() if self.duplicate_job.created_at else None,
                "job_url": self.duplicate_job.job_url
            }
        
        return result
    
    @classmethod
    def log_job(
        cls,
        session_id: PyUUID,
        platform_name: str,
        job_index: int,
        raw_job_data: Dict[str, Any],
        platform_status_id: Optional[int] = None
    ) -> "SessionJobLog":
        """Create a pending job log entry."""
        log = cls(
            session_id=session_id,
            platform_name=platform_name,
            platform_status_id=platform_status_id,
            job_index=job_index,
            raw_job_data=raw_job_data,
            external_job_id=raw_job_data.get("jobId") or raw_job_data.get("job_id") or raw_job_data.get("external_job_id"),
            title=raw_job_data.get("title"),
            company=raw_job_data.get("company"),
            location=raw_job_data.get("location"),
            status="pending"
        )
        db.session.add(log)
        return log
    
    def mark_imported(self, job_id: int) -> None:
        """Mark this job as successfully imported."""
        self.status = "imported"
        self.imported_job_id = job_id
        self.processed_at = datetime.utcnow()
    
    def mark_skipped(
        self,
        reason: str,
        detail: str,
        duplicate_job_id: Optional[int] = None
    ) -> None:
        """Mark this job as skipped with reason."""
        self.status = "skipped"
        self.skip_reason = reason
        self.skip_reason_detail = detail
        self.duplicate_job_id = duplicate_job_id
        self.processed_at = datetime.utcnow()
    
    def mark_error(self, error_message: str) -> None:
        """Mark this job as having an error."""
        self.status = "error"
        self.error_message = error_message
        self.processed_at = datetime.utcnow()
    
    @classmethod
    def get_session_summary(cls, session_id: PyUUID) -> Dict[str, Any]:
        """Get summary statistics for a session."""
        logs = cls.query.filter_by(session_id=session_id).all()
        
        summary = {
            "total": len(logs),
            "imported": 0,
            "skipped": 0,
            "error": 0,
            "pending": 0,
            "skip_reasons": {
                "duplicate_platform_id": 0,
                "duplicate_title_company_location": 0,
                "duplicate_title_company_description": 0,
                "missing_required": 0,
                "error": 0
            },
            "by_platform": {}
        }
        
        for log in logs:
            # Count by status
            if log.status == "imported":
                summary["imported"] += 1
            elif log.status == "skipped":
                summary["skipped"] += 1
                if log.skip_reason:
                    if log.skip_reason in summary["skip_reasons"]:
                        summary["skip_reasons"][log.skip_reason] += 1
            elif log.status == "error":
                summary["error"] += 1
            else:
                summary["pending"] += 1
            
            # Count by platform
            if log.platform_name not in summary["by_platform"]:
                summary["by_platform"][log.platform_name] = {
                    "total": 0,
                    "imported": 0,
                    "skipped": 0,
                    "error": 0
                }
            summary["by_platform"][log.platform_name]["total"] += 1
            summary["by_platform"][log.platform_name][log.status] += 1
        
        return summary

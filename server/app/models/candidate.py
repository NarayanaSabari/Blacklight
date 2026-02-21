"""
Candidate Model
Stores candidate information with resume parsing support
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy import Index

from app import db


class BaseModel(db.Model):
    """Base model with common fields"""

    __abstract__ = True

    id = db.Column(Integer, primary_key=True)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Candidate(BaseModel):
    """
    Candidate model with comprehensive resume parsing support.
    Uses single table with JSONB columns for flexible structured data.
    """

    __tablename__ = "candidates"

    # Performance indexes
    __table_args__ = (
        Index('idx_candidates_tenant', 'tenant_id'),
        Index('idx_candidates_tenant_status', 'tenant_id', 'status'),
        Index('idx_candidates_tenant_created', 'tenant_id', db.text('created_at DESC')),
        # IVFFlat ANN index on embedding is created via raw SQL in migration
        # (pgvector indexes require special CREATE INDEX syntax)
    )

    # Tenant relationship (multi-tenant support)
    tenant_id = db.Column(
        Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    # Basic Information
    first_name = db.Column(String(100), nullable=False)
    last_name = db.Column(String(100), nullable=True)  # Nullable for resume parsing
    email = db.Column(String(255), nullable=True)  # Nullable for resume parsing
    phone = db.Column(String(20))

    # Status and Source
    status = db.Column(
        String(50),
        nullable=False,
        default="processing",  # Default for manual upload
    )  # processing, pending_review, new, screening, interviewed, offered, hired, rejected, withdrawn, onboarded, ready_for_assignment
    source = db.Column(
        String(100)
    )  # LinkedIn, Referral, Job Board, resume_upload, invitation, etc.

    # Onboarding Workflow Fields
    onboarding_status = db.Column(
        String(50), nullable=True, default=None
    )  # PENDING_ASSIGNMENT, ASSIGNED, PENDING_ONBOARDING, ONBOARDED, APPROVED, REJECTED
    onboarded_by_user_id = db.Column(
        Integer, db.ForeignKey("portal_users.id"), nullable=True
    )
    onboarded_at = db.Column(DateTime, nullable=True)
    approved_by_user_id = db.Column(
        Integer, db.ForeignKey("portal_users.id"), nullable=True
    )
    approved_at = db.Column(DateTime, nullable=True)
    rejected_by_user_id = db.Column(
        Integer, db.ForeignKey("portal_users.id"), nullable=True
    )
    rejected_at = db.Column(DateTime, nullable=True)
    rejection_reason = db.Column(Text, nullable=True)

    # Denormalized fields for quick access (updated via assignment service)
    manager_id = db.Column(Integer, db.ForeignKey("portal_users.id"), nullable=True)
    recruiter_id = db.Column(Integer, db.ForeignKey("portal_users.id"), nullable=True)

    # Tenant-wide visibility flag (for broadcast assignments)
    # When True, this candidate is visible to ALL managers and recruiters in the tenant
    # including future hires (no explicit CandidateAssignment record needed)
    is_visible_to_all_team = db.Column(db.Boolean, default=False, server_default="false", nullable=False)

    # NOTE: Resume fields moved to CandidateResume model for multi-resume support
    # See candidate_resumes table and use candidate.primary_resume for access

    # Enhanced Personal Information (from resume parsing)
    full_name = db.Column(String(200))  # Parsed full name
    location = db.Column(String(200))  # City, State, Country
    linkedin_url = db.Column(String(500))
    portfolio_url = db.Column(String(500))

    # Professional Details
    current_title = db.Column(String(200))
    total_experience_years = db.Column(Integer)
    notice_period = db.Column(String(100))
    expected_salary = db.Column(String(100))
    professional_summary = db.Column(Text)
    
    # Visa/Work Authorization
    visa_type = db.Column(String(50))  # US Citizen, Green Card, H1B, H4 EAD, L1, L2 EAD, OPT, CPT, TN, O1, E2, Other

    # Structured Arrays (PostgreSQL ARRAY columns)
    preferred_locations = db.Column(ARRAY(String))  # ["San Francisco", "Remote"]
    skills = db.Column(ARRAY(String))  # ["Python", "React", "Node.js"]
    certifications = db.Column(ARRAY(String))  # ["AWS Certified", "Scrum Master"]
    languages = db.Column(ARRAY(String))  # ["English", "Spanish", "French"]

    # Role Preferences (NEW)
    preferred_roles = db.Column(ARRAY(String(100)))  # Manually entered preferred roles
    # Example: ["Software Engineer", "Tech Lead", "Solutions Architect"]

    # Structured Data (PostgreSQL JSONB columns)
    education = db.Column(JSONB)  # Array of education objects
    # Example: [
    #   {
    #     "degree": "B.S. Computer Science",
    #     "field_of_study": "Computer Science",
    #     "institution": "MIT",
    #     "graduation_year": 2018,
    #     "gpa": 3.8
    #   }
    # ]

    work_experience = db.Column(JSONB)  # Array of work experience objects
    # Example: [
    #   {
    #     "title": "Senior Software Engineer",
    #     "company": "Google",
    #     "location": "San Francisco, CA",
    #     "start_date": "2020-01",
    #     "end_date": "Present",
    #     "description": "Led team of 5 engineers...",
    #     "is_current": true,
    #     "duration_months": 60
    #   }
    # ]

    # NOTE: parsed_resume_data and polished_resume_data moved to CandidateResume model
    # Each resume now has its own parsed and polished data

    # AI-Suggested Roles (NEW)
    suggested_roles = db.Column(JSONB)  # AI-generated role suggestions
    # Example: {
    #   "roles": [
    #     {"role": "Senior Software Engineer", "score": 0.95, "reasoning": "Strong Python/React skills"},
    #     {"role": "Tech Lead", "score": 0.88, "reasoning": "Leadership experience"}
    #   ],
    #   "generated_at": "2025-11-26T12:00:00Z",
    #   "model_version": "gemini-1.5-flash"
    # }

    # AI Matching Data
    embedding = db.Column(Vector(768))  # Google Gemini embeddings for semantic matching

    # Relationships
    tenant = db.relationship("Tenant", back_populates="candidates")
    
    # Global roles (for role-based scrape queue)
    global_roles = db.relationship(
        "CandidateGlobalRole",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    
    # Multiple resumes support
    resumes = db.relationship(
        "CandidateResume",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="desc(CandidateResume.is_primary), desc(CandidateResume.created_at)",
    )

    # Onboarding relationships
    assignments = db.relationship(
        "CandidateAssignment",
        backref="candidate",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    onboarded_by = db.relationship(
        "PortalUser",
        foreign_keys=[onboarded_by_user_id],
        backref="candidates_onboarded",
    )
    approved_by = db.relationship(
        "PortalUser", foreign_keys=[approved_by_user_id], backref="candidates_approved"
    )
    rejected_by = db.relationship(
        "PortalUser", foreign_keys=[rejected_by_user_id], backref="candidates_rejected"
    )
    manager = db.relationship(
        "PortalUser", foreign_keys=[manager_id], backref="managed_candidates"
    )
    recruiter = db.relationship(
        "PortalUser", foreign_keys=[recruiter_id], backref="recruited_candidates"
    )

    def __repr__(self):
        return f"<Candidate {self.first_name} {self.last_name}>"

    def to_dict(self, include_assignments=False, include_onboarding_users=False, include_resumes=False):
        """
        Convert candidate to dictionary

        Args:
            include_assignments: Include assignment history
            include_onboarding_users: Include onboarded_by, approved_by, rejected_by user details
            include_resumes: Include resume list with basic info
        """
        # Get primary resume for backward compatibility
        primary = self.primary_resume
        
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "status": self.status,
            "source": self.source,
            # Resume fields from primary resume (for backward compatibility)
            "resume_file_key": primary.file_key if primary else None,
            "resume_storage_backend": primary.storage_backend if primary else None,
            "resume_uploaded_at": primary.uploaded_at.isoformat() if primary and primary.uploaded_at else None,
            "resume_parsed_at": primary.processed_at.isoformat() if primary and primary.processed_at else None,
            "has_primary_resume": primary is not None,
            "resume_count": len(list(self.resumes)) if self.resumes else 0,  # type: ignore[arg-type]
            "full_name": self.full_name,
            "location": self.location,
            "linkedin_url": self.linkedin_url,
            "portfolio_url": self.portfolio_url,
            "current_title": self.current_title,
            "total_experience_years": self.total_experience_years,
            "notice_period": self.notice_period,
            "expected_salary": self.expected_salary,
            "visa_type": self.visa_type,
            "professional_summary": self.professional_summary,
            "preferred_locations": self.preferred_locations,
            "skills": self.skills,
            "certifications": self.certifications,
            "languages": self.languages,
            "education": self.education,
            "work_experience": self.work_experience,
            # Resume data from primary resume (for backward compatibility)
            "parsed_resume_data": primary.parsed_resume_data if primary else None,
            "polished_resume_data": primary.polished_resume_data if primary else None,
            # Role preferences
            "preferred_roles": self.preferred_roles if self.preferred_roles else [],
            "suggested_roles": self.suggested_roles,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Onboarding fields
            "onboarding_status": self.onboarding_status,
            "onboarded_by_user_id": self.onboarded_by_user_id,
            "onboarded_at": self.onboarded_at.isoformat()
            if self.onboarded_at
            else None,
            "approved_by_user_id": self.approved_by_user_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_by_user_id": self.rejected_by_user_id,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "rejection_reason": self.rejection_reason,
            "manager_id": self.manager_id,
            "recruiter_id": self.recruiter_id,
            "is_visible_to_all_team": self.is_visible_to_all_team,
        }

        # Include assignment history if requested
        if include_assignments:
            result["assignments"] = [
                {
                    "id": assignment.id,
                    "assigned_to_user_id": assignment.assigned_to_user_id,
                    "assigned_by_user_id": assignment.assigned_by_user_id,
                    "assignment_type": assignment.assignment_type,
                    "assigned_at": assignment.assigned_at.isoformat()
                    if assignment.assigned_at
                    else None,
                    "status": assignment.status,
                }
                for assignment in self.assignments  # type: ignore[union-attr]
            ]

        # Include onboarding user details if requested
        if include_onboarding_users:
            if self.onboarded_by:
                result["onboarded_by"] = {
                    "id": self.onboarded_by.id,
                    "email": self.onboarded_by.email,
                    "first_name": self.onboarded_by.first_name,
                    "last_name": self.onboarded_by.last_name,
                }
            if self.approved_by:
                result["approved_by"] = {
                    "id": self.approved_by.id,
                    "email": self.approved_by.email,
                    "first_name": self.approved_by.first_name,
                    "last_name": self.approved_by.last_name,
                }
            if self.rejected_by:
                result["rejected_by"] = {
                    "id": self.rejected_by.id,
                    "email": self.rejected_by.email,
                    "first_name": self.rejected_by.first_name,
                    "last_name": self.rejected_by.last_name,
                }
            if self.manager:
                result["manager"] = {
                    "id": self.manager.id,
                    "email": self.manager.email,
                    "first_name": self.manager.first_name,
                    "last_name": self.manager.last_name,
                }
            if self.recruiter:
                result["recruiter"] = {
                    "id": self.recruiter.id,
                    "email": self.recruiter.email,
                    "first_name": self.recruiter.first_name,
                    "last_name": self.recruiter.last_name,
                }
        
        # Include resumes list if requested
        if include_resumes and self.resumes:
            result["resumes"] = [
                resume.to_dict(include_parsed_data=False, include_polished_data=False)
                for resume in self.resumes  # type: ignore[union-attr]
            ]

        return result

    # Helper property to get the primary resume
    @property
    def primary_resume(self):
        """Get the primary resume for this candidate."""
        # Access the relationship as a list (SQLAlchemy lazy loads it)
        resumes_list = list(self.resumes) if self.resumes else []  # type: ignore[arg-type]
        if not resumes_list:
            return None
        for resume in resumes_list:
            if resume.is_primary:
                return resume
        # If no primary is set, return the most recent one
        return resumes_list[0] if resumes_list else None

    # Helper methods for polished resume data (from primary resume)
    @property
    def polished_resume_markdown(self) -> str:
        """Get the polished resume markdown content from primary resume."""
        primary = self.primary_resume
        if primary and primary.polished_resume_data:
            return primary.polished_resume_data.get("markdown_content", "")
        return ""

    @property
    def has_polished_resume(self) -> bool:
        """Check if candidate has a polished resume (on primary)."""
        primary = self.primary_resume
        return bool(
            primary
            and primary.polished_resume_data
            and primary.polished_resume_data.get("markdown_content")
        )
    
    @property
    def parsed_resume_data(self):
        """Get parsed resume data from primary resume (for backward compatibility)."""
        primary = self.primary_resume
        return primary.parsed_resume_data if primary else None
    
    @property
    def polished_resume_data(self):
        """Get polished resume data from primary resume (for backward compatibility)."""
        primary = self.primary_resume
        return primary.polished_resume_data if primary else None
    
    # Resume file properties (for Pydantic schema compatibility)
    @property
    def resume_file_key(self):
        """Get resume file key from primary resume (for backward compatibility)."""
        primary = self.primary_resume
        return primary.file_key if primary else None
    
    @property
    def resume_storage_backend(self):
        """Get resume storage backend from primary resume (for backward compatibility)."""
        primary = self.primary_resume
        return primary.storage_backend if primary else None
    
    @property
    def resume_uploaded_at(self):
        """Get resume uploaded timestamp from primary resume (for backward compatibility)."""
        primary = self.primary_resume
        return primary.uploaded_at if primary else None
    
    @property
    def resume_parsed_at(self):
        """Get resume parsed timestamp from primary resume (for backward compatibility)."""
        primary = self.primary_resume
        return primary.processed_at if primary else None


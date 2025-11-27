"""
Candidate Model
Stores candidate information with resume parsing support
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

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

    # Resume File Storage
    # GCS file key for the resume (preferred storage key in GCS)
    resume_file_key = db.Column(String(1000))
    # Which storage backend the resume uses (e.g., 'local' or 'gcs')
    resume_storage_backend = db.Column(String(20), default="gcs")
    # Legacy/local fields retained for backward compatibility (may be deprecated later)
    resume_file_path = db.Column(String(500))
    resume_file_url = db.Column(String(500))
    resume_uploaded_at = db.Column(DateTime)
    resume_parsed_at = db.Column(DateTime)

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

    # Full parsed resume data (raw output from parser)
    parsed_resume_data = db.Column(JSONB)

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
    tenant = db.relationship("Tenant", backref="candidates")

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

    def to_dict(self, include_assignments=False, include_onboarding_users=False):
        """
        Convert candidate to dictionary

        Args:
            include_assignments: Include assignment history
            include_onboarding_users: Include onboarded_by, approved_by, rejected_by user details
        """
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "status": self.status,
            "source": self.source,
            "resume_file_key": self.resume_file_key,
            "resume_storage_backend": self.resume_storage_backend,
            "resume_file_path": self.resume_file_path,
            "resume_file_url": self.resume_file_url,
            "resume_uploaded_at": self.resume_uploaded_at.isoformat()
            if self.resume_uploaded_at
            else None,
            "resume_parsed_at": self.resume_parsed_at.isoformat()
            if self.resume_parsed_at
            else None,
            "full_name": self.full_name,
            "location": self.location,
            "linkedin_url": self.linkedin_url,
            "portfolio_url": self.portfolio_url,
            "current_title": self.current_title,
            "total_experience_years": self.total_experience_years,
            "notice_period": self.notice_period,
            "expected_salary": self.expected_salary,
            "professional_summary": self.professional_summary,
            "preferred_locations": self.preferred_locations,
            "skills": self.skills,
            "certifications": self.certifications,
            "languages": self.languages,
            "education": self.education,
            "work_experience": self.work_experience,
            "parsed_resume_data": self.parsed_resume_data,
            # Role preferences (NEW)
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
                for assignment in self.assignments
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

        return result

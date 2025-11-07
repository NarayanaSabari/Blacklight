"""
Candidate Model
Stores candidate information with resume parsing support
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from app import db


class BaseModel(db.Model):
    """Base model with common fields"""
    __abstract__ = True
    
    id = db.Column(Integer, primary_key=True)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Candidate(BaseModel):
    """
    Candidate model with comprehensive resume parsing support.
    Uses single table with JSONB columns for flexible structured data.
    """
    __tablename__ = 'candidates'
    
    # Tenant relationship (multi-tenant support)
    tenant_id = db.Column(Integer, db.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Basic Information
    first_name = db.Column(String(100), nullable=False)
    last_name = db.Column(String(100), nullable=True)  # Nullable for resume parsing
    email = db.Column(String(255), nullable=True)  # Nullable for resume parsing
    phone = db.Column(String(20))
    
    # Status and Source
    status = db.Column(
        String(50), 
        nullable=False, 
        default='NEW'
    )  # NEW, SCREENING, INTERVIEWING, OFFERED, HIRED, REJECTED, WITHDRAWN
    source = db.Column(String(100))  # LinkedIn, Referral, Job Board, etc.
    
    # Resume File Storage
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
    
    # Relationships
    tenant = db.relationship('Tenant', backref='candidates')
    
    def __repr__(self):
        return f'<Candidate {self.first_name} {self.last_name}>'
    
    def to_dict(self):
        """Convert candidate to dictionary"""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'status': self.status,
            'source': self.source,
            'resume_file_path': self.resume_file_path,
            'resume_file_url': self.resume_file_url,
            'resume_uploaded_at': self.resume_uploaded_at.isoformat() if self.resume_uploaded_at else None,
            'resume_parsed_at': self.resume_parsed_at.isoformat() if self.resume_parsed_at else None,
            'full_name': self.full_name,
            'location': self.location,
            'linkedin_url': self.linkedin_url,
            'portfolio_url': self.portfolio_url,
            'current_title': self.current_title,
            'total_experience_years': self.total_experience_years,
            'notice_period': self.notice_period,
            'expected_salary': self.expected_salary,
            'professional_summary': self.professional_summary,
            'preferred_locations': self.preferred_locations,
            'skills': self.skills,
            'certifications': self.certifications,
            'languages': self.languages,
            'education': self.education,
            'work_experience': self.work_experience,
            'parsed_resume_data': self.parsed_resume_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

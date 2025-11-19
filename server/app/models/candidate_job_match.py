"""
Candidate Job Match Model
Stores AI-generated job matches for candidates with scoring details
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean, DECIMAL, ARRAY, Index, ForeignKey
from app import db


class CandidateJobMatch(db.Model):
    """
    Stores candidate-job matches with detailed scoring.
    Updated daily by background job.
    """
    __tablename__ = 'candidate_job_matches'
    
    id = db.Column(Integer, primary_key=True)
    
    # Relationships
    candidate_id = db.Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False, index=True)
    job_posting_id = db.Column(Integer, ForeignKey('job_postings.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Match Scoring (0.00 to 100.00)
    match_score = db.Column(DECIMAL(5, 2), nullable=False, index=True)  # Overall score
    skill_match_score = db.Column(DECIMAL(5, 2))  # Skills overlap percentage
    experience_match_score = db.Column(DECIMAL(5, 2))  # Experience level match
    location_match_score = db.Column(DECIMAL(5, 2))  # Location preference match
    salary_match_score = db.Column(DECIMAL(5, 2))  # Salary expectation match
    semantic_similarity = db.Column(DECIMAL(5, 2))  # Cosine similarity from embeddings
    
    # Match Details
    matched_skills = db.Column(ARRAY(String))  # Skills that match
    missing_skills = db.Column(ARRAY(String))  # Required skills candidate lacks
    match_reasons = db.Column(ARRAY(String))  # ["Strong Python skills", "AWS experience"]
    
    # Match Status
    status = db.Column(String(50), default='SUGGESTED', index=True)  # SUGGESTED, VIEWED, APPLIED, REJECTED, SHORTLISTED
    is_recommended = db.Column(Boolean, default=True)
    recommendation_reason = db.Column(Text)
    
    # Candidate Actions
    viewed_at = db.Column(DateTime)
    applied_at = db.Column(DateTime)
    rejected_at = db.Column(DateTime)
    rejection_reason = db.Column(Text)
    notes = db.Column(Text)
    
    # Timestamps
    matched_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    candidate = db.relationship('Candidate', backref='job_matches')
    job_posting = db.relationship('JobPosting', back_populates='matches')
    
    # Indexes
    __table_args__ = (
        Index('idx_candidate_job_match_unique', 'candidate_id', 'job_posting_id', unique=True),
        Index('idx_candidate_job_match_score_desc', 'match_score', postgresql_ops={'match_score': 'DESC'}),
        Index('idx_candidate_job_match_candidate_score', 'candidate_id', 'match_score', postgresql_ops={'match_score': 'DESC'}),
    )
    
    def __repr__(self):
        return f'<CandidateJobMatch candidate={self.candidate_id} job={self.job_posting_id} score={self.match_score}>'
    
    def to_dict(self, include_candidate=False, include_job=False):
        """Convert match to dictionary"""
        result = {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'job_posting_id': self.job_posting_id,
            'match_score': float(self.match_score) if self.match_score else 0.0,
            'skill_match_score': float(self.skill_match_score) if self.skill_match_score else 0.0,
            'experience_match_score': float(self.experience_match_score) if self.experience_match_score else 0.0,
            'location_match_score': float(self.location_match_score) if self.location_match_score else 0.0,
            'salary_match_score': float(self.salary_match_score) if self.salary_match_score else 0.0,
            'semantic_similarity': float(self.semantic_similarity) if self.semantic_similarity else 0.0,
            'matched_skills': self.matched_skills,
            'missing_skills': self.missing_skills,
            'match_reasons': self.match_reasons,
            'status': self.status,
            'is_recommended': self.is_recommended,
            'recommendation_reason': self.recommendation_reason,
            'viewed_at': self.viewed_at.isoformat() if self.viewed_at else None,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'rejection_reason': self.rejection_reason,
            'notes': self.notes,
            'matched_at': self.matched_at.isoformat() if self.matched_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_candidate and self.candidate:
            result['candidate'] = {
                'id': self.candidate.id,
                'first_name': self.candidate.first_name,
                'last_name': self.candidate.last_name,
                'email': self.candidate.email,
                'current_title': self.candidate.current_title,
                'skills': self.candidate.skills,
                'total_experience_years': self.candidate.total_experience_years,
            }
        
        if include_job and self.job_posting:
            result['job'] = self.job_posting.to_dict(include_description=False)
        
        return result
    
    @property
    def match_grade(self):
        """Get letter grade for match score"""
        score = float(self.match_score)
        if score >= 90:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 80:
            return 'B+'
        elif score >= 75:
            return 'B'
        elif score >= 70:
            return 'C+'
        elif score >= 65:
            return 'C'
        else:
            return 'D'

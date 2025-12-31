"""
Candidate Job Match Model
Stores AI-generated job matches for candidates with unified scoring details.

Unified Scoring Weights:
- Skills:     45% - Direct skill matching with synonyms
- Experience: 20% - Years of experience fit
- Semantic:   35% - Embedding cosine similarity

Note: Keyword scoring was removed to speed up job imports.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean, DECIMAL, ARRAY, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app import db


class CandidateJobMatch(db.Model):
    """
    Stores candidate-job matches with unified scoring.
    Updated by background job when jobs are imported.
    Same score is used for job matching and resume tailoring.
    """
    __tablename__ = 'candidate_job_matches'
    
    id = db.Column(Integer, primary_key=True)
    
    # Relationships
    candidate_id = db.Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False, index=True)
    job_posting_id = db.Column(Integer, ForeignKey('job_postings.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # ===========================================
    # Unified Match Scoring (0.00 to 100.00)
    # ===========================================
    match_score = db.Column(DECIMAL(5, 2), nullable=False, index=True)  # Overall weighted score
    
    # Individual component scores (weights: 45%, 20%, 35%)
    skill_match_score = db.Column(DECIMAL(5, 2))      # 45% - Skills overlap
    keyword_match_score = db.Column(DECIMAL(5, 2))    # DEPRECATED - No longer used
    experience_match_score = db.Column(DECIMAL(5, 2)) # 20% - Experience level match
    semantic_similarity = db.Column(DECIMAL(5, 2))    # 35% - Embedding cosine similarity
    
    # Match grade (A+, A, B+, B, C+, C - no D/F)
    match_grade = db.Column(String(5), index=True)
    
    # ===========================================
    # Match Details
    # ===========================================
    matched_skills = db.Column(ARRAY(String))   # Skills that match
    missing_skills = db.Column(ARRAY(String))   # Required skills candidate lacks
    matched_keywords = db.Column(ARRAY(String)) # DEPRECATED - No longer used
    missing_keywords = db.Column(ARRAY(String)) # DEPRECATED - No longer used
    match_reasons = db.Column(ARRAY(String))    # ["Strong Python skills", "AWS experience"]
    
    # ===========================================
    # AI Compatibility (on-demand, cached 24h)
    # ===========================================
    ai_compatibility_score = db.Column(DECIMAL(5, 2), nullable=True)
    ai_compatibility_details = db.Column(JSONB, nullable=True)
    # Structure: {
    #     "strengths": [...],
    #     "gaps": [...],
    #     "recommendations": [...],
    #     "experience_analysis": "...",
    #     "culture_fit_indicators": [...]
    # }
    ai_scored_at = db.Column(DateTime, nullable=True)
    
    # ===========================================
    # Match Status
    # ===========================================
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
            # Unified scores
            'match_score': float(self.match_score) if self.match_score else 0.0,
            'match_grade': self.match_grade,
            'skill_match_score': float(self.skill_match_score) if self.skill_match_score else 0.0,
            'keyword_match_score': float(self.keyword_match_score) if self.keyword_match_score else None,  # DEPRECATED
            'experience_match_score': float(self.experience_match_score) if self.experience_match_score else 0.0,
            'semantic_similarity': float(self.semantic_similarity) if self.semantic_similarity else 0.0,
            # Match details
            'matched_skills': self.matched_skills or [],
            'missing_skills': self.missing_skills or [],
            'matched_keywords': self.matched_keywords or [],  # DEPRECATED
            'missing_keywords': self.missing_keywords or [],  # DEPRECATED
            'match_reasons': self.match_reasons or [],
            # AI compatibility (on-demand)
            'ai_compatibility_score': float(self.ai_compatibility_score) if self.ai_compatibility_score else None,
            'ai_compatibility_details': self.ai_compatibility_details,
            'ai_scored_at': self.ai_scored_at.isoformat() if self.ai_scored_at else None,
            # Status
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
    
    def get_grade_from_score(self, score: float) -> str:
        """
        Calculate letter grade from score.
        Grades: A+ (90+), A (80+), B+ (75+), B (70+), C+ (65+), C (60+)
        No D or F grades - minimum is C.
        """
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 75:
            return 'B+'
        elif score >= 70:
            return 'B'
        elif score >= 65:
            return 'C+'
        else:
            return 'C'

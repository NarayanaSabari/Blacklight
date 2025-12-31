"""
Pydantic schemas for Candidate-Job Match validation and serialization.
Handles AI-generated matching scores and recommendations.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from decimal import Decimal


class CandidateJobMatchBase(BaseModel):
    """Base schema for candidate job match shared fields
    
    Unified Scoring System Weights:
    - Skills: 45%
    - Experience: 20%
    - Semantic: 35%
    
    Note: Keyword scoring was removed to speed up job imports.
    """
    match_score: Decimal = Field(..., ge=0, le=100, description="Overall match score (0-100)")
    match_grade: Optional[str] = Field(None, max_length=5, description="Match grade (A+, A, B+, B, C+, C)")
    # Unified scoring components
    skill_match_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Skill match score (45% weight)")
    keyword_match_score: Optional[Decimal] = Field(None, ge=0, le=100, description="DEPRECATED: No longer used")
    experience_match_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Experience match score (20% weight)")
    semantic_similarity: Optional[Decimal] = Field(None, ge=0, le=100, description="Semantic similarity (35% weight)")
    # Skill matching details
    matched_skills: Optional[List[str]] = Field(default_factory=list, description="Matched skills")
    missing_skills: Optional[List[str]] = Field(default_factory=list, description="Missing skills")
    # Keyword matching details (DEPRECATED - kept for backwards compatibility)
    matched_keywords: Optional[List[str]] = Field(default_factory=list, description="DEPRECATED: No longer used")
    missing_keywords: Optional[List[str]] = Field(default_factory=list, description="DEPRECATED: No longer used")
    # AI compatibility (on-demand, cached 24h)
    ai_compatibility_score: Optional[Decimal] = Field(None, ge=0, le=100, description="AI compatibility score")
    ai_compatibility_details: Optional[dict] = Field(None, description="AI analysis details (strengths, gaps, recommendations)")
    ai_scored_at: Optional[datetime] = Field(None, description="When AI analysis was performed")
    # Legacy/optional fields
    match_reasons: Optional[List[str]] = Field(default_factory=list, description="Reasons for match")
    status: Optional[str] = Field(default="NEW", max_length=50, description="Match status")
    is_recommended: Optional[bool] = Field(default=False, description="Is this a recommended match")
    recommendation_reason: Optional[str] = Field(None, description="Reason for recommendation")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @field_validator('matched_skills', 'missing_skills', 'matched_keywords', 'missing_keywords', 'match_reasons', mode='before')
    @classmethod
    def ensure_list(cls, v):
        """Ensure array fields are lists"""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class CandidateJobMatchCreate(CandidateJobMatchBase):
    """Schema for creating a new candidate-job match"""
    candidate_id: int = Field(..., gt=0, description="Candidate ID")
    job_posting_id: int = Field(..., gt=0, description="Job posting ID")


class CandidateJobMatchUpdate(BaseModel):
    """Schema for updating an existing match"""
    status: Optional[str] = Field(None, max_length=50, description="Match status")
    is_recommended: Optional[bool] = Field(None, description="Is recommended")
    recommendation_reason: Optional[str] = Field(None, description="Recommendation reason")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    model_config = ConfigDict(extra='forbid')


class CandidateJobMatchResponse(CandidateJobMatchBase):
    """Schema for candidate job match response"""
    id: int = Field(..., description="Match ID")
    candidate_id: int = Field(..., description="Candidate ID")
    job_posting_id: int = Field(..., description="Job posting ID")
    viewed_at: Optional[datetime] = Field(None, description="When match was viewed")
    applied_at: Optional[datetime] = Field(None, description="When candidate applied")
    rejected_at: Optional[datetime] = Field(None, description="When match was rejected")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection")
    matched_at: datetime = Field(..., description="When match was generated")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Related data (populated from joins)
    job_title: Optional[str] = Field(None, description="Job title")
    company: Optional[str] = Field(None, description="Company name")
    location: Optional[str] = Field(None, description="Job location")
    candidate_name: Optional[str] = Field(None, description="Candidate name")
    
    model_config = ConfigDict(from_attributes=True)


class CandidateJobMatchWithDetails(CandidateJobMatchResponse):
    """Schema for match response with full job and candidate details"""
    from app.schemas.job_posting_schema import JobPostingResponse
    from app.schemas.candidate_schema import CandidateResponseSchema
    
    job_details: Optional[JobPostingResponse] = Field(None, description="Full job details")
    candidate_details: Optional[CandidateResponseSchema] = Field(None, description="Full candidate details")


class CandidateJobMatchListResponse(BaseModel):
    """Schema for paginated match list"""
    matches: List[CandidateJobMatchResponse] = Field(..., description="List of matches")
    total: int = Field(..., ge=0, description="Total number of matches")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")


class GenerateMatchesRequest(BaseModel):
    """Schema for requesting match generation"""
    candidate_id: Optional[int] = Field(None, gt=0, description="Generate for specific candidate")
    job_posting_id: Optional[int] = Field(None, gt=0, description="Generate for specific job")
    force_regenerate: bool = Field(default=False, description="Force regenerate existing matches")
    top_n: int = Field(default=20, ge=1, le=100, description="Number of top matches to generate")
    min_score: Decimal = Field(default=Decimal("50"), ge=0, le=100, description="Minimum match score threshold")


class MatchScoreBreakdown(BaseModel):
    """Schema for detailed match score breakdown
    
    Unified Scoring System:
    - Skills: 45% weight
    - Experience: 20% weight
    - Semantic: 35% weight
    
    Note: Keyword scoring was removed to speed up job imports.
    
    Grades (no D/F):
    - A+: 90+
    - A: 80-89
    - B+: 75-79
    - B: 70-74
    - C+: 65-69
    - C: <65
    """
    overall_score: Decimal = Field(..., ge=0, le=100, description="Overall match score")
    skill_score: Decimal = Field(..., ge=0, le=100, description="Skill match (45% weight)")
    keyword_score: Optional[Decimal] = Field(None, ge=0, le=100, description="DEPRECATED: No longer used")
    experience_score: Decimal = Field(..., ge=0, le=100, description="Experience match (20% weight)")
    semantic_score: Decimal = Field(..., ge=0, le=100, description="Semantic similarity (35% weight)")
    matched_skills_count: int = Field(..., ge=0, description="Number of matched skills")
    matched_keywords_count: Optional[int] = Field(None, ge=0, description="DEPRECATED: No longer used")
    total_required_skills: int = Field(..., ge=0, description="Total required skills")
    skill_coverage_percent: Decimal = Field(..., ge=0, le=100, description="Skill coverage percentage")
    match_grade: str = Field(..., description="Letter grade (A+ to C)")
    is_strong_match: bool = Field(..., description="Is score >= 80")
    recommendation: str = Field(..., description="Recommendation text")


class CandidateJobMatchStatsResponse(BaseModel):
    """Schema for candidate-job match statistics"""
    total_matches: int = Field(..., ge=0, description="Total number of matches")
    strong_matches: int = Field(..., ge=0, description="Matches with score >= 80")
    good_matches: int = Field(..., ge=0, description="Matches with score >= 60")
    viewed_matches: int = Field(..., ge=0, description="Number of viewed matches")
    applied_matches: int = Field(..., ge=0, description="Number of applied matches")
    rejected_matches: int = Field(..., ge=0, description="Number of rejected matches")
    avg_match_score: Optional[Decimal] = Field(None, description="Average match score")
    top_matched_skills: List[str] = Field(default_factory=list, description="Most frequently matched skills")
    matches_by_grade: dict = Field(..., description="Match counts by grade (A+, A, B+, etc.)")

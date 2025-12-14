"""
Pydantic schemas for Resume Tailor validation and serialization.
Handles tailored resume creation, progress tracking, and response formatting.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from decimal import Decimal
from enum import Enum


class TailoredResumeStatusEnum(str, Enum):
    """Status enum for tailored resume processing"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# Request Schemas
# ============================================================================

class TailorResumeRequest(BaseModel):
    """Schema for initiating a resume tailoring request"""
    candidate_id: int = Field(..., gt=0, description="ID of the candidate whose resume to tailor")
    job_posting_id: int = Field(..., gt=0, description="ID of the job posting to tailor the resume for")
    target_score: Optional[int] = Field(
        default=80,
        ge=50,
        le=100,
        description="Target match score to achieve (50-100)"
    )
    max_iterations: Optional[int] = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum number of improvement iterations (1-5)"
    )
    preserve_accuracy: Optional[bool] = Field(
        default=True,
        description="Ensure no false information is added"
    )
    
    model_config = ConfigDict(extra='forbid')


class TailorResumeFromMatchRequest(BaseModel):
    """Schema for tailoring resume from an existing match record"""
    match_id: int = Field(..., gt=0, description="ID of the candidate-job match record")
    target_score: Optional[int] = Field(
        default=80,
        ge=50,
        le=100,
        description="Target match score to achieve (50-100)"
    )
    max_iterations: Optional[int] = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum number of improvement iterations (1-5)"
    )
    
    model_config = ConfigDict(extra='forbid')


# ============================================================================
# Improvement Detail Schemas
# ============================================================================

class SkillImprovementDetail(BaseModel):
    """Details of a skill-related improvement"""
    skill: str = Field(..., description="The skill that was improved")
    action: str = Field(..., description="Action taken: 'highlighted', 'added_context', 'reworded'")
    before: Optional[str] = Field(None, description="Original text (if applicable)")
    after: str = Field(..., description="Improved text")
    section: str = Field(..., description="Resume section where improvement was made")


class SectionImprovementDetail(BaseModel):
    """Details of a section-level improvement"""
    section: str = Field(..., description="Section name (e.g., 'summary', 'experience', 'skills')")
    improvement_type: str = Field(..., description="Type: 'rewritten', 'reorganized', 'enhanced'")
    description: str = Field(..., description="Description of what was improved")
    keywords_added: Optional[List[str]] = Field(default_factory=list, description="Keywords added from job description")


class ImprovementSummary(BaseModel):
    """Summary of all improvements made to the resume"""
    total_changes: int = Field(..., ge=0, description="Total number of changes made")
    skill_improvements: List[SkillImprovementDetail] = Field(
        default_factory=list,
        description="List of skill-related improvements"
    )
    section_improvements: List[SectionImprovementDetail] = Field(
        default_factory=list,
        description="List of section-level improvements"
    )
    keywords_integrated: List[str] = Field(
        default_factory=list,
        description="Keywords from job description integrated into resume"
    )
    ats_optimizations: Optional[List[str]] = Field(
        default_factory=list,
        description="ATS optimization changes made"
    )


# ============================================================================
# Progress Tracking Schemas (for SSE streaming)
# ============================================================================

class TailorProgressUpdate(BaseModel):
    """Schema for real-time progress updates via SSE"""
    tailor_id: str = Field(..., description="UUID of the tailoring request")
    status: TailoredResumeStatusEnum = Field(..., description="Current status")
    progress_percentage: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    current_step: str = Field(..., description="Current processing step")
    message: str = Field(..., description="Human-readable progress message")
    iteration: Optional[int] = Field(None, description="Current iteration number")
    current_score: Optional[Decimal] = Field(None, description="Current match score")
    target_score: Optional[int] = Field(None, description="Target match score")
    error: Optional[str] = Field(None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of update")


class TailorProgressStep(str, Enum):
    """Enum for tailoring progress steps"""
    INITIALIZING = "initializing"
    EXTRACTING_JOB_KEYWORDS = "extracting_job_keywords"
    ANALYZING_RESUME = "analyzing_resume"
    CALCULATING_INITIAL_SCORE = "calculating_initial_score"
    GENERATING_IMPROVEMENTS = "generating_improvements"
    APPLYING_IMPROVEMENTS = "applying_improvements"
    RECALCULATING_SCORE = "recalculating_score"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# Response Schemas
# ============================================================================

class TailoredResumeResponse(BaseModel):
    """Schema for tailored resume response (summary view)"""
    id: int = Field(..., description="Database ID")
    tailor_id: str = Field(..., description="UUID for external reference")
    candidate_id: int = Field(..., description="Candidate ID")
    job_posting_id: int = Field(..., description="Job posting ID")
    status: TailoredResumeStatusEnum = Field(..., description="Processing status")
    original_match_score: Optional[Decimal] = Field(None, description="Original match score before tailoring")
    tailored_match_score: Optional[Decimal] = Field(None, description="Match score after tailoring")
    score_improvement: Optional[Decimal] = Field(None, description="Score improvement percentage")
    matched_skills: List[str] = Field(default_factory=list, description="Skills matched to job")
    missing_skills: List[str] = Field(default_factory=list, description="Skills still missing")
    added_skills: List[str] = Field(default_factory=list, description="Skills highlighted/added")
    iterations_used: Optional[int] = Field(None, description="Number of improvement iterations used")
    processing_time_seconds: Optional[int] = Field(None, description="Time taken to process")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    # Computed fields
    is_completed: bool = Field(..., description="Whether tailoring is complete")
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('matched_skills', 'missing_skills', 'added_skills', mode='before')
    @classmethod
    def ensure_list(cls, v):
        """Ensure array fields are lists"""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class TailoredResumeDetailResponse(TailoredResumeResponse):
    """Schema for detailed tailored resume response (includes content)"""
    original_resume_markdown: Optional[str] = Field(None, description="Original resume in markdown")
    tailored_resume_markdown: Optional[str] = Field(None, description="Tailored resume in markdown")
    improvements: Optional[ImprovementSummary] = Field(None, description="Detailed improvement summary")
    ai_model: Optional[str] = Field(None, description="AI model used")
    
    # Related data (populated from joins)
    candidate_name: Optional[str] = Field(None, description="Candidate's full name")
    job_title: Optional[str] = Field(None, description="Job title")
    company: Optional[str] = Field(None, description="Company name")


class TailoredResumeListResponse(BaseModel):
    """Schema for paginated list of tailored resumes"""
    items: List[TailoredResumeResponse] = Field(..., description="List of tailored resumes")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


# ============================================================================
# Export Schemas
# ============================================================================

class ExportFormat(str, Enum):
    """Supported export formats"""
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"


class ExportResumeRequest(BaseModel):
    """Schema for exporting tailored resume"""
    tailor_id: str = Field(..., description="UUID of the tailored resume to export")
    format: ExportFormat = Field(default=ExportFormat.PDF, description="Export format")
    include_cover_letter: Optional[bool] = Field(
        default=False,
        description="Include AI-generated cover letter"
    )
    
    model_config = ConfigDict(extra='forbid')


class ExportResumeResponse(BaseModel):
    """Schema for export response"""
    tailor_id: str = Field(..., description="UUID of the tailored resume")
    format: ExportFormat = Field(..., description="Export format")
    download_url: str = Field(..., description="URL to download the exported file")
    filename: str = Field(..., description="Generated filename")
    expires_at: datetime = Field(..., description="URL expiration timestamp")


# ============================================================================
# Analytics Schemas
# ============================================================================

class TailorAnalytics(BaseModel):
    """Schema for resume tailor analytics"""
    total_tailored: int = Field(..., ge=0, description="Total resumes tailored")
    successful_tailored: int = Field(..., ge=0, description="Successfully completed")
    failed_tailored: int = Field(..., ge=0, description="Failed tailoring attempts")
    average_score_improvement: Optional[Decimal] = Field(None, description="Average score improvement")
    average_processing_time: Optional[int] = Field(None, description="Average processing time in seconds")
    most_improved_skills: Optional[List[str]] = Field(default_factory=list, description="Most commonly improved skills")
    common_missing_skills: Optional[List[str]] = Field(default_factory=list, description="Most commonly missing skills")


class CandidateTailorHistory(BaseModel):
    """Schema for a candidate's tailoring history"""
    candidate_id: int = Field(..., description="Candidate ID")
    candidate_name: str = Field(..., description="Candidate name")
    total_tailored: int = Field(..., ge=0, description="Total resumes tailored for this candidate")
    last_tailored_at: Optional[datetime] = Field(None, description="Last tailoring timestamp")
    tailored_resumes: List[TailoredResumeResponse] = Field(
        default_factory=list,
        description="List of tailored resumes"
    )


# ============================================================================
# Comparison Schema
# ============================================================================

class ResumeComparisonResponse(BaseModel):
    """Schema for side-by-side resume comparison"""
    tailor_id: str = Field(..., description="UUID of the tailored resume")
    original: Dict[str, Any] = Field(..., description="Original resume sections")
    tailored: Dict[str, Any] = Field(..., description="Tailored resume sections")
    diff_highlights: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Highlighted differences between versions"
    )
    score_before: Decimal = Field(..., description="Match score before")
    score_after: Decimal = Field(..., description="Match score after")
    improvements_applied: int = Field(..., ge=0, description="Number of improvements applied")

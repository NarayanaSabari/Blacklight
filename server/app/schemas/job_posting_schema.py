"""
Pydantic schemas for Job Posting validation and serialization.
Handles request/response data for job postings with comprehensive validation.
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class JobPostingBase(BaseModel):
    """Base schema for job posting shared fields"""
    external_job_id: str = Field(..., min_length=1, max_length=500, description="External job ID from platform")
    platform: str = Field(..., min_length=1, max_length=100, description="Job platform (indeed, dice, etc.)")
    title: str = Field(..., min_length=1, max_length=500, description="Job title")
    company: str = Field(..., min_length=1, max_length=500, description="Company name")
    location: Optional[str] = Field(None, max_length=500, description="Job location")
    salary_range: Optional[str] = Field(None, max_length=200, description="Salary range string")
    salary_min: Optional[int] = Field(None, ge=0, description="Minimum salary")
    salary_max: Optional[int] = Field(None, ge=0, description="Maximum salary")
    salary_currency: Optional[str] = Field(None, max_length=10, description="Salary currency (USD, EUR, etc.)")
    description: str = Field(..., min_length=1, description="Full job description")
    snippet: Optional[str] = Field(None, description="Job snippet/summary")
    requirements: Optional[str] = Field(None, description="Job requirements")
    posted_date: Optional[date] = Field(None, description="Date job was posted")
    expires_at: Optional[date] = Field(None, description="Job expiration date")
    job_type: Optional[str] = Field(None, max_length=100, description="Job type (full-time, contract, etc.)")
    is_remote: Optional[bool] = Field(None, description="Is remote position")
    experience_required: Optional[str] = Field(None, max_length=200, description="Experience requirement string")
    experience_min: Optional[int] = Field(None, ge=0, description="Minimum years of experience")
    experience_max: Optional[int] = Field(None, ge=0, description="Maximum years of experience")
    skills: Optional[List[str]] = Field(default_factory=list, description="Required skills")
    keywords: Optional[List[str]] = Field(default_factory=list, description="Job keywords")
    job_url: str = Field(..., min_length=1, description="Job listing URL")
    apply_url: Optional[str] = Field(None, description="Direct apply URL")
    status: Optional[str] = Field(default="ACTIVE", max_length=50, description="Job status")
    raw_metadata: Optional[dict] = Field(None, description="Raw metadata from platform")
    
    @field_validator('skills', 'keywords', mode='before')
    @classmethod
    def ensure_list(cls, v):
        """Ensure skills and keywords are lists"""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v
    
    @field_validator('salary_max')
    @classmethod
    def validate_salary_range(cls, v, info):
        """Ensure max salary is greater than min"""
        if v is not None and info.data.get('salary_min') is not None:
            if v < info.data['salary_min']:
                raise ValueError('salary_max must be greater than or equal to salary_min')
        return v
    
    @field_validator('experience_max')
    @classmethod
    def validate_experience_range(cls, v, info):
        """Ensure max experience is greater than min"""
        if v is not None and info.data.get('experience_min') is not None:
            if v < info.data['experience_min']:
                raise ValueError('experience_max must be greater than or equal to experience_min')
        return v


class JobPostingCreate(JobPostingBase):
    """Schema for creating a new job posting (global, no tenant_id needed)"""
    pass


class JobPostingUpdate(BaseModel):
    """Schema for updating an existing job posting"""
    status: Optional[str] = Field(None, max_length=50, description="Job status")
    expires_at: Optional[date] = Field(None, description="Job expiration date")
    salary_range: Optional[str] = Field(None, max_length=200, description="Salary range string")
    salary_min: Optional[int] = Field(None, ge=0, description="Minimum salary")
    salary_max: Optional[int] = Field(None, ge=0, description="Maximum salary")
    skills: Optional[List[str]] = Field(None, description="Required skills")
    keywords: Optional[List[str]] = Field(None, description="Job keywords")
    raw_metadata: Optional[dict] = Field(None, description="Raw metadata from platform")
    
    model_config = ConfigDict(extra='forbid')


class JobPostingResponse(JobPostingBase):
    """Schema for job posting response"""
    id: int = Field(..., description="Job posting ID")
    imported_at: Optional[datetime] = Field(None, description="Import timestamp")
    last_synced_at: Optional[datetime] = Field(None, description="Last sync timestamp")
    import_batch_id: Optional[str] = Field(None, description="Import batch ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Computed fields from model properties
    is_expired: Optional[bool] = Field(None, description="Is job expired")
    days_since_posted: Optional[int] = Field(None, description="Days since posted")
    
    model_config = ConfigDict(from_attributes=True)


class JobPostingListResponse(BaseModel):
    """Schema for paginated job posting list"""
    jobs: List[JobPostingResponse] = Field(..., description="List of job postings")
    total: int = Field(..., ge=0, description="Total number of jobs")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")


class JobPostingSearchRequest(BaseModel):
    """Schema for job search request"""
    query: Optional[str] = Field(None, min_length=1, max_length=500, description="Search query")
    skills: Optional[List[str]] = Field(None, description="Filter by skills")
    location: Optional[str] = Field(None, max_length=500, description="Filter by location")
    is_remote: Optional[bool] = Field(None, description="Filter remote jobs")
    platform: Optional[str] = Field(None, max_length=100, description="Filter by platform")
    job_type: Optional[str] = Field(None, max_length=100, description="Filter by job type")
    salary_min: Optional[int] = Field(None, ge=0, description="Minimum salary filter")
    salary_max: Optional[int] = Field(None, ge=0, description="Maximum salary filter")
    experience_min: Optional[int] = Field(None, ge=0, description="Minimum experience filter")
    experience_max: Optional[int] = Field(None, ge=0, description="Maximum experience filter")
    status: Optional[str] = Field(default="ACTIVE", max_length=50, description="Job status filter")
    posted_after: Optional[date] = Field(None, description="Filter jobs posted after date")
    posted_before: Optional[date] = Field(None, description="Filter jobs posted before date")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default="posted_date", description="Sort field")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")


class JobPostingStatsResponse(BaseModel):
    """Schema for job posting statistics"""
    total_jobs: int = Field(..., ge=0, description="Total number of jobs")
    active_jobs: int = Field(..., ge=0, description="Number of active jobs")
    expired_jobs: int = Field(..., ge=0, description="Number of expired jobs")
    jobs_by_platform: dict = Field(..., description="Job counts by platform")
    jobs_by_location: dict = Field(..., description="Job counts by location")
    remote_jobs_count: int = Field(..., ge=0, description="Number of remote jobs")
    avg_salary: Optional[float] = Field(None, description="Average salary")
    jobs_posted_this_week: int = Field(..., ge=0, description="Jobs posted this week")
    jobs_posted_this_month: int = Field(..., ge=0, description="Jobs posted this month")

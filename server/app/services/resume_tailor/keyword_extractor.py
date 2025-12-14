"""
Keyword Extractor Service

Extracts structured keywords and requirements from job descriptions.
Uses LangChain with Google Gemini for intelligent extraction.
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from config.settings import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Schemas for Structured Output
# ============================================================================

class JobRequirements(BaseModel):
    """Extracted requirements from a job posting"""
    required_skills: List[str] = Field(
        default_factory=list,
        description="Hard requirements - skills that are mandatory"
    )
    preferred_skills: List[str] = Field(
        default_factory=list,
        description="Nice-to-have skills that add value"
    )
    years_experience: Optional[int] = Field(
        None,
        description="Required years of experience"
    )
    education_level: Optional[str] = Field(
        None,
        description="Required education level (Bachelor's, Master's, PhD)"
    )
    certifications: List[str] = Field(
        default_factory=list,
        description="Required or preferred certifications"
    )


class JobKeywords(BaseModel):
    """Keywords extracted from job description for ATS optimization"""
    technical_keywords: List[str] = Field(
        default_factory=list,
        description="Technical terms, tools, frameworks mentioned"
    )
    action_verbs: List[str] = Field(
        default_factory=list,
        description="Action verbs used in responsibilities"
    )
    industry_terms: List[str] = Field(
        default_factory=list,
        description="Industry-specific terminology"
    )
    soft_skills: List[str] = Field(
        default_factory=list,
        description="Soft skills mentioned (leadership, communication, etc.)"
    )


class JobContext(BaseModel):
    """Context about the job role for better tailoring"""
    job_title: str = Field(..., description="The job title")
    company_name: Optional[str] = Field(None, description="Company name if available")
    department_focus: Optional[str] = Field(
        None,
        description="Department or team focus (e.g., 'DevOps', 'Frontend', 'Data')"
    )
    seniority_level: Optional[str] = Field(
        None,
        description="Seniority level (Entry, Mid, Senior, Staff, Principal, Director)"
    )
    key_responsibilities: List[str] = Field(
        default_factory=list,
        description="Top 5 key responsibilities"
    )


class ExtractedJobData(BaseModel):
    """Complete extracted job data"""
    context: JobContext
    requirements: JobRequirements
    keywords: JobKeywords


class KeywordExtractorService:
    """
    Service for extracting keywords and requirements from job descriptions.
    
    Uses LangChain with Gemini for intelligent extraction with structured output.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the keyword extractor with Gemini API.
        
        Args:
            api_key: Google API key. If not provided, reads from settings.
        """
        self.api_key = api_key or settings.google_api_key
        
        if not self.api_key:
            raise ValueError(
                "Google API key is required. Set GOOGLE_API_KEY in environment."
            )
        
        # Initialize LangChain Gemini model
        self.model = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=self.api_key,
            temperature=0.1,  # Low temperature for consistent extraction
            max_output_tokens=4096,
            timeout=60,
            max_retries=2,
        )
        
        logger.info(f"KeywordExtractorService initialized with model: {settings.gemini_model}")
    
    def extract_job_data(
        self,
        job_title: str,
        job_description: str,
        company_name: Optional[str] = None
    ) -> ExtractedJobData:
        """
        Extract all relevant data from a job description.
        
        Args:
            job_title: The job title
            job_description: Full job description text
            company_name: Company name if available
            
        Returns:
            ExtractedJobData with requirements, keywords, and context
        """
        try:
            logger.info(f"Extracting job data for: {job_title}")
            
            # Create structured output model
            structured_llm = self.model.with_structured_output(ExtractedJobData)
            
            prompt = self._build_extraction_prompt(job_title, job_description, company_name)
            
            result: ExtractedJobData = structured_llm.invoke([HumanMessage(content=prompt)])
            
            logger.info(
                f"Extracted {len(result.requirements.required_skills)} required skills, "
                f"{len(result.keywords.technical_keywords)} technical keywords"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract job data: {e}")
            # Return minimal extracted data on failure
            return ExtractedJobData(
                context=JobContext(job_title=job_title, company_name=company_name),
                requirements=JobRequirements(),
                keywords=JobKeywords()
            )
    
    def extract_keywords_only(self, job_description: str) -> JobKeywords:
        """
        Extract only keywords from job description (faster, for quick matching).
        
        Args:
            job_description: Job description text
            
        Returns:
            JobKeywords with extracted keywords
        """
        try:
            structured_llm = self.model.with_structured_output(JobKeywords)
            
            prompt = f"""Extract keywords from this job description for ATS matching.

JOB DESCRIPTION:
{job_description[:4000]}

EXTRACTION RULES:
1. technical_keywords: ALL tools, frameworks, languages, platforms mentioned
2. action_verbs: Strong action verbs used (design, implement, lead, develop, etc.)
3. industry_terms: Domain-specific terminology (agile, CI/CD, microservices, etc.)
4. soft_skills: Communication, leadership, teamwork, problem-solving skills mentioned

Return only keywords that actually appear in the job description."""
            
            result: JobKeywords = structured_llm.invoke([HumanMessage(content=prompt)])
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract keywords: {e}")
            return JobKeywords()
    
    def extract_requirements_only(self, job_description: str) -> JobRequirements:
        """
        Extract only requirements from job description.
        
        Args:
            job_description: Job description text
            
        Returns:
            JobRequirements with extracted requirements
        """
        try:
            structured_llm = self.model.with_structured_output(JobRequirements)
            
            prompt = f"""Extract requirements from this job description.

JOB DESCRIPTION:
{job_description[:4000]}

EXTRACTION RULES:
1. required_skills: Skills explicitly marked as "required" or "must have"
2. preferred_skills: Skills marked as "preferred", "nice to have", or "bonus"
3. years_experience: Number of years required (extract just the number)
4. education_level: Degree requirement if mentioned
5. certifications: Specific certifications mentioned (AWS, PMP, etc.)

Be precise - only include items explicitly stated in the job description."""
            
            result: JobRequirements = structured_llm.invoke([HumanMessage(content=prompt)])
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract requirements: {e}")
            return JobRequirements()
    
    def _build_extraction_prompt(
        self,
        job_title: str,
        job_description: str,
        company_name: Optional[str] = None
    ) -> str:
        """Build the extraction prompt for full job data extraction."""
        company_context = f"Company: {company_name}" if company_name else ""
        
        return f"""Analyze this job posting and extract structured data for resume tailoring.

JOB TITLE: {job_title}
{company_context}

JOB DESCRIPTION:
{job_description[:5000]}

EXTRACT THE FOLLOWING:

1. CONTEXT:
   - job_title: The exact job title
   - company_name: Company name if available
   - department_focus: What area this role focuses on (Frontend, Backend, DevOps, Data, etc.)
   - seniority_level: Entry-level, Mid-level, Senior, Staff, Principal, Director
   - key_responsibilities: Top 5 most important responsibilities

2. REQUIREMENTS:
   - required_skills: Skills explicitly stated as required or mandatory
   - preferred_skills: Nice-to-have skills
   - years_experience: Required years of experience (number only)
   - education_level: Degree requirement (Bachelor's, Master's, etc.)
   - certifications: Specific certifications mentioned

3. KEYWORDS (for ATS optimization):
   - technical_keywords: All technical terms, tools, frameworks, languages
   - action_verbs: Strong verbs from responsibilities (design, implement, lead, etc.)
   - industry_terms: Industry-specific terminology (agile, CI/CD, microservices)
   - soft_skills: Communication, leadership, teamwork skills mentioned

IMPORTANT:
- Only include items actually mentioned in the job description
- Differentiate between required and preferred skills
- Extract exact keywords as they appear (for ATS matching)"""
    
    def compute_keyword_overlap(
        self,
        job_keywords: JobKeywords,
        resume_text: str
    ) -> Dict[str, Any]:
        """
        Compute the overlap between job keywords and resume text.
        
        Args:
            job_keywords: Extracted job keywords
            resume_text: Resume text content
            
        Returns:
            Dictionary with match analysis
        """
        resume_lower = resume_text.lower()
        
        def find_matches(keywords: List[str]) -> tuple:
            found = []
            missing = []
            for kw in keywords:
                if kw.lower() in resume_lower:
                    found.append(kw)
                else:
                    missing.append(kw)
            return found, missing
        
        tech_found, tech_missing = find_matches(job_keywords.technical_keywords)
        action_found, action_missing = find_matches(job_keywords.action_verbs)
        industry_found, industry_missing = find_matches(job_keywords.industry_terms)
        soft_found, soft_missing = find_matches(job_keywords.soft_skills)
        
        total_keywords = (
            len(job_keywords.technical_keywords) +
            len(job_keywords.action_verbs) +
            len(job_keywords.industry_terms) +
            len(job_keywords.soft_skills)
        )
        
        total_found = len(tech_found) + len(action_found) + len(industry_found) + len(soft_found)
        
        match_percentage = (total_found / total_keywords * 100) if total_keywords > 0 else 0
        
        return {
            'match_percentage': round(match_percentage, 1),
            'total_keywords': total_keywords,
            'total_found': total_found,
            'technical': {
                'found': tech_found,
                'missing': tech_missing,
                'match_rate': len(tech_found) / len(job_keywords.technical_keywords) * 100 if job_keywords.technical_keywords else 0
            },
            'action_verbs': {
                'found': action_found,
                'missing': action_missing,
            },
            'industry_terms': {
                'found': industry_found,
                'missing': industry_missing,
            },
            'soft_skills': {
                'found': soft_found,
                'missing': soft_missing,
            }
        }

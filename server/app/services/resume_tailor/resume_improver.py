"""
Resume Improver Service

AI-powered service to improve resume content for better job matching.
Uses LangChain with Google Gemini for intelligent content enhancement.
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import settings
from app.services.resume_tailor.keyword_extractor import ExtractedJobData, JobKeywords

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Schemas for AI Output
# ============================================================================

class SectionImprovement(BaseModel):
    """Improvement for a specific section"""
    section_name: str = Field(..., description="Section: summary, experience, skills, education")
    original_content: str = Field(..., description="Original section content")
    improved_content: str = Field(..., description="Improved section content")
    changes_made: List[str] = Field(default_factory=list, description="List of changes made")
    keywords_added: List[str] = Field(default_factory=list, description="Job keywords integrated")


class ResumeImprovements(BaseModel):
    """Complete set of resume improvements"""
    sections: List[SectionImprovement] = Field(
        default_factory=list,
        description="Improvements by section"
    )
    overall_changes: int = Field(0, description="Total number of changes made")
    keywords_integrated: List[str] = Field(
        default_factory=list,
        description="All keywords integrated across sections"
    )
    ats_optimizations: List[str] = Field(
        default_factory=list,
        description="ATS-specific optimizations made"
    )


class ImprovedResumeMarkdown(BaseModel):
    """Complete improved resume in markdown format"""
    content: str = Field(..., description="Full improved resume in markdown")
    summary_of_changes: List[str] = Field(
        default_factory=list,
        description="Summary of all improvements made"
    )
    preserved_facts: List[str] = Field(
        default_factory=list,
        description="Key facts preserved from original"
    )


class ResumeImproverService:
    """
    Service for improving resume content to better match job descriptions.
    
    Key principles:
    - NEVER add false information
    - Highlight relevant existing experience
    - Integrate job keywords naturally
    - Improve clarity and impact of descriptions
    - Optimize for ATS parsing
    """
    
    # System prompt for resume improvement
    SYSTEM_PROMPT = """You are an expert resume writer and ATS optimization specialist.

Your task is to improve resumes to better match specific job descriptions while following these CRITICAL RULES:

1. NEVER FABRICATE:
   - Do NOT add skills the candidate doesn't have
   - Do NOT invent work experiences or projects
   - Do NOT exaggerate responsibilities or achievements
   - Only work with information present in the original resume

2. PRESERVE CONTACT INFORMATION:
   - ALWAYS keep the candidate's name as the main header (# Name)
   - ALWAYS preserve email, phone, location, and LinkedIn URL exactly as provided
   - The header/contact section must remain at the TOP of the resume
   - Never modify or omit contact details

3. IMPROVEMENT STRATEGIES:
   - Highlight existing relevant skills more prominently
   - Reword experience to use job description keywords (where truthful)
   - Reorder skills to prioritize those matching the job
   - Strengthen action verbs (managed → spearheaded, worked on → engineered)
   - Quantify achievements where possible from context clues
   - Remove irrelevant information to focus on job-relevant content

4. ATS OPTIMIZATION:
   - Use standard section headers (Summary, Experience, Skills, Education)
   - Include exact keywords from job description (where applicable)
   - Avoid graphics, tables, or complex formatting
   - Use common job title variations if applicable

5. FORMAT:
   - Output in clean Markdown format
   - Start with candidate name as H1 header, followed by contact info
   - Use bullet points for experience items
   - Keep formatting simple and parseable

Remember: A tailored resume should be TRUTHFUL but STRATEGICALLY PRESENTED for the target role."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the resume improver with Gemini API.
        
        Args:
            api_key: Google API key. If not provided, reads from settings.
        """
        self.api_key = api_key or settings.google_api_key
        
        if not self.api_key:
            raise ValueError(
                "Google API key is required. Set GOOGLE_API_KEY in environment."
            )
        
        # Initialize LangChain Gemini model with higher output limit for resume content
        self.model = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=self.api_key,
            temperature=0.3,  # Slightly higher for creative improvements
            max_output_tokens=8192,  # Need more tokens for full resume
            timeout=120,  # Longer timeout for complex improvements
            max_retries=2,
        )
        
        logger.info(f"ResumeImproverService initialized with model: {settings.gemini_model}")
    
    def improve_resume(
        self,
        original_resume_markdown: str,
        job_title: str,
        job_description: str,
        job_data: Optional[ExtractedJobData] = None,
        missing_skills: Optional[List[str]] = None,
        target_keywords: Optional[List[str]] = None
    ) -> ImprovedResumeMarkdown:
        """
        Generate an improved version of the resume.
        
        Args:
            original_resume_markdown: Original resume in markdown format
            job_title: Target job title
            job_description: Full job description
            job_data: Pre-extracted job data (optional, will extract if not provided)
            missing_skills: Skills the candidate is missing (for awareness, not adding)
            target_keywords: Specific keywords to try to integrate
            
        Returns:
            ImprovedResumeMarkdown with improved content
        """
        try:
            logger.info(f"Improving resume for job: {job_title}")
            
            # Build the improvement prompt
            prompt = self._build_improvement_prompt(
                original_resume_markdown,
                job_title,
                job_description,
                job_data,
                missing_skills,
                target_keywords
            )
            
            # Use structured output for consistent results
            structured_llm = self.model.with_structured_output(ImprovedResumeMarkdown)
            
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            result: ImprovedResumeMarkdown = structured_llm.invoke(messages)
            
            logger.info(f"Resume improved with {len(result.summary_of_changes)} changes")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to improve resume: {e}")
            raise
    
    def improve_section(
        self,
        section_name: str,
        section_content: str,
        job_title: str,
        job_keywords: JobKeywords,
        context: Optional[str] = None
    ) -> SectionImprovement:
        """
        Improve a specific section of the resume.
        
        Args:
            section_name: Name of the section (summary, experience, skills, education)
            section_content: Original content of the section
            job_title: Target job title
            job_keywords: Extracted keywords from job description
            context: Additional context (e.g., other sections for reference)
            
        Returns:
            SectionImprovement with before/after content
        """
        try:
            logger.info(f"Improving section: {section_name}")
            
            structured_llm = self.model.with_structured_output(SectionImprovement)
            
            prompt = f"""Improve this resume section to better match the target job.

TARGET JOB: {job_title}

SECTION TO IMPROVE: {section_name}
ORIGINAL CONTENT:
{section_content}

JOB KEYWORDS TO INTEGRATE (where truthful):
Technical: {', '.join(job_keywords.technical_keywords[:15])}
Action Verbs: {', '.join(job_keywords.action_verbs[:10])}
Industry Terms: {', '.join(job_keywords.industry_terms[:10])}

{f'ADDITIONAL CONTEXT:{chr(10)}{context}' if context else ''}

IMPROVEMENT RULES:
1. Keep all factual information from the original
2. Integrate job keywords where they fit naturally
3. Strengthen action verbs and impact statements
4. Do NOT add skills or experiences not in the original
5. Focus on relevance to the target job

Return the section_name, original_content, improved_content, list of changes_made, and keywords_added."""
            
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            result: SectionImprovement = structured_llm.invoke(messages)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to improve section {section_name}: {e}")
            # Return unchanged on error
            return SectionImprovement(
                section_name=section_name,
                original_content=section_content,
                improved_content=section_content,
                changes_made=["Error during improvement - content unchanged"],
                keywords_added=[]
            )
    
    def generate_tailored_summary(
        self,
        original_summary: Optional[str],
        resume_highlights: str,
        job_title: str,
        job_description: str,
        candidate_skills: List[str]
    ) -> str:
        """
        Generate a tailored professional summary for the target job.
        
        Args:
            original_summary: Original professional summary (if exists)
            resume_highlights: Key highlights from the full resume
            job_title: Target job title
            job_description: Job description
            candidate_skills: List of candidate's actual skills
            
        Returns:
            Tailored professional summary string
        """
        try:
            prompt = f"""Write a professional summary for this candidate targeting the role of {job_title}.

ORIGINAL SUMMARY (if any):
{original_summary or 'No existing summary'}

CANDIDATE'S ACTUAL SKILLS:
{', '.join(candidate_skills[:20])}

CAREER HIGHLIGHTS:
{resume_highlights[:1500]}

JOB DESCRIPTION EXCERPT:
{job_description[:1500]}

REQUIREMENTS:
1. Write 3-4 sentences maximum
2. Lead with years of experience and primary expertise
3. Highlight 2-3 most relevant skills for this job
4. Include a career achievement if applicable
5. ONLY mention skills the candidate actually has
6. Use active, confident language

Return ONLY the summary text, no additional formatting."""
            
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            response = self.model.invoke(messages)
            
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return original_summary or ""
    
    def reorder_skills_for_job(
        self,
        candidate_skills: List[str],
        job_keywords: JobKeywords
    ) -> List[str]:
        """
        Reorder skills to prioritize those most relevant to the job.
        
        Args:
            candidate_skills: Candidate's original skill list
            job_keywords: Extracted job keywords
            
        Returns:
            Reordered skill list with most relevant first
        """
        job_skills_lower = {s.lower() for s in job_keywords.technical_keywords}
        
        # Categorize skills
        matching = []
        related = []
        other = []
        
        for skill in candidate_skills:
            skill_lower = skill.lower()
            
            if skill_lower in job_skills_lower:
                matching.append(skill)
            elif any(kw in skill_lower or skill_lower in kw for kw in job_skills_lower):
                related.append(skill)
            else:
                other.append(skill)
        
        # Return prioritized list
        return matching + related + other
    
    def strengthen_bullet_points(
        self,
        bullet_points: List[str],
        job_keywords: JobKeywords
    ) -> List[str]:
        """
        Strengthen experience bullet points with better action verbs and keywords.
        
        Args:
            bullet_points: Original bullet points
            job_keywords: Job keywords to integrate
            
        Returns:
            Improved bullet points
        """
        try:
            structured_llm = self.model.with_structured_output(
                self._BulletPointsResult
            )
            
            prompt = f"""Improve these resume bullet points for maximum impact.

ORIGINAL BULLET POINTS:
{chr(10).join(f'- {bp}' for bp in bullet_points)}

ACTION VERBS TO USE (where appropriate):
{', '.join(job_keywords.action_verbs[:10])}

TECHNICAL KEYWORDS TO INTEGRATE (where truthful):
{', '.join(job_keywords.technical_keywords[:15])}

IMPROVEMENT RULES:
1. Start each bullet with a strong action verb
2. Add metrics/numbers where context suggests them
3. Integrate technical keywords naturally
4. Keep the same number of bullet points
5. Preserve all factual information
6. Focus on impact and results

Return the improved bullet points as a list."""
            
            result = structured_llm.invoke([HumanMessage(content=prompt)])
            
            return result.bullets
            
        except Exception as e:
            logger.error(f"Failed to strengthen bullets: {e}")
            return bullet_points
    
    class _BulletPointsResult(BaseModel):
        """Internal schema for bullet point improvement"""
        bullets: List[str] = Field(..., description="Improved bullet points")
    
    def _build_improvement_prompt(
        self,
        original_resume: str,
        job_title: str,
        job_description: str,
        job_data: Optional[ExtractedJobData],
        missing_skills: Optional[List[str]],
        target_keywords: Optional[List[str]]
    ) -> str:
        """Build the comprehensive improvement prompt."""
        
        # Extract key info from job data if available
        required_skills = []
        key_responsibilities = []
        keywords_str = ""
        
        if job_data:
            required_skills = job_data.requirements.required_skills[:10]
            key_responsibilities = job_data.context.key_responsibilities[:5]
            all_keywords = (
                job_data.keywords.technical_keywords[:10] +
                job_data.keywords.action_verbs[:5] +
                job_data.keywords.industry_terms[:5]
            )
            keywords_str = f"\nKEYWORDS TO INTEGRATE:\n{', '.join(all_keywords)}"
        
        if target_keywords:
            keywords_str = f"\nKEYWORDS TO INTEGRATE:\n{', '.join(target_keywords)}"
        
        missing_info = ""
        if missing_skills:
            missing_info = f"""
NOTE - SKILLS THE CANDIDATE IS MISSING (do NOT add these, just be aware):
{', '.join(missing_skills[:10])}
Focus on highlighting existing relevant skills instead."""
        
        return f"""Improve this resume to better match the target job while maintaining complete truthfulness.

TARGET JOB: {job_title}

JOB DESCRIPTION:
{job_description[:3000]}

{'REQUIRED SKILLS: ' + ', '.join(required_skills) if required_skills else ''}
{'KEY RESPONSIBILITIES: ' + chr(10).join(f'- {r}' for r in key_responsibilities) if key_responsibilities else ''}
{keywords_str}
{missing_info}

ORIGINAL RESUME:
{original_resume[:6000]}

IMPROVEMENT INSTRUCTIONS:
1. PRESERVE THE HEADER SECTION EXACTLY - Keep the candidate's name, email, phone, location, and LinkedIn as-is
2. Rewrite the professional summary to target this specific role
3. Reorder skills to prioritize job-relevant skills first
4. Enhance experience bullet points with stronger action verbs
5. Integrate job keywords where they fit naturally and truthfully
6. Quantify achievements where context allows
7. Remove or de-emphasize irrelevant information
8. Ensure ATS-friendly formatting (standard sections, no tables)

CRITICAL: 
- The header with contact information (name, email, phone, location) MUST remain at the top
- Preserve ALL factual information
- Do NOT add skills, experiences, or qualifications not in the original
- Output in clean Markdown format with the header first

Return the complete improved resume in the 'content' field (starting with the candidate's name and contact info), along with a summary_of_changes list and preserved_facts list."""
    
    def convert_to_markdown(self, parsed_resume_data: Dict[str, Any]) -> str:
        """
        Convert parsed resume JSON data to markdown format.
        
        Args:
            parsed_resume_data: Parsed resume data dictionary
            
        Returns:
            Resume formatted as markdown string
        """
        md_parts = []
        
        # Personal Info / Header
        personal = parsed_resume_data.get('personal_info', {})
        if personal:
            name = personal.get('full_name', 'Candidate')
            md_parts.append(f"# {name}\n")
            
            contact_parts = []
            if personal.get('email'):
                contact_parts.append(personal['email'])
            if personal.get('phone'):
                contact_parts.append(personal['phone'])
            if personal.get('location'):
                contact_parts.append(personal['location'])
            if personal.get('linkedin_url'):
                contact_parts.append(personal['linkedin_url'])
            
            if contact_parts:
                md_parts.append(" | ".join(contact_parts) + "\n")
        
        # Professional Summary
        summary = parsed_resume_data.get('professional_summary')
        if summary:
            md_parts.append("\n## Professional Summary\n")
            md_parts.append(f"{summary}\n")
        
        # Skills
        skills = parsed_resume_data.get('skills', [])
        if skills:
            md_parts.append("\n## Skills\n")
            md_parts.append(", ".join(skills) + "\n")
        
        # Work Experience
        experience = parsed_resume_data.get('work_experience', [])
        if experience:
            md_parts.append("\n## Experience\n")
            for exp in experience:
                title = exp.get('title', 'Position')
                company = exp.get('company', 'Company')
                start = exp.get('start_date', '')
                end = exp.get('end_date', 'Present') if not exp.get('is_current') else 'Present'
                location = exp.get('location', '')
                
                md_parts.append(f"\n### {title} | {company}\n")
                if start:
                    md_parts.append(f"*{start} - {end}*")
                if location:
                    md_parts.append(f" | {location}")
                md_parts.append("\n")
                
                desc = exp.get('description', '')
                if desc:
                    # Split description into bullet points if not already
                    if '\n' in desc:
                        for line in desc.split('\n'):
                            line = line.strip()
                            if line and not line.startswith('-') and not line.startswith('•'):
                                md_parts.append(f"- {line}\n")
                            elif line:
                                md_parts.append(f"{line}\n")
                    else:
                        md_parts.append(f"- {desc}\n")
        
        # Education
        education = parsed_resume_data.get('education', [])
        if education:
            md_parts.append("\n## Education\n")
            for edu in education:
                degree = edu.get('degree', 'Degree')
                field = edu.get('field_of_study', '')
                institution = edu.get('institution', 'Institution')
                year = edu.get('graduation_year', '')
                
                if field:
                    md_parts.append(f"### {degree} in {field}\n")
                else:
                    md_parts.append(f"### {degree}\n")
                md_parts.append(f"*{institution}*")
                if year:
                    md_parts.append(f" | {year}")
                md_parts.append("\n")
        
        # Certifications
        certifications = parsed_resume_data.get('certifications', [])
        if certifications:
            md_parts.append("\n## Certifications\n")
            for cert in certifications:
                md_parts.append(f"- {cert}\n")
        
        return "".join(md_parts)

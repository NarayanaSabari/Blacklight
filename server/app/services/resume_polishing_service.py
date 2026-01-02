"""
Resume Polishing Service

AI-powered service to convert raw parsed resume data into well-formatted,
professional markdown that is suitable for display and further processing.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from config.settings import settings

logger = logging.getLogger(__name__)


class PolishedResumeOutput(BaseModel):
    """Structured output for polished resume"""
    markdown_content: str = Field(
        ..., 
        description="Complete resume in well-formatted markdown"
    )
    formatting_notes: list[str] = Field(
        default_factory=list,
        description="Notes about formatting improvements made"
    )


class ResumePolishingService:
    """
    Service for converting raw parsed resume data into polished markdown.
    
    Key features:
    - Consistent section formatting
    - Professional presentation
    - Grammar and spelling corrections
    - ATS-friendly structure
    - Clean markdown output for rendering
    """
    
    SYSTEM_PROMPT = """You are an expert resume formatter and editor. Your task is to take raw parsed resume data and convert it into a beautifully formatted, professional markdown resume.

FORMATTING RULES:

1. STRUCTURE:
   - Start with candidate name as H1 (# Name)
   - Contact info on single line below name (email | phone | location | LinkedIn)
   - Use H2 (##) for main sections: Professional Summary, Skills, Experience, Education, Certifications
   - Use H3 (###) for job titles within Experience section
   - Use bullet points (-) for experience descriptions and skills lists

2. PROFESSIONAL SUMMARY:
   - Write in third person or first person (be consistent)
   - 3-4 sentences maximum
   - Highlight key strengths and experience level
   - If no summary exists, create a brief one from the work experience

3. SKILLS SECTION:
   - Group skills by category if there are many (e.g., Programming Languages, Frameworks, Tools)
   - List as comma-separated values or bullet points
   - Put most relevant/impressive skills first

4. EXPERIENCE SECTION:
   - Format: ### Job Title | Company Name
   - Date range in italics: *Jan 2020 - Present* | Location
   - 3-5 bullet points per role
   - Start bullets with strong action verbs
   - Quantify achievements where possible
   - Fix any grammar or spelling issues

5. EDUCATION SECTION:
   - Format: ### Degree in Field of Study
   - Institution name in italics with graduation year
   - Include GPA only if notable (3.5+)

6. CERTIFICATIONS (if any):
   - Simple bullet list
   - Include year if available

7. QUALITY IMPROVEMENTS:
   - Fix grammar and spelling errors
   - Improve weak action verbs
   - Ensure consistent tense (past for previous roles, present for current)
   - Remove redundant information
   - Ensure dates are formatted consistently (MMM YYYY format preferred)

8. KEEP FACTUAL:
   - Do NOT add information not present in the original data
   - Do NOT exaggerate or fabricate achievements
   - Only reorganize, format, and polish existing content

OUTPUT:
Return ONLY the markdown content. Make it render beautifully in any markdown viewer."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the resume polishing service.
        
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
            temperature=0.2,  # Low temperature for consistent formatting
            max_output_tokens=8192,  # Full resume content
            timeout=120,
            max_retries=2,
        )
        
        logger.info(f"ResumePolishingService initialized with model: {settings.gemini_model}")

    def polish_resume(
        self,
        parsed_data: Dict[str, Any],
        candidate_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert parsed resume data to polished markdown.
        
        Args:
            parsed_data: Raw parsed resume data (JSONB from candidate.parsed_resume_data)
            candidate_name: Optional override for candidate name
            
        Returns:
            Dictionary with polished resume data:
            {
                "markdown_content": "# Name\n...",
                "polished_at": "2026-01-02T10:30:00Z",
                "polished_by": "ai",
                "ai_model": "gemini-2.5-flash",
                "version": 1,
                "last_edited_at": None,
                "last_edited_by_user_id": None
            }
        """
        try:
            logger.info("Polishing resume with AI")
            
            # Build the prompt with parsed data
            prompt = self._build_polish_prompt(parsed_data, candidate_name)
            
            # Use structured output for consistent results
            structured_llm = self.model.with_structured_output(PolishedResumeOutput)
            
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            result: PolishedResumeOutput = structured_llm.invoke(messages)
            
            logger.info(f"Resume polished successfully. Notes: {result.formatting_notes}")
            
            # Build the response structure
            return {
                "markdown_content": result.markdown_content,
                "polished_at": datetime.utcnow().isoformat() + "Z",
                "polished_by": "ai",
                "ai_model": settings.gemini_model,
                "version": 1,
                "last_edited_at": None,
                "last_edited_by_user_id": None,
            }
            
        except Exception as e:
            logger.error(f"Failed to polish resume: {e}")
            raise

    def polish_resume_simple(
        self,
        parsed_data: Dict[str, Any],
        candidate_name: Optional[str] = None
    ) -> str:
        """
        Simple version that returns just the markdown content.
        
        Args:
            parsed_data: Raw parsed resume data
            candidate_name: Optional override for candidate name
            
        Returns:
            Polished markdown string
        """
        result = self.polish_resume(parsed_data, candidate_name)
        return result.get("markdown_content", "")

    def _build_polish_prompt(
        self,
        parsed_data: Dict[str, Any],
        candidate_name: Optional[str] = None
    ) -> str:
        """Build the polishing prompt from parsed data."""
        
        # Extract sections from parsed data
        personal_info = parsed_data.get("personal_info", {})
        
        # Determine name
        name = candidate_name
        if not name:
            name = personal_info.get("full_name") or parsed_data.get("full_name", "")
        if not name:
            first = personal_info.get("first_name", "")
            last = personal_info.get("last_name", "")
            name = f"{first} {last}".strip()
        
        # Contact info
        email = personal_info.get("email") or parsed_data.get("email", "")
        phone = personal_info.get("phone") or parsed_data.get("phone", "")
        location = personal_info.get("location") or parsed_data.get("location", "")
        linkedin = personal_info.get("linkedin_url") or parsed_data.get("linkedin_url", "")
        
        # Professional summary
        summary = parsed_data.get("professional_summary", "")
        
        # Skills
        skills = parsed_data.get("skills", [])
        skills_str = ", ".join(skills) if skills else "Not provided"
        
        # Work experience
        work_exp = parsed_data.get("work_experience", [])
        work_exp_str = self._format_work_experience_for_prompt(work_exp)
        
        # Education
        education = parsed_data.get("education", [])
        education_str = self._format_education_for_prompt(education)
        
        # Certifications
        certifications = parsed_data.get("certifications", [])
        certs_str = ", ".join(certifications) if certifications else "None"
        
        # Current title and experience
        current_title = parsed_data.get("current_title", "")
        years_exp = parsed_data.get("total_experience_years", "")
        
        return f"""Convert this parsed resume data into a polished, professional markdown resume.

CANDIDATE INFORMATION:

Name: {name or 'Unknown'}
Email: {email or 'Not provided'}
Phone: {phone or 'Not provided'}
Location: {location or 'Not provided'}
LinkedIn: {linkedin or 'Not provided'}

Current Title: {current_title or 'Not provided'}
Total Experience: {years_exp} years

PROFESSIONAL SUMMARY:
{summary or 'Not provided - please create a brief one from the work experience'}

SKILLS:
{skills_str}

WORK EXPERIENCE:
{work_exp_str or 'Not provided'}

EDUCATION:
{education_str or 'Not provided'}

CERTIFICATIONS:
{certs_str}

Please format this into a clean, professional markdown resume following all the formatting rules. Fix any grammar issues and ensure consistent formatting throughout."""

    def _format_work_experience_for_prompt(self, work_exp: list) -> str:
        """Format work experience list for the prompt."""
        if not work_exp:
            return "Not provided"
        
        parts = []
        for i, exp in enumerate(work_exp, 1):
            title = exp.get("title") or exp.get("job_title", "Position")
            company = exp.get("company", "Company")
            location = exp.get("location", "")
            start_date = exp.get("start_date", "")
            end_date = exp.get("end_date", "Present")
            is_current = exp.get("is_current", False)
            description = exp.get("description", "")
            
            if is_current:
                end_date = "Present"
            
            exp_str = f"""
Experience {i}:
- Title: {title}
- Company: {company}
- Location: {location}
- Duration: {start_date} to {end_date}
- Description: {description}
"""
            parts.append(exp_str)
        
        return "\n".join(parts)

    def _format_education_for_prompt(self, education: list) -> str:
        """Format education list for the prompt."""
        if not education:
            return "Not provided"
        
        parts = []
        for i, edu in enumerate(education, 1):
            degree = edu.get("degree", "Degree")
            field = edu.get("field_of_study", "")
            institution = edu.get("institution", "Institution")
            year = edu.get("graduation_year", "")
            gpa = edu.get("gpa", "")
            
            edu_str = f"""
Education {i}:
- Degree: {degree}
- Field: {field}
- Institution: {institution}
- Year: {year}
- GPA: {gpa if gpa else 'Not provided'}
"""
            parts.append(edu_str)
        
        return "\n".join(parts)

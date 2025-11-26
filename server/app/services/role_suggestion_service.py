"""
Role Suggestion Service
AI-powered role suggestions for candidates using Gemini
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.models.candidate import Candidate


# Pydantic schema for structured output
class RoleSuggestion(BaseModel):
    """Single role suggestion"""
    role: str = Field(description="Role title")
    score: float = Field(description="Match score from 0-1")
    reasoning: str = Field(description="Brief explanation of why this role fits")


class RoleSuggestionsResponse(BaseModel):
    """Complete role suggestions response"""
    roles: List[RoleSuggestion] = Field(description="Top 5 role suggestions")


class RoleSuggestionService:
    """
    AI-powered role suggestion service.
    Analyzes candidate data to suggest suitable roles.
    """
    
    def __init__(self):
        """Initialize service with Gemini AI"""
        self._configure_ai()
    
    def _configure_ai(self):
        """Configure Gemini AI (same pattern as resume parser)"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment. "
                "Get one from https://ai.google.dev/"
            )
        if api_key == 'your_gemini_api_key_here' or api_key.startswith('your_'):
            raise ValueError(
                "GEMINI_API_KEY is not configured properly. "
                "Please set a valid API key in .env file."
            )
        
        # Get model from environment or use default
        model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        
        # Initialize LangChain ChatGoogleGenerativeAI with timeout and retry config
        self.ai_model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.2,  # Slightly higher for creative suggestions
            max_output_tokens=2048,
            timeout=30,  # 30 second timeout for suggestions
            max_retries=3,  # 3 retries as requested
        )
        print(f"[DEBUG] Configured Gemini for role suggestions: {model_name}")
    
    async def generate_suggestions(self, candidate: Candidate) -> Dict:
        """
        Generate top 5 role suggestions for a candidate.
        
        Args:
            candidate: Candidate model instance
            
        Returns:
            Dictionary with roles, generated_at, model_version
        """
        try:
            print(f"[DEBUG] Generating role suggestions for candidate {candidate.id}")
            
            # Build prompt from candidate data
            prompt = self._build_analysis_prompt(candidate)
            
            # Create structured output model
            structured_llm = self.ai_model.with_structured_output(RoleSuggestionsResponse)
            
            # Generate suggestions
            result: RoleSuggestionsResponse = structured_llm.invoke([HumanMessage(content=prompt)])
            
            print(f"[DEBUG] Generated {len(result.roles)} role suggestions")
            
            # Convert to dict and add metadata
            suggestions = {
                "roles": [
                    {
                        "role": r.role,
                        "score": round(r.score, 2),
                        "reasoning": r.reasoning
                    }
                    for r in result.roles[:5]  # Top 5 only
                ],
                "generated_at": datetime.utcnow().isoformat(),
                "model_version": os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            }
            
            return suggestions
            
        except Exception as e:
            error_message = str(e)
            print(f"[ERROR] Role suggestion generation failed: {error_message}")
            
            # Check if timeout - will auto-retry via max_retries
            if 'timeout' in error_message.lower() or 'deadline' in error_message.lower():
                print(f"[WARNING] Gemini API timed out - retrying...")
            
            raise  # Re-raise for retry logic
    
    def _build_analysis_prompt(self, candidate: Candidate) -> str:
        """Build prompt for AI model"""
        
        # Format work experience
        work_exp_text = "None"
        if candidate.work_experience:
            work_exp_text = "\n".join([
                f"- {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')} ({exp.get('duration_months', 'N/A')} months)"
                for exp in candidate.work_experience[:5]  # Top 5 most recent
            ])
        
        # Format education
        education_text = "None"
        if candidate.education:
            education_text = "\n".join([
                f"- {edu.get('degree', 'N/A')} in {edu.get('field_of_study', 'N/A')} from {edu.get('institution', 'N/A')}"
                for edu in candidate.education
            ])
        
        # Format skills
        skills_text = ", ".join(candidate.skills[:20]) if candidate.skills else "None"
        
        prompt = f"""You are an expert technical recruiter analyzing a candidate's profile to suggest suitable roles.

Candidate Profile:
- Name: {candidate.full_name or f"{candidate.first_name} {candidate.last_name}"}
- Current Title: {candidate.current_title or "Not specified"}
- Total Experience: {candidate.total_experience_years or 0} years
- Location: {candidate.location or "Not specified"}

Skills: {skills_text}

Work History:
{work_exp_text}

Education:
{education_text}

Certifications: {", ".join(candidate.certifications) if candidate.certifications else "None"}

Based on this profile, suggest the top 5 most suitable technical/professional roles for this candidate.
For each role, provide:
1. Role name (specific and relevant)
2. Match score (0.0 to 1.0, where 1.0 is perfect match)
3. Brief reasoning (one sentence explaining why)

IMPORTANT:
- Suggest REALISTIC roles that match the experience level
- Consider career progression potential
- Focus on technical roles if this is a technical candidate
- Be specific (e.g., "Senior Software Engineer" not just "Engineer")
- Ensure score reflects actual fit (be honest, don't inflate scores)
- Order by match score (highest first)
"""
        
        return prompt


# Singleton instance
_service_instance = None

def get_role_suggestion_service() -> RoleSuggestionService:
    """Get or create singleton instance of RoleSuggestionService"""
    global _service_instance
    if _service_instance is None:
        _service_instance = RoleSuggestionService()
    return _service_instance

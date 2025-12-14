"""
Resume Tailor Service Package

AI-powered resume tailoring to match job descriptions.
Uses LangChain with Google Gemini for intelligent improvements.

Sub-modules:
- keyword_extractor: Extract keywords and requirements from job descriptions
- resume_scorer: Calculate match scores between resume and job
- resume_improver: Apply AI improvements to resumes
- orchestrator: Coordinate the tailoring workflow
"""

from app.services.resume_tailor.orchestrator import ResumeTailorOrchestrator
from app.services.resume_tailor.keyword_extractor import KeywordExtractorService
from app.services.resume_tailor.resume_scorer import ResumeScorerService
from app.services.resume_tailor.resume_improver import ResumeImproverService

__all__ = [
    'ResumeTailorOrchestrator',
    'KeywordExtractorService',
    'ResumeScorerService',
    'ResumeImproverService',
]

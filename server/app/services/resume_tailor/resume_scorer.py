"""
Resume Scorer Service

Calculates match scores between resume and job description.
Uses both keyword-based and semantic similarity scoring.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from config.settings import settings
from app.services.embedding_service import EmbeddingService
from app.services.resume_tailor.keyword_extractor import (
    KeywordExtractorService,
    JobKeywords,
    JobRequirements,
    ExtractedJobData
)

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Schemas for Scoring Results
# ============================================================================

class SkillMatch(BaseModel):
    """Individual skill match result"""
    skill: str = Field(..., description="Skill name")
    matched: bool = Field(..., description="Whether skill was found in resume")
    match_type: str = Field(
        ..., 
        description="Type: 'exact', 'synonym', 'partial', 'missing'"
    )
    confidence: float = Field(
        default=1.0, 
        ge=0, 
        le=1, 
        description="Confidence of the match"
    )
    resume_context: Optional[str] = Field(
        None, 
        description="Context where skill was found in resume"
    )


class SectionScore(BaseModel):
    """Score for a specific resume section"""
    section: str = Field(..., description="Section name")
    score: float = Field(..., ge=0, le=100, description="Section score 0-100")
    weight: float = Field(..., ge=0, le=1, description="Weight in total score")
    feedback: str = Field(..., description="Feedback for improvement")


class DetailedMatchScore(BaseModel):
    """Comprehensive match score breakdown"""
    overall_score: float = Field(..., ge=0, le=100, description="Overall match score")
    keyword_score: float = Field(..., ge=0, le=100, description="Keyword match score")
    skills_score: float = Field(..., ge=0, le=100, description="Skills match score")
    experience_score: float = Field(..., ge=0, le=100, description="Experience relevance score")
    semantic_score: float = Field(..., ge=0, le=100, description="Semantic similarity score")
    
    # Skill breakdown
    matched_skills: List[str] = Field(default_factory=list, description="Skills found in resume")
    missing_skills: List[str] = Field(default_factory=list, description="Skills not found")
    partial_matches: List[str] = Field(default_factory=list, description="Partially matched skills")
    
    # Detailed analysis
    skill_matches: List[SkillMatch] = Field(default_factory=list, description="Detailed skill matches")
    section_scores: List[SectionScore] = Field(default_factory=list, description="Per-section scores")
    
    # Improvement suggestions
    improvement_areas: List[str] = Field(
        default_factory=list, 
        description="Areas to improve"
    )
    quick_wins: List[str] = Field(
        default_factory=list, 
        description="Easy improvements to make"
    )


class ResumeScorerService:
    """
    Service for calculating match scores between resume and job description.
    
    Uses a combination of:
    - Keyword matching (exact, synonym, partial)
    - Skills gap analysis
    - Semantic similarity via embeddings
    - AI-powered relevance scoring
    """
    
    # Scoring weights
    WEIGHT_KEYWORDS = 0.25
    WEIGHT_SKILLS = 0.35
    WEIGHT_EXPERIENCE = 0.20
    WEIGHT_SEMANTIC = 0.20
    
    # Skill matching synonyms (commonly interchangeable skills)
    SKILL_SYNONYMS = {
        'javascript': ['js', 'es6', 'ecmascript', 'node.js', 'nodejs'],
        'typescript': ['ts'],
        'python': ['py', 'python3'],
        'react': ['react.js', 'reactjs'],
        'vue': ['vue.js', 'vuejs'],
        'angular': ['angular.js', 'angularjs'],
        'aws': ['amazon web services', 'ec2', 's3', 'lambda'],
        'gcp': ['google cloud', 'google cloud platform'],
        'azure': ['microsoft azure'],
        'docker': ['containerization'],
        'kubernetes': ['k8s'],
        'postgres': ['postgresql', 'pg'],
        'mysql': ['mariadb'],
        'mongodb': ['mongo'],
        'redis': ['in-memory cache'],
        'ci/cd': ['continuous integration', 'continuous deployment', 'jenkins', 'github actions'],
        'agile': ['scrum', 'kanban'],
        'rest': ['restful', 'rest api'],
        'graphql': ['gql'],
        'machine learning': ['ml', 'deep learning', 'ai'],
        'data science': ['data analysis', 'analytics'],
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the resume scorer with required services.
        
        Args:
            api_key: Google API key. If not provided, reads from settings.
        """
        self.api_key = api_key or settings.google_api_key
        
        if not self.api_key:
            raise ValueError(
                "Google API key is required. Set GOOGLE_API_KEY in environment."
            )
        
        # Initialize dependencies
        self.keyword_extractor = KeywordExtractorService(api_key=self.api_key)
        self.embedding_service = EmbeddingService(api_key=self.api_key)
        
        # Initialize LangChain Gemini for advanced scoring
        self.model = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=self.api_key,
            temperature=0.1,
            max_output_tokens=4096,
            timeout=60,
            max_retries=2,
        )
        
        logger.info("ResumeScorerService initialized")
    
    def calculate_match_score(
        self,
        resume_text: str,
        job_title: str,
        job_description: str,
        resume_skills: Optional[List[str]] = None
    ) -> DetailedMatchScore:
        """
        Calculate comprehensive match score between resume and job.
        
        Args:
            resume_text: Full resume text
            job_title: Job title
            job_description: Full job description
            resume_skills: Optional pre-extracted resume skills
            
        Returns:
            DetailedMatchScore with full breakdown
        """
        try:
            logger.info(f"Calculating match score for job: {job_title}")
            
            # Step 1: Extract job data
            job_data = self.keyword_extractor.extract_job_data(
                job_title=job_title,
                job_description=job_description
            )
            
            # Step 2: Calculate individual scores
            keyword_score = self._calculate_keyword_score(
                job_data.keywords, 
                resume_text
            )
            
            skills_result = self._calculate_skills_score(
                job_data.requirements,
                resume_text,
                resume_skills
            )
            
            experience_score = self._calculate_experience_score(
                job_data,
                resume_text
            )
            
            semantic_score = self._calculate_semantic_score(
                resume_text,
                job_description
            )
            
            # Step 3: Calculate weighted overall score
            overall_score = (
                keyword_score * self.WEIGHT_KEYWORDS +
                skills_result['score'] * self.WEIGHT_SKILLS +
                experience_score * self.WEIGHT_EXPERIENCE +
                semantic_score * self.WEIGHT_SEMANTIC
            )
            
            # Step 4: Generate improvement suggestions
            improvement_areas, quick_wins = self._generate_improvement_suggestions(
                skills_result,
                job_data
            )
            
            # Step 5: Build detailed response
            return DetailedMatchScore(
                overall_score=round(overall_score, 1),
                keyword_score=round(keyword_score, 1),
                skills_score=round(skills_result['score'], 1),
                experience_score=round(experience_score, 1),
                semantic_score=round(semantic_score, 1),
                matched_skills=skills_result['matched'],
                missing_skills=skills_result['missing'],
                partial_matches=skills_result['partial'],
                skill_matches=skills_result['detailed_matches'],
                improvement_areas=improvement_areas,
                quick_wins=quick_wins
            )
            
        except Exception as e:
            logger.error(f"Error calculating match score: {e}")
            raise
    
    def quick_score(
        self,
        resume_text: str,
        job_description: str
    ) -> float:
        """
        Quick scoring for initial assessment (faster, less detailed).
        
        Args:
            resume_text: Resume text
            job_description: Job description
            
        Returns:
            Overall match score (0-100)
        """
        try:
            # Just do keyword extraction and basic matching
            keywords = self.keyword_extractor.extract_keywords_only(job_description)
            keyword_overlap = self.keyword_extractor.compute_keyword_overlap(
                keywords, 
                resume_text
            )
            
            keyword_score = keyword_overlap['match_percentage']
            
            # Semantic similarity
            semantic_score = self._calculate_semantic_score(resume_text, job_description)
            
            # Simple weighted average
            overall = keyword_score * 0.6 + semantic_score * 0.4
            
            return round(overall, 1)
            
        except Exception as e:
            logger.error(f"Error in quick score: {e}")
            return 0.0
    
    def _calculate_keyword_score(
        self,
        job_keywords: JobKeywords,
        resume_text: str
    ) -> float:
        """Calculate keyword match score."""
        overlap = self.keyword_extractor.compute_keyword_overlap(job_keywords, resume_text)
        return overlap['match_percentage']
    
    def _calculate_skills_score(
        self,
        requirements: JobRequirements,
        resume_text: str,
        resume_skills: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate skills match score with detailed breakdown.
        
        Returns:
            Dictionary with score, matched, missing, partial, and detailed_matches
        """
        resume_lower = resume_text.lower()
        resume_skills_lower = [s.lower() for s in (resume_skills or [])]
        
        all_required = requirements.required_skills + requirements.preferred_skills
        
        matched = []
        missing = []
        partial = []
        detailed_matches = []
        
        for skill in all_required:
            skill_lower = skill.lower()
            
            # Check for exact match
            if skill_lower in resume_lower or skill_lower in resume_skills_lower:
                matched.append(skill)
                detailed_matches.append(SkillMatch(
                    skill=skill,
                    matched=True,
                    match_type='exact',
                    confidence=1.0
                ))
                continue
            
            # Check for synonym match
            synonym_found = False
            for base_skill, synonyms in self.SKILL_SYNONYMS.items():
                if skill_lower == base_skill or skill_lower in synonyms:
                    # Check if any synonym is in resume
                    all_variants = [base_skill] + synonyms
                    for variant in all_variants:
                        if variant in resume_lower:
                            matched.append(skill)
                            detailed_matches.append(SkillMatch(
                                skill=skill,
                                matched=True,
                                match_type='synonym',
                                confidence=0.9,
                                resume_context=f"Found as: {variant}"
                            ))
                            synonym_found = True
                            break
                    if synonym_found:
                        break
            
            if synonym_found:
                continue
            
            # Check for partial match (skill appears as substring)
            partial_found = False
            for word in skill_lower.split():
                if len(word) > 3 and word in resume_lower:
                    partial.append(skill)
                    detailed_matches.append(SkillMatch(
                        skill=skill,
                        matched=False,
                        match_type='partial',
                        confidence=0.5,
                        resume_context=f"Partial: {word}"
                    ))
                    partial_found = True
                    break
            
            if not partial_found:
                missing.append(skill)
                detailed_matches.append(SkillMatch(
                    skill=skill,
                    matched=False,
                    match_type='missing',
                    confidence=0.0
                ))
        
        # Calculate score
        total = len(all_required)
        if total == 0:
            score = 100.0
        else:
            # Full credit for matched, half credit for partial
            score = ((len(matched) + len(partial) * 0.5) / total) * 100
        
        return {
            'score': score,
            'matched': matched,
            'missing': missing,
            'partial': partial,
            'detailed_matches': detailed_matches
        }
    
    def _calculate_experience_score(
        self,
        job_data: ExtractedJobData,
        resume_text: str
    ) -> float:
        """
        Calculate experience relevance score.
        
        Checks if resume experiences align with job responsibilities.
        """
        try:
            # Use AI for relevance scoring
            structured_llm = self.model.with_structured_output(
                self._ExperienceScoreResult
            )
            
            # Truncate to avoid timeouts
            resume_truncated = resume_text[:4000]
            responsibilities = job_data.context.key_responsibilities[:5]
            
            prompt = f"""Score how well this resume's experience matches the job requirements.

KEY RESPONSIBILITIES:
{chr(10).join(f'- {r}' for r in responsibilities)}

REQUIRED SENIORITY: {job_data.context.seniority_level or 'Not specified'}
REQUIRED EXPERIENCE YEARS: {job_data.requirements.years_experience or 'Not specified'}

RESUME EXCERPT:
{resume_truncated}

SCORING CRITERIA (0-100):
- 90-100: Extensive directly relevant experience
- 70-89: Good relevant experience with some gaps
- 50-69: Some relevant experience but missing key areas
- 30-49: Limited relevant experience
- 0-29: No relevant experience

Evaluate experience depth, relevance to responsibilities, and seniority match."""
            
            result = structured_llm.invoke([HumanMessage(content=prompt)])
            return result.score
            
        except Exception as e:
            logger.warning(f"Experience scoring failed, using fallback: {e}")
            # Fallback: simple keyword check
            return 60.0  # Default moderate score
    
    class _ExperienceScoreResult(BaseModel):
        """Internal schema for experience scoring"""
        score: float = Field(..., ge=0, le=100, description="Experience match score")
        reasoning: str = Field(..., description="Brief reasoning")
    
    def _calculate_semantic_score(
        self,
        resume_text: str,
        job_description: str
    ) -> float:
        """
        Calculate semantic similarity using embeddings.
        """
        try:
            # Generate embeddings
            resume_embedding = self.embedding_service.generate_embedding(
                resume_text[:3000],  # Limit for embedding
                task_type="RETRIEVAL_DOCUMENT"
            )
            job_embedding = self.embedding_service.generate_embedding(
                job_description[:3000],
                task_type="RETRIEVAL_QUERY"
            )
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(resume_embedding, job_embedding)
            
            # Convert to 0-100 scale (similarity is typically 0-1)
            # Normalize: 0.5 similarity = 0 score, 1.0 similarity = 100 score
            normalized_score = max(0, (similarity - 0.5) * 200)
            
            return min(100, normalized_score)
            
        except Exception as e:
            logger.warning(f"Semantic scoring failed: {e}")
            return 50.0  # Default neutral score
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _generate_improvement_suggestions(
        self,
        skills_result: Dict[str, Any],
        job_data: ExtractedJobData
    ) -> Tuple[List[str], List[str]]:
        """
        Generate improvement suggestions based on analysis.
        
        Returns:
            Tuple of (improvement_areas, quick_wins)
        """
        improvement_areas = []
        quick_wins = []
        
        # Missing required skills are top priority
        for skill in skills_result['missing'][:5]:
            if skill in job_data.requirements.required_skills:
                improvement_areas.append(f"Add experience with '{skill}' - required skill")
            else:
                improvement_areas.append(f"Consider adding '{skill}' - preferred skill")
        
        # Partial matches are quick wins
        for skill in skills_result['partial'][:3]:
            quick_wins.append(f"Expand on your experience with '{skill}'")
        
        # Add keyword suggestions
        if job_data.keywords.action_verbs:
            quick_wins.append(
                f"Use action verbs like: {', '.join(job_data.keywords.action_verbs[:3])}"
            )
        
        return improvement_areas, quick_wins

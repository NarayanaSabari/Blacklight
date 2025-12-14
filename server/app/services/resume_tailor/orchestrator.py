"""
Resume Tailor Orchestrator

Coordinates the complete resume tailoring workflow:
1. Extract job keywords and requirements
2. Calculate initial match score
3. Generate improvements iteratively
4. Recalculate score after improvements
5. Store results and track progress
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Generator
from decimal import Decimal

from sqlalchemy import select

from app import db
from app.models.tailored_resume import TailoredResume, TailoredResumeStatus
from app.models.candidate import Candidate
from app.models.job_posting import JobPosting
from app.models.candidate_job_match import CandidateJobMatch
from app.services.resume_tailor.keyword_extractor import KeywordExtractorService, ExtractedJobData
from app.services.resume_tailor.resume_scorer import ResumeScorerService, DetailedMatchScore
from app.services.resume_tailor.resume_improver import ResumeImproverService
from app.services.file_storage import FileStorageService
from app.utils.text_extractor import TextExtractor
from config.settings import settings

logger = logging.getLogger(__name__)


class TailorProgressEvent:
    """Progress event for SSE streaming"""
    
    def __init__(
        self,
        tailor_id: str,
        status: str,
        progress: int,
        step: str,
        message: str,
        iteration: Optional[int] = None,
        current_score: Optional[float] = None,
        target_score: Optional[int] = None,
        error: Optional[str] = None
    ):
        self.tailor_id = tailor_id
        self.status = status
        self.progress = progress
        self.step = step
        self.message = message
        self.iteration = iteration
        self.current_score = current_score
        self.target_score = target_score
        self.error = error
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tailor_id': self.tailor_id,
            'status': self.status,
            'progress_percentage': self.progress,
            'current_step': self.step,
            'message': self.message,
            'iteration': self.iteration,
            'current_score': self.current_score,
            'target_score': self.target_score,
            'error': self.error,
            'timestamp': self.timestamp.isoformat()
        }
    
    def to_sse(self) -> str:
        """Format as SSE event"""
        import json
        return f"data: {json.dumps(self.to_dict())}\n\n"


class ResumeTailorOrchestrator:
    """
    Main orchestrator for the resume tailoring workflow.
    
    Coordinates between extraction, scoring, and improvement services
    to produce optimized resumes with progress tracking.
    """
    
    # Progress step weights (for calculating overall progress)
    STEP_WEIGHTS = {
        'initializing': 5,
        'extracting_job_keywords': 10,
        'analyzing_resume': 15,
        'calculating_initial_score': 20,
        'generating_improvements': 50,  # This is iterative
        'applying_improvements': 70,
        'recalculating_score': 85,
        'finalizing': 95,
        'completed': 100,
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the orchestrator with all required services.
        
        Args:
            api_key: Google API key. If not provided, reads from settings.
        """
        self.api_key = api_key or settings.google_api_key
        
        if not self.api_key:
            raise ValueError(
                "Google API key is required. Set GOOGLE_API_KEY in environment."
            )
        
        # Initialize sub-services
        self.keyword_extractor = KeywordExtractorService(api_key=self.api_key)
        self.scorer = ResumeScorerService(api_key=self.api_key)
        self.improver = ResumeImproverService(api_key=self.api_key)
        self.file_storage = FileStorageService()
        
        logger.info("ResumeTailorOrchestrator initialized")
    
    def tailor_resume(
        self,
        candidate_id: int,
        job_posting_id: int,
        tenant_id: int,
        target_score: int = 80,
        max_iterations: int = 3
    ) -> TailoredResume:
        """
        Execute the full resume tailoring workflow.
        
        Args:
            candidate_id: ID of the candidate
            job_posting_id: ID of the job posting
            tenant_id: Tenant ID for multi-tenancy
            target_score: Target match score to achieve (50-100)
            max_iterations: Maximum improvement iterations (1-5)
            
        Returns:
            TailoredResume model with results
        """
        try:
            # Get candidate and job data first
            candidate = db.session.get(Candidate, candidate_id)
            job_posting = db.session.get(JobPosting, job_posting_id)
            
            if not candidate:
                raise ValueError(f"Candidate {candidate_id} not found")
            if not job_posting:
                raise ValueError(f"Job posting {job_posting_id} not found")
            
            # Extract resume text and markdown
            resume_text = self._get_resume_text(candidate)
            resume_markdown = self._get_resume_markdown(candidate)
            
            # Create initial record with original content
            tailored_resume = TailoredResume(
                candidate_id=candidate_id,
                job_posting_id=job_posting_id,
                tenant_id=tenant_id,
                original_resume_content=resume_markdown,
                job_title=job_posting.title,
                job_company=job_posting.company,
                job_description_snippet=(job_posting.description or "")[:500],
                ai_provider='gemini',
                ai_model=settings.gemini_model,
                options={
                    'target_score': target_score / 100.0,  # Store as decimal
                    'max_iterations': max_iterations
                }
            )
            db.session.add(tailored_resume)
            db.session.commit()
            
            # Start processing
            tailored_resume.start_processing()
            db.session.commit()
            
            # Extract job data
            job_data = self.keyword_extractor.extract_job_data(
                job_title=job_posting.title,
                job_description=job_posting.description or "",
                company_name=job_posting.company
            )
            
            # Store job keywords
            tailored_resume.job_keywords = job_data.keywords.technical_keywords[:20]
            tailored_resume.update_progress('analyzing_resume', 15)
            db.session.commit()
            
            # Calculate initial score (convert to 0-1 scale)
            initial_score = self.scorer.calculate_match_score(
                resume_text=resume_text,
                job_title=job_posting.title,
                job_description=job_posting.description or "",
                resume_skills=candidate.skills
            )
            
            # Update with initial analysis (scores are 0-1 in model)
            initial_score_decimal = initial_score.overall_score / 100.0
            tailored_resume.original_match_score = Decimal(str(round(initial_score_decimal, 4)))
            tailored_resume.original_resume_keywords = initial_score.matched_skills[:20]
            tailored_resume.matched_skills = initial_score.matched_skills
            tailored_resume.missing_skills = initial_score.missing_skills
            tailored_resume.update_progress('calculating_initial_score', 25)
            db.session.commit()
            
            target_score_decimal = target_score / 100.0
            
            # Check if improvement is needed
            if initial_score_decimal >= target_score_decimal:
                logger.info(f"Score {initial_score_decimal:.2%} already meets target {target_score_decimal:.2%}")
                tailored_resume.complete(
                    tailored_content=resume_markdown,
                    tailored_html=None,
                    tailored_score=initial_score_decimal,
                    improvements=[],
                    skill_comparison=self._build_skill_comparison(initial_score),
                    iterations=0
                )
                db.session.commit()
                return tailored_resume
            
            # Iterative improvement - track best version
            current_markdown = resume_markdown
            current_score = initial_score_decimal
            best_markdown = resume_markdown
            best_score = initial_score_decimal
            iterations_used = 0
            all_improvements = []
            
            for iteration in range(1, max_iterations + 1):
                iterations_used = iteration
                progress = 25 + int((iteration / max_iterations) * 50)
                tailored_resume.update_progress(f'iteration_{iteration}', progress)
                db.session.commit()
                
                logger.info(f"Improvement iteration {iteration}/{max_iterations}, current score: {current_score:.2%}")
                
                # Generate improvements
                improved = self.improver.improve_resume(
                    original_resume_markdown=current_markdown,
                    job_title=job_posting.title,
                    job_description=job_posting.description or "",
                    job_data=job_data,
                    missing_skills=initial_score.missing_skills,
                    target_keywords=job_data.keywords.technical_keywords[:15]
                )
                
                candidate_markdown = improved.content
                
                # Build improvement records
                for change in improved.summary_of_changes:
                    all_improvements.append({
                        'section': 'general',
                        'type': 'llm_improvement',
                        'description': change,
                        'iteration': iteration
                    })
                
                # Recalculate score
                new_score = self.scorer.quick_score(
                    resume_text=candidate_markdown,
                    job_description=job_posting.description or ""
                ) / 100.0  # Convert to 0-1
                
                logger.info(f"Score after iteration {iteration}: {new_score:.2%}")
                
                # Only keep this version if it's better than our best
                if new_score > best_score:
                    best_score = new_score
                    best_markdown = candidate_markdown
                    current_markdown = candidate_markdown  # Use this as base for next iteration
                    current_score = new_score
                    logger.info(f"New best score: {best_score:.2%}")
                else:
                    logger.info(f"Score {new_score:.2%} not better than best {best_score:.2%}, keeping previous version")
                
                # Check if target reached
                if best_score >= target_score_decimal:
                    logger.info(f"Target score {target_score_decimal:.2%} reached!")
                    break
            
            # Use the best version we found
            final_markdown = best_markdown
            final_score = best_score
            
            # Identify added skills
            added_skills = self._identify_added_skills(
                original_markdown=resume_markdown,
                improved_markdown=final_markdown,
                job_keywords=job_data.keywords.technical_keywords
            )
            tailored_resume.added_skills = added_skills
            
            # Extract keywords from tailored content
            tailored_resume.tailored_resume_keywords = self._extract_keywords_from_text(
                final_markdown, 
                job_data.keywords.technical_keywords
            )
            
            # Build skill comparison
            skill_comparison = self._build_skill_comparison(initial_score)
            
            # Complete the tailoring
            tailored_resume.complete(
                tailored_content=final_markdown,
                tailored_html=None,  # Could convert markdown to HTML here
                tailored_score=final_score,
                improvements=all_improvements,
                skill_comparison=skill_comparison,
                iterations=iterations_used
            )
            db.session.commit()
            
            logger.info(
                f"Resume tailoring completed. Score: {initial_score_decimal:.2%} -> {final_score:.2%} "
                f"in {iterations_used} iterations, {tailored_resume.processing_duration_seconds}s"
            )
            
            return tailored_resume
            
        except Exception as e:
            logger.error(f"Resume tailoring failed: {e}")
            
            # Update record with failure if it exists
            if 'tailored_resume' in locals() and tailored_resume.id:
                try:
                    tailored_resume.fail(str(e))
                    db.session.commit()
                except Exception as db_error:
                    logger.error(f"Failed to update error status: {db_error}")
            
            raise
    
    def tailor_resume_streaming(
        self,
        candidate_id: int,
        job_posting_id: int,
        tenant_id: int,
        target_score: int = 80,
        max_iterations: int = 3
    ) -> Generator[TailorProgressEvent, None, None]:
        """
        Execute resume tailoring with streaming progress updates.
        
        Yields TailorProgressEvent objects for SSE streaming.
        
        Args:
            candidate_id: ID of the candidate
            job_posting_id: ID of the job posting
            tenant_id: Tenant ID
            target_score: Target match score
            max_iterations: Maximum iterations
            
        Yields:
            TailorProgressEvent objects with progress updates
        """
        tailored_resume = None
        tailor_id = None
        
        def emit(step: str, message: str, progress: int = None, **kwargs):
            prog = progress if progress is not None else self.STEP_WEIGHTS.get(step, 0)
            return TailorProgressEvent(
                tailor_id=tailor_id or 'pending',
                status='processing',
                progress=prog,
                step=step,
                message=message,
                target_score=target_score,
                **kwargs
            )
        
        try:
            # Initialize
            yield emit('initializing', 'Starting resume tailoring process...')
            
            # Get data first
            candidate = db.session.get(Candidate, candidate_id)
            job_posting = db.session.get(JobPosting, job_posting_id)
            
            if not candidate:
                raise ValueError(f"Candidate {candidate_id} not found")
            if not job_posting:
                raise ValueError(f"Job posting {job_posting_id} not found")
            
            yield emit(
                'analyzing_resume', 
                f'Analyzing resume for {candidate.first_name} {candidate.last_name}...'
            )
            
            resume_text = self._get_resume_text(candidate)
            resume_markdown = self._get_resume_markdown(candidate)
            
            # Create record with required fields
            tailored_resume = TailoredResume(
                candidate_id=candidate_id,
                job_posting_id=job_posting_id,
                tenant_id=tenant_id,
                original_resume_content=resume_markdown,
                job_title=job_posting.title,
                job_company=job_posting.company,
                job_description_snippet=(job_posting.description or "")[:500],
                ai_provider='gemini',
                ai_model=settings.gemini_model,
                options={
                    'target_score': target_score / 100.0,
                    'max_iterations': max_iterations
                }
            )
            db.session.add(tailored_resume)
            db.session.commit()
            
            tailor_id = tailored_resume.tailor_id
            tailored_resume.start_processing()
            db.session.commit()
            
            yield emit('extracting_job_keywords', f'Analyzing job requirements for {job_posting.title}...')
            
            # Extract job data
            job_data = self.keyword_extractor.extract_job_data(
                job_title=job_posting.title,
                job_description=job_posting.description or "",
                company_name=job_posting.company
            )
            
            tailored_resume.job_keywords = job_data.keywords.technical_keywords[:20]
            db.session.commit()
            
            yield emit('calculating_initial_score', 'Calculating initial match score...')
            
            initial_score = self.scorer.calculate_match_score(
                resume_text=resume_text,
                job_title=job_posting.title,
                job_description=job_posting.description or "",
                resume_skills=candidate.skills
            )
            
            # Store scores as 0-1 decimals
            initial_score_decimal = initial_score.overall_score / 100.0
            target_score_decimal = target_score / 100.0
            
            tailored_resume.original_match_score = Decimal(str(round(initial_score_decimal, 4)))
            tailored_resume.original_resume_keywords = initial_score.matched_skills[:20]
            tailored_resume.matched_skills = initial_score.matched_skills
            tailored_resume.missing_skills = initial_score.missing_skills
            tailored_resume.update_progress('calculating_initial_score', 25)
            db.session.commit()
            
            yield emit(
                'calculating_initial_score',
                f'Initial match score: {initial_score.overall_score:.1f}%',
                current_score=initial_score.overall_score
            )
            
            # Check if improvement needed
            if initial_score_decimal >= target_score_decimal:
                tailored_resume.complete(
                    tailored_content=resume_markdown,
                    tailored_html=None,
                    tailored_score=initial_score_decimal,
                    improvements=[],
                    skill_comparison=self._build_skill_comparison(initial_score),
                    iterations=0
                )
                db.session.commit()
                
                yield TailorProgressEvent(
                    tailor_id=tailor_id,
                    status='completed',
                    progress=100,
                    step='completed',
                    message=f'Score already meets target! ({initial_score.overall_score:.1f}% >= {target_score}%)',
                    current_score=initial_score.overall_score,
                    target_score=target_score,
                    iteration=0
                )
                return
            
            # Iterative improvement
            current_markdown = resume_markdown
            current_score = initial_score_decimal
            iterations_used = 0
            all_improvements = []
            
            for iteration in range(1, max_iterations + 1):
                iterations_used = iteration
                iteration_progress = 25 + int((iteration / max_iterations) * 50)
                
                tailored_resume.update_progress(f'iteration_{iteration}', iteration_progress)
                db.session.commit()
                
                yield emit(
                    'generating_improvements',
                    f'Improvement iteration {iteration}/{max_iterations}...',
                    progress=iteration_progress,
                    iteration=iteration,
                    current_score=current_score * 100
                )
                
                improved = self.improver.improve_resume(
                    original_resume_markdown=current_markdown,
                    job_title=job_posting.title,
                    job_description=job_posting.description or "",
                    job_data=job_data,
                    missing_skills=initial_score.missing_skills
                )
                
                current_markdown = improved.content
                
                for change in improved.summary_of_changes:
                    all_improvements.append({
                        'section': 'general',
                        'type': 'llm_improvement',
                        'description': change,
                        'iteration': iteration
                    })
                
                yield emit(
                    'recalculating_score',
                    f'Recalculating match score...',
                    progress=iteration_progress + 10,
                    iteration=iteration
                )
                
                new_score = self.scorer.quick_score(
                    resume_text=current_markdown,
                    job_description=job_posting.description or ""
                ) / 100.0
                
                current_score = new_score
                
                yield emit(
                    'applying_improvements',
                    f'Iteration {iteration} complete: Score improved to {new_score * 100:.1f}%',
                    progress=iteration_progress + 15,
                    iteration=iteration,
                    current_score=new_score * 100
                )
                
                if new_score >= target_score_decimal:
                    break
            
            yield emit('finalizing', 'Finalizing tailored resume...', progress=95)
            
            # Identify added skills
            added_skills = self._identify_added_skills(
                original_markdown=resume_markdown,
                improved_markdown=current_markdown,
                job_keywords=job_data.keywords.technical_keywords
            )
            tailored_resume.added_skills = added_skills
            tailored_resume.tailored_resume_keywords = self._extract_keywords_from_text(
                current_markdown,
                job_data.keywords.technical_keywords
            )
            
            # Complete the record
            tailored_resume.complete(
                tailored_content=current_markdown,
                tailored_html=None,
                tailored_score=current_score,
                improvements=all_improvements,
                skill_comparison=self._build_skill_comparison(initial_score),
                iterations=iterations_used
            )
            db.session.commit()
            
            score_improvement = (current_score - initial_score_decimal) * 100
            
            yield TailorProgressEvent(
                tailor_id=tailor_id,
                status='completed',
                progress=100,
                step='completed',
                message=f'Resume tailored successfully! Score: {initial_score.overall_score:.1f}% → {current_score * 100:.1f}% (+{score_improvement:.1f}%)',
                current_score=current_score * 100,
                target_score=target_score,
                iteration=iterations_used
            )
            
        except Exception as e:
            logger.error(f"Streaming tailoring failed: {e}")
            
            yield TailorProgressEvent(
                tailor_id=tailor_id or 'error',
                status='failed',
                progress=0,
                step='failed',
                message='Resume tailoring failed',
                error=str(e)
            )
            
            # Update failure in DB
            if tailored_resume and tailored_resume.id:
                try:
                    tailored_resume.fail(str(e))
                    db.session.commit()
                except Exception:
                    pass
    
    def tailor_from_match(
        self,
        match_id: int,
        tenant_id: int,
        target_score: int = 80,
        max_iterations: int = 3
    ) -> TailoredResume:
        """
        Tailor resume from an existing candidate-job match record.
        
        Args:
            match_id: ID of the CandidateJobMatch record
            tenant_id: Tenant ID
            target_score: Target score
            max_iterations: Max iterations
            
        Returns:
            TailoredResume with results
        """
        match = db.session.get(CandidateJobMatch, match_id)
        
        if not match:
            raise ValueError(f"Match {match_id} not found")
        
        return self.tailor_resume(
            candidate_id=match.candidate_id,
            job_posting_id=match.job_posting_id,
            tenant_id=tenant_id,
            target_score=target_score,
            max_iterations=max_iterations
        )
    
    def get_tailored_resume(self, tailor_id: str) -> Optional[TailoredResume]:
        """Get a tailored resume by its UUID."""
        stmt = select(TailoredResume).where(TailoredResume.tailor_id == tailor_id)
        return db.session.scalar(stmt)
    
    def get_candidate_tailored_resumes(
        self,
        candidate_id: int,
        tenant_id: int
    ) -> List[TailoredResume]:
        """Get all tailored resumes for a candidate."""
        stmt = (
            select(TailoredResume)
            .where(
                TailoredResume.candidate_id == candidate_id,
                TailoredResume.tenant_id == tenant_id
            )
            .order_by(TailoredResume.created_at.desc())
        )
        return list(db.session.scalars(stmt))
    
    def _get_resume_text(self, candidate: Candidate) -> str:
        """Extract resume text from candidate's resume file."""
        # Try to get from file first
        if candidate.resume_file_key:
            try:
                # Download to temp file and extract text
                temp_path, error = self.file_storage.download_to_temp(candidate.resume_file_key)
                if temp_path and not error:
                    result = TextExtractor.extract_from_file(temp_path)
                    text = result.get('text', '')
                    # Clean up temp file
                    import os
                    try:
                        os.unlink(temp_path)
                    except Exception:
                        pass
                    if text:
                        return text
            except Exception as e:
                logger.warning(f"Could not extract from file: {e}")
        
        # Fallback to parsed data
        if candidate.parsed_resume_data:
            return self._parsed_data_to_text(candidate.parsed_resume_data)
        
        # Last resort: build from candidate fields
        parts = []
        if candidate.first_name and candidate.last_name:
            parts.append(f"{candidate.first_name} {candidate.last_name}")
        if candidate.email:
            parts.append(candidate.email)
        if candidate.current_title:
            parts.append(f"Title: {candidate.current_title}")
        if candidate.skills:
            parts.append(f"Skills: {', '.join(candidate.skills)}")
        if candidate.professional_summary:
            parts.append(candidate.professional_summary)
        
        return "\n".join(parts)
    
    def _get_resume_markdown(self, candidate: Candidate) -> str:
        """Get resume as markdown format."""
        if candidate.parsed_resume_data:
            return self.improver.convert_to_markdown(candidate.parsed_resume_data)
        
        # Build basic markdown from candidate data
        md_parts = []
        
        name = f"{candidate.first_name or ''} {candidate.last_name or ''}".strip()
        if name:
            md_parts.append(f"# {name}\n")
        
        contact = []
        if candidate.email:
            contact.append(candidate.email)
        if candidate.phone:
            contact.append(candidate.phone)
        if candidate.location:
            contact.append(candidate.location)
        if contact:
            md_parts.append(" | ".join(contact) + "\n")
        
        if candidate.professional_summary:
            md_parts.append("\n## Professional Summary\n")
            md_parts.append(candidate.professional_summary + "\n")
        
        if candidate.skills:
            md_parts.append("\n## Skills\n")
            md_parts.append(", ".join(candidate.skills) + "\n")
        
        if candidate.work_experience:
            md_parts.append("\n## Experience\n")
            for exp in candidate.work_experience:
                if isinstance(exp, dict):
                    title = exp.get('title', 'Position')
                    company = exp.get('company', 'Company')
                    md_parts.append(f"\n### {title} | {company}\n")
                    if exp.get('description'):
                        md_parts.append(f"{exp['description']}\n")
        
        return "".join(md_parts)
    
    def _parsed_data_to_text(self, parsed_data: Dict[str, Any]) -> str:
        """Convert parsed resume data to plain text."""
        parts = []
        
        personal = parsed_data.get('personal_info', {})
        if personal.get('full_name'):
            parts.append(personal['full_name'])
        if personal.get('email'):
            parts.append(personal['email'])
        
        if parsed_data.get('professional_summary'):
            parts.append(parsed_data['professional_summary'])
        
        if parsed_data.get('skills'):
            parts.append("Skills: " + ", ".join(parsed_data['skills']))
        
        for exp in parsed_data.get('work_experience', []):
            parts.append(f"{exp.get('title', '')} at {exp.get('company', '')}")
            if exp.get('description'):
                parts.append(exp['description'])
        
        for edu in parsed_data.get('education', []):
            parts.append(f"{edu.get('degree', '')} - {edu.get('institution', '')}")
        
        return "\n".join(parts)
    
    def _identify_added_skills(
        self,
        original_markdown: str,
        improved_markdown: str,
        job_keywords: List[str]
    ) -> List[str]:
        """
        Identify skills that were highlighted/emphasized in the improvement.
        
        These are job keywords that appear more prominently in the improved version.
        """
        original_lower = original_markdown.lower()
        improved_lower = improved_markdown.lower()
        
        added = []
        for keyword in job_keywords:
            kw_lower = keyword.lower()
            
            # Count occurrences
            original_count = original_lower.count(kw_lower)
            improved_count = improved_lower.count(kw_lower)
            
            # If keyword appears more in improved version
            if improved_count > original_count:
                added.append(keyword)
        
        return added[:10]  # Limit to top 10
    
    def _build_skill_comparison(self, score_result: DetailedMatchScore) -> List[Dict[str, Any]]:
        """Build skill comparison list for storage."""
        comparison = []
        
        for skill in score_result.matched_skills:
            comparison.append({
                'skill': skill,
                'status': 'matched',
                'resume_mentions': 1,
                'job_mentions': 1
            })
        
        for skill in score_result.missing_skills:
            comparison.append({
                'skill': skill,
                'status': 'missing',
                'resume_mentions': 0,
                'job_mentions': 1
            })
        
        return comparison
    
    def _extract_keywords_from_text(
        self, 
        text: str, 
        reference_keywords: List[str]
    ) -> List[str]:
        """Extract keywords from text that match reference keywords."""
        text_lower = text.lower()
        found = []
        
        for kw in reference_keywords:
            if kw.lower() in text_lower:
                found.append(kw)
        
        return found[:20]  # Limit to 20

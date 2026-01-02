"""
Inngest Resume Parsing Workflow
Handles async resume parsing after upload
"""
import logging
import os
from typing import Dict, Any, Optional

import inngest
from app.inngest import inngest_client

from app import db
from app.models.candidate import Candidate
from app.services.resume_parser import ResumeParserService
from app.services.resume_polishing_service import ResumePolishingService
from app.utils.text_extractor import TextExtractor  # FIXED: correct import path
from app.services.file_storage import FileStorageService

logger = logging.getLogger(__name__)


@inngest_client.create_function(
    fn_id="parse-resume-async",
    trigger=inngest.TriggerEvent(event="candidate/parse-resume"),
    # Disable automatic retries to avoid multiple executions per upload while debugging
    retries=0,
    name="Parse Resume Async"
)
async def parse_resume_workflow(ctx: inngest.Context) -> dict:
    """
    Async workflow to parse resume after upload
    
    Workflow Steps:
    1. Fetch candidate record
    2. Extract text from resume file (STEP - external dependency)
    3. Run AI parsing (STEP - external API, needs retry)
    4. Update candidate with parsed data
    5. Change status to 'pending_review'
    
    Event data:
        - candidate_id: int
        - tenant_id: int
    """
    event_data = ctx.event.data
    candidate_id = event_data.get("candidate_id")
    tenant_id = event_data.get("tenant_id")
    
    logger.info(f"[PARSE-RESUME] Starting async parsing for candidate {candidate_id}")
    
    try:
        # Step 1: Fetch candidate (direct - no step needed, fast DB query)
        candidate = _fetch_candidate(candidate_id, tenant_id)
        
        if not candidate:
            logger.error(f"[PARSE-RESUME] Candidate {candidate_id} not found")
            return {"status": "error", "message": "Candidate not found"}
        
        # Idempotency guard: if candidate is already parsed & in/after pending_review, skip work
        if getattr(candidate, "resume_parsed_at", None) is not None and candidate.status in [
            "pending_review",
            "onboarded",
            "ready_for_assignment",
        ]:
            logger.info(f"[PARSE-RESUME] Candidate {candidate_id} already parsed; skipping re-processing")
            return {
                "status": "success",
                "candidate_id": candidate_id,
                "has_data": bool(getattr(candidate, "parsed_resume_data", None)),
                "skipped": True,
            }
        
        if not candidate.resume_file_key:
            logger.error(f"[PARSE-RESUME] No resume file for candidate {candidate_id}")
            _update_candidate_status(candidate_id, "pending_review", {})
            return {"status": "error", "message": "No resume file"}
        
        # Step 2: Extract text (STEP - file operation, might fail)
        local_path = None
        # If file is remote, download to temp using FileStorageService
        if getattr(candidate, 'resume_file_key', None):
            storage = FileStorageService()
            local_path, err = storage.download_to_temp(candidate.resume_file_key)
            if err:
                logger.error(f"[PARSE-RESUME] Failed to download file for candidate {candidate_id}: {err}")
                _update_candidate_status(candidate_id, "pending_review", {})
                return {"status": "error", "message": "Failed to download resume file"}

            try:
                resume_text = await ctx.step.run(
                    "extract-resume-text",
                    lambda: _extract_resume_text(local_path)
                )
            finally:
                try:
                    import os
                    os.remove(local_path)
                except Exception:
                    pass
        else:
            # NOTE: No local fallback supported in Phase 3 - we only support parsing by file_key.
            resume_text = await ctx.step.run(
                "extract-resume-text",
                lambda: _extract_resume_text(local_path)
            )
        
        if not resume_text:
            logger.error(f"[PARSE-RESUME] Failed to extract text from resume for candidate {candidate_id}")
            # Update to pending_review so HR can manually enter data
            _update_candidate_status(candidate_id, "pending_review", {})
            return {"status": "error", "message": "Could not extract resume text"}
        
        # Step 3: Run AI parsing (STEP - external API, can fail, needs retry)
        parsed_data = await ctx.step.run(
            "ai-parse-resume",
            lambda: _parse_with_ai(resume_text, local_path)
        )
        
        # Step 4: Update candidate with parsed data (direct - simple DB operations)
        if parsed_data:
            _update_candidate_with_parsed_data(candidate_id, parsed_data)
        
        # Step 5: Polish resume - convert parsed data to formatted markdown
        # This runs after parsing so we have data to polish
        polished_data = None
        if parsed_data:
            try:
                # Fetch fresh candidate for name
                fresh_candidate = _fetch_candidate(candidate_id, tenant_id)
                candidate_name = None
                if fresh_candidate:
                    candidate_name = fresh_candidate.full_name or f"{fresh_candidate.first_name} {fresh_candidate.last_name}".strip()
                
                polished_data = await ctx.step.run(
                    "ai-polish-resume",
                    lambda: _polish_resume(parsed_data, candidate_name)
                )
                
                if polished_data:
                    _update_candidate_with_polished_data(candidate_id, polished_data)
                    logger.info(f"[PARSE-RESUME] Successfully polished resume for candidate {candidate_id}")
            except Exception as polish_error:
                # Log but don't fail - polishing is non-critical
                logger.warning(f"[PARSE-RESUME] Resume polishing failed for candidate {candidate_id}: {polish_error}")
        
        # Step 6: Update status to pending_review
        _update_candidate_status(candidate_id, "pending_review", parsed_data)
        
        logger.info(f"[PARSE-RESUME] Successfully parsed resume for candidate {candidate_id}, status: pending_review")
        
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "has_data": bool(parsed_data),
            "has_polished_data": bool(polished_data)
        }
    
    except Exception as e:
        # Catch-all error handler - always update status to pending_review even on failure
        logger.error(f"[PARSE-RESUME] Workflow failed for candidate {candidate_id}: {e}", exc_info=True)
        try:
            _update_candidate_status(candidate_id, "pending_review", {})
            logger.info(f"[PARSE-RESUME] Updated candidate {candidate_id} to pending_review after error")
        except Exception as status_error:
            logger.error(f"[PARSE-RESUME] Failed to update status: {status_error}")
        
        return {
            "status": "error",
            "candidate_id": candidate_id,
            "error": str(e)
        }


# Helper functions (sync)

def _fetch_candidate(candidate_id: int, tenant_id: int) -> Candidate:
    """Fetch candidate from database"""
    from sqlalchemy import select
    stmt = select(Candidate).where(
        Candidate.id == candidate_id,
        Candidate.tenant_id == tenant_id
    )
    return db.session.scalar(stmt)


def _extract_resume_text(file_path: str) -> str:
    """Extract text from resume file"""
    if not file_path:
        return ""
    
    try:
        # TextExtractor.extract_from_file() returns dict with 'text' key
        result = TextExtractor.extract_from_file(file_path)
        text = result.get('text', '')
        logger.info(f"[PARSE-RESUME] Extracted {len(text)} characters from resume")
        return text
    except Exception as e:
        logger.error(f"[PARSE-RESUME] Text extraction failed: {e}")
        return ""


def _parse_with_ai(text: str, filename: str) -> Dict[str, Any]:
    """Run AI parsing on resume text"""
    try:
        parser = ResumeParserService()
        # Determine file type from filename
        file_type = 'pdf' if filename.endswith('.pdf') else 'docx'
        parsed_data = parser.parse_resume(text, file_type)
        logger.info(f"[PARSE-RESUME] AI parsing completed successfully")
        return parsed_data
    except Exception as e:
        logger.error(f"[PARSE-RESUME] AI parsing failed: {e}")
        return {}


def _update_candidate_with_parsed_data(candidate_id: int, parsed_data: Dict[str, Any]) -> Candidate:
    """Update candidate with parsed data"""
    from sqlalchemy import select
    
    stmt = select(Candidate).where(Candidate.id == candidate_id)
    candidate = db.session.scalar(stmt)
    
    if not candidate:
        return None
    
    # Update fields from parsed data
    if parsed_data:
        # Personal info - support both flat and nested structure
        personal = parsed_data.get('personal_info', parsed_data)  # Fall back to parsed_data if no personal_info
        
        if personal.get('full_name'):
            candidate.full_name = personal['full_name']
            # Also update first/last name if needed
            if not candidate.first_name or candidate.first_name == 'Unknown' or candidate.first_name == 'Processing':
                names = personal['full_name'].split()
                if names:
                    candidate.first_name = names[0]
                    candidate.last_name = ' '.join(names[1:]) if len(names) > 1 else ''
        
        if personal.get('email'):
            candidate.email = personal['email']
        if personal.get('phone'):
            candidate.phone = personal['phone']
        if personal.get('location'):
            candidate.location = personal['location']
        if personal.get('linkedin_url'):
            candidate.linkedin_url = personal['linkedin_url']
        if personal.get('portfolio_url'):
            candidate.portfolio_url = personal['portfolio_url']
        
        # Professional info
        if parsed_data.get('professional_summary'):
            candidate.professional_summary = parsed_data['professional_summary']
        if parsed_data.get('current_title'):
            candidate.current_title = parsed_data['current_title']
        if parsed_data.get('total_experience_years'):
            candidate.total_experience_years = parsed_data['total_experience_years']
        if parsed_data.get('notice_period'):
            candidate.notice_period = parsed_data['notice_period']
        if parsed_data.get('expected_salary'):
            candidate.expected_salary = parsed_data['expected_salary']
        
        # Arrays
        if parsed_data.get('skills'):
            candidate.skills = parsed_data['skills']
        if parsed_data.get('certifications'):
            candidate.certifications = parsed_data['certifications']
        if parsed_data.get('languages'):
            candidate.languages = parsed_data.get('languages', [])
        if parsed_data.get('preferred_locations'):
            candidate.preferred_locations = parsed_data['preferred_locations']
        
        # Auto-infer preferred_roles from current_title if not already set
        # This enables role normalization and job matching after approval
        if not candidate.preferred_roles or len(candidate.preferred_roles) == 0:
            inferred_roles = []
            if parsed_data.get('current_title'):
                inferred_roles.append(parsed_data['current_title'])
            # Also extract unique titles from work experience
            if parsed_data.get('work_experience'):
                for exp in parsed_data['work_experience'][:3]:  # Top 3 most recent jobs
                    title = exp.get('title') or exp.get('job_title')
                    if title and title not in inferred_roles:
                        inferred_roles.append(title)
            if inferred_roles:
                candidate.preferred_roles = inferred_roles[:5]  # Max 5 inferred roles
                logger.info(f"[PARSE-RESUME] Auto-inferred preferred_roles: {candidate.preferred_roles}")
        
        # JSONB
        if parsed_data.get('education'):
            candidate.education = parsed_data['education']
        if parsed_data.get('work_experience'):
            candidate.work_experience = parsed_data['work_experience']
        
        # Store full parsed data
        candidate.parsed_resume_data = parsed_data
        candidate.resume_parsed_at = db.func.now()
    
    db.session.commit()
    logger.info(f"[PARSE-RESUME] Updated candidate {candidate_id} with parsed data")
    return candidate


def _update_candidate_status(candidate_id: int, status: str, parsed_data: Dict[str, Any]) -> bool:
    """Update candidate status"""
    from sqlalchemy import select
    
    stmt = select(Candidate).where(Candidate.id == candidate_id)
    candidate = db.session.scalar(stmt)
    
    if not candidate:
        return False
    
    candidate.status = status
    db.session.commit()
    logger.info(f"[PARSE-RESUME] Updated candidate {candidate_id} status to '{status}'")
    return True


def _polish_resume(parsed_data: Dict[str, Any], candidate_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Polish parsed resume data into formatted markdown.
    
    Args:
        parsed_data: Raw parsed resume data from AI parser
        candidate_name: Optional candidate name override
        
    Returns:
        Polished resume data dict with markdown_content and metadata
    """
    try:
        service = ResumePolishingService()
        polished_data = service.polish_resume(parsed_data, candidate_name)
        logger.info(f"[PARSE-RESUME] Resume polished successfully")
        return polished_data
    except Exception as e:
        logger.error(f"[PARSE-RESUME] Resume polishing failed: {e}")
        return {}


def _update_candidate_with_polished_data(candidate_id: int, polished_data: Dict[str, Any]) -> bool:
    """
    Update candidate with polished resume data.
    
    Args:
        candidate_id: Candidate ID
        polished_data: Polished resume data from ResumePolishingService
        
    Returns:
        True if successful, False otherwise
    """
    from sqlalchemy import select
    
    stmt = select(Candidate).where(Candidate.id == candidate_id)
    candidate = db.session.scalar(stmt)
    
    if not candidate:
        logger.warning(f"[PARSE-RESUME] Candidate {candidate_id} not found for polished data update")
        return False
    
    candidate.polished_resume_data = polished_data
    db.session.commit()
    logger.info(f"[PARSE-RESUME] Updated candidate {candidate_id} with polished resume data")
    return True

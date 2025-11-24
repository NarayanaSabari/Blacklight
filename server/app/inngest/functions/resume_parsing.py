"""
Inngest Resume Parsing Workflow
Handles async resume parsing after upload
"""
import logging
from typing import Dict, Any

import inngest
from app.inngest import inngest_client

from app import db
from app.models.candidate import Candidate
from app.services.resume_parser import ResumeParserService
from app.utils.text_extractor import TextExtractor  # FIXED: correct import path

logger = logging.getLogger(__name__)


@inngest_client.create_function(
    fn_id="parse-resume-async",
    trigger=inngest.TriggerEvent(event="candidate/parse-resume"),
    retries=3,
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
        
        if not candidate.resume_file_path:
            logger.error(f"[PARSE-RESUME] No resume file for candidate {candidate_id}")
            _update_candidate_status(candidate_id, "pending_review", {})
            return {"status": "error", "message": "No resume file"}
        
        # Step 2: Extract text (STEP - file operation, might fail)
        resume_text = await ctx.step.run(
            "extract-resume-text",
            lambda: _extract_resume_text(candidate.resume_file_path)
        )
        
        if not resume_text:
            logger.error(f"[PARSE-RESUME] Failed to extract text from resume for candidate {candidate_id}")
            # Update to pending_review so HR can manually enter data
            _update_candidate_status(candidate_id, "pending_review", {})
            return {"status": "error", "message": "Could not extract resume text"}
        
        # Step 3: Run AI parsing (STEP - external API, can fail, needs retry)
        parsed_data = await ctx.step.run(
            "ai-parse-resume",
            lambda: _parse_with_ai(resume_text, candidate.resume_file_path)
        )
        
        # Step 4 & 5: Update candidate (direct - simple DB operations)
        if parsed_data:
            _update_candidate_with_parsed_data(candidate_id, parsed_data)
        
        _update_candidate_status(candidate_id, "pending_review", parsed_data)
        
        logger.info(f"[PARSE-RESUME] Successfully parsed resume for candidate {candidate_id}, status: pending_review")
        
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "has_data": bool(parsed_data)
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

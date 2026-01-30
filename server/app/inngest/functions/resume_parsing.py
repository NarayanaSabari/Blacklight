"""
Inngest Resume Parsing Workflow
Handles async resume parsing after upload

Supports both:
- New CandidateResume model via 'candidate-resume/parse' event
- Legacy candidate.resume_file_key via 'candidate/parse-resume' event (backward compat)
"""
import logging
import os
from typing import Dict, Any, Optional, List

import inngest
from app.inngest import inngest_client

from app import db
from app.models.candidate import Candidate
from app.models.candidate_resume import CandidateResume
from app.services.resume_parser import ResumeParserService
from app.services.resume_polishing_service import ResumePolishingService
from app.utils.text_extractor import TextExtractor
from app.services.file_storage import FileStorageService
from app.services.candidate_resume_service import CandidateResumeService

logger = logging.getLogger(__name__)


# =============================================================================
# NEW: Resume-centric parsing (uses CandidateResume model)
# =============================================================================

@inngest_client.create_function(
    fn_id="parse-candidate-resume",
    trigger=inngest.TriggerEvent(event="candidate-resume/parse"),
    retries=2,
    name="Parse Candidate Resume"
)
async def parse_candidate_resume_workflow(ctx) -> dict:
    """
    Async workflow to parse a specific resume from CandidateResume table.
    
    This is the new preferred method for resume parsing that works with
    the multi-resume feature.
    
    Workflow Steps:
    1. Fetch resume record
    2. Update status to 'processing'
    3. Extract text from resume file
    4. Run AI parsing
    5. Polish resume
    6. Update resume record with parsed/polished data
    7. If primary resume, update candidate profile fields
    
    Event data:
        - resume_id: int (required)
        - tenant_id: int (required)
        - update_candidate_profile: bool (default True for primary resume)
    """
    event_data = ctx.event.data
    resume_id = event_data.get("resume_id")
    tenant_id = event_data.get("tenant_id")
    update_profile = event_data.get("update_candidate_profile", True)
    
    logger.info(f"[PARSE-RESUME] Starting parsing for resume {resume_id}")
    
    try:
        # Step 1: Fetch resume record
        resume = _fetch_resume(resume_id, tenant_id)
        
        if not resume:
            logger.error(f"[PARSE-RESUME] Resume {resume_id} not found")
            return {"status": "error", "message": "Resume not found"}
        
        candidate_id = resume.candidate_id
        
        # Idempotency guard: if resume is already completed, skip
        if resume.processing_status == 'completed' and resume.parsed_resume_data:
            logger.info(f"[PARSE-RESUME] Resume {resume_id} already parsed; skipping")
            return {
                "status": "success",
                "resume_id": resume_id,
                "candidate_id": candidate_id,
                "skipped": True,
            }
        
        # Step 2: Update status to processing
        _update_resume_status(resume_id, 'processing')
        
        if not resume.file_key:
            logger.error(f"[PARSE-RESUME] No file_key for resume {resume_id}")
            _update_resume_status(resume_id, 'failed', error="No resume file")
            return {"status": "error", "message": "No resume file"}
        
        # Step 3: Download and extract text
        storage = FileStorageService()
        local_path, err = storage.download_to_temp(resume.file_key)
        
        if err or not local_path:
            logger.error(f"[PARSE-RESUME] Failed to download file for resume {resume_id}: {err}")
            _update_resume_status(resume_id, 'failed', error=f"Download failed: {err}")
            return {"status": "error", "message": "Failed to download resume file"}
        
        try:
            resume_text = await ctx.step.run(
                "extract-resume-text",
                lambda: _extract_resume_text(local_path)
            )
        finally:
            try:
                if local_path:
                    os.remove(local_path)
            except Exception:
                pass
        
        if not resume_text:
            error_msg = f"Failed to extract text from resume {resume_id}. Check logs for details - possible causes: file not found, empty file, unsupported format, or extraction error."
            logger.error(f"[PARSE-RESUME] {error_msg}")
            _update_resume_status(resume_id, 'failed', error="Could not extract text - check file format and content")
            return {"status": "error", "message": "Could not extract resume text", "details": error_msg, "resume_id": resume_id}
        
        # Step 4: Run AI parsing
        parsed_data = await ctx.step.run(
            "ai-parse-resume",
            lambda: _parse_with_ai(resume_text, resume.original_filename or "resume.pdf")
        )
        
        if not parsed_data:
            logger.warning(f"[PARSE-RESUME] AI parsing returned empty for resume {resume_id}")
            _update_resume_status(resume_id, 'failed', error="AI parsing failed")
            return {"status": "error", "message": "AI parsing failed"}
        
        # Step 5: Polish resume
        # Get candidate name from parsed data (not from candidate record which may still have "Processing")
        candidate_name = None
        personal_info = parsed_data.get('personal_info', parsed_data)
        if personal_info.get('full_name'):
            candidate_name = personal_info['full_name']
        elif personal_info.get('first_name'):
            first = personal_info.get('first_name', '')
            last = personal_info.get('last_name', '')
            candidate_name = f"{first} {last}".strip()
        
        # Fallback to candidate record only if parsed data doesn't have a name
        if not candidate_name:
            candidate = _fetch_candidate(candidate_id, tenant_id)
            if candidate and candidate.first_name and candidate.first_name not in ('Unknown', 'Processing'):
                candidate_name = candidate.full_name or f"{candidate.first_name} {candidate.last_name}".strip()
        
        polished_data = None
        try:
            polished_data = await ctx.step.run(
                "ai-polish-resume",
                lambda: _polish_resume(parsed_data, candidate_name)
            )
        except Exception as polish_error:
            logger.warning(f"[PARSE-RESUME] Resume polishing failed for resume {resume_id}: {polish_error}")
        
        # Step 6: Update resume record with parsed/polished data
        CandidateResumeService.update_processing_status(
            resume_id=resume_id,
            status='completed',
            parsed_data=parsed_data,
            polished_data=polished_data
        )
        
        # Step 7: If primary resume and update_profile is True, update candidate fields
        if resume.is_primary and update_profile and parsed_data:
            _update_candidate_with_parsed_data(candidate_id, parsed_data)
            if polished_data:
                _update_candidate_polished_via_resume(candidate_id, polished_data)
            # Update status to pending_review
            _update_candidate_status(candidate_id, "pending_review")
        
        logger.info(f"[PARSE-RESUME] Successfully parsed resume {resume_id} for candidate {candidate_id}")
        
        return {
            "status": "success",
            "resume_id": resume_id,
            "candidate_id": candidate_id,
            "has_data": bool(parsed_data),
            "has_polished_data": bool(polished_data)
        }
    
    except Exception as e:
        logger.error(f"[PARSE-RESUME] Workflow failed for resume {resume_id}: {e}", exc_info=True)
        try:
            _update_resume_status(resume_id, 'failed', error=str(e))
        except Exception:
            pass
        
        return {
            "status": "error",
            "resume_id": resume_id,
            "error": str(e)
        }


@inngest_client.create_function(
    fn_id="polish-candidate-resume",
    trigger=inngest.TriggerEvent(event="candidate-resume/polish"),
    retries=2,
    name="Polish Candidate Resume"
)
async def polish_candidate_resume_workflow(ctx) -> dict:
    """
    Async workflow to polish an already-parsed resume from CandidateResume table.
    
    Event data:
        - resume_id: int (required)
        - tenant_id: int (required)
    """
    event_data = ctx.event.data
    resume_id = event_data.get("resume_id")
    tenant_id = event_data.get("tenant_id")
    
    # Ensure IDs are integers (they may come as strings from JSON)
    if resume_id is not None:
        resume_id = int(resume_id)
    if tenant_id is not None:
        tenant_id = int(tenant_id)
    
    logger.info(f"[POLISH-RESUME] Starting polishing for resume {resume_id}, tenant {tenant_id}")
    logger.info(f"[POLISH-RESUME] Full event data: {event_data}")
    
    try:
        # Fetch resume record
        resume = _fetch_resume(resume_id, tenant_id)
        
        if not resume:
            # Debug: Check what resumes exist
            from sqlalchemy import select
            all_resumes_stmt = select(CandidateResume.id, CandidateResume.tenant_id).limit(10)
            existing = db.session.execute(all_resumes_stmt).fetchall()
            logger.error(f"[POLISH-RESUME] Resume {resume_id} (tenant={tenant_id}) not found. Sample existing resumes: {existing}")
            return {"status": "error", "message": "Resume not found"}
        
        # Check if already polished
        if resume.polished_resume_data and resume.polished_resume_data.get('markdown_content'):
            logger.info(f"[POLISH-RESUME] Resume {resume_id} already polished, skipping")
            return {
                "status": "success",
                "resume_id": resume_id,
                "skipped": True
            }
        
        # Check if we have parsed data
        if not resume.parsed_resume_data:
            logger.warning(f"[POLISH-RESUME] Resume {resume_id} has no parsed data")
            return {"status": "error", "message": "No parsed data available"}
        
        # Get candidate name from parsed data first
        candidate_name = None
        parsed_data = resume.parsed_resume_data or {}
        personal_info = parsed_data.get('personal_info', parsed_data)
        if personal_info.get('full_name'):
            candidate_name = personal_info['full_name']
        elif personal_info.get('first_name'):
            first = personal_info.get('first_name', '')
            last = personal_info.get('last_name', '')
            candidate_name = f"{first} {last}".strip()
        
        # Fallback to candidate record only if parsed data doesn't have a name
        if not candidate_name:
            candidate = _fetch_candidate(resume.candidate_id, tenant_id)
            if candidate and candidate.first_name and candidate.first_name not in ('Unknown', 'Processing'):
                candidate_name = candidate.full_name or f"{candidate.first_name or ''} {candidate.last_name or ''}".strip()
        
        # Polish the resume
        polished_data = await ctx.step.run(
            "ai-polish-resume",
            lambda: _polish_resume(resume.parsed_resume_data, candidate_name)
        )
        
        if not polished_data or not polished_data.get('markdown_content'):
            logger.error(f"[POLISH-RESUME] Polishing failed for resume {resume_id}")
            return {"status": "error", "message": "Polishing failed"}
        
        # Update resume with polished data
        CandidateResumeService.update_processing_status(
            resume_id=resume_id,
            status='completed',
            polished_data=polished_data
        )
        
        # If primary resume, also update candidate (polished data is accessed via primary_resume property)
        # No need to update candidate directly since polished_resume_data is a property
        
        logger.info(f"[POLISH-RESUME] Successfully polished resume {resume_id}")
        
        return {
            "status": "success",
            "resume_id": resume_id,
            "has_polished_data": True
        }
    
    except Exception as e:
        logger.error(f"[POLISH-RESUME] Error for resume {resume_id}: {e}", exc_info=True)
        return {
            "status": "error",
            "resume_id": resume_id,
            "error": str(e)
        }


# =============================================================================
# LEGACY: Candidate-centric parsing (backward compatibility)
# =============================================================================

@inngest_client.create_function(
    fn_id="parse-resume-async",
    trigger=inngest.TriggerEvent(event="candidate/parse-resume"),
    retries=0,
    name="Parse Resume Async (Legacy)"
)
async def parse_resume_workflow(ctx) -> dict:
    """
    LEGACY: Async workflow to parse resume after upload.
    
    This function maintains backward compatibility for code that still
    triggers the old 'candidate/parse-resume' event.
    
    For new code, use 'candidate-resume/parse' event with resume_id instead.
    
    Event data:
        - candidate_id: int
        - tenant_id: int
        - resume_id: int (optional - if provided, delegates to new workflow)
    """
    event_data = ctx.event.data
    candidate_id = event_data.get("candidate_id")
    tenant_id = event_data.get("tenant_id")
    resume_id = event_data.get("resume_id")
    
    logger.info(f"[PARSE-RESUME-LEGACY] Starting for candidate {candidate_id}")
    
    # If resume_id is provided, find and use that resume
    if resume_id:
        resume = _fetch_resume(resume_id, tenant_id)
        if resume:
            # Delegate to the new resume-centric parsing
            return await _parse_resume_impl(ctx, resume, candidate_id, tenant_id)
    
    # Otherwise, try to find the primary/latest resume for this candidate
    candidate = _fetch_candidate(candidate_id, tenant_id)
    if not candidate:
        logger.error(f"[PARSE-RESUME-LEGACY] Candidate {candidate_id} not found")
        return {"status": "error", "message": "Candidate not found"}
    
    # Try to get primary resume from new model
    primary_resume = candidate.primary_resume
    if primary_resume:
        return await _parse_resume_impl(ctx, primary_resume, candidate_id, tenant_id)
    
    # No resume found - update status and return error
    logger.error(f"[PARSE-RESUME-LEGACY] No resume found for candidate {candidate_id}")
    _update_candidate_status(candidate_id, "pending_review")
    return {"status": "error", "message": "No resume found"}


async def _parse_resume_impl(ctx, resume: CandidateResume, candidate_id: int, tenant_id: int) -> dict:
    """
    Implementation of resume parsing logic for a CandidateResume record.
    """
    resume_id = resume.id
    
    try:
        # Idempotency guard
        if resume.processing_status == 'completed' and resume.parsed_resume_data:
            candidate = _fetch_candidate(candidate_id, tenant_id)
            if candidate and candidate.status in ["pending_review", "onboarded", "ready_for_assignment"]:
                logger.info(f"[PARSE-RESUME] Resume {resume_id} already parsed; skipping")
                return {
                    "status": "success",
                    "resume_id": resume_id,
                    "candidate_id": candidate_id,
                    "skipped": True,
                }
        
        # Update status to processing
        _update_resume_status(resume_id, 'processing')
        
        if not resume.file_key:
            logger.error(f"[PARSE-RESUME] No file_key for resume {resume_id}")
            _update_resume_status(resume_id, 'failed', error="No resume file")
            _update_candidate_status(candidate_id, "pending_review")
            return {"status": "error", "message": "No resume file"}
        
        # Download file
        storage = FileStorageService()
        local_path, err = storage.download_to_temp(resume.file_key)
        
        if err or not local_path:
            logger.error(f"[PARSE-RESUME] Failed to download: {err}")
            _update_resume_status(resume_id, 'failed', error=f"Download failed: {err}")
            _update_candidate_status(candidate_id, "pending_review")
            return {"status": "error", "message": "Failed to download resume file"}
        
        try:
            resume_text = await ctx.step.run(
                "extract-resume-text",
                lambda: _extract_resume_text(local_path)
            )
        finally:
            try:
                if local_path:
                    os.remove(local_path)
            except Exception:
                pass
        
        if not resume_text:
            error_msg = f"Failed to extract text from resume {resume_id}. Check logs for details - possible causes: file not found, empty file, unsupported format, or extraction error."
            logger.error(f"[PARSE-RESUME] {error_msg}")
            _update_resume_status(resume_id, 'failed', error="Could not extract text - check file format and content")
            _update_candidate_status(candidate_id, "pending_review")
            return {"status": "error", "message": "Could not extract resume text", "details": error_msg, "resume_id": resume_id}
        
        # AI parsing
        parsed_data = await ctx.step.run(
            "ai-parse-resume",
            lambda: _parse_with_ai(resume_text, resume.original_filename or "resume.pdf")
        )
        
        # Update candidate with parsed data
        if parsed_data:
            _update_candidate_with_parsed_data(candidate_id, parsed_data)
        
        # Polish resume
        polished_data = None
        if parsed_data:
            try:
                # Get candidate name from parsed data first (more reliable)
                candidate_name = None
                personal_info = parsed_data.get('personal_info', parsed_data)
                if personal_info.get('full_name'):
                    candidate_name = personal_info['full_name']
                elif personal_info.get('first_name'):
                    first = personal_info.get('first_name', '')
                    last = personal_info.get('last_name', '')
                    candidate_name = f"{first} {last}".strip()
                
                polished_data = await ctx.step.run(
                    "ai-polish-resume",
                    lambda: _polish_resume(parsed_data, candidate_name)
                )
                
                # Polished data is stored in resume, accessible via candidate.primary_resume.polished_resume_data
            except Exception as polish_error:
                logger.warning(f"[PARSE-RESUME] Polishing failed: {polish_error}")
        
        # Update resume record
        CandidateResumeService.update_processing_status(
            resume_id=resume_id,
            status='completed',
            parsed_data=parsed_data,
            polished_data=polished_data
        )
        
        # Update candidate status
        _update_candidate_status(candidate_id, "pending_review")
        
        logger.info(f"[PARSE-RESUME] Successfully parsed resume {resume_id} for candidate {candidate_id}")
        
        return {
            "status": "success",
            "resume_id": resume_id,
            "candidate_id": candidate_id,
            "has_data": bool(parsed_data),
            "has_polished_data": bool(polished_data)
        }
    
    except Exception as e:
        logger.error(f"[PARSE-RESUME] Failed for resume {resume_id}: {e}", exc_info=True)
        try:
            _update_resume_status(resume_id, 'failed', error=str(e))
            _update_candidate_status(candidate_id, "pending_review")
        except Exception:
            pass
        
        return {
            "status": "error",
            "resume_id": resume_id,
            "candidate_id": candidate_id,
            "error": str(e)
        }


@inngest_client.create_function(
    fn_id="polish-resume-async",
    trigger=inngest.TriggerEvent(event="candidate/polish-resume"),
    retries=2,
    name="Polish Resume Async (Legacy)"
)
async def polish_resume_workflow(ctx) -> dict:
    """
    LEGACY: Async workflow to polish an already-parsed resume.
    
    For new code, use 'candidate-resume/polish' event with resume_id.
    
    Event data:
        - candidate_id: int
        - tenant_id: int
        - resume_id: int (optional)
    """
    event_data = ctx.event.data
    candidate_id = event_data.get("candidate_id")
    tenant_id = event_data.get("tenant_id")
    resume_id = event_data.get("resume_id")
    
    logger.info(f"[POLISH-RESUME-LEGACY] Starting for candidate {candidate_id}")
    
    try:
        # If resume_id provided, use new model
        if resume_id:
            resume = _fetch_resume(resume_id, tenant_id)
            if resume and resume.parsed_resume_data:
                # Get candidate name from parsed data first (candidate record may still have "Processing")
                candidate_name = None
                parsed_data = resume.parsed_resume_data
                personal_info = parsed_data.get('personal_info', parsed_data)
                if personal_info.get('full_name'):
                    candidate_name = personal_info['full_name']
                elif personal_info.get('first_name'):
                    first = personal_info.get('first_name', '')
                    last = personal_info.get('last_name', '')
                    candidate_name = f"{first} {last}".strip()
                
                # Fallback to candidate record only if parsed data doesn't have a valid name
                if not candidate_name:
                    candidate = _fetch_candidate(candidate_id, tenant_id)
                    if candidate and candidate.first_name and candidate.first_name not in ('Unknown', 'Processing'):
                        candidate_name = candidate.full_name or f"{candidate.first_name or ''} {candidate.last_name or ''}".strip()
                
                polished_data = await ctx.step.run(
                    "ai-polish-resume",
                    lambda: _polish_resume(resume.parsed_resume_data, candidate_name)
                )
                
                if polished_data:
                    CandidateResumeService.update_processing_status(
                        resume_id=resume_id,
                        status='completed',
                        polished_data=polished_data
                    )
                
                return {
                    "status": "success",
                    "resume_id": resume_id,
                    "candidate_id": candidate_id,
                    "has_polished_data": bool(polished_data)
                }
        
        # Fallback to candidate's primary resume
        candidate = _fetch_candidate(candidate_id, tenant_id)
        if not candidate:
            return {"status": "error", "message": "Candidate not found"}
        
        primary_resume = candidate.primary_resume
        if not primary_resume:
            return {"status": "error", "message": "No resume found"}
        
        if not primary_resume.parsed_resume_data:
            return {"status": "error", "message": "No parsed data available"}
        
        parsed_data = primary_resume.parsed_resume_data
        
        # Check if already polished
        if primary_resume.polished_resume_data and primary_resume.polished_resume_data.get('markdown_content'):
            return {"status": "success", "candidate_id": candidate_id, "skipped": True}
        
        # Get candidate name from parsed data first (candidate record may still have "Processing")
        candidate_name = None
        personal_info = parsed_data.get('personal_info', parsed_data)
        if personal_info.get('full_name'):
            candidate_name = personal_info['full_name']
        elif personal_info.get('first_name'):
            first = personal_info.get('first_name', '')
            last = personal_info.get('last_name', '')
            candidate_name = f"{first} {last}".strip()
        
        # Fallback to candidate record only if parsed data doesn't have a valid name
        if not candidate_name and candidate.first_name and candidate.first_name not in ('Unknown', 'Processing'):
            candidate_name = candidate.full_name or f"{candidate.first_name or ''} {candidate.last_name or ''}".strip()
        
        polished_data = await ctx.step.run(
            "ai-polish-resume",
            lambda: _polish_resume(parsed_data, candidate_name)
        )
        
        if not polished_data or not polished_data.get('markdown_content'):
            return {"status": "error", "message": "Polishing failed"}
        
        # Update resume record
        CandidateResumeService.update_processing_status(
            resume_id=primary_resume.id,
            status='completed',
            polished_data=polished_data
        )
        
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "has_polished_data": True
        }
    
    except Exception as e:
        logger.error(f"[POLISH-RESUME-LEGACY] Error: {e}", exc_info=True)
        return {"status": "error", "candidate_id": candidate_id, "error": str(e)}


# =============================================================================
# Helper Functions
# =============================================================================

def _fetch_resume(resume_id: int, tenant_id: int) -> Optional[CandidateResume]:
    """Fetch resume from database"""
    from sqlalchemy import select, and_
    
    if resume_id is None or tenant_id is None:
        logger.error(f"[_fetch_resume] Invalid IDs: resume_id={resume_id}, tenant_id={tenant_id}")
        return None
    
    logger.info(f"[_fetch_resume] Looking for resume_id={resume_id} (type={type(resume_id)}), tenant_id={tenant_id} (type={type(tenant_id)})")
    
    stmt = select(CandidateResume).where(
        and_(
            CandidateResume.id == resume_id,
            CandidateResume.tenant_id == tenant_id
        )
    )
    result = db.session.scalar(stmt)
    logger.info(f"[_fetch_resume] Query result: {result}")
    return result


def _update_resume_status(resume_id: int, status: str, error: Optional[str] = None) -> None:
    """Update resume processing status"""
    from datetime import datetime
    resume = db.session.get(CandidateResume, resume_id)
    if resume:
        resume.processing_status = status
        resume.processing_error = error
        if status == 'completed':
            resume.processed_at = datetime.utcnow()
        db.session.commit()


def _fetch_candidate(candidate_id: int, tenant_id: int) -> Optional[Candidate]:
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
        logger.error("[PARSE-RESUME] No file path provided for text extraction")
        return ""
    
    import os
    
    # Debug file info
    try:
        if not os.path.exists(file_path):
            logger.error(f"[PARSE-RESUME] File does not exist: {file_path}")
            return ""
        
        file_size = os.path.getsize(file_path)
        logger.info(f"[PARSE-RESUME] File exists: {file_path}, Size: {file_size} bytes")
        
        if file_size == 0:
            logger.error(f"[PARSE-RESUME] File is empty (0 bytes): {file_path}")
            return ""
        
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            logger.warning(f"[PARSE-RESUME] Large file detected ({file_size} bytes): {file_path}")
        
    except Exception as e:
        logger.error(f"[PARSE-RESUME] Error checking file info: {e}")
    
    try:
        logger.info(f"[PARSE-RESUME] Starting text extraction from: {file_path}")
        result = TextExtractor.extract_from_file(file_path)
        
        if not result:
            logger.error(f"[PARSE-RESUME] TextExtractor returned None for: {file_path}")
            return ""
        
        text = result.get('text', '')
        file_type = result.get('file_type', 'unknown')
        pages = result.get('pages', 'unknown')
        
        logger.info(f"[PARSE-RESUME] Extracted {len(text)} characters from {file_type} file (pages: {pages}): {file_path}")
        
        if not text or len(text.strip()) == 0:
            logger.error(f"[PARSE-RESUME] Extracted text is empty for: {file_path}")
            return ""
        
        return text
    except Exception as e:
        logger.error(f"[PARSE-RESUME] Text extraction failed for {file_path}: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[PARSE-RESUME] Traceback: {traceback.format_exc()}")
        return ""


def _parse_with_ai(text: str, filename: str) -> Dict[str, Any]:
    """Run AI parsing on resume text"""
    try:
        parser = ResumeParserService()
        file_type = 'pdf' if filename.endswith('.pdf') else 'docx'
        parsed_data = parser.parse_resume(text, file_type)
        logger.info(f"[PARSE-RESUME] AI parsing completed successfully")
        return parsed_data
    except Exception as e:
        logger.error(f"[PARSE-RESUME] AI parsing failed: {e}")
        return {}


def _update_candidate_with_parsed_data(candidate_id: int, parsed_data: Dict[str, Any]) -> Optional[Candidate]:
    """Update candidate profile fields with parsed data from resume."""
    from sqlalchemy import select
    
    stmt = select(Candidate).where(Candidate.id == candidate_id)
    candidate = db.session.scalar(stmt)
    
    if not candidate:
        return None
    
    if parsed_data:
        # Personal info - support both flat and nested structure
        personal = parsed_data.get('personal_info', parsed_data)
        
        # Only update name fields if candidate doesn't have a real name yet
        # (preserve user-provided names from resume upload)
        if not candidate.first_name or candidate.first_name in ('Unknown', 'Processing'):
            if personal.get('full_name'):
                candidate.full_name = personal['full_name']
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
        if parsed_data.get('visa_type'):
            candidate.visa_type = parsed_data['visa_type']
        
        # Arrays
        if parsed_data.get('skills'):
            candidate.skills = parsed_data['skills']
        if parsed_data.get('certifications'):
            candidate.certifications = parsed_data['certifications']
        if parsed_data.get('languages'):
            candidate.languages = parsed_data.get('languages', [])
        if parsed_data.get('preferred_locations'):
            candidate.preferred_locations = parsed_data['preferred_locations']
        
        # Auto-infer preferred_roles
        if not candidate.preferred_roles or len(candidate.preferred_roles) == 0:
            inferred_roles: List[str] = []
            if parsed_data.get('current_title'):
                inferred_roles.append(parsed_data['current_title'])
            if parsed_data.get('work_experience'):
                for exp in parsed_data['work_experience'][:3]:
                    title = exp.get('title') or exp.get('job_title')
                    if title and title not in inferred_roles:
                        inferred_roles.append(title)
            if inferred_roles:
                candidate.preferred_roles = inferred_roles[:5]
                logger.info(f"[PARSE-RESUME] Auto-inferred preferred_roles: {candidate.preferred_roles}")
        
        # JSONB
        if parsed_data.get('education'):
            candidate.education = parsed_data['education']
        if parsed_data.get('work_experience'):
            candidate.work_experience = parsed_data['work_experience']
    
    db.session.commit()
    logger.info(f"[PARSE-RESUME] Updated candidate {candidate_id} with parsed data")
    return candidate


def _update_candidate_status(candidate_id: int, status: str) -> bool:
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
    """Polish parsed resume data into formatted markdown."""
    try:
        service = ResumePolishingService()
        polished_data = service.polish_resume(parsed_data, candidate_name)
        logger.info(f"[PARSE-RESUME] Resume polished successfully")
        return polished_data
    except Exception as e:
        logger.error(f"[PARSE-RESUME] Resume polishing failed: {e}")
        return {}


def _update_candidate_polished_via_resume(candidate_id: int, polished_data: Dict[str, Any]) -> bool:
    """
    Note: Polished data is now stored in CandidateResume table and accessed via
    candidate.primary_resume.polished_resume_data property.
    
    This function is kept for backward compatibility but polished_resume_data
    is now a property on Candidate that delegates to primary_resume.
    
    The actual update happens in CandidateResumeService.update_processing_status()
    """
    logger.info(f"[PARSE-RESUME] Polished data stored in resume record for candidate {candidate_id}")
    return True

"""
Candidate Resume Routes
RESTful API endpoints for managing multiple resumes per candidate
"""
from flask import Blueprint, request, jsonify, g, send_file
from werkzeug.datastructures import FileStorage
from io import BytesIO
from typing import Optional
import logging

from app import db
from app.models.candidate import Candidate
from app.models.candidate_resume import CandidateResume
from app.services.candidate_resume_service import CandidateResumeService
from app.services.file_storage import FileStorageService
from app.schemas.candidate_resume_schema import (
    CandidateResumeResponseSchema,
    CandidateResumeDetailSchema,
    CandidateResumeListSchema,
    CandidateResumeUploadSchema,
    SetPrimaryResumeSchema,
    ReprocessResumeSchema,
    PolishedResumeUpdateSchema,
)
from app.middleware.portal_auth import require_portal_auth, require_permission
from app.middleware.tenant_context import with_tenant_context

logger = logging.getLogger(__name__)

# Create Blueprint - nested under candidates
candidate_resume_bp = Blueprint(
    'candidate_resumes', 
    __name__, 
    url_prefix='/api/candidates/<int:candidate_id>/resumes'
)


def error_response(message: str, status: int = 400, details: dict = None):
    """Helper to create error responses"""
    return jsonify({
        'error': 'Error',
        'message': message,
        'status': status,
        'details': details or {}
    }), status


def _get_candidate_or_404(candidate_id: int, tenant_id: int) -> Optional[Candidate]:
    """Get candidate by ID and tenant, or return 404 response."""
    from sqlalchemy import select, and_
    stmt = select(Candidate).where(
        and_(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id
        )
    )
    return db.session.scalar(stmt)


# ==================== List Resumes ====================

@candidate_resume_bp.route('', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def list_resumes(candidate_id: int):
    """
    List all resumes for a candidate.
    
    Returns:
        200: List of resumes with primary resume ID
        404: Candidate not found
    """
    try:
        tenant_id = g.tenant_id
        
        # Verify candidate exists
        candidate = _get_candidate_or_404(candidate_id, tenant_id)
        if not candidate:
            return error_response("Candidate not found", 404)
        
        # Get all resumes
        resumes = CandidateResumeService.get_resumes_for_candidate(candidate_id, tenant_id)
        
        # Look up CandidateDocument verification status by file_key
        from sqlalchemy import select, and_
        from app.models.candidate_document import CandidateDocument
        
        # Build a mapping of file_key -> is_verified
        file_keys = [r.file_key for r in resumes]
        doc_stmt = select(CandidateDocument.file_key, CandidateDocument.is_verified).where(
            and_(
                CandidateDocument.tenant_id == tenant_id,
                CandidateDocument.candidate_id == candidate_id,
                CandidateDocument.file_key.in_(file_keys)
            )
        )
        doc_results = db.session.execute(doc_stmt).fetchall()
        verification_map = {row.file_key: row.is_verified for row in doc_results}
        
        # Find primary resume ID
        primary_id = None
        for resume in resumes:
            if resume.is_primary:
                primary_id = resume.id
                break
        
        # Serialize response with is_verified added
        resume_dicts = []
        for r in resumes:
            r_dict = r.to_dict()
            # Add is_verified from the corresponding CandidateDocument
            r_dict['is_verified'] = verification_map.get(r.file_key, None)
            resume_dicts.append(CandidateResumeResponseSchema.model_validate(r_dict))
        
        response = CandidateResumeListSchema(
            total=len(resumes),
            primary_resume_id=primary_id,
            resumes=resume_dicts
        )
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        logger.error(f"Error listing resumes for candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to list resumes: {str(e)}", 500)


# ==================== Get Resume Details ====================

@candidate_resume_bp.route('/<int:resume_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_resume(candidate_id: int, resume_id: int):
    """
    Get detailed information about a specific resume.
    
    Query params:
        - include_parsed: Include parsed resume data (default: false)
        - include_polished: Include polished resume data (default: false)
    
    Returns:
        200: Resume details
        404: Resume not found
    """
    try:
        tenant_id = g.tenant_id
        
        # Get resume
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        
        if not resume or resume.candidate_id != candidate_id:
            return error_response("Resume not found", 404)
        
        # Parse query params
        include_parsed = request.args.get('include_parsed', 'false').lower() == 'true'
        include_polished = request.args.get('include_polished', 'false').lower() == 'true'
        
        # Serialize response
        resume_dict = resume.to_dict(
            include_parsed_data=include_parsed,
            include_polished_data=include_polished
        )
        response = CandidateResumeDetailSchema.model_validate(resume_dict)
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        logger.error(f"Error getting resume {resume_id}: {e}", exc_info=True)
        return error_response(f"Failed to get resume: {str(e)}", 500)


# ==================== Upload Resume ====================

@candidate_resume_bp.route('', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def upload_resume(candidate_id: int):
    """
    Upload a new resume for a candidate.
    
    Required: multipart/form-data with 'file' field
    Form fields:
        - file: The resume file to upload
        - is_primary: Set as primary resume (default: false)
        - trigger_parsing: Trigger async resume parsing (default: true)
    
    Returns:
        201: Resume uploaded successfully
        400: Validation error or file missing
        404: Candidate not found
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Verify candidate exists
        candidate = _get_candidate_or_404(candidate_id, tenant_id)
        if not candidate:
            return error_response("Candidate not found", 404)
        
        # Check for file
        if 'file' not in request.files:
            return error_response("No file provided in request", 400)
        
        file: FileStorage = request.files['file']
        if not file or file.filename == '':
            return error_response("No file selected", 400)
        
        # Validate file type
        allowed_extensions = {'pdf', 'doc', 'docx'}
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return error_response(
                f"Invalid file type. Allowed: {', '.join(allowed_extensions)}", 
                400
            )
        
        # Parse form data
        is_primary = request.form.get('is_primary', 'false').lower() == 'true'
        trigger_parsing = request.form.get('trigger_parsing', 'true').lower() == 'true'
        
        # Upload and create resume record
        resume, file_key = CandidateResumeService.upload_and_create_resume(
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            file=file,
            is_primary=is_primary,
            uploaded_by_user_id=user_id,
            uploaded_by_candidate=False,
        )
        
        # Also create a CandidateDocument record for consistency with email invitation flow
        # This ensures resumes appear in document listings and are subject to verification
        from app.models.candidate_document import CandidateDocument
        
        resume_document = CandidateDocument(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            invitation_id=None,  # HR upload, not from invitation
            document_type='resume',
            file_name=file.filename or 'resume',
            file_key=file_key,
            file_size=resume.file_size or 0,
            mime_type=resume.mime_type or 'application/pdf',
            storage_backend=resume.storage_backend or 'gcs',
            uploaded_by_id=user_id,
            is_verified=False,  # Requires HR verification like other docs
        )
        db.session.add(resume_document)
        
        # CRITICAL: Commit the resume before triggering Inngest event
        # CandidateResumeService.upload_and_create_resume() only does flush(), not commit()
        # The Inngest worker runs in a separate process and needs committed data
        db.session.commit()
        
        logger.info(f"Uploaded resume {resume.id} and document {resume_document.id} for candidate {candidate_id}")
        
        # Trigger async parsing if requested
        if trigger_parsing:
            try:
                from app.inngest import inngest_client
                inngest_client.send_sync({
                    "name": "candidate-resume/parse",
                    "data": {
                        "resume_id": resume.id,
                        "tenant_id": tenant_id,
                        "update_candidate_profile": resume.is_primary,
                    }
                })
                logger.info(f"Triggered parsing for resume {resume.id}")
            except Exception as inngest_error:
                logger.warning(f"Failed to trigger resume parsing: {inngest_error}")
        
        # Serialize response
        response = CandidateResumeResponseSchema.model_validate(resume.to_dict())
        
        return jsonify(response.model_dump()), 201
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error uploading resume for candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to upload resume: {str(e)}", 500)


# ==================== Set Primary Resume ====================

@candidate_resume_bp.route('/<int:resume_id>/primary', methods=['PATCH'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def set_primary_resume(candidate_id: int, resume_id: int):
    """
    Set a resume as the primary resume for a candidate.
    
    Returns:
        200: Resume set as primary
        404: Resume not found
    """
    try:
        tenant_id = g.tenant_id
        
        # Get resume
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        
        if not resume or resume.candidate_id != candidate_id:
            return error_response("Resume not found", 404)
        
        # Set as primary
        updated_resume = CandidateResumeService.set_primary(resume_id, tenant_id)
        
        # Serialize response
        response = CandidateResumeResponseSchema.model_validate(updated_resume.to_dict())
        
        return jsonify(response.model_dump()), 200
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error setting primary resume {resume_id}: {e}", exc_info=True)
        return error_response(f"Failed to set primary resume: {str(e)}", 500)


# ==================== Delete Resume ====================

@candidate_resume_bp.route('/<int:resume_id>', methods=['DELETE'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.delete')
def delete_resume(candidate_id: int, resume_id: int):
    """
    Delete a resume.
    
    Note: Cannot delete the only resume for a candidate.
    
    Returns:
        200: Resume deleted
        400: Cannot delete only resume
        404: Resume not found
    """
    try:
        tenant_id = g.tenant_id
        
        # Get resume
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        
        if not resume or resume.candidate_id != candidate_id:
            return error_response("Resume not found", 404)
        
        # Delete resume
        deleted = CandidateResumeService.delete_resume(resume_id, tenant_id)
        
        if not deleted:
            return error_response("Failed to delete resume", 500)
        
        return jsonify({
            "message": "Resume deleted successfully",
            "resume_id": resume_id
        }), 200
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error deleting resume {resume_id}: {e}", exc_info=True)
        return error_response(f"Failed to delete resume: {str(e)}", 500)


# ==================== Download Resume ====================

@candidate_resume_bp.route('/<int:resume_id>/download', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def download_resume(candidate_id: int, resume_id: int):
    """
    Download a resume file.
    
    Returns:
        200: File download
        404: Resume not found
    """
    try:
        tenant_id = g.tenant_id
        
        # Get resume
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        
        if not resume or resume.candidate_id != candidate_id:
            return error_response("Resume not found", 404)
        
        # Get signed URL for redirect (preferred for GCS)
        if resume.storage_backend == 'gcs':
            download_url = CandidateResumeService.get_resume_download_url(resume_id, tenant_id)
            if download_url:
                return jsonify({
                    "download_url": download_url,
                    "filename": resume.original_filename,
                    "expires_in": 3600  # 1 hour
                }), 200
        
        # For local storage, serve the file directly
        storage_service = FileStorageService()
        file_content = storage_service.download_file(resume.file_key)
        
        if not file_content:
            return error_response("Failed to retrieve file", 500)
        
        return send_file(
            BytesIO(file_content),
            as_attachment=True,
            download_name=resume.original_filename,
            mimetype=resume.mime_type or 'application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error downloading resume {resume_id}: {e}", exc_info=True)
        return error_response(f"Failed to download resume: {str(e)}", 500)


# ==================== Reprocess Resume ====================

@candidate_resume_bp.route('/<int:resume_id>/reprocess', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def reprocess_resume(candidate_id: int, resume_id: int):
    """
    Trigger reprocessing (parsing and polishing) of a resume.
    
    Request body (optional):
        - update_candidate_profile: Update candidate profile from parsed data (default: true for primary)
    
    Returns:
        202: Reprocessing triggered
        404: Resume not found
    """
    try:
        tenant_id = g.tenant_id
        
        # Get resume
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        
        if not resume or resume.candidate_id != candidate_id:
            return error_response("Resume not found", 404)
        
        # Parse request body
        data = request.get_json() or {}
        update_profile = data.get('update_candidate_profile', resume.is_primary)
        
        # Reset processing status
        CandidateResumeService.update_processing_status(
            resume_id=resume_id,
            status='pending'
        )
        
        # Trigger async parsing
        try:
            from app.inngest import inngest_client
            inngest_client.send_sync({
                "name": "candidate-resume/parse",
                "data": {
                    "resume_id": resume.id,
                    "tenant_id": tenant_id,
                    "update_candidate_profile": update_profile,
                }
            })
            logger.info(f"Triggered reprocessing for resume {resume.id}")
        except Exception as inngest_error:
            logger.error(f"Failed to trigger resume reprocessing: {inngest_error}")
            return error_response("Failed to trigger reprocessing", 500)
        
        return jsonify({
            "message": "Reprocessing triggered",
            "resume_id": resume_id,
            "status": "pending"
        }), 202
        
    except Exception as e:
        logger.error(f"Error reprocessing resume {resume_id}: {e}", exc_info=True)
        return error_response(f"Failed to reprocess resume: {str(e)}", 500)


# ==================== Get Polished Resume ====================

@candidate_resume_bp.route('/<int:resume_id>/polished', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_polished_resume(candidate_id: int, resume_id: int):
    """
    Get the polished/formatted version of a resume.
    
    Returns:
        200: Polished resume data with markdown content
        404: Resume not found
        422: Resume has no polished data
    """
    try:
        tenant_id = g.tenant_id
        
        # Get resume
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        
        if not resume or resume.candidate_id != candidate_id:
            return error_response("Resume not found", 404)
        
        if not resume.polished_resume_data:
            return error_response("Resume has not been polished yet", 422)
        
        return jsonify({
            "resume_id": resume_id,
            "is_primary": resume.is_primary,
            "has_polished_data": True,
            "markdown_content": resume.polished_resume_markdown,
            "polished_at": resume.processed_at.isoformat() if resume.processed_at else None,
            "polished_data": resume.polished_resume_data,
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting polished resume {resume_id}: {e}", exc_info=True)
        return error_response(f"Failed to get polished resume: {str(e)}", 500)


# ==================== Update Polished Resume ====================

@candidate_resume_bp.route('/<int:resume_id>/polished', methods=['PUT'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def update_polished_resume(candidate_id: int, resume_id: int):
    """
    Update the polished/formatted version of a resume.
    
    Request body:
        - markdown_content: Updated markdown content
    
    Returns:
        200: Polished resume updated
        404: Resume not found
    """
    try:
        tenant_id = g.tenant_id
        
        # Get resume
        resume = CandidateResumeService.get_resume_by_id(resume_id, tenant_id)
        
        if not resume or resume.candidate_id != candidate_id:
            return error_response("Resume not found", 404)
        
        # Validate request body
        data = PolishedResumeUpdateSchema.model_validate(request.get_json())
        
        # Update polished data
        polished_data = resume.polished_resume_data or {}
        polished_data['markdown_content'] = data.markdown_content
        polished_data['manually_edited'] = True
        
        resume.set_polished_resume(data.markdown_content)
        db.session.commit()
        
        return jsonify({
            "message": "Polished resume updated",
            "resume_id": resume_id,
            "markdown_content": data.markdown_content,
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating polished resume {resume_id}: {e}", exc_info=True)
        return error_response(f"Failed to update polished resume: {str(e)}", 500)

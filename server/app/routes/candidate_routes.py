"""
Candidate routes for resume parsing and candidate management
"""
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.datastructures import FileStorage
from pydantic import ValidationError
import logging
from datetime import datetime

from app import db
from app.models.candidate import Candidate
from app.services import CandidateService
from app.schemas.candidate_schema import (
    CandidateCreateSchema,
    CandidateUpdateSchema,
    CandidateFilterSchema,
    CandidateResponseSchema,
    CandidateListItemSchema,
    CandidateListResponseSchema,
    UploadResumeResponseSchema,
    ReparseResumeResponseSchema,
    CandidateStatsSchema,
    PolishedResumeResponseSchema,
    PolishedResumeUpdateSchema,
)
from app.middleware.portal_auth import require_portal_auth, require_permission
from app.middleware.tenant_context import with_tenant_context

logger = logging.getLogger(__name__)

candidate_bp = Blueprint('candidate', __name__, url_prefix='/api/candidates')
candidate_service = CandidateService()


def error_response(message: str, status: int = 400, details: dict = None):
    """Helper to create error responses"""
    return jsonify({
        'error': 'Error',
        'message': message,
        'status': status,
        'details': details or {}
    }), status


# ==================== CRUD Endpoints ====================

@candidate_bp.route('', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.create')
def create_candidate():
    """
    Create a new candidate manually (without resume)
    
    Request Body: CandidateCreateSchema
    Returns: CandidateResponseSchema
    """
    try:
        # Get tenant_id from context (set by middleware)
        tenant_id = g.tenant_id
        
        # Validate request body
        data = CandidateCreateSchema.model_validate(request.get_json())
        
        from app.services.candidate_service import CandidateService
        service = CandidateService()
        
        candidate_data = {
            'first_name': data.first_name,
            'last_name': data.last_name,
            'email': data.email,
            'phone': data.phone,
            'full_name': data.full_name or f"{data.first_name} {data.last_name}",
            'location': data.location,
            'linkedin_url': data.linkedin_url,
            'portfolio_url': data.portfolio_url,
            'current_title': data.current_title,
            'total_experience_years': data.total_experience_years,
            'notice_period': data.notice_period,
            'expected_salary': data.expected_salary,
            'visa_type': data.visa_type,
            'professional_summary': data.professional_summary,
            'preferred_locations': data.preferred_locations or [],
            'skills': data.skills or [],
            'certifications': data.certifications or [],
            'languages': data.languages or [],
            'education': data.education or [],
            'work_experience': data.work_experience or [],
            'status': data.status,
            'source': data.source,
        }
        
        candidate = service.create_candidate(candidate_data, tenant_id)
        
        response = CandidateResponseSchema.model_validate(candidate)
        return jsonify(response.model_dump()), 201
    
    except ValidationError as e:
        logger.warning(f"Validation error creating candidate: {e}")
        return error_response("Validation error", 400, e.errors())
    
    except Exception as e:
        logger.error(f"Error creating candidate: {e}", exc_info=True)
        return error_response(f"Failed to create candidate: {str(e)}", 500)


@candidate_bp.route('/<int:candidate_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_candidate(candidate_id: int):
    """
    Get a candidate by ID
    
    Returns: CandidateResponseSchema
    """
    try:
        tenant_id = g.tenant_id
        
        candidate = candidate_service.get_candidate(candidate_id, tenant_id)
        
        if not candidate:
            return error_response("Candidate not found", 404)
        
        logger.info(f"[GET] Candidate {candidate_id} - work_experience count: {len(candidate.work_experience or [])}")
        logger.info(f"[GET] Candidate {candidate_id} - education count: {len(candidate.education or [])}")
        
        response = CandidateResponseSchema.model_validate(candidate)
        response_dict = response.model_dump()
        
        logger.info(f"[GET] Response - work_experience count: {len(response_dict.get('work_experience', []))}")
        logger.info(f"[GET] Response - education count: {len(response_dict.get('education', []))}")
        
        return jsonify(response_dict), 200
    except Exception as e:
        logger.error(f"Error getting candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to get candidate: {str(e)}", 500)

@candidate_bp.route('/<int:candidate_id>/resume-url', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_candidate_resume_url(candidate_id: int):
        """
        Generate a signed URL for the candidate's resume if stored in GCS.

        Optional query param: ttl (seconds) to override default expiry.
        """
        try:
            tenant_id = g.tenant_id
            # Ensure candidate accessible
            candidate = candidate_service.get_candidate(candidate_id, tenant_id)
            if not candidate:
                return error_response("Candidate not found", 404)

            # Get primary resume for URL generation
            primary_resume = candidate.primary_resume
            if not primary_resume or not primary_resume.file_key or primary_resume.storage_backend != 'gcs':
                return error_response("No resume available for signed URL", 404)

            # Optional TTL
            ttl = request.args.get('ttl')
            ttl_seconds = int(ttl) if ttl else None
            from app.services.file_storage import FileStorageService
            fs = FileStorageService()
            url, err = fs.generate_signed_url(primary_resume.file_key, expiry_seconds=ttl_seconds) if ttl_seconds else fs.generate_signed_url(primary_resume.file_key)
            if err or not url:
                return error_response(f"Failed to generate signed URL: {err or 'unknown error'}", 500)

            return jsonify({"signed_url": url}), 200

        except Exception as e:
            logger.error(f"Error generating resume signed URL for candidate {candidate_id}: {e}", exc_info=True)
            return error_response(f"Failed to generate signed URL: {str(e)}", 500)
    
    


@candidate_bp.route('/<int:candidate_id>', methods=['PUT'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def update_candidate(candidate_id: int):
    """
    Update a candidate
    
    Request Body: CandidateUpdateSchema
    Returns: CandidateResponseSchema
    """
    try:
        tenant_id = g.tenant_id
        
        # Validate request body
        data = CandidateUpdateSchema.model_validate(request.get_json())
        
        # Update candidate
        candidate = candidate_service.update_candidate(
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            data=data.model_dump(exclude_unset=True)
        )
        
        if not candidate:
            return error_response("Candidate not found", 404)
        
        response = CandidateResponseSchema.model_validate(candidate)
        return jsonify(response.model_dump()), 200
    
    except ValidationError as e:
        logger.warning(f"Validation error updating candidate {candidate_id}: {e}")
        return error_response("Validation error", 400, e.errors())
    
    except Exception as e:
        logger.error(f"Error updating candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to update candidate: {str(e)}", 500)


@candidate_bp.route('/<int:candidate_id>', methods=['DELETE'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.delete')
def delete_candidate(candidate_id: int):
    """
    Delete a candidate (idempotent - returns 200 even if already deleted)
    
    Returns: Success message
    """
    logger.info(f"DELETE route hit for candidate_id={candidate_id}, tenant_id={g.get('tenant_id', 'NO_TENANT')}")
    try:
        tenant_id = g.tenant_id
        
        success = candidate_service.delete_candidate(candidate_id, tenant_id)
        
        if not success:
            logger.warning(f"Candidate {candidate_id} not found (may be already deleted) in tenant {tenant_id}")
            # Return 200 for idempotent delete - don't fail if already deleted
            return jsonify({
                'message': 'Candidate deleted successfully',
                'candidate_id': candidate_id,
                'already_deleted': True
            }), 200
        
        logger.info(f"Candidate {candidate_id} deleted successfully from tenant {tenant_id}")
        return jsonify({
            'message': 'Candidate deleted successfully',
            'candidate_id': candidate_id
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to delete candidate: {str(e)}", 500)


@candidate_bp.route('', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def list_candidates():
    """
    List candidates with filters and pagination
    
    Query Params: status, skills[], search, page, per_page
    Returns: CandidateListResponseSchema
    """
    try:
        tenant_id = g.tenant_id
        
        # Parse query parameters
        status = request.args.get('status')
        skills = request.args.getlist('skills[]') or request.args.getlist('skills')
        search = request.args.get('search')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # List candidates
        result = candidate_service.list_candidates(
            tenant_id=tenant_id,
            status=status,
            skills=skills if skills else None,
            page=page,
            per_page=per_page
        )
        
        # Convert to response schema
        candidates_list = [
            CandidateListItemSchema.model_validate(c).model_dump()
            for c in result['candidates']
        ]
        
        response = CandidateListResponseSchema(
            candidates=candidates_list,
            total=result['total'],
            page=result['page'],
            per_page=result['per_page'],
            pages=result['pages']
        )
        
        return jsonify(response.model_dump()), 200
    
    except Exception as e:
        logger.error(f"Error listing candidates: {e}", exc_info=True)
        return error_response(f"Failed to list candidates: {str(e)}", 500)


# ==================== Review & Approve Endpoints ====================

@candidate_bp.route('/pending-review', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_pending_review():
    """
    Get candidates with status='pending_review' (waiting for HR review)
    
    Returns: List of candidates needing review
    """
    try:
        tenant_id = g.tenant_id
        
        from sqlalchemy import select, or_
        # Include both 'pending_review' and 'processing' so uploads are visible
        # even if the async parser hasn't finished or failed.
        stmt = select(Candidate).where(
            Candidate.tenant_id == tenant_id,
            or_(
                Candidate.status == 'pending_review',
                Candidate.status == 'processing',
            ),
        ).order_by(Candidate.created_at.desc())
        
        candidates = list(db.session.scalars(stmt))
        
        # Convert to response schema using to_dict() which handles None values properly
        candidate_list = [c.to_dict() for c in candidates]
        
        return jsonify({
            'candidates': candidate_list,
            'total': len(candidate_list)
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching pending review candidates: {e}", exc_info=True)
        return error_response(f"Failed to fetch pending candidates: {str(e)}", 500)


@candidate_bp.route('/<int:candidate_id>/review', methods=['PUT'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.update')
def review_candidate(candidate_id: int):
    """
    Review and edit parsed candidate data
    
    Request Body: Partial CandidateUpdateSchema (edited fields)
    Returns: Updated candidate
    """
    try:
        # Validate input
        try:
            data = CandidateUpdateSchema(**request.json)
        except ValidationError as e:
            return error_response(f"Invalid input: {str(e)}", 400)
        
        from app.services.candidate_service import CandidateService
        service = CandidateService()
        
        update_dict = data.model_dump(exclude_unset=True)
        candidate = service.update_candidate(candidate_id, g.tenant_id, update_dict)
        
        if not candidate:
            return error_response("Candidate not found", 404)
        
        logger.info(f"Candidate {candidate_id} reviewed and updated by user {g.user_id}")
        
        # Return updated candidate using to_dict() to handle None values
        return jsonify(candidate.to_dict()), 200
    
    except ValidationError as e:
        return error_response(f"Invalid input: {str(e)}", 400)
    except Exception as e:
        logger.error(f"Error reviewing candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to review candidate: {str(e)}", 500)


@candidate_bp.route('/<int:candidate_id>/approve', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.update')
def approve_candidate(candidate_id: int):
    """
    Approve candidate after review
    
    Changes status: 'pending_review' -> 'ready_for_assignment'
    Validates preferred_roles (required for job scraping)
    Normalizes preferred roles -> global_roles table
    Triggers job matching workflow
    
    Returns: Approved candidate
    """
    try:
        from app.services.candidate_service import CandidateService
        service = CandidateService()
        
        try:
            candidate = service.approve_candidate(
                candidate_id=candidate_id,
                approved_by_user_id=g.user_id,
                tenant_id=g.tenant_id
            )
            
            logger.info(f"Candidate {candidate_id} approved by user {g.user_id}, status: ready_for_assignment")
            return jsonify(candidate.to_dict()), 200
            
        except ValueError as e:
            error_msg = str(e)
            
            if "has already been approved" in error_msg:
                from sqlalchemy import select
                stmt = select(Candidate).where(
                    Candidate.id == candidate_id,
                    Candidate.tenant_id == g.tenant_id
                )
                candidate = db.session.scalar(stmt)
                
                if candidate and candidate.status == 'ready_for_assignment':
                    logger.info(f"Candidate {candidate_id} already approved with status '{candidate.status}'")
                    return jsonify({
                        "message": "Candidate already approved",
                        "candidate": candidate.to_dict(),
                        "already_approved": True
                    }), 200
            
            if "document(s) pending verification" in error_msg:
                return error_response(error_msg, 400)
            
            return error_response(error_msg, 400)
    
    except Exception as e:
        logger.error(f"Error approving candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to approve candidate: {str(e)}", 500)


# ==================== Resume Upload Endpoints ====================

@candidate_bp.route('/upload', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.create')
@require_permission('candidates.upload_resume')
def upload_and_create():
    """
    Upload resume and trigger async parsing (fast response)
    
    Form Data:
        - file: Resume file (PDF/DOCX)
    
    Returns: Candidate ID and processing status (1-2 seconds)
    """
    import uuid
    import os
    from datetime import datetime
    request_id = str(uuid.uuid4())[:8]
    
    try:
        # Guard against duplicate handler invocations within a single HTTP request
        # (can happen if the route is registered multiple times or middleware re-calls it)
        if getattr(g, "resume_upload_handled", False):
            logger.warning(f"[UPLOAD-{request_id}] Duplicate /upload call in same request; returning cached response")
            cached = getattr(g, "resume_upload_response", None)
            if cached is not None:
                return jsonify(cached), 200
        
        # Use tenant from portal auth / tenant middleware
        tenant_id = g.tenant_id
        
        logger.info(f"[UPLOAD-{request_id}] Starting async resume upload for tenant {tenant_id}")
        
        # Validate file
        if 'file' not in request.files:
            return error_response("No file provided", 400)
        
        file = request.files['file']
        
        if file.filename == '':
            return error_response("No file selected", 400)
        
        logger.info(f"[UPLOAD-{request_id}] File received: {file.filename}")
        
        # Upload file to storage (fast - 1-2s)
        from app.services.file_storage import FileStorageService
        storage = FileStorageService()
        
        upload_result = storage.upload_file(
            file=file,
            tenant_id=tenant_id,
            document_type='resume',
            candidate_id=None  # Will be updated after candidate creation
        )
        
        if not upload_result.get('success'):
            logger.error(f"[UPLOAD-{request_id}] File upload failed: {upload_result.get('error')}")
            return error_response(
                upload_result.get('error', 'Failed to upload file'),
                500
            )
        
        logger.info(f"[UPLOAD-{request_id}] File uploaded successfully: {upload_result['file_key']}")
        
        from app.services.candidate_service import CandidateService
        from app.services.candidate_resume_service import CandidateResumeService
        service = CandidateService()
        
        candidate_data = {
            "tenant_id": tenant_id,
            "first_name": "Processing",
            "last_name": "",
            "email": None,
            "phone": None,
            "status": "processing",
            "source": "resume_upload",
        }
        
        candidate = service.create_candidate(candidate_data, tenant_id)
        
        logger.info(f"[UPLOAD-{request_id}] Created candidate {candidate.id} with status='processing'")
        
        file_key = upload_result.get('file_key') or upload_result.get('file_path')
        resume, resume_document = CandidateResumeService.create_resume_with_document(
            candidate_id=candidate.id,
            tenant_id=tenant_id,
            file_key=file_key,
            storage_backend=upload_result.get('storage_backend', 'gcs'),
            original_filename=file.filename or 'resume',
            file_size=upload_result.get('file_size'),
            mime_type=upload_result.get('mime_type'),
            is_primary=True,
            uploaded_by_user_id=g.user_id,
        )
        
        logger.info(f"[UPLOAD-{request_id}] Created resume {resume.id} and document {resume_document.id} for candidate {candidate.id}")
        
        # Trigger async Inngest parsing workflow (fire and forget)
        try:
            from app.inngest import inngest_client
            import inngest
            
            # Use new candidate-resume/parse event with resume_id
            inngest_client.send_sync(
                inngest.Event(
                    name="candidate-resume/parse",
                    data={
                        "resume_id": resume.id,
                        "candidate_id": candidate.id,
                        "tenant_id": tenant_id
                    }
                )
            )
            logger.info(f"[UPLOAD-{request_id}] Triggered async parsing workflow for resume {resume.id}")
        except Exception as e:
            # Log but don't fail - candidate is created, parsing can be retried
            logger.warning(f"[UPLOAD-{request_id}] Failed to trigger parsing workflow: {str(e)}")
        
        # Return immediately (1-2 seconds total)
        from app.schemas.candidate_schema import UploadResumeResponseSchema
        response = UploadResumeResponseSchema(
            candidate_id=candidate.id,
            status='processing',
            message='Resume uploaded successfully. AI parsing in progress...',
            file_info={
                'filename': file.filename,
                'file_key': upload_result['file_key'],
                'file_size': upload_result.get('file_size'),
                'mime_type': upload_result.get('mime_type')
            }
        )
        
        # Cache response on request context so any duplicate invocations
        # for the same HTTP request can return the same payload without
        # creating additional candidates.
        g.resume_upload_handled = True
        g.resume_upload_response = response.model_dump()
        
        return jsonify(g.resume_upload_response), 200
    
    except Exception as e:
        logger.error(f"[UPLOAD-{request_id}] Error uploading resume: {e}", exc_info=True)
        return error_response(f"Failed to upload resume: {str(e)}", 500)


# NOTE: Removed duplicate `get_candidate` implementation in this file.
# The canonical `get_candidate` route is declared earlier; keeping a single route avoids
# conflicts during blueprint registration.


# NOTE: Duplicate `get_candidate_resume_url` implementation removed.
# The canonical `get_candidate_resume_url` route is declared earlier in this file.

# ==================== Statistics Endpoint ====================

@candidate_bp.route('/stats', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('reports.view')
def get_stats():
    """
    Get candidate statistics for tenant
    
    Returns: CandidateStatsSchema
    """
    try:
        tenant_id = g.tenant_id
        
        from app import db
        from app.models.candidate import Candidate
        from sqlalchemy import select, func
        from datetime import datetime, timedelta
        
        # Total candidates
        total = db.session.scalar(
            select(func.count()).select_from(Candidate).where(Candidate.tenant_id == tenant_id)
        )
        
        # By status
        by_status_query = select(
            Candidate.status,
            func.count(Candidate.id)
        ).where(
            Candidate.tenant_id == tenant_id
        ).group_by(Candidate.status)
        
        by_status = {}
        for status, count in db.session.execute(by_status_query):
            by_status[status] = count
        
        # Recent uploads (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent = db.session.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.resume_uploaded_at >= seven_days_ago
            )
        ) or 0
        
        response = CandidateStatsSchema(
            total_candidates=total or 0,
            by_status=by_status,
            recent_uploads=recent
        )
        
        return jsonify(response.model_dump()), 200
    
    except Exception as e:
        logger.error(f"Error getting candidate stats: {e}", exc_info=True)
        return error_response(f"Failed to get statistics: {str(e)}", 500)


# ==================== Health Check ====================

@candidate_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'candidate',
        'message': 'Candidate service is running'
    }), 200
"""
Add these two new endpoints to candidate_routes.py at the end of the file
"""

# ==================== Role Preferences Endpoints ====================

@candidate_bp.route('/<int:candidate_id>/preferred-roles', methods=['PUT'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def update_preferred_roles(candidate_id: int):
    """
    Update candidate's preferred roles.
    
    This endpoint:
    1. Updates the preferred_roles array on the candidate
    2. Triggers async workflow for AI Role Normalization
    3. Workflow will link candidate to GlobalRole for queue-based job matching
    
    Request Body:
        {
            "preferred_roles": ["Software Engineer", "Tech Lead", "Solutions Architect"]
        }
    
    Returns: Updated candidate (normalization happens in background)
    Permissions: candidates.edit
    """
    try:
        tenant_id = g.tenant_id
        data = request.get_json()
        
        if not data or 'preferred_roles' not in data:
            return error_response("preferred_roles is required", 400)
        
        preferred_roles = data['preferred_roles']
        
        # Validate that it's a list
        if not isinstance(preferred_roles, list):
            return error_response("preferred_roles must be an array", 400)
        
        # Limit to 10 roles max
        if len(preferred_roles) > 10:
            return error_response("Maximum 10 preferred roles allowed", 400)
        
        preferred_roles = [r.strip() for r in preferred_roles if r and r.strip()]
        
        from app.services.candidate_service import CandidateService
        service = CandidateService()
        
        candidate = service.update_candidate(
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            data={"preferred_roles": preferred_roles}
        )
        
        if not candidate:
            return error_response("Candidate not found", 404)
        
        logger.info(f"Updated preferred roles for candidate {candidate_id}: {len(preferred_roles)} roles")
        
        # Trigger async workflow for role normalization
        if preferred_roles:
            try:
                import inngest
                from app.inngest import inngest_client
                import hashlib
                
                # Create a unique key based on candidate_id and roles
                roles_hash = hashlib.md5(','.join(sorted(preferred_roles)).encode()).hexdigest()[:8]
                
                logger.info(f"[PREFERRED-ROLES] Triggering normalization for candidate {candidate_id}, roles_hash={roles_hash}")
                
                inngest_client.send_sync(
                    inngest.Event(
                        name="role/normalize-candidate",
                        data={
                            "candidate_id": candidate_id,
                            "tenant_id": tenant_id,
                            "preferred_roles": preferred_roles,
                            "preferred_locations": candidate.preferred_locations or [],
                            "trigger_source": "profile_update",
                            "roles_hash": roles_hash
                        }
                    )
                )
                logger.info(f"[PREFERRED-ROLES] ✅ Workflow triggered for candidate {candidate_id}")
            except Exception as trigger_error:
                # Log but don't fail - workflow trigger is non-critical
                logger.warning(f"Failed to trigger role normalization workflow: {trigger_error}")
        
        return jsonify({
            'message': 'Preferred roles updated successfully. Normalization in progress.',
            'candidate': candidate.to_dict(),
            'normalization_status': 'pending' if preferred_roles else 'skipped'
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating preferred roles: {str(e)}", exc_info=True)
        return error_response(f"Failed to update preferred roles: {str(e)}", 500)


@candidate_bp.route('/<int:candidate_id>/suggest-roles', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def generate_role_suggestions(candidate_id: int):
    """
    Generate AI-powered role suggestions for candidate.
    
    Uses Gemini AI to analyze candidate profile and suggest top 5 roles.
    
    Returns: 
        {
            "message": "...",
            "suggested_roles": {
                "roles": [...],
                "generated_at": "...",
                "model_version": "..."
            }
        }
    
    Permissions: candidates.edit
    """
    try:
        tenant_id = g.tenant_id
        
        # Get candidate
        from app.models.candidate import Candidate
        candidate = db.session.get(Candidate, candidate_id)
        
        if not candidate or candidate.tenant_id != tenant_id:
            return error_response("Candidate not found", 404)
        
        # Validate candidate has sufficient data
        if not candidate.skills and not candidate.work_experience and not candidate.current_title:
            return error_response(
                "Candidate needs more profile data (skills, experience, or title) to generate suggestions",
                400
            )
        
        # Generate suggestions using AI service
        from app.services.role_suggestion_service import get_role_suggestion_service
        import asyncio
        
        role_service = get_role_suggestion_service()
        
        logger.info(f"Generating role suggestions for candidate {candidate_id}...")
        
        suggestions = asyncio.run(role_service.generate_suggestions(candidate))
        
        from app.services.candidate_service import CandidateService
        service = CandidateService()
        
        candidate = service.update_candidate(
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            data={"suggested_roles": suggestions}
        )
        
        if not candidate:
            return error_response("Candidate not found", 404)
        
        logger.info(f"Generated {len(suggestions.get('roles', []))} role suggestions for candidate {candidate_id}")
        
        return jsonify({
            'message': f"Successfully generated {len(suggestions.get('roles', []))} role suggestions",
            'suggested_roles': suggestions
        }), 200
        
    except ValueError as e:
        # Configuration errors
        logger.error(f"Configuration error: {str(e)}")
        return error_response(f"Configuration error: {str(e)}", 500)
        
    except Exception as e:
        # AI generation or other errors
        error_msg = str(e)
        logger.error(f"Error generating role suggestions: {error_msg}", exc_info=True)
        
        # Check if it's a timeout that exceeded retries
        if 'timeout' in error_msg.lower() or 'deadline' in error_msg.lower():
            return error_response(
                "AI service timed out after multiple retries. Please try again later.",
                503
            )
        
        return error_response(f"Failed to generate role suggestions: {error_msg}", 500)


# ==================== Job Access Endpoints (Scrape Queue Mode) ====================

@candidate_bp.route('/<int:candidate_id>/jobs', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_candidate_jobs(candidate_id: int):
    """
    Get jobs for candidate's preferred roles WITHOUT scoring.
    
    In scrape queue mode, jobs are scraped once per role and made available
    to ALL candidates with that role. This endpoint returns all jobs associated
    with the candidate's global roles.
    
    GET /api/candidates/:id/jobs?page=1&per_page=50
    
    Query params:
    - page: Page number (default 1)
    - per_page: Jobs per page (default 50, max 100)
    - platform: Filter by job platform (optional)
    - location: Filter by location (optional)
    
    Permissions: candidates.view
    
    Returns all jobs for candidate's preferred roles without calculating scores.
    Use /api/candidates/:id/job-matches for scored results.
    """
    from sqlalchemy import select
    from app.models.candidate import Candidate
    from app.models.candidate_global_role import CandidateGlobalRole
    from app.models.job_posting import JobPosting
    from app.models.role_job_mapping import RoleJobMapping
    
    try:
        tenant_id = g.tenant_id
        
        # Verify candidate exists and belongs to tenant
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return error_response(f"Candidate {candidate_id} not found", 404)
        
        if candidate.tenant_id != tenant_id:
            return error_response("Access denied", 403)
        
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        platform = request.args.get('platform')
        location = request.args.get('location')
        
        # Validate parameters
        if per_page < 1 or per_page > 100:
            return error_response("per_page must be between 1 and 100")
        if page < 1:
            return error_response("page must be >= 1")
        
        # Get candidate's global roles
        global_role_query = select(CandidateGlobalRole.global_role_id).where(
            CandidateGlobalRole.candidate_id == candidate_id
        )
        global_role_ids = [row[0] for row in db.session.execute(global_role_query).all()]
        
        if not global_role_ids:
            # No assigned roles - return empty result
            return jsonify({
                'candidate_id': candidate_id,
                'preferred_roles': candidate.preferred_roles or [],
                'total_jobs': 0,
                'jobs': [],
                'page': page,
                'per_page': per_page,
                'message': 'No global roles assigned to this candidate'
            }), 200
        
        # Get all job IDs mapped to these roles
        job_mapping_query = select(RoleJobMapping.job_posting_id).where(
            RoleJobMapping.global_role_id.in_(global_role_ids)
        ).distinct()
        job_ids = [row[0] for row in db.session.execute(job_mapping_query).all()]
        
        if not job_ids:
            return jsonify({
                'candidate_id': candidate_id,
                'preferred_roles': candidate.preferred_roles or [],
                'total_jobs': 0,
                'jobs': [],
                'page': page,
                'per_page': per_page,
                'message': 'No jobs found for assigned roles'
            }), 200
        
        # Build job query
        from sqlalchemy import func
        count_query = select(func.count(JobPosting.id)).where(
            JobPosting.id.in_(job_ids),
            JobPosting.status == 'ACTIVE'
        )
        
        if platform:
            count_query = count_query.where(JobPosting.platform == platform)
        if location:
            count_query = count_query.where(JobPosting.location.ilike(f"%{location}%"))
        
        total_jobs = db.session.execute(count_query).scalar()
        
        # Fetch jobs
        job_query = select(JobPosting).where(
            JobPosting.id.in_(job_ids),
            JobPosting.status == 'ACTIVE'
        )
        
        if platform:
            job_query = job_query.where(JobPosting.platform == platform)
        if location:
            job_query = job_query.where(JobPosting.location.ilike(f"%{location}%"))
        
        offset = (page - 1) * per_page
        job_query = job_query.order_by(JobPosting.posted_date.desc().nullslast()).offset(offset).limit(per_page)
        
        jobs = db.session.execute(job_query).scalars().all()
        
        # Get role names for response
        from app.models.global_role import GlobalRole
        role_names = []
        for role_id in global_role_ids:
            role = db.session.get(GlobalRole, role_id)
            if role:
                role_names.append(role.name)
        
        return jsonify({
            'candidate_id': candidate_id,
            'preferred_roles': role_names,
            'total_jobs': total_jobs,
            'jobs': [
                {
                    'id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'location': job.location,
                    'salary_range': job.salary_range,
                    'salary_min': job.salary_min,
                    'salary_max': job.salary_max,
                    'posted_date': job.posted_date.isoformat() if job.posted_date else None,
                    'is_remote': job.is_remote,
                    'job_url': job.job_url,
                    'platform': job.platform,
                    'skills': job.skills or []
                }
                for job in jobs
            ],
            'page': page,
            'per_page': per_page,
            'total_pages': (total_jobs + per_page - 1) // per_page if total_jobs > 0 else 0
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching jobs for candidate {candidate_id}: {str(e)}")
        return error_response("Failed to fetch jobs", 500)


@candidate_bp.route('/<int:candidate_id>/job-matches', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_candidate_job_matches(candidate_id: int):
    """
    Get matched jobs for candidate WITH scoring calculated on-the-fly.
    
    This endpoint calculates match scores between the candidate and jobs
    associated with their global roles. Scores are computed dynamically.
    
    GET /api/candidates/:id/job-matches?min_score=0&sort_by=created_at&page=1&per_page=50
    
    Query params:
    - min_score: Minimum match score filter (default 0)
    - sort_by: Sort field (created_at, match_score, posted_date, default: created_at)
    - page: Page number (default 1)
    - per_page: Matches per page (default 50, max 100)
    
    Permissions: candidates.view
    
    Returns jobs with match scores calculated on-the-fly.
    """
    from sqlalchemy import select
    from app.models.candidate import Candidate
    from app.models.candidate_global_role import CandidateGlobalRole
    from app.models.job_posting import JobPosting
    from app.models.role_job_mapping import RoleJobMapping
    from app.services.job_matching_service import JobMatchingService
    
    try:
        tenant_id = g.tenant_id
        
        # Verify candidate exists and belongs to tenant
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return error_response(f"Candidate {candidate_id} not found", 404)
        
        if candidate.tenant_id != tenant_id:
            return error_response("Access denied", 403)
        
        # Parse query parameters
        min_score = request.args.get('min_score', 0, type=float)
        sort_by = request.args.get('sort_by', 'created_at')  # Default: latest first
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Validate parameters
        if per_page < 1 or per_page > 100:
            return error_response("per_page must be between 1 and 100")
        if page < 1:
            return error_response("page must be >= 1")
        
        # Get candidate's global roles
        global_role_query = select(CandidateGlobalRole.global_role_id).where(
            CandidateGlobalRole.candidate_id == candidate_id
        )
        global_role_ids = [row[0] for row in db.session.execute(global_role_query).all()]
        
        if not global_role_ids:
            return jsonify({
                'candidate_id': candidate_id,
                'total_matches': 0,
                'matches': [],
                'page': page,
                'per_page': per_page,
                'message': 'No global roles assigned to this candidate'
            }), 200
        
        # Get all job IDs mapped to these roles
        job_mapping_query = select(RoleJobMapping.job_posting_id).where(
            RoleJobMapping.global_role_id.in_(global_role_ids)
        ).distinct()
        job_ids = [row[0] for row in db.session.execute(job_mapping_query).all()]
        
        if not job_ids:
            return jsonify({
                'candidate_id': candidate_id,
                'total_matches': 0,
                'matches': [],
                'page': page,
                'per_page': per_page,
                'message': 'No jobs found for assigned roles'
            }), 200
        
        # Initialize unified scoring service
        from app.services.unified_scorer_service import UnifiedScorerService
        service = UnifiedScorerService()
        
        # Calculate scores for all jobs (we need to score all to filter/sort properly)
        # Fetch jobs
        job_query = select(JobPosting).where(
            JobPosting.id.in_(job_ids),
            JobPosting.status == 'ACTIVE'
        )
        jobs = db.session.execute(job_query).scalars().all()
        
        # Calculate match scores
        scored_matches = []
        for job in jobs:
            try:
                match_result = service.calculate_score(candidate, job)
                overall_score = match_result.overall_score
                
                # Apply min_score filter
                if overall_score >= min_score:
                    scored_matches.append({
                        'job': job,
                        'match_result': match_result
                    })
            except Exception as e:
                logger.warning(f"Failed to calculate score for job {job.id}: {e}")
                continue
        
        # Sort matches
        if sort_by == 'created_at':
            scored_matches.sort(key=lambda x: x['job'].created_at or datetime.min, reverse=True)
        elif sort_by == 'match_score':
            scored_matches.sort(key=lambda x: x['match_result'].overall_score, reverse=True)
        elif sort_by == 'posted_date':
            scored_matches.sort(key=lambda x: x['job'].posted_date or datetime.min, reverse=True)
        else:
            # Default: sort by created_at (latest first)
            scored_matches.sort(key=lambda x: x['job'].created_at or datetime.min, reverse=True)
        
        # Total count (after filtering)
        total_matches = len(scored_matches)
        
        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_matches = scored_matches[start:end]
        
        return jsonify({
            'candidate_id': candidate_id,
            'total_matches': total_matches,
            'matches': [
                {
                    'job': {
                        'id': m['job'].id,
                        'title': m['job'].title,
                        'company': m['job'].company,
                        'location': m['job'].location,
                        'salary_range': m['job'].salary_range,
                        'salary_min': m['job'].salary_min,
                        'salary_max': m['job'].salary_max,
                        'skills': m['job'].skills or [],
                        'job_url': m['job'].job_url,
                        'platform': m['job'].platform,
                        'posted_date': m['job'].posted_date.isoformat() if m['job'].posted_date else None,
                        'created_at': m['job'].created_at.isoformat() if m['job'].created_at else None
                    },
                    'match_score': round(m['match_result'].overall_score, 2),
                    'match_grade': m['match_result'].match_grade,
                    'skill_match_score': round(m['match_result'].skill_score, 2),
                    'keyword_match_score': None,  # DEPRECATED - no longer used
                    'experience_match_score': round(m['match_result'].experience_score, 2),
                    'semantic_similarity': round(m['match_result'].semantic_score, 2),
                    'matched_skills': m['match_result'].matched_skills,
                    'missing_skills': m['match_result'].missing_skills,
                    'matched_keywords': None,  # DEPRECATED - no longer used
                    'missing_keywords': None  # DEPRECATED - no longer used
                }
                for m in paginated_matches
            ],
            'page': page,
            'per_page': per_page,
            'total_pages': (total_matches + per_page - 1) // per_page if total_matches > 0 else 0
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching job matches for candidate {candidate_id}: {str(e)}")
        return error_response("Failed to fetch job matches", 500)


# ==================== Polished Resume Endpoints ====================

@candidate_bp.route('/<int:candidate_id>/polished-resume', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_polished_resume(candidate_id: int):
    """
    Get the polished resume data for a candidate.
    
    Returns the AI-polished markdown resume with metadata.
    
    Returns:
        {
            "has_polished_resume": true,
            "polished_resume_data": {
                "markdown_content": "# John Doe\n...",
                "polished_at": "2026-01-02T10:30:00Z",
                "polished_by": "ai",
                "ai_model": "gemini-2.5-flash",
                "version": 1,
                "last_edited_at": null,
                "last_edited_by_user_id": null
            }
        }
    
    Permissions: candidates.view
    """
    try:
        tenant_id = g.tenant_id
        
        candidate = candidate_service.get_candidate(candidate_id, tenant_id)
        
        if not candidate:
            return error_response("Candidate not found", 404)
        
        return jsonify({
            'has_polished_resume': candidate.has_polished_resume,
            'polished_resume_data': candidate.polished_resume_data,
            'candidate_id': candidate_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting polished resume for candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to get polished resume: {str(e)}", 500)


@candidate_bp.route('/<int:candidate_id>/polished-resume', methods=['PUT'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def update_polished_resume(candidate_id: int):
    """
    Update the polished resume markdown (recruiter edit).
    
    Allows recruiters to manually edit the AI-polished markdown.
    
    Request Body:
        {
            "markdown_content": "# Updated Resume\n..."
        }
    
    Returns: Updated polished resume data
    
    Permissions: candidates.edit
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        
        # Validate request
        data = request.get_json()
        if not data or 'markdown_content' not in data:
            return error_response("markdown_content is required", 400)
        
        markdown_content = data['markdown_content']
        
        if not markdown_content or not markdown_content.strip():
            return error_response("markdown_content cannot be empty", 400)
        
        # Get candidate
        from sqlalchemy import select
        stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id
        )
        candidate = db.session.scalar(stmt)
        
        if not candidate:
            return error_response("Candidate not found", 404)
        
        primary_resume = candidate.primary_resume
        if not primary_resume:
            return error_response("Candidate has no resume to update", 400)
        
        from app.services.candidate_resume_service import CandidateResumeService
        
        primary_resume = CandidateResumeService.update_polished_resume(
            resume_id=primary_resume.id,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            markdown_content=markdown_content.strip()
        )
        
        logger.info(f"Polished resume updated for candidate {candidate_id} (resume {primary_resume.id}) by user {user_id}")
        
        return jsonify({
            'message': 'Polished resume updated successfully',
            'polished_resume_data': candidate.polished_resume_data,
            'candidate_id': candidate_id
        }), 200
        
    except ValidationError as e:
        return error_response(f"Validation error: {str(e)}", 400)
    except Exception as e:
        logger.error(f"Error updating polished resume for candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to update polished resume: {str(e)}", 500)


@candidate_bp.route('/<int:candidate_id>/polished-resume/regenerate', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def regenerate_polished_resume(candidate_id: int):
    """
    Regenerate the polished resume using AI.
    
    Re-runs the AI polishing on the parsed_resume_data to create a fresh
    polished version. Useful if the parsed data was updated or the recruiter
    wants to reset to the AI-generated version.
    
    Returns: Newly polished resume data
    
    Permissions: candidates.edit
    """
    try:
        tenant_id = g.tenant_id
        
        # Get candidate
        from sqlalchemy import select
        stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id
        )
        candidate = db.session.scalar(stmt)
        
        if not candidate:
            return error_response("Candidate not found", 404)
        
        primary_resume = candidate.primary_resume
        if not primary_resume:
            return error_response("Candidate has no resume to polish", 400)
        
        candidate_name = candidate.full_name or f"{candidate.first_name} {candidate.last_name}".strip()
        
        from app.services.candidate_resume_service import CandidateResumeService
        
        try:
            primary_resume = CandidateResumeService.regenerate_polished_resume(
                resume_id=primary_resume.id,
                candidate_id=candidate_id,
                tenant_id=tenant_id,
                candidate_name=candidate_name
            )
        except ValueError as e:
            return error_response(str(e), 400)
        except Exception as polish_error:
            logger.error(f"AI polishing failed for candidate {candidate_id}: {polish_error}")
            return error_response(f"AI polishing failed: {str(polish_error)}", 500)
        
        logger.info(f"Polished resume regenerated for candidate {candidate_id} (resume {primary_resume.id})")
        
        return jsonify({
            'message': 'Polished resume regenerated successfully',
            'polished_resume_data': candidate.polished_resume_data,
            'candidate_id': candidate_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error regenerating polished resume for candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to regenerate polished resume: {str(e)}", 500)

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
        
        # Create candidate using service
        from app import db
        from app.models.candidate import Candidate
        
        candidate = Candidate(
            tenant_id=tenant_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            full_name=data.full_name or f"{data.first_name} {data.last_name}",
            location=data.location,
            linkedin_url=data.linkedin_url,
            portfolio_url=data.portfolio_url,
            current_title=data.current_title,
            total_experience_years=data.total_experience_years,
            notice_period=data.notice_period,
            expected_salary=data.expected_salary,
            professional_summary=data.professional_summary,
            preferred_locations=data.preferred_locations or [],
            skills=data.skills or [],
            certifications=data.certifications or [],
            languages=data.languages or [],
            education=data.education or [],
            work_experience=data.work_experience or [],
            status=data.status,
            source=data.source,
        )
        
        db.session.add(candidate)
        db.session.commit()
        
        # Return response
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
        
        from sqlalchemy import select
        stmt = select(Candidate).where(
            Candidate.tenant_id == tenant_id,
            Candidate.status == 'pending_review'
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
        
        # Validate input
        try:
            data = CandidateUpdateSchema(**request.json)
        except ValidationError as e:
            return error_response(f"Invalid input: {str(e)}", 400)
        
        # Update candidate with reviewed data
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if hasattr(candidate, key):
                setattr(candidate, key, value)
        
        db.session.commit()
        
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
    
    Changes status: 'pending_review' -> 'onboarded'
    Triggers job matching workflow
    After job matching -> status becomes 'ready_for_assignment'
    
    Returns: Approved candidate
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
        
        # Make endpoint idempotent - if already approved, return success
        if candidate.status in ['onboarded', 'ready_for_assignment']:
            logger.info(f"Candidate {candidate_id} already approved with status '{candidate.status}'")
            return jsonify({
                "message": "Candidate already approved",
                "candidate": candidate.to_dict(),
                "already_approved": True
            }), 200
        
        if candidate.status != 'pending_review':
            return error_response(
                f"Cannot approve candidate with status '{candidate.status}'. " 
                "Only candidates with status 'pending_review' can be approved.",
                400
            )
        
        # Update status to 'onboarded'
        candidate.status = 'onboarded'
        candidate.onboarding_status = 'PENDING_ASSIGNMENT'  # For assignment workflow
        db.session.commit()
        
        logger.info(f"Candidate {candidate_id} approved by user {g.user_id}, status: onboarded")
        
        # Trigger job matching workflow
        try:
            from app.inngest import inngest_client
            import inngest
            
            inngest_client.send_sync(
                inngest.Event(
                    name="job-match/generate-candidate",
                    data={
                        "candidate_id": candidate.id,
                        "tenant_id": tenant_id,
                        "min_score": 50.0,
                        "trigger": "onboarding_approval"
                    }
                )
            )
            logger.info(f"Triggered job matching for approved candidate {candidate_id}")
        except Exception as e:
            # Log but don't fail
            logger.warning(f"Failed to trigger job matching for candidate {candidate_id}: {str(e)}")
        
        # Return approved candidate using to_dict() to handle None values
        return jsonify(candidate.to_dict()), 200
    
    except Exception as e:
        logger.error(f"Error approving candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to approve candidate: {str(e)}", 500)


# ==================== Resume Upload Endpoints ====================

@candidate_bp.route('/upload', methods=['POST'])
# @require_portal_auth
# @with_tenant_context
# @require_permission('candidates.create')
# @require_permission('candidates.upload_resume')
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
        # tenant_id = g.tenant_id
        tenant_id = 2 # Hardcoded for testing
        
        logger.info(f"[UPLOAD-{request_id}] Starting async resume upload for tenant {tenant_id}")
        
        # Validate file
        if 'file' not in request.files:
            return error_response("No file provided", 400)
        
        file = request.files['file']
        
        if file.filename == '':
            return error_response("No file selected", 400)
        
        logger.info(f"[UPLOAD-{request_id}] File received: {file.filename}")
        
        # Upload file to storage (fast - 1-2s)
        from app.services.file_storage import LegacyResumeStorageService
        storage = LegacyResumeStorageService()
        
        upload_result = storage.upload_resume(
            file=file,
            tenant_id=tenant_id,
            candidate_id=None  # Will be updated after candidate creation
        )
        
        if not upload_result.get('success'):
            logger.error(f"[UPLOAD-{request_id}] File upload failed: {upload_result.get('error')}")
            return error_response(
                upload_result.get('error', 'Failed to upload file'),
                500
            )
        
        logger.info(f"[UPLOAD-{request_id}] File uploaded successfully: {upload_result['file_path']}")
        
        # Create candidate with minimal data and status='processing'
        from app.models.candidate import Candidate
        candidate = Candidate(
            tenant_id=tenant_id,
            first_name="Processing",  # Temporary, will be updated by AI
            last_name="",
            email=None,
            phone=None,
            status='processing',  # NEW: Processing status
            source='resume_upload',
            resume_file_path=upload_result['file_path'],
            resume_uploaded_at=datetime.utcnow()
        )
        
        db.session.add(candidate)
        db.session.commit()
        
        logger.info(f"[UPLOAD-{request_id}] Created candidate {candidate.id} with status='processing'")
        
        # Trigger async Inngest parsing workflow (fire and forget)
        try:
            from app.inngest import inngest_client
            import inngest
            
            inngest_client.send_sync(
                inngest.Event(
                    name="candidate/parse-resume",
                    data={
                        "candidate_id": candidate.id,
                        "tenant_id": tenant_id
                    }
                )
            )
            logger.info(f"[UPLOAD-{request_id}] Triggered async parsing workflow for candidate {candidate.id}")
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
                'file_path': upload_result['file_path'],
                'file_size': upload_result.get('file_size'),
                'mime_type': upload_result.get('mime_type')
            }
        )
        
        return jsonify(response.model_dump()), 200
    
    except Exception as e:
        logger.error(f"[UPLOAD-{request_id}] Error uploading resume: {e}", exc_info=True)
        return error_response(f"Failed to upload resume: {str(e)}", 500)


@candidate_bp.route('/<int:candidate_id>/resume', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
@require_permission('candidates.upload_resume')
def upload_resume_for_candidate(candidate_id: int):
    """
    Upload resume for existing candidate
    
    Form Data:
        - file: Resume file (PDF/DOCX)
    
    Returns: UploadResumeResponseSchema
    """
    try:
        tenant_id = g.tenant_id
        
        # Validate file
        if 'file' not in request.files:
            return error_response("No file provided", 400)
        
        file = request.files['file']
        
        if file.filename == '':
            return error_response("No file selected", 400)
        
        # Upload and parse
        result = candidate_service.upload_and_parse_resume(
            file=file,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            auto_create=False
        )
        
        if result['status'] == 'error':
            return error_response(
                result.get('error', 'Failed to upload and parse resume'),
                500
            )
        
        # Trigger background job for embedding generation and job matching
        try:
            from app.inngest import inngest_client
            import inngest
            import threading
            
            def trigger_job_matching():
                try:
                    inngest_client.send_sync(
                        inngest.Event(
                            name="job-match/generate-candidate",
                            data={
                                "candidate_id": candidate_id,
                                "tenant_id": tenant_id,
                                "min_score": 50.0,
                                "trigger": "resume_upload"
                            }
                        )
                    )
                    logger.info(f"Triggered job matching workflow for candidate {candidate_id}")
                except Exception as e:
                    logger.warning(f"Failed to trigger job matching in thread: {str(e)}")
            
            # Run in background thread to not block response
            thread = threading.Thread(target=trigger_job_matching, daemon=True)
            thread.start()
            logger.info(f"Started background thread for job matching candidate {candidate_id}")
        except Exception as e:
            # Don't fail the upload if background job trigger fails
            logger.warning(f"Failed to start job matching thread for candidate {candidate_id}: {str(e)}")
        
        # Return response
        response = UploadResumeResponseSchema(
            candidate_id=result['candidate_id'],
            status='success',
            message='Resume uploaded and parsed successfully',
            file_info=result['file_info'],
            parsed_data=result['parsed_data'],
            extracted_metadata=result['extracted_metadata']
        )
        
        return jsonify(response.model_dump()), 200
    
    except Exception as e:
        logger.error(f"Error uploading resume for candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to upload resume: {str(e)}", 500)


@candidate_bp.route('/<int:candidate_id>/reparse', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def reparse_resume(candidate_id: int):
    """
    Re-parse existing resume file
    
    Returns: ReparseResumeResponseSchema
    """
    try:
        tenant_id = g.tenant_id
        
        # Reparse
        result = candidate_service.reparse_resume(candidate_id, tenant_id)
        
        response = ReparseResumeResponseSchema(
            candidate_id=result['candidate_id'],
            status='success',
            message='Resume re-parsed successfully',
            parsed_data=result['parsed_data'],
            extracted_metadata=result['extracted_metadata']
        )
        
        return jsonify(response.model_dump()), 200
    
    except ValueError as e:
        logger.warning(f"Error reparsing resume for candidate {candidate_id}: {e}")
        return error_response(str(e), 404)
    
    except Exception as e:
        logger.error(f"Error reparsing resume for candidate {candidate_id}: {e}", exc_info=True)
        return error_response(f"Failed to reparse resume: {str(e)}", 500)


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
    
    Request Body:
        {
            "preferred_roles": ["Software Engineer", "Tech Lead", "Solutions Architect"]
        }
    
    Returns: Updated candidate
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
        
        # Get candidate
        from app.models.candidate import Candidate
        candidate = db.session.get(Candidate, candidate_id)
        
        if not candidate or candidate.tenant_id != tenant_id:
            return error_response("Candidate not found", 404)
        
        # Update preferred roles
        candidate.preferred_roles = preferred_roles
        db.session.commit()
        
        logger.info(f"Updated preferred roles for candidate {candidate_id}: {len(preferred_roles)} roles")
        
        return jsonify({
            'message': 'Preferred roles updated successfully',
            'candidate': candidate.to_dict()
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
        
        # Run async function in sync context
        suggestions = asyncio.run(role_service.generate_suggestions(candidate))
        
        # Save to database
        candidate.suggested_roles = suggestions
        db.session.commit()
        
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

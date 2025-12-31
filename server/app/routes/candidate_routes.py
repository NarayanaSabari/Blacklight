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
        
        # NOTE: We persist both `resume_file_key` + `resume_storage_backend` and
        # the legacy `resume_file_path` for backward compatibility. This legacy
        # field will be removed in Phase 3 after migration verification.
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

            if not candidate.resume_file_key or candidate.resume_storage_backend != 'gcs':
                return error_response("No resume available for signed URL", 404)

            # Optional TTL
            ttl = request.args.get('ttl')
            ttl_seconds = int(ttl) if ttl else None
            from app.services.file_storage import FileStorageService
            fs = FileStorageService()
            url, err = fs.generate_signed_url(candidate.resume_file_key, expiry_seconds=ttl_seconds) if ttl_seconds else fs.generate_signed_url(candidate.resume_file_key)
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
    
    Changes status: 'pending_review' -> 'ready_for_assignment'
    Validates preferred_roles (required for job scraping)
    Normalizes preferred roles -> global_roles table
    Triggers job matching workflow
    
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
        if candidate.status == 'ready_for_assignment':
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
        
        # VALIDATION: Check preferred_roles is filled (required for job scraping)
        # Auto-fill from parsed_resume_data if empty (fallback for legacy/incomplete data)
        if not candidate.preferred_roles or len(candidate.preferred_roles) == 0:
            parsed_data = candidate.parsed_resume_data or {}
            if isinstance(parsed_data, dict) and parsed_data.get('preferred_roles'):
                candidate.preferred_roles = parsed_data['preferred_roles']
                logger.info(f"Auto-filled preferred_roles from parsed_resume_data for candidate {candidate_id}")
        
        # Still validate after fallback attempt
        if not candidate.preferred_roles or len(candidate.preferred_roles) == 0:
            return error_response(
                "Preferred roles are required for approval. "
                "Please add at least one preferred role for the candidate.",
                400
            )
        
        # VALIDATION: Check preferred_locations is filled (required for location-based job scraping)
        # Auto-fill from parsed_resume_data if empty (fallback for legacy/incomplete data)
        if not candidate.preferred_locations or len(candidate.preferred_locations) == 0:
            parsed_data = candidate.parsed_resume_data or {}
            if isinstance(parsed_data, dict) and parsed_data.get('preferred_locations'):
                candidate.preferred_locations = parsed_data['preferred_locations']
                logger.info(f"Auto-filled preferred_locations from parsed_resume_data for candidate {candidate_id}")
        
        # Still validate after fallback attempt
        if not candidate.preferred_locations or len(candidate.preferred_locations) == 0:
            return error_response(
                "Preferred locations are required for approval. "
                "Please add at least one preferred location for the candidate "
                "(e.g., 'New York, NY', 'Remote', 'Los Angeles, CA').",
                400
            )
        
        # Update status to 'ready_for_assignment'
        candidate.status = 'ready_for_assignment'
        candidate.onboarding_status = 'APPROVED'  # For tracking
        
        # Also update associated invitation status if exists
        from app.models.candidate_invitation import CandidateInvitation
        from sqlalchemy import select as sql_select
        invitation_stmt = sql_select(CandidateInvitation).where(
            CandidateInvitation.candidate_id == candidate_id,
            CandidateInvitation.tenant_id == tenant_id
        )
        invitation = db.session.scalar(invitation_stmt)
        
        if invitation and invitation.status == 'pending_review':
            invitation.status = 'approved'
            invitation.reviewed_by_id = g.user_id
            invitation.reviewed_at = datetime.utcnow()
            logger.info(f"Updated invitation {invitation.id} status to 'approved' for candidate {candidate_id}")
        
        # Move documents from invitation to candidate folder (GCS/local storage)
        if invitation:
            from app.services.document_service import DocumentService
            moved_count, move_error = DocumentService.move_documents_to_candidate(
                invitation_id=invitation.id,
                candidate_id=candidate_id,
                tenant_id=tenant_id
            )
            if move_error:
                logger.warning(f"Document move had issues: {move_error}")
            else:
                logger.info(f"Moved {moved_count} documents from invitation {invitation.id} to candidate {candidate_id}")
        
        db.session.commit()
        
        logger.info(f"Candidate {candidate_id} approved by user {g.user_id}, status: ready_for_assignment")
        
        # Send approval email to candidate via Inngest
        try:
            from app.inngest import inngest_client
            import inngest
            
            candidate_name = f"{candidate.first_name} {candidate.last_name}".strip() if candidate.first_name else "Candidate"
            
            # Build candidate data for email
            candidate_data = {
                "full_name": candidate.full_name or candidate_name,
                "email": candidate.email,
                "phone": candidate.phone,
                "current_title": candidate.current_title,
                "experience_years": candidate.total_experience_years,
                "skills": candidate.skills or [],
                "preferred_roles": candidate.preferred_roles or [],
            }
            
            inngest_client.send_sync(
                inngest.Event(
                    name="email/approval",
                    data={
                        "candidate_id": candidate.id,
                        "tenant_id": tenant_id,
                        "to_email": candidate.email,
                        "candidate_name": candidate_name,
                        "candidate_data": candidate_data,
                        "hr_edited_fields": []
                    }
                )
            )
            logger.info(f"Triggered approval email for candidate {candidate_id}")
        except Exception as e:
            logger.warning(f"Failed to send approval email for candidate {candidate_id}: {str(e)}")
        
        # Trigger Inngest workflows for role normalization and job matching
        try:
            from app.inngest import inngest_client
            import inngest
            
            # 1. Trigger role normalization workflow (async, visible in Inngest dashboard)
            if candidate.preferred_roles:
                logger.info(f"[APPROVAL-ROUTE] Triggering role normalization for candidate {candidate_id}")
                inngest_client.send_sync(
                    inngest.Event(
                        name="role/normalize-candidate",
                        data={
                            "candidate_id": candidate.id,
                            "tenant_id": tenant_id,
                            "preferred_roles": candidate.preferred_roles,
                            "preferred_locations": candidate.preferred_locations or [],
                            "trigger_source": "approval_route"
                        }
                    )
                )
                logger.info(f"[APPROVAL-ROUTE] ✅ Role normalization event sent for candidate {candidate_id}")
            
            # 2. Trigger job matching workflow (async)
            logger.info(f"[INNGEST] Triggering job matching for candidate {candidate_id}")
            inngest_client.send_sync(
                inngest.Event(
                    name="job-match/generate-candidate",
                    data={
                        "candidate_id": candidate.id,
                        "tenant_id": tenant_id,
                        "trigger_source": "candidate_approval",
                        "preferred_roles": candidate.preferred_roles or []
                    }
                )
            )
            logger.info(f"[INNGEST] ✅ Job matching event sent for candidate {candidate_id}")
            
        except Exception as e:
            # Log but don't fail
            logger.warning(f"Failed to trigger Inngest workflows for candidate {candidate_id}: {str(e)}")
        
        # Return approved candidate using to_dict() to handle None values
        return jsonify(candidate.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
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
            resume_file_key=upload_result.get('file_key') or upload_result.get('file_path'),
            resume_storage_backend=upload_result.get('storage_backend', 'local'),
            # Note: legacy `resume_file_path` and `resume_file_url` are deprecated; store only file_key + backend
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
        
        # Clean up the roles (remove empty strings)
        preferred_roles = [r.strip() for r in preferred_roles if r and r.strip()]
        
        # Get candidate
        from app.models.candidate import Candidate
        candidate = db.session.get(Candidate, candidate_id)
        
        if not candidate or candidate.tenant_id != tenant_id:
            return error_response("Candidate not found", 404)
        
        # Update preferred roles
        candidate.preferred_roles = preferred_roles
        db.session.commit()
        
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
            JobPosting.status == 'active'
        )
        
        if platform:
            count_query = count_query.where(JobPosting.platform == platform)
        if location:
            count_query = count_query.where(JobPosting.location.ilike(f"%{location}%"))
        
        total_jobs = db.session.execute(count_query).scalar()
        
        # Fetch jobs
        job_query = select(JobPosting).where(
            JobPosting.id.in_(job_ids),
            JobPosting.status == 'active'
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
    
    GET /api/candidates/:id/job-matches?min_score=0&sort_by=match_score&page=1&per_page=50
    
    Query params:
    - min_score: Minimum match score filter (default 0)
    - sort_by: Sort field (match_score, posted_date, default: match_score)
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
        sort_by = request.args.get('sort_by', 'match_score')
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
        
        # Initialize matching service
        service = JobMatchingService(tenant_id=tenant_id)
        
        # Calculate scores for all jobs (we need to score all to filter/sort properly)
        # Fetch jobs
        job_query = select(JobPosting).where(
            JobPosting.id.in_(job_ids),
            JobPosting.status == 'active'
        )
        jobs = db.session.execute(job_query).scalars().all()
        
        # Calculate match scores
        scored_matches = []
        for job in jobs:
            match_result = service.calculate_match_score(candidate, job)
            overall_score = match_result.get('overall_score', 0)
            
            # Apply min_score filter
            if overall_score >= min_score:
                scored_matches.append({
                    'job': job,
                    'match_result': match_result
                })
        
        # Sort matches
        if sort_by == 'match_score':
            scored_matches.sort(key=lambda x: x['match_result']['overall_score'], reverse=True)
        elif sort_by == 'posted_date':
            scored_matches.sort(key=lambda x: x['job'].posted_date or datetime.min, reverse=True)
        
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
                        'posted_date': m['job'].posted_date.isoformat() if m['job'].posted_date else None
                    },
                    'match_score': round(m['match_result']['overall_score'], 2),
                    'grade': m['match_result']['match_grade'],
                    'skill_match_score': round(m['match_result']['skill_match_score'], 2),
                    'experience_match_score': round(m['match_result']['experience_match_score'], 2),
                    'location_match_score': round(m['match_result']['location_match_score'], 2),
                    'salary_match_score': round(m['match_result']['salary_match_score'], 2),
                    'semantic_similarity': round(m['match_result']['semantic_similarity'], 2),
                    'matched_skills': m['match_result']['matched_skills'],
                    'missing_skills': m['match_result']['missing_skills']
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

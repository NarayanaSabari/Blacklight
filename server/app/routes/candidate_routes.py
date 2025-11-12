"""
Candidate routes for resume parsing and candidate management
"""
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.datastructures import FileStorage
from pydantic import ValidationError
import logging
from datetime import datetime

from app import db
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
    Delete a candidate
    
    Returns: Success message
    """
    try:
        tenant_id = g.tenant_id
        
        success = candidate_service.delete_candidate(candidate_id, tenant_id)
        
        if not success:
            return error_response("Candidate not found", 404)
        
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


# ==================== Resume Upload Endpoints ====================

@candidate_bp.route('/upload', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.create')
@require_permission('candidates.upload_resume')
def upload_and_create():
    """
    Upload resume and parse synchronously (returns parsed data)
    
    Form Data:
        - file: Resume file (PDF/DOCX)
    
    Returns: UploadResumeResponseSchema with parsed data
    """
    try:
        tenant_id = g.tenant_id
        
        logger.info(f"[UPLOAD] Starting resume upload for tenant {tenant_id}")
        
        # Validate file
        if 'file' not in request.files:
            return error_response("No file provided", 400)
        
        file = request.files['file']
        
        if file.filename == '':
            return error_response("No file selected", 400)
        
        logger.info(f"[UPLOAD] File received: {file.filename}")
        
        # Upload and parse synchronously
        result = candidate_service.upload_and_parse_resume(
            file=file,
            tenant_id=tenant_id,
            candidate_id=None,
            auto_create=True  # Create candidate with parsed data
        )
        
        if result['status'] == 'error':
            logger.error(f"[UPLOAD] Upload/parse failed: {result.get('error')}")
            return error_response(
                result.get('error', 'Failed to upload and parse resume'),
                500
            )
        
        logger.info(f"[UPLOAD] Successfully uploaded and parsed resume for candidate {result['candidate_id']}")
        
        # Return response with parsed data
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
        logger.error(f"Error uploading resume: {e}", exc_info=True)
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

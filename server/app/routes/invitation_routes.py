"""
Candidate Invitation Routes
Authenticated routes for HR and public routes for candidates
"""
from flask import Blueprint, request, jsonify, current_app, send_file
from pydantic import ValidationError
import os
import logging

from app import db, limiter
from app.middleware.portal_auth import require_portal_auth, require_permission
from app.services.invitation_service import InvitationService
from app.services.document_service import DocumentService
from app.services.email_service import EmailService
from app.schemas import (
    InvitationCreateSchema,
    InvitationResendSchema,
    InvitationSubmitSchema,
    InvitationReviewSchema,
    InvitationResponseSchema,
    InvitationDetailResponseSchema,
    InvitationListResponseSchema,
    InvitationAuditLogResponseSchema,
    DocumentUploadSchema,
    DocumentVerifySchema,
    DocumentResponseSchema,
    DocumentListResponseSchema,
    DocumentTypesConfigResponseSchema,
)

bp = Blueprint("invitations", __name__, url_prefix="/api/invitations")
logger = logging.getLogger(__name__)


def error_response(message: str, status: int = 400, details: dict = None):
    """Create a standardized error response."""
    return jsonify({
        "error": "Error",
        "message": message,
        "status": status,
        "details": details,
    }), status


# ============================================================================
# AUTHENTICATED ROUTES (HR/Recruiter)
# ============================================================================

@bp.route("", methods=["POST"])
@require_portal_auth
@require_permission('candidates.create')
def create_invitation():
    """
    Create a new candidate invitation.
    
    POST /api/invitations
    Headers: Authorization: Bearer <token>
    Body: {email, first_name, last_name, position, recruiter_notes, expiry_hours}
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        user_id = request.portal_user["user_id"]
        
        # Validate request
        data = InvitationCreateSchema.model_validate(request.get_json())
        
        # Create invitation (service handles duplicate checking and reuse logic)
        # If cancelled/expired/rejected/approved invitation exists, it will be reused
        invitation = InvitationService.create_invitation(
            tenant_id=tenant_id,
            email=data.email,
            invited_by_id=user_id,
            first_name=data.first_name,
            last_name=data.last_name,
            position=data.position,
            recruiter_notes=data.recruiter_notes,
            expiry_hours=data.expiry_hours
        )
        
        # Build response
        response = InvitationResponseSchema.model_validate({
            **invitation.to_dict(),
            "is_expired": invitation.is_expired,
            "is_valid": invitation.is_valid,
            "can_be_resent": invitation.can_be_resent,
        })
        
        return jsonify(response.model_dump()), 201
        
    except ValidationError as e:
        return error_response("Validation error", 400, e.errors())
    except ValueError as e:
        # Check if it's a duplicate invitation error
        if "already exists" in str(e):
            return error_response(str(e), 409)  # Conflict
        return error_response(str(e), 400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating invitation: {e}")
        return error_response("Internal server error", 500)


@bp.route("", methods=["GET"])
@require_portal_auth
@require_permission('candidates.view')
def list_invitations():
    """
    List invitations with pagination and filtering.
    
    GET /api/invitations?page=1&per_page=10&status=pending&email=john@example.com
    Headers: Authorization: Bearer <token>
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        
        # Get query parameters
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        status = request.args.get("status")  # Optional filter
        email = request.args.get("email")    # Optional filter
        
        # Get invitations
        invitations, total = InvitationService.list_invitations(
            tenant_id=tenant_id,
            status_filter=status,
            email_filter=email,
            page=page,
            per_page=per_page
        )
        
        # Calculate pagination
        pages = (total + per_page - 1) // per_page if total > 0 else 0
        
        # Build response
        items = []
        for inv in invitations:
            items.append(InvitationResponseSchema.model_validate({
                **inv.to_dict(),
                "is_expired": inv.is_expired,
                "is_valid": inv.is_valid,
                "can_be_resent": inv.can_be_resent,
            }).model_dump())
        
        response = InvitationListResponseSchema(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        current_app.logger.error(f"Error listing invitations: {e}")
        return error_response("Internal server error", 500)


@bp.route("/stats", methods=["GET"])
@require_portal_auth
@require_permission('reports.view')
def get_invitation_stats():
    """
    Get invitation statistics for the tenant.
    
    GET /api/invitations/stats
    Headers: Authorization: Bearer <token>
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        
        # Get stats efficiently from the service layer
        stats = InvitationService.get_invitation_stats(tenant_id=tenant_id)
        
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting invitation stats: {e}")
        return error_response("Internal server error", 500)


@bp.route("/<int:invitation_id>", methods=["GET"])
@require_portal_auth
@require_permission('candidates.view')
def get_invitation(invitation_id):
    """
    Get invitation details.
    
    GET /api/invitations/{id}
    Headers: Authorization: Bearer <token>
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        
        invitation = InvitationService.get_by_id(invitation_id, tenant_id)
        if not invitation:
            return error_response("Invitation not found", 404)
        
        # Build detailed response
        response = InvitationDetailResponseSchema.model_validate({
            **invitation.to_dict(include_sensitive=True),
            "is_expired": invitation.is_expired,
            "is_valid": invitation.is_valid,
            "can_be_resent": invitation.can_be_resent,
        })
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting invitation: {e}")
        return error_response("Internal server error", 500)


@bp.route("/<int:invitation_id>/resend", methods=["POST"])
@require_portal_auth
@require_permission('candidates.edit')
def resend_invitation(invitation_id):
    """
    Resend invitation with new token.
    
    POST /api/invitations/{id}/resend
    Headers: Authorization: Bearer <token>
    Body: {expiry_hours}
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        user_id = request.portal_user["user_id"]
        
        # Validate request (body is optional, defaults to 7 days)
        body = request.get_json(silent=True) or {}
        data = InvitationResendSchema.model_validate(body)
        
        # Resend invitation (service handles sending the email)
        invitation = InvitationService.resend_invitation(
            invitation_id=invitation_id,
            resent_by_id=user_id,
            expiry_hours=data.expiry_hours
        )
        
        # Build response
        response = InvitationResponseSchema.model_validate({
            **invitation.to_dict(),
            "is_expired": invitation.is_expired,
            "is_valid": invitation.is_valid,
            "can_be_resent": invitation.can_be_resent,
        })
        
        return jsonify(response.model_dump()), 200
        
    except ValidationError as e:
        return error_response("Validation error", 400, e.errors())
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error resending invitation: {e}")
        return error_response("Internal server error", 500)


@bp.route("/<int:invitation_id>/review", methods=["POST"])
@require_portal_auth
@require_permission('candidates.edit')
def review_invitation(invitation_id):
    """
    Approve or reject invitation submission.
    
    POST /api/invitations/{id}/review
    Headers: Authorization: Bearer <token>
    Body: {action: "approve"|"reject", notes, rejection_reason}
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        user_id = request.portal_user["user_id"]
        
        # Validate request
        data = InvitationReviewSchema.model_validate(request.get_json())
        
        if data.action == "approve":
            # Approve and create candidate (with optional HR edits)
            # Note: approve_invitation sends email via Inngest automatically
            candidate = InvitationService.approve_invitation(
                invitation_id=invitation_id,
                tenant_id=tenant_id,
                reviewed_by_id=user_id,
                notes=data.notes,
                edited_data=data.edited_data
            )
            
            return jsonify({
                "message": "Invitation approved and candidate created",
                "candidate_id": candidate.id,
                "invitation_id": invitation_id
            }), 200
            
        else:  # reject
            # Reject invitation
            # Note: reject_invitation sends email via Inngest automatically
            invitation = InvitationService.reject_invitation(
                invitation_id=invitation_id,
                tenant_id=tenant_id,
                reviewed_by_id=user_id,
                reason=data.rejection_reason,
                notes=data.notes
            )
            
            return jsonify({
                "message": "Invitation rejected",
                "invitation_id": invitation_id
            }), 200
        
    except ValidationError as e:
        return error_response("Validation error", 400, e.errors())
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reviewing invitation: {e}")
        return error_response("Internal server error", 500)


@bp.route("/<int:invitation_id>/cancel", methods=["POST"])
@require_portal_auth
@require_permission('candidates.edit')
def cancel_invitation(invitation_id):
    """
    Cancel a pending invitation.
    
    POST /api/invitations/{id}/cancel
    Headers: Authorization: Bearer <token>
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        user_id = request.portal_user["user_id"]
        
        invitation = InvitationService.cancel_invitation(
            invitation_id=invitation_id,
            tenant_id=tenant_id,
            cancelled_by_id=user_id
        )
        
        return jsonify({
            "message": "Invitation cancelled",
            "invitation_id": invitation_id
        }), 200
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling invitation: {e}")
        return error_response("Internal server error", 500)


@bp.route("/<int:invitation_id>/audit-logs", methods=["GET"])
@require_portal_auth
@require_permission('candidates.view')
def get_audit_logs(invitation_id):
    """
    Get audit trail for invitation.
    
    GET /api/invitations/{id}/audit-logs
    Headers: Authorization: Bearer <token>
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        
        logs = InvitationService.get_invitation_audit_trail(invitation_id)
        
        items = [
            InvitationAuditLogResponseSchema.model_validate(log.to_dict()).model_dump()
            for log in logs
        ]
        
        return jsonify({"items": items, "total": len(items)}), 200
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Error getting audit trail: {e}")
        return error_response("Internal server error", 500)


# ============================================================================
# PUBLIC ROUTES (Candidate)
# ============================================================================

@bp.route("/public/verify", methods=["GET"])
@limiter.limit("20/minute")
def verify_token():
    """
    Verify invitation token and get basic info.
    
    GET /api/invitations/public/verify?token=xxx
    """
    try:
        token = request.args.get("token")
        if not token:
            return error_response("Token is required", 400)
        
        invitation = InvitationService.get_by_token(token)
        if not invitation:
            return error_response("Invalid or expired invitation", 404)
        
        # Mark as opened
        InvitationService.mark_as_opened(
            token=token,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
        
        # Return basic info (no sensitive data)
        return jsonify({
            "id": invitation.id,
            "email": invitation.email,
            "first_name": invitation.first_name,
            "last_name": invitation.last_name,
            "position": invitation.position,
            "status": invitation.status,
            "expires_at": invitation.expires_at.isoformat(),
            "is_expired": invitation.is_expired,
            "is_valid": invitation.is_valid,
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error verifying token: {e}")
        return error_response("Internal server error", 500)


@bp.route("/public/submit", methods=["POST"])
@limiter.limit("10/minute")
def submit_invitation():
    """
    Submit invitation with candidate information.
    
    POST /api/invitations/public/submit?token=xxx
    Body: {first_name, last_name, email, phone, address, ...}
    """
    try:
        token = request.args.get("token")
        logger.info(f"[SUBMIT] Received submission request with token: {token}")
        
        if not token:
            logger.error("[SUBMIT] No token provided")
            return error_response("Token is required", 400)
        
        # Get request data
        request_data = request.get_json()
        logger.info(f"[SUBMIT] Request data keys: {list(request_data.keys()) if request_data else 'None'}")
        
        # Validate request
        data = InvitationSubmitSchema.model_validate(request_data)
        logger.info(f"[SUBMIT] Validation passed, submitting invitation")
        
        # Submit invitation
        invitation = InvitationService.submit_invitation(
            token=token,
            invitation_data=data.model_dump(),
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
        logger.info(f"[SUBMIT] Invitation {invitation.id} submitted successfully")
        
        # Send confirmation email to candidate
        EmailService.send_submission_confirmation(
            tenant_id=invitation.tenant_id,
            to_email=data.email,
            candidate_name=f"{data.first_name} {data.last_name}"
        )
        
        # TODO: Send notification to HR team
        # EmailService.send_hr_notification(...)
        
        return jsonify({
            "message": "Submission received successfully",
            "invitation_id": invitation.id
        }), 200
        
    except ValidationError as e:
        return error_response("Validation error", 400, e.errors())
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error submitting invitation: {e}")
        return error_response("Internal server error", 500)


@bp.route("/public/suggest-roles", methods=["POST"])
@limiter.limit("5/minute")
def suggest_roles_from_invitation_data():
    """
    Generate AI role suggestions from invitation data (before candidate creation).
    
    POST /api/invitations/public/suggest-roles
    Body: {
        token: str,
        skills: List[str],
        work_experience: List[dict],
        current_title: str,
        experience_years: int
    }
    
    Returns: {
        message: str,
        suggested_roles: {
            roles: [...],
            generated_at: str,
            model_version: str
        }
    }
    """
    try:
        # Get request data
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return error_response("token is required", 400)
        
        # Get invitation
        invitation = InvitationService.get_by_token(token)
        
        if not invitation:
            return error_response("Invalid invitation token", 404)
        
        # Build temporary candidate-like object for role suggestion service
        # Use a simple class to hold the data
        class TempCandidate:
            def __init__(self, invitation_data, form_data):
                self.id = None  # Temporary candidate has no real ID
                self.full_name = f"{invitation_data.first_name} {invitation_data.last_name}".strip() if invitation_data.first_name else "Candidate"
                self.first_name = invitation_data.first_name
                self.last_name = invitation_data.last_name
                self.current_title = form_data.get('current_title')
                self.total_experience_years = form_data.get('experience_years')
                self.location = None
                
                # Skills - ensure it's a list
                self.skills = form_data.get('skills', [])
                if not isinstance(self.skills, list):
                    self.skills = []
                
                # Work experience - ensure it's a list of dicts
                work_exp = form_data.get('work_experience', [])
                if isinstance(work_exp, list):
                    self.work_experience = work_exp
                else:
                    self.work_experience = []
                
                # Education - ensure it's a list of dicts  
                education = form_data.get('education', [])
                if isinstance(education, list):
                    self.education = education
                else:
                    self.education = []
                
                self.certifications = []
        
        temp_candidate = TempCandidate(invitation, data)
        
        # Debug: Log what we're sending to AI
        print(f"[DEBUG] TempCandidate data: skills={len(temp_candidate.skills)}, work_exp={len(temp_candidate.work_experience)}, edu={len(temp_candidate.education)}")
        
        # Generate suggestions using role suggestion service
        from app.services.role_suggestion_service import get_role_suggestion_service
        import asyncio
        
        role_service = get_role_suggestion_service()
        suggestions = asyncio.run(role_service.generate_suggestions(temp_candidate))
        
        return jsonify({
            'message': 'Role suggestions generated successfully',
            'suggested_roles': suggestions
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating role suggestions: {str(e)}", exc_info=True)
        return error_response(f"Failed to generate suggestions: {str(e)}", 500)


@bp.route("/public/documents", methods=["POST"])
@limiter.limit("10/minute")
def upload_document_public():
    """
    Upload document for invitation (public endpoint).
    
    POST /api/invitations/public/documents?token=xxx
    Content-Type: multipart/form-data
    Body: file, document_type, notes
    """
    try:
        token = request.args.get("token")
        logger.info(f"[DOC_UPLOAD] Received token from query params: {token} (type: {type(token).__name__})")
        
        if not token:
            return error_response("Token is required", 400)
        
        # Verify invitation
        logger.info(f"[DOC_UPLOAD] Calling get_by_token with: {token}")
        invitation = InvitationService.get_by_token(token)
        if not invitation:
            return error_response("Invalid or expired invitation", 404)
        
        # Mark as in progress (pass token, not ID)
        InvitationService.mark_as_in_progress(token)
        
        # Get file
        if 'file' not in request.files:
            return error_response("No file uploaded", 400)
        
        file = request.files['file']
        if file.filename == '':
            return error_response("No file selected", 400)
        
        # Get metadata
        document_type = request.form.get('document_type')
        notes = request.form.get('notes')
        
        if not document_type:
            return error_response("document_type is required", 400)
        
        # Validate metadata
        metadata_schema = DocumentUploadSchema(document_type=document_type, notes=notes)
        
        # Upload document
        document, error = DocumentService.upload_document(
            tenant_id=invitation.tenant_id,
            invitation_id=invitation.id,
            file=file,
            document_type=metadata_schema.document_type
        )
        
        if error:
            logger.error(f"[DOC_UPLOAD] Upload failed with error: {error}")
            return error_response(error, 400)
        
        if not document:
            logger.error("[DOC_UPLOAD] Upload returned no document and no error")
            return error_response("Document upload failed", 500)
        
        logger.info(f"[DOC_UPLOAD] Successfully uploaded document {document.id}")
        
        # Build response
        try:
            response = DocumentResponseSchema.model_validate(document.to_dict())
            return jsonify(response.model_dump()), 201
        except Exception as resp_error:
            logger.error(f"[DOC_UPLOAD] Response building failed: {resp_error}")
            # Return a simpler response if schema validation fails
            return jsonify({
                "id": document.id,
                "document_type": document.document_type,
                "file_name": document.file_name,
                "message": "Document uploaded successfully"
            }), 201
        
    except ValidationError as e:
        logger.error(f"[DOC_UPLOAD] Validation error: {e.errors()}")
        return error_response("Validation error", 400, e.errors())
    except ValueError as e:
        logger.error(f"[DOC_UPLOAD] ValueError: {str(e)}")
        return error_response(str(e), 400)
    except Exception as e:
        db.session.rollback()
        logger.error(f"[DOC_UPLOAD] Unexpected error: {e}", exc_info=True)
        return error_response("Internal server error", 500)


# ============================================================================
# DOCUMENT ROUTES (Authenticated)
# ============================================================================

@bp.route("/<int:invitation_id>/documents", methods=["GET"])
@require_portal_auth
@require_permission('candidates.view')
def list_invitation_documents(invitation_id):
    """
    List documents for invitation.
    
    GET /api/invitations/{id}/documents
    Headers: Authorization: Bearer <token>
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        
        documents = DocumentService.list_documents(
            tenant_id=tenant_id,
            invitation_id=invitation_id
        )
        
        items = [
            DocumentResponseSchema.model_validate({
                **doc.to_dict(),
                "file_size_mb": doc.file_size_mb,
                "file_extension": doc.file_extension,
            }).model_dump()
            for doc in documents
        ]
        
        response = DocumentListResponseSchema(items=items, total=len(items))
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        current_app.logger.error(f"Error listing documents: {e}")
        return error_response("Internal server error", 500)


@bp.route("/documents/<int:document_id>/verify", methods=["POST"])
@require_portal_auth
@require_permission('candidates.edit')
def verify_document(document_id):
    """
    Verify a document.
    
    POST /api/invitations/documents/{id}/verify
    Headers: Authorization: Bearer <token>
    Body: {is_verified, verification_notes}
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        user_id = request.portal_user["user_id"]
        
        # Validate request
        data = DocumentVerifySchema.model_validate(request.get_json())
        
        # Verify document
        document = DocumentService.verify_document(
            document_id=document_id,
            tenant_id=tenant_id,
            is_verified=data.is_verified,
            verification_notes=data.verification_notes,
            verified_by_id=user_id
        )
        
        # Build response
        response = DocumentResponseSchema.model_validate({
            **document.to_dict(),
            "file_size_mb": document.file_size_mb,
            "file_extension": document.file_extension,
        })
        
        return jsonify(response.model_dump()), 200
        
    except ValidationError as e:
        return error_response("Validation error", 400, e.errors())
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error verifying document: {e}")
        return error_response("Internal server error", 500)


@bp.route("/documents/config", methods=["GET"])
@require_portal_auth
@require_permission('candidates.view')
def get_document_config():
    """
    Get document types configuration for tenant.
    
    GET /api/invitations/documents/config
    Headers: Authorization: Bearer <token>
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        
        config = DocumentService.get_document_types_config(tenant_id)
        
        response = DocumentTypesConfigResponseSchema(document_types=config)
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting document config: {e}")
        return error_response("Internal server error", 500)

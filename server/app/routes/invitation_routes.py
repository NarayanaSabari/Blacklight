"""
Candidate Invitation Routes
Authenticated routes for HR and public routes for candidates
"""
from flask import Blueprint, request, jsonify, current_app, send_file
from pydantic import ValidationError
import os

from app import db
from app.middleware.portal_auth import require_portal_auth
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
        email = request.args.get("email")    # Optional filter (not yet implemented in service)
        
        # Get invitations
        invitations, total = InvitationService.list_invitations(
            tenant_id=tenant_id,
            status_filter=status,
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
def get_invitation_stats():
    """
    Get invitation statistics for the tenant.
    
    GET /api/invitations/stats
    Headers: Authorization: Bearer <token>
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        
        # Get all invitations for the tenant
        invitations, total = InvitationService.list_invitations(
            tenant_id=tenant_id,
            page=1,
            per_page=10000  # Get all for stats
        )
        
        # Calculate stats
        stats = {
            "total": total,
            "by_status": {
                "invited": 0,
                "opened": 0,
                "in_progress": 0,
                "submitted": 0,
                "approved": 0,
                "rejected": 0,
                "expired": 0
            }
        }
        
        for inv in invitations:
            if inv.status in stats["by_status"]:
                stats["by_status"][inv.status] += 1
            if inv.is_expired and inv.status not in ["approved", "rejected"]:
                stats["by_status"]["expired"] += 1
        
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting invitation stats: {e}")
        return error_response("Internal server error", 500)


@bp.route("/<int:invitation_id>", methods=["GET"])
@require_portal_auth
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
        
        # Resend invitation
        invitation = InvitationService.resend_invitation(
            invitation_id=invitation_id,
            resent_by_id=user_id,
            expiry_hours=data.expiry_hours
        )
        
        # Generate new onboarding URL
        frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
        onboarding_url = f"{frontend_url}/onboarding?token={invitation.token}"
        
        # Send email
        EmailService.send_invitation_email(
            tenant_id=tenant_id,
            to_email=invitation.email,
            candidate_name=f"{invitation.first_name} {invitation.last_name}" if invitation.first_name else None,
            onboarding_url=onboarding_url,
            expiry_date=invitation.expires_at.strftime("%B %d, %Y at %I:%M %p")
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
            # Approve and create candidate
            candidate = InvitationService.approve_invitation(
                invitation_id=invitation_id,
                tenant_id=tenant_id,
                reviewed_by_id=user_id,
                notes=data.notes
            )
            
            # Get updated invitation
            invitation = InvitationService.get_by_id(invitation_id, tenant_id)
            
            # Send approval email
            EmailService.send_approval_email(
                tenant_id=tenant_id,
                to_email=invitation.email,
                candidate_name=f"{candidate.first_name} {candidate.last_name}"
            )
            
            return jsonify({
                "message": "Invitation approved and candidate created",
                "candidate_id": candidate.id,
                "invitation_id": invitation_id
            }), 200
            
        else:  # reject
            # Reject invitation
            invitation = InvitationService.reject_invitation(
                invitation_id=invitation_id,
                tenant_id=tenant_id,
                reviewed_by_id=user_id,
                reason=data.rejection_reason,
                notes=data.notes
            )
            
            # Send rejection email
            EmailService.send_rejection_email(
                tenant_id=tenant_id,
                to_email=invitation.email,
                candidate_name=f"{invitation.first_name} {invitation.last_name}" if invitation.first_name else "there",
                reason=data.rejection_reason
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


@bp.route("/<int:invitation_id>/audit-trail", methods=["GET"])
@require_portal_auth
def get_audit_trail(invitation_id):
    """
    Get audit trail for invitation.
    
    GET /api/invitations/{id}/audit-trail
    Headers: Authorization: Bearer <token>
    """
    try:
        tenant_id = request.portal_user["tenant_id"]
        
        logs = InvitationService.get_invitation_audit_trail(invitation_id, tenant_id)
        
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
            invitation_id=invitation.id,
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
def submit_invitation():
    """
    Submit invitation with candidate information.
    
    POST /api/invitations/public/submit?token=xxx
    Body: {first_name, last_name, email, phone, address, ...}
    """
    try:
        token = request.args.get("token")
        if not token:
            return error_response("Token is required", 400)
        
        # Validate request
        data = InvitationSubmitSchema.model_validate(request.get_json())
        
        # Submit invitation
        invitation = InvitationService.submit_invitation(
            token=token,
            data=data.model_dump(),
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
        
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


@bp.route("/public/documents", methods=["POST"])
def upload_document_public():
    """
    Upload document for invitation (public endpoint).
    
    POST /api/invitations/public/documents?token=xxx
    Content-Type: multipart/form-data
    Body: file, document_type, notes
    """
    try:
        token = request.args.get("token")
        if not token:
            return error_response("Token is required", 400)
        
        # Verify invitation
        invitation = InvitationService.get_by_token(token)
        if not invitation:
            return error_response("Invalid or expired invitation", 404)
        
        # Mark as in progress
        InvitationService.mark_as_in_progress(invitation.id)
        
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
        upload_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
        document = DocumentService.upload_document(
            tenant_id=invitation.tenant_id,
            invitation_id=invitation.id,
            file=file,
            document_type=metadata_schema.document_type,
            notes=metadata_schema.notes,
            upload_dir=upload_dir
        )
        
        # Build response
        response = DocumentResponseSchema.model_validate({
            **document.to_dict(),
            "file_size_mb": document.file_size_mb,
            "file_extension": document.file_extension,
        })
        
        return jsonify(response.model_dump()), 201
        
    except ValidationError as e:
        return error_response("Validation error", 400, e.errors())
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading document: {e}")
        return error_response("Internal server error", 500)


# ============================================================================
# DOCUMENT ROUTES (Authenticated)
# ============================================================================

@bp.route("/<int:invitation_id>/documents", methods=["GET"])
@require_portal_auth
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

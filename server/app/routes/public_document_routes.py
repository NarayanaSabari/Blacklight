"""
Public Document Routes
Public API endpoints for candidate document upload during onboarding (token-based auth)
"""
from flask import Blueprint, request, jsonify
from werkzeug.datastructures import FileStorage
from datetime import datetime, timezone
import os

from app.services.document_service import DocumentService
from app.services.invitation_service import InvitationService
from app.schemas.document_schema import (
    DocumentResponse,
    ErrorResponse
)
from app import db

# Create Blueprint
public_document_bp = Blueprint('public_documents', __name__, url_prefix='/api/public/documents')


def validate_invitation_token(invitation_token: str):
    """
    Validate invitation token and return invitation details
    
    Args:
        invitation_token: The invitation token from request
    
    Returns:
        tuple: (invitation, error_response)
            - invitation: Invitation object if valid
            - error_response: Error tuple (dict, status_code) if invalid
    """
    if not invitation_token:
        return None, (jsonify(ErrorResponse(
            error="Authentication Failed",
            message="invitation_token is required",
            status=401
        ).model_dump()), 401)
    
    # Get invitation by token
    invitation = InvitationService.get_by_token(invitation_token)
    
    if not invitation:
        return None, (jsonify(ErrorResponse(
            error="Authentication Failed",
            message="Invalid invitation token",
            status=401
        ).model_dump()), 401)
    
    # Check if token is expired
    if invitation.expires_at < datetime.now(timezone.utc):
        return None, (jsonify(ErrorResponse(
            error="Token Expired",
            message="Invitation token has expired",
            status=401
        ).model_dump()), 401)
    
    # Check if invitation is still pending
    if invitation.status != 'pending':
        return None, (jsonify(ErrorResponse(
            error="Invitation Not Pending",
            message=f"Invitation status is '{invitation.status}'. Can only upload documents for pending invitations.",
            status=400
        ).model_dump()), 400)
    
    return invitation, None


@public_document_bp.route('/upload', methods=['POST'])
def upload_public_document():
    """
    Public endpoint for candidate document upload during onboarding
    
    Required: multipart/form-data with 'file' field
    Form fields:
        - file: The file to upload
        - invitation_token: Invitation token for authentication
        - document_type: Type of document (resume, id_proof, etc.)
    
    Returns:
        201: Document uploaded successfully
        400: Validation error or file missing
        401: Invalid or expired token
        413: File too large
        500: Server error
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify(ErrorResponse(
                error="File Missing",
                message="No file provided in request",
                status=400
            ).model_dump()), 400
        
        file: FileStorage = request.files['file']
        if not file or file.filename == '':
            return jsonify(ErrorResponse(
                error="File Missing",
                message="No file selected",
                status=400
            ).model_dump()), 400
        
        # Get form data
        invitation_token = request.form.get('invitation_token')
        document_type = request.form.get('document_type')
        
        if not document_type:
            return jsonify(ErrorResponse(
                error="Validation Error",
                message="document_type is required",
                status=400
            ).model_dump()), 400
        
        # Validate invitation token
        invitation, error_response = validate_invitation_token(invitation_token)
        if error_response:
            return error_response
        
        # Upload document (no uploaded_by_id for public uploads)
        document, error = DocumentService.upload_document(
            tenant_id=invitation.tenant_id,
            file=file,
            document_type=document_type,
            uploaded_by_id=None,  # Candidate self-upload
            candidate_id=None,
            invitation_id=invitation.id
        )
        
        if error:
            return jsonify(ErrorResponse(
                error="Upload Failed",
                message=error,
                status=400
            ).model_dump()), 400
        
        # 🆕 NEW: Parse resume if document_type is 'resume'
        if document_type == 'resume' and document:
            try:
                from app.services.resume_parser import ResumeParserService
                from app.utils.text_extractor import TextExtractor
                from app.services.skills_matcher import SkillsMatcher
                import logging
                
                logger = logging.getLogger(__name__)
                parser = ResumeParserService()
                skills_matcher = SkillsMatcher()
                
                logger.info(f"[PARSE] Starting resume parsing for invitation {invitation.id}")
                
                # Extract text from uploaded file
                from app.services.file_storage import FileStorageService
                fs = FileStorageService()
                if getattr(document, 'storage_backend', None) == 'gcs' or (document.file_path and not os.path.exists(document.file_path)):
                    tmp_file, err = fs.download_to_temp(document.file_key)
                    if err:
                        logger.error(f"[PARSE] Failed to download resume for parsing: {err}")
                        text = ''
                    else:
                        extracted = TextExtractor.extract_from_file(tmp_file)
                        text = TextExtractor.clean_text(extracted.get('text', ''))
                        try:
                            os.remove(tmp_file)
                        except Exception:
                            pass
                else:
                    extracted = TextExtractor.extract_from_file(document.file_path)
                    text = TextExtractor.clean_text(extracted.get('text', ''))
                
                if not text or len(text.strip()) < 50:
                    logger.warning(f"[PARSE] Insufficient text extracted from resume for invitation {invitation.id} (length: {len(text) if text else 0})")
                else:
                    # Parse with AI
                    parsed_data = parser.parse_resume(text, file_type=document.file_extension)
                    
                    # Enhance skills with skills matcher
                    if parsed_data.get('skills'):
                        skills_analysis = skills_matcher.extract_skills(' '.join(parsed_data['skills']))
                        parsed_data['skills'] = skills_analysis['matched_skills']
                        parsed_data['skills_categories'] = skills_analysis['categories']
                    
                    # Store parsed data in invitation_data
                    current_data = invitation.invitation_data or {}
                    current_data['parsed_resume_data'] = parsed_data
                    invitation.invitation_data = current_data
                    # Note: Will be committed below with last_activity_at update
                    
                    # Log the actual structure for debugging
                    logger.info(f"[PARSE] ✅ Resume parsed successfully for invitation {invitation.id}")
                    logger.info(f"[PARSE] Extracted: {len(parsed_data.get('skills', []))} skills, "
                               f"{len(parsed_data.get('education', []))} education entries, "
                               f"{len(parsed_data.get('work_experience', []))} work experiences")
                    logger.info(f"[PARSE] Education type: {type(parsed_data.get('education'))}")
                    logger.info(f"[PARSE] Work experience type: {type(parsed_data.get('work_experience'))}")
                    if parsed_data.get('education'):
                        logger.info(f"[PARSE] First education entry: {parsed_data['education'][0] if parsed_data['education'] else 'None'}")
                    if parsed_data.get('work_experience'):
                        logger.info(f"[PARSE] First work experience entry: {parsed_data['work_experience'][0] if parsed_data['work_experience'] else 'None'}")
                
            except Exception as e:
                logger.error(f"[PARSE] Failed to parse resume for invitation {invitation.id}: {e}", exc_info=True)
                # Don't fail the upload, just log the error
                # Candidate can still be created with form data
        
        # Serialize response
        response = DocumentResponse.model_validate(document.to_dict())
        return jsonify(response.model_dump()), 201
        
    except ValueError as e:
        return jsonify(ErrorResponse(
            error="Validation Error",
            message=str(e),
            status=400
        ).model_dump()), 400
    except Exception as e:
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"Failed to upload document: {str(e)}",
            status=500
        ).model_dump()), 500


@public_document_bp.route('/list', methods=['GET'])
def list_public_documents():
    """
    Public endpoint to list documents for an invitation
    
    Query params:
        - invitation_token: Invitation token for authentication
    
    Returns:
        200: List of documents for this invitation
        401: Invalid or expired token
        500: Server error
    """
    try:
        invitation_token = request.args.get('invitation_token')
        
        # Validate invitation token
        invitation, error_response = validate_invitation_token(invitation_token)
        if error_response:
            return error_response
        
        # Get documents for this invitation
        documents, total = DocumentService.list_documents(
            tenant_id=invitation.tenant_id,
            filters={'invitation_id': invitation.id},
            pagination={'page': 1, 'per_page': 100}  # Get all documents for invitation
        )
        
        # Serialize response
        response = {
            "documents": [DocumentResponse.model_validate(doc.to_dict()).model_dump() for doc in documents],
            "total": total
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"Failed to list documents: {str(e)}",
            status=500
        ).model_dump()), 500


@public_document_bp.route('/<int:document_id>', methods=['DELETE'])
def delete_public_document(document_id):
    """
    Public endpoint to delete a document during onboarding
    
    Query params:
        - invitation_token: Invitation token for authentication
    
    Returns:
        200: Document deleted successfully
        401: Invalid or expired token
        403: Document does not belong to this invitation
        404: Document not found
        500: Server error
    """
    try:
        invitation_token = request.args.get('invitation_token')
        
        # Validate invitation token
        invitation, error_response = validate_invitation_token(invitation_token)
        if error_response:
            return error_response
        
        # Get document to verify it belongs to this invitation
        document, error = DocumentService.get_document_by_id(document_id, invitation.tenant_id)
        
        if error:
            return jsonify(ErrorResponse(
                error="Not Found",
                message=error,
                status=404
            ).model_dump()), 404
        
        # Verify document belongs to this invitation
        if document.invitation_id != invitation.id:
            return jsonify(ErrorResponse(
                error="Access Denied",
                message="This document does not belong to your invitation",
                status=403
            ).model_dump()), 403
        
        # Delete document
        success, error = DocumentService.delete_document(
            document_id=document_id,
            tenant_id=invitation.tenant_id
        )
        
        if error:
            return jsonify(ErrorResponse(
                error="Delete Failed",
                message=error,
                status=500
            ).model_dump()), 500
        
        return jsonify({
            "message": "Document deleted successfully",
            "document_id": document_id
        }), 200
        
    except Exception as e:
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"Failed to delete document: {str(e)}",
            status=500
        ).model_dump()), 500

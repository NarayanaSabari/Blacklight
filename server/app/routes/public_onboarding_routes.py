"""
Public Onboarding Routes
Public API endpoints for candidate onboarding with resume parsing (token-based auth)
"""
from flask import Blueprint, request, jsonify
from werkzeug.datastructures import FileStorage
from datetime import datetime, timezone
import logging
import os

from app.services.invitation_service import InvitationService
from app.services.resume_parser import ResumeParserService
from app.utils.text_extractor import TextExtractor
from app.schemas.document_schema import ErrorResponse
from app import db
import tempfile

logger = logging.getLogger(__name__)

# Create Blueprint
public_onboarding_bp = Blueprint('public_onboarding', __name__, url_prefix='/api/public/invitations')


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
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # Make naive for comparison
    if invitation.expires_at < now:
        return None, (jsonify(ErrorResponse(
            error="Token Expired",
            message="Invitation token has expired",
            status=401
        ).model_dump()), 401)
    
    # Check if invitation is in a valid state for onboarding
    valid_statuses = ['pending', 'opened', 'in_progress']
    if invitation.status not in valid_statuses:
        return None, (jsonify(ErrorResponse(
            error="Invalid Invitation Status",
            message=f"Invitation status is '{invitation.status}'. Can only parse resume for active invitations.",
            status=400
        ).model_dump()), 400)
    
    return invitation, None


@public_onboarding_bp.route('/parse-resume', methods=['POST'])
def parse_resume_public():
    """
    Public endpoint for parsing resume during onboarding (no candidate creation)
    
    This endpoint parses a resume and returns the extracted data for candidate review.
    The candidate is NOT created until the final submission in the onboarding flow.
    
    Required: multipart/form-data with 'file' field
    Form fields:
        - file: Resume file (PDF or DOCX)
        - invitation_token: Invitation token for authentication
    
    Returns:
        200: Resume parsed successfully with extracted data
        400: Validation error or file missing
        401: Invalid or expired token
        413: File too large
        500: Server error or parsing failed
    """
    try:
        logger.info("[PUBLIC_PARSE] Resume parsing request received")
        
        # Check if file is present
        if 'file' not in request.files:
            logger.warning("[PUBLIC_PARSE] No file in request")
            return jsonify(ErrorResponse(
                error="File Missing",
                message="No file provided in request",
                status=400
            ).model_dump()), 400
        
        file: FileStorage = request.files['file']
        if not file or file.filename == '':
            logger.warning("[PUBLIC_PARSE] Empty file")
            return jsonify(ErrorResponse(
                error="File Missing",
                message="No file selected",
                status=400
            ).model_dump()), 400
        
        # Get invitation token from form data
        invitation_token = request.form.get('invitation_token')
        
        # Validate invitation token
        invitation, error_response = validate_invitation_token(invitation_token)
        if error_response:
            logger.warning(f"[PUBLIC_PARSE] Invalid token: {invitation_token}")
            return error_response
        
        logger.info(f"[PUBLIC_PARSE] Valid invitation for: {invitation.email}")
        
        # Validate file type
        allowed_extensions = {'pdf', 'doc', 'docx'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            logger.warning(f"[PUBLIC_PARSE] Invalid file type: {file_ext}")
            return jsonify(ErrorResponse(
                error="Invalid File Type",
                message=f"File type '.{file_ext}' not supported. Please upload PDF or DOCX files.",
                status=400
            ).model_dump()), 400
        
        logger.info(f"[PUBLIC_PARSE] Processing file: {file.filename} ({file_ext})")
        
        # Extract text from file
        try:
            # Save FileStorage to temporary file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name
            
            try:
                # Extract text using TextExtractor
                extraction_result = TextExtractor.extract_from_file(temp_path)
                text = extraction_result.get('text', '')
                
                if not text or len(text.strip()) < 50:
                    logger.error("[PUBLIC_PARSE] Insufficient text extracted")
                    return jsonify(ErrorResponse(
                        error="Parsing Failed",
                        message="Could not extract sufficient text from resume. Please ensure the file is not empty or corrupted.",
                        status=400
                    ).model_dump()), 400
                
                logger.info(f"[PUBLIC_PARSE] Extracted {len(text)} characters from resume using {extraction_result.get('method')}")
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"[PUBLIC_PARSE] Text extraction failed: {e}", exc_info=True)
            return jsonify(ErrorResponse(
                error="Text Extraction Failed",
                message=f"Failed to extract text from file: {str(e)}",
                status=500
            ).model_dump()), 500
        
        # Parse resume using AI
        try:
            parser = ResumeParserService()
            parsed_data = parser.parse_resume(text, file_type=file_ext)
            
            logger.info(f"[PUBLIC_PARSE] Successfully parsed resume")
            logger.info(f"[PUBLIC_PARSE] Extracted name: {parsed_data.get('full_name')}")
            logger.info(f"[PUBLIC_PARSE] Extracted email: {parsed_data.get('email')}")
            logger.info(f"[PUBLIC_PARSE] Extracted {len(parsed_data.get('skills', []))} skills")
            logger.info(f"[PUBLIC_PARSE] Extracted {len(parsed_data.get('work_experience', []))} jobs")
            
        except Exception as e:
            logger.error(f"[PUBLIC_PARSE] Resume parsing failed: {e}", exc_info=True)
            return jsonify(ErrorResponse(
                error="Parsing Failed",
                message=f"Failed to parse resume: {str(e)}",
                status=500
            ).model_dump()), 500
        
        # Format response data for frontend
        response_data = {
            "status": "success",
            "message": "Resume parsed successfully",
            "parsed_data": {
                # Personal Information
                "full_name": parsed_data.get('full_name'),
                "email": parsed_data.get('email'),
                "phone": parsed_data.get('phone'),
                "location": parsed_data.get('location'),
                "linkedin_url": parsed_data.get('linkedin_url'),
                "portfolio_url": parsed_data.get('portfolio_url'),
                
                # Professional Information
                "current_title": parsed_data.get('current_title'),
                "total_experience_years": parsed_data.get('total_experience_years'),
                "professional_summary": parsed_data.get('professional_summary'),
                
                # Skills and Experience (arrays/objects)
                "skills": parsed_data.get('skills', []),
                "work_experience": parsed_data.get('work_experience', []),
                "education": parsed_data.get('education', []),
                "certifications": parsed_data.get('certifications', []),
                "languages": parsed_data.get('languages', []),
                
                # Additional fields
                "notice_period": parsed_data.get('notice_period'),
                "expected_salary": parsed_data.get('expected_salary'),
                "visa_type": parsed_data.get('visa_type'),
                "preferred_locations": parsed_data.get('preferred_locations', []),
            },
            "metadata": {
                "parsed_at": parsed_data.get('parsed_at'),
                "parser_version": parsed_data.get('parser_version'),
                "ai_provider": parsed_data.get('ai_provider'),
                "confidence_scores": parsed_data.get('confidence_scores', {}),
                "file_name": file.filename,
                "file_type": file_ext
            }
        }
        
        logger.info(f"[PUBLIC_PARSE] Returning parsed data for invitation {invitation.id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"[PUBLIC_PARSE] Unexpected error: {e}", exc_info=True)
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"An unexpected error occurred: {str(e)}",
            status=500
        ).model_dump()), 500


@public_onboarding_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'public_onboarding',
        'message': 'Public onboarding service is running'
    }), 200

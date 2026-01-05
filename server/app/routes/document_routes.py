"""
Document Management Routes
RESTful API endpoints for document upload, download, verification, and management
"""
from flask import Blueprint, request, jsonify, send_file
from werkzeug.datastructures import FileStorage
from io import BytesIO
from typing import Optional

from app.services.document_service import DocumentService
from app.schemas.document_schema import (
    DocumentUploadRequest,
    DocumentResponse,
    DocumentListResponse,
    DocumentUrlResponse,
    DocumentVerifyRequest,
    DocumentStatsResponse,
    ErrorResponse
)
from app.middleware.portal_auth import require_portal_auth, require_permission
from app.middleware.tenant_context import with_tenant_context

# Create Blueprint
document_bp = Blueprint('documents', __name__, url_prefix='/api/documents')


@document_bp.route('/upload', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def upload_document():
    """
    Upload a document
    
    Required: multipart/form-data with 'file' field
    Form fields:
        - file: The file to upload
        - document_type: Type of document (resume, id_proof, etc.)
        - candidate_id: (optional) Candidate ID for post-approval uploads
        - invitation_id: (optional) Invitation ID for onboarding uploads
    
    Returns:
        201: Document uploaded successfully
        400: Validation error or file missing
        413: File too large
        500: Server error
    """
    try:
        # Get tenant and user from auth context
        tenant_id = request.portal_user["tenant_id"]
        user_id = request.portal_user["user_id"]
        
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
        document_type = request.form.get('document_type')
        candidate_id = request.form.get('candidate_id', type=int)
        invitation_id = request.form.get('invitation_id', type=int)
        
        if not document_type:
            return jsonify(ErrorResponse(
                error="Validation Error",
                message="document_type is required",
                status=400
            ).model_dump()), 400
        
        # Validate that either candidate_id or invitation_id is provided
        if not candidate_id and not invitation_id:
            return jsonify(ErrorResponse(
                error="Validation Error",
                message="Either candidate_id or invitation_id must be provided",
                status=400
            ).model_dump()), 400
        
        # Upload document
        document, error = DocumentService.upload_document(
            tenant_id=tenant_id,
            file=file,
            document_type=document_type,
            uploaded_by_id=user_id,
            candidate_id=candidate_id,
            invitation_id=invitation_id
        )
        
        if error:
            return jsonify(ErrorResponse(
                error="Upload Failed",
                message=error,
                status=400
            ).model_dump()), 400
        
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


@document_bp.route('', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def list_documents():
    """
    List documents with filtering and pagination
    
    Query params:
        - candidate_id: Filter by candidate
        - invitation_id: Filter by invitation
        - document_type: Filter by document type
        - is_verified: Filter by verification status (true/false)
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
    
    Returns:
        200: List of documents
        500: Server error
    """
    try:
        # Get tenant from auth context
        tenant_id = request.portal_user["tenant_id"]
        
        # Parse query params
        filters = {
            'candidate_id': request.args.get('candidate_id', type=int),
            'invitation_id': request.args.get('invitation_id', type=int),
            'document_type': request.args.get('document_type'),
            'is_verified': request.args.get('is_verified', type=lambda v: v.lower() == 'true')
        }
        
        pagination = {
            'page': request.args.get('page', 1, type=int),
            'per_page': request.args.get('per_page', 20, type=int)
        }
        
        # Get documents
        documents, total = DocumentService.list_documents(
            tenant_id=tenant_id,
            filters=filters,
            pagination=pagination
        )
        
        # Calculate pages
        pages = (total + pagination['per_page'] - 1) // pagination['per_page']
        
        # Serialize response
        response = DocumentListResponse(
            documents=[DocumentResponse.model_validate(doc.to_dict()) for doc in documents],
            total=total,
            page=pagination['page'],
            per_page=pagination['per_page'],
            pages=pages
        )
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"Failed to list documents: {str(e)}",
            status=500
        ).model_dump()), 500


@document_bp.route('/<int:document_id>', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_document(document_id):
    """
    Get document metadata by ID
    
    Returns:
        200: Document metadata
        404: Document not found
        500: Server error
    """
    try:
        # Get tenant from auth context
        tenant_id = request.portal_user["tenant_id"]
        
        document, error = DocumentService.get_document_by_id(document_id, tenant_id)
        
        if error:
            return jsonify(ErrorResponse(
                error="Not Found",
                message=error,
                status=404
            ).model_dump()), 404
        
        response = DocumentResponse.model_validate(document.to_dict())
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"Failed to get document: {str(e)}",
            status=500
        ).model_dump()), 500


@document_bp.route('/<int:document_id>/download', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def download_document(document_id):
    """
    Download document file
    
    Returns:
        200: File content with appropriate headers
        404: Document not found
        500: Server error
    """
    try:
        # Get tenant from auth context
        tenant_id = request.portal_user["tenant_id"]
        
        file_data, content_type, error = DocumentService.download_document(
            document_id=document_id,
            tenant_id=tenant_id
        )
        
        if error:
            return jsonify(ErrorResponse(
                error="Download Failed",
                message=error,
                status=404 if "not found" in error.lower() else 500
            ).model_dump()), 404 if "not found" in error.lower() else 500
        
        # Get document for filename
        document, _ = DocumentService.get_document_by_id(document_id, tenant_id)
        
        # Return file
        return send_file(
            BytesIO(file_data),
            mimetype=content_type,
            as_attachment=True,
            download_name=document.file_name
        )
        
    except Exception as e:
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"Failed to download document: {str(e)}",
            status=500
        ).model_dump()), 500


@document_bp.route('/<int:document_id>/url', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def get_document_url(document_id):
    """
    Get signed URL for document download (for GCS backend)
    
    Query params:
        - expiry: URL expiry time in seconds (default: 3600)
    
    Returns:
        200: Signed URL
        404: Document not found
        500: Server error
    """
    try:
        # Get tenant from auth context
        tenant_id = request.portal_user["tenant_id"]
        
        expiry_seconds = request.args.get('expiry', 3600, type=int)
        
        signed_url, error = DocumentService.get_document_url(
            document_id=document_id,
            tenant_id=tenant_id,
            expiry_seconds=expiry_seconds
        )
        
        if error:
            return jsonify(ErrorResponse(
                error="URL Generation Failed",
                message=error,
                status=404 if "not found" in error.lower() else 500
            ).model_dump()), 404 if "not found" in error.lower() else 500
        
        # Get document for filename
        document, _ = DocumentService.get_document_by_id(document_id, tenant_id)
        
        response = DocumentUrlResponse(
            url=signed_url,
            expires_in=expiry_seconds,
            document_id=document_id,
            file_name=document.file_name
        )
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"Failed to generate URL: {str(e)}",
            status=500
        ).model_dump()), 500


@document_bp.route('/<int:document_id>', methods=['DELETE'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.delete')
def delete_document(document_id):
    """
    Delete a document
    
    Returns:
        200: Document deleted successfully
        404: Document not found
        500: Server error
    """
    try:
        # Get tenant from auth context
        tenant_id = request.portal_user["tenant_id"]
        
        success, error = DocumentService.delete_document(
            document_id=document_id,
            tenant_id=tenant_id
        )
        
        if error:
            return jsonify(ErrorResponse(
                error="Delete Failed",
                message=error,
                status=404 if "not found" in error.lower() else 500
            ).model_dump()), 404 if "not found" in error.lower() else 500
        
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


@document_bp.route('/<int:document_id>/verify', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.edit')
def verify_document(document_id):
    """
    Verify a document (HR only)
    
    Request body:
        - notes: Optional verification notes
    
    Returns:
        200: Document verified successfully
        400: Validation error
        404: Document not found
        500: Server error
    """
    try:
        # Get tenant and user from auth context
        tenant_id = request.portal_user["tenant_id"]
        user_id = request.portal_user["user_id"]
        
        # Parse request
        data = request.get_json() or {}
        verify_request = DocumentVerifyRequest.model_validate(data)
        
        # Verify document
        document, error = DocumentService.verify_document(
            document_id=document_id,
            tenant_id=tenant_id,
            verified_by_id=user_id,
            notes=verify_request.notes
        )
        
        if error:
            return jsonify(ErrorResponse(
                error="Verification Failed",
                message=error,
                status=404 if "not found" in error.lower() else 400
            ).model_dump()), 404 if "not found" in error.lower() else 400
        
        response = DocumentResponse.model_validate(document.to_dict())
        return jsonify(response.model_dump()), 200
        
    except ValueError as e:
        return jsonify(ErrorResponse(
            error="Validation Error",
            message=str(e),
            status=400
        ).model_dump()), 400
    except Exception as e:
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"Failed to verify document: {str(e)}",
            status=500
        ).model_dump()), 500


@document_bp.route('/stats', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('reports.view')
def get_document_stats():
    """
    Get document statistics for tenant
    
    Returns:
        200: Document statistics
        500: Server error
    """
    try:
        # Get tenant from auth context
        tenant_id = request.portal_user["tenant_id"]
        
        stats = DocumentService.get_document_stats(tenant_id)
        
        response = DocumentStatsResponse.model_validate(stats)
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"Failed to get stats: {str(e)}",
            status=500
        ).model_dump()), 500


@document_bp.route('/storage/browse', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('reports.view')
def browse_storage():
    """
    Browse files and folders in storage for this tenant.
    Shows the actual file structure in GCS/local storage.
    
    Query params:
        - path: Folder path to browse (relative to tenant folder, default: root)
        - recursive: If true, list all files recursively (default: false)
    
    Returns:
        200: List of files and folders
        500: Server error
    """
    try:
        from app.services.file_storage import FileStorageService
        
        # Get tenant from auth context
        tenant_id = request.portal_user["tenant_id"]
        
        # Parse query params
        path = request.args.get('path', '')
        recursive = request.args.get('recursive', 'false').lower() == 'true'
        
        # Initialize storage service
        storage = FileStorageService()
        
        # Use delimiter for folder-like browsing (non-recursive)
        delimiter = None if recursive else '/'
        
        # List files
        result = storage.list_files(
            tenant_id=tenant_id,
            prefix=path,
            delimiter=delimiter
        )
        
        if not result.get('success'):
            return jsonify(ErrorResponse(
                error="Storage Error",
                message=result.get('error', 'Failed to list files'),
                status=500
            ).model_dump()), 500
        
        return jsonify({
            "success": True,
            "path": path or "/",
            "storage_backend": storage.storage_backend,
            "files": result.get('files', []),
            "folders": result.get('prefixes', []),
            "total_count": result.get('total_count', 0),
            "total_size_bytes": result.get('total_size_bytes', 0)
        }), 200
        
    except Exception as e:
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"Failed to browse storage: {str(e)}",
            status=500
        ).model_dump()), 500


@document_bp.route('/storage/download', methods=['GET'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.view')
def download_storage_file():
    """
    Download a file directly from storage by its path.
    
    Query params:
        - path: Full file path (relative to tenant folder)
    
    Returns:
        200: File content
        400: Missing path
        404: File not found
        500: Server error
    """
    try:
        from app.services.file_storage import FileStorageService
        
        # Get tenant from auth context
        tenant_id = request.portal_user["tenant_id"]
        
        # Get file path
        file_path = request.args.get('path', '')
        if not file_path:
            return jsonify(ErrorResponse(
                error="Bad Request",
                message="path parameter is required",
                status=400
            ).model_dump()), 400
        
        # Build full file key with tenant prefix
        file_key = f"tenants/{tenant_id}/{file_path.lstrip('/')}"
        
        # Initialize storage service
        storage = FileStorageService()
        
        # Check if file exists
        if not storage.file_exists(file_key):
            return jsonify(ErrorResponse(
                error="Not Found",
                message="File not found",
                status=404
            ).model_dump()), 404
        
        # Download file
        content, content_type, error = storage.download_file(file_key)
        
        if error:
            return jsonify(ErrorResponse(
                error="Download Failed",
                message=error,
                status=500
            ).model_dump()), 500
        
        # Extract filename from path
        filename = file_path.rsplit('/', 1)[-1]
        
        # Return file
        return send_file(
            BytesIO(content),
            mimetype=content_type,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify(ErrorResponse(
            error="Server Error",
            message=f"Failed to download file: {str(e)}",
            status=500
        ).model_dump()), 500

"""
Scraper Credential Routes

Two sets of endpoints with different authentication:

1. PM_ADMIN Dashboard API (for CentralD UI) - CRUD operations
   - Authentication: JWT token via @require_pm_admin
   
2. Scraper API (for external scrapers) - Get credentials, report failures
   - Authentication: X-Scraper-API-Key header via @require_scraper_auth
"""
import logging
from functools import wraps
from flask import Blueprint, request, jsonify, g

from app import db
from app.models.scraper_api_key import ScraperApiKey
from app.models.scraper_credential import ScraperCredential, CredentialPlatform, CredentialStatus
from app.services.scraper_credential_service import ScraperCredentialService
from app.middleware import require_pm_admin

logger = logging.getLogger(__name__)

scraper_credentials_bp = Blueprint('scraper_credentials', __name__, url_prefix='/api/scraper-credentials')


def require_scraper_auth(f):
    """
    Middleware to validate scraper API key.
    Expects X-Scraper-API-Key header.
    Sets g.scraper_key on success.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-Scraper-API-Key')
        
        if not api_key:
            return jsonify({
                "error": "Unauthorized",
                "message": "Missing X-Scraper-API-Key header"
            }), 401
        
        scraper_key = ScraperApiKey.validate_key(api_key)
        
        if not scraper_key:
            return jsonify({
                "error": "Unauthorized",
                "message": "Invalid or revoked API key"
            }), 401
        
        g.scraper_key = scraper_key
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================================================
# PM_ADMIN DASHBOARD ENDPOINTS (CentralD UI)
# Authentication: JWT token via @require_pm_admin
# ============================================================================

@scraper_credentials_bp.route('/', methods=['GET'])
@require_pm_admin
def list_credentials():
    """
    List all credentials with optional filters.
    
    Query params:
        platform: Filter by platform (linkedin, glassdoor, techfetch)
        status: Filter by status (available, in_use, failed, disabled, cooldown)
    
    Returns:
        List of credentials (without decrypted passwords)
    """
    platform = request.args.get('platform')
    status = request.args.get('status')
    
    credentials = ScraperCredentialService.get_all_credentials(
        platform=platform,
        status=status
    )
    
    return jsonify({
        "credentials": [c.to_dict(include_credentials=False) for c in credentials],
        "total": len(credentials)
    }), 200


@scraper_credentials_bp.route('/stats', methods=['GET'])
@require_pm_admin
def get_stats():
    """
    Get credential statistics for all platforms.
    
    Returns:
        Stats for each platform (total, available, in_use, failed, etc.)
    """
    stats = ScraperCredentialService.get_all_platform_stats()
    return jsonify(stats), 200


@scraper_credentials_bp.route('/platforms/<platform>', methods=['GET'])
@require_pm_admin
def get_platform_credentials(platform: str):
    """
    Get all credentials for a specific platform.
    
    Path params:
        platform: Platform name (linkedin, glassdoor, techfetch)
    
    Query params:
        status: Optional status filter
    
    Returns:
        List of credentials for the platform
    """
    if platform.lower() not in ScraperCredentialService.PLATFORMS:
        return jsonify({
            "error": "Invalid platform",
            "message": f"Supported platforms: {list(ScraperCredentialService.PLATFORMS.keys())}"
        }), 400
    
    status = request.args.get('status')
    
    credentials = ScraperCredentialService.get_credentials_by_platform(
        platform=platform,
        status=status
    )
    
    stats = ScraperCredentialService.get_platform_stats(platform)
    
    return jsonify({
        "platform": platform,
        "credentials": [c.to_dict(include_credentials=False) for c in credentials],
        "stats": stats
    }), 200


@scraper_credentials_bp.route('/', methods=['POST'])
@require_pm_admin
def create_credential():
    """
    Create a new scraper credential.
    
    Request body for LinkedIn/Techfetch:
    {
        "platform": "linkedin",
        "name": "Account 1",
        "email": "user@example.com",
        "password": "secret123",
        "notes": "Optional notes"
    }
    
    Request body for Glassdoor:
    {
        "platform": "glassdoor",
        "name": "Cookie Set 1",
        "json_credentials": { ... },
        "notes": "Optional notes"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    
    platform = data.get('platform', '').lower()
    name = data.get('name')
    
    if not platform or not name:
        return jsonify({"error": "Platform and name are required"}), 400
    
    try:
        credential = ScraperCredentialService.create_credential(
            platform=platform,
            name=name,
            email=data.get('email'),
            password=data.get('password'),
            json_credentials=data.get('json_credentials'),
            notes=data.get('notes')
        )
        
        logger.info(f"Created credential {credential.id} for platform {platform}")
        
        return jsonify({
            "message": "Credential created successfully",
            "credential": credential.to_dict(include_credentials=False)
        }), 201
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@scraper_credentials_bp.route('/<int:credential_id>', methods=['GET'])
@require_pm_admin
def get_credential(credential_id: int):
    """
    Get a specific credential by ID.
    
    Query params:
        include_credentials: If "true", include decrypted credentials (use with caution!)
    """
    credential = ScraperCredentialService.get_credential(credential_id)
    
    if not credential:
        return jsonify({"error": "Credential not found"}), 404
    
    include_creds = request.args.get('include_credentials', '').lower() == 'true'
    
    return jsonify({
        "credential": credential.to_dict(include_credentials=include_creds)
    }), 200


@scraper_credentials_bp.route('/<int:credential_id>', methods=['PUT'])
@require_pm_admin
def update_credential(credential_id: int):
    """
    Update an existing credential.
    
    Request body (all fields optional):
    {
        "name": "New Name",
        "email": "new@example.com",
        "password": "newpassword",
        "json_credentials": { ... },
        "notes": "Updated notes"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    
    try:
        credential = ScraperCredentialService.update_credential(
            credential_id=credential_id,
            name=data.get('name'),
            email=data.get('email'),
            password=data.get('password'),
            json_credentials=data.get('json_credentials'),
            notes=data.get('notes')
        )
        
        logger.info(f"Updated credential {credential_id}")
        
        return jsonify({
            "message": "Credential updated successfully",
            "credential": credential.to_dict(include_credentials=False)
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@scraper_credentials_bp.route('/<int:credential_id>', methods=['DELETE'])
@require_pm_admin
def delete_credential(credential_id: int):
    """Delete a credential."""
    success = ScraperCredentialService.delete_credential(credential_id)
    
    if not success:
        return jsonify({"error": "Credential not found"}), 404
    
    logger.info(f"Deleted credential {credential_id}")
    
    return jsonify({"message": "Credential deleted successfully"}), 200


@scraper_credentials_bp.route('/<int:credential_id>/enable', methods=['POST'])
@require_pm_admin
def enable_credential(credential_id: int):
    """Enable a disabled/failed credential."""
    try:
        credential = ScraperCredentialService.enable_credential(credential_id)
        logger.info(f"Enabled credential {credential_id}")
        
        return jsonify({
            "message": "Credential enabled",
            "credential": credential.to_dict(include_credentials=False)
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@scraper_credentials_bp.route('/<int:credential_id>/disable', methods=['POST'])
@require_pm_admin
def disable_credential(credential_id: int):
    """Disable a credential."""
    try:
        credential = ScraperCredentialService.disable_credential(credential_id)
        logger.info(f"Disabled credential {credential_id}")
        
        return jsonify({
            "message": "Credential disabled",
            "credential": credential.to_dict(include_credentials=False)
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@scraper_credentials_bp.route('/<int:credential_id>/reset', methods=['POST'])
@require_pm_admin
def reset_credential(credential_id: int):
    """Reset a failed credential to available status."""
    try:
        credential = ScraperCredentialService.reset_credential(credential_id)
        logger.info(f"Reset credential {credential_id}")
        
        return jsonify({
            "message": "Credential reset to available",
            "credential": credential.to_dict(include_credentials=False)
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


# ============================================================================
# SCRAPER API ENDPOINTS (for external scrapers)
# Authentication: X-Scraper-API-Key header via @require_scraper_auth
# ============================================================================

@scraper_credentials_bp.route('/queue/<platform>/next', methods=['GET'])
@require_scraper_auth
def get_next_credential(platform: str):
    """
    Get the next available credential for a platform.
    
    The credential is marked as 'in_use' and assigned to the scraper.
    Scraper must report success or failure after using the credential.
    
    Query params:
        session_id: Scraper session ID (for tracking)
    
    Returns (200):
    {
        "id": 1,
        "platform": "linkedin",
        "name": "Account 1",
        "email": "user@example.com",
        "password": "secret123"
    }
    
    For Glassdoor:
    {
        "id": 1,
        "platform": "glassdoor",
        "name": "Cookie Set 1",
        "credentials": { ... }
    }
    
    Returns 204 if no credentials available.
    """
    if platform.lower() not in ScraperCredentialService.PLATFORMS:
        return jsonify({
            "error": "Invalid platform",
            "message": f"Supported platforms: {list(ScraperCredentialService.PLATFORMS.keys())}"
        }), 400
    
    session_id = request.args.get('session_id', f"scraper-{g.scraper_key.id}")
    
    credential = ScraperCredentialService.get_next_credential_for_scraper(
        platform=platform,
        session_id=session_id
    )
    
    if not credential:
        return '', 204
    
    # Record API key usage
    g.scraper_key.record_usage()
    db.session.commit()
    
    logger.info(f"Assigned credential {credential.id} to session {session_id}")
    
    return jsonify(credential.to_scraper_dict()), 200


@scraper_credentials_bp.route('/queue/<int:credential_id>/success', methods=['POST'])
@require_scraper_auth
def report_success(credential_id: int):
    """
    Report that a credential was used successfully.
    Releases the credential back to the available pool.
    
    Request body (optional):
    {
        "message": "Optional success message"
    }
    """
    try:
        credential = ScraperCredentialService.report_credential_success(credential_id)
        
        g.scraper_key.record_usage()
        db.session.commit()
        
        logger.info(f"Credential {credential_id} reported success")
        
        return jsonify({
            "message": "Credential released successfully",
            "status": credential.status
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@scraper_credentials_bp.route('/queue/<int:credential_id>/failure', methods=['POST'])
@require_scraper_auth
def report_failure(credential_id: int):
    """
    Report that a credential failed.
    Marks the credential as failed with the error message.
    
    Request body:
    {
        "error_message": "Login failed: Invalid credentials",
        "cooldown_minutes": 0  // Optional: put credential on cooldown
    }
    """
    data = request.get_json() or {}
    
    error_message = data.get('error_message', 'Unknown error')
    cooldown_minutes = data.get('cooldown_minutes', 0)
    
    try:
        credential = ScraperCredentialService.report_credential_failure(
            credential_id=credential_id,
            error_message=error_message,
            cooldown_minutes=cooldown_minutes
        )
        
        g.scraper_key.record_usage()
        db.session.commit()
        
        logger.warning(f"Credential {credential_id} reported failure: {error_message}")
        
        return jsonify({
            "message": "Credential failure recorded",
            "status": credential.status,
            "failure_count": credential.failure_count
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@scraper_credentials_bp.route('/queue/<int:credential_id>/release', methods=['POST'])
@require_scraper_auth
def release_credential_route(credential_id: int):
    """
    Release a credential without reporting success or failure.
    Useful if scraper needs to return credential without using it.
    """
    try:
        credential = ScraperCredentialService.release_credential(
            credential_id=credential_id,
            success=True
        )
        
        logger.info(f"Credential {credential_id} released")
        
        return jsonify({
            "message": "Credential released",
            "status": credential.status
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

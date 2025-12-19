"""
Email Integration Routes

Handles OAuth connection flows for Gmail and Outlook email integrations,
and provides endpoints for managing email integrations.
"""

import json
import logging
from urllib.parse import urlencode

from flask import Blueprint, g, jsonify, redirect, request

from app.middleware.portal_auth import require_portal_auth, require_permission
from app.services.email_integration_service import email_integration_service
from app.services.oauth.gmail_oauth import gmail_oauth_service
from app.services.oauth.outlook_oauth import outlook_oauth_service
from config.settings import settings

bp = Blueprint("email_integrations", __name__, url_prefix="/api/integrations/email")
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
# Integration Status Endpoints
# ============================================================================

@bp.route("/status", methods=["GET"])
@require_portal_auth
def get_integration_status():
    """
    Get email integration status for current user.
    
    Returns:
        JSON with gmail and outlook connection status
    """
    user_id = g.user_id
    tenant_id = g.tenant_id
    
    stats = email_integration_service.get_integration_stats(user_id, tenant_id)
    
    # Add configuration status
    stats["gmail"]["is_configured"] = gmail_oauth_service.is_configured()
    stats["outlook"]["is_configured"] = outlook_oauth_service.is_configured()
    
    return jsonify(stats), 200


@bp.route("/list", methods=["GET"])
@require_portal_auth
def list_integrations():
    """
    List all email integrations for current user.
    
    Returns:
        JSON array of integration objects
    """
    user_id = g.user_id
    tenant_id = g.tenant_id
    
    integrations = email_integration_service.get_integrations_for_user(user_id, tenant_id)
    
    result = []
    for integration in integrations:
        result.append({
            "id": integration.id,
            "provider": integration.provider,
            "email_address": integration.email_address,
            "is_active": integration.is_active,
            "last_synced_at": integration.last_synced_at.isoformat() if integration.last_synced_at else None,
            "emails_processed_count": integration.emails_processed_count or 0,
            "jobs_created_count": integration.jobs_created_count or 0,
            "last_error": integration.last_error,
            "created_at": integration.created_at.isoformat() if integration.created_at else None,
        })
    
    return jsonify(result), 200


# ============================================================================
# Gmail OAuth Flow
# ============================================================================

@bp.route("/connect/gmail", methods=["GET"])
@require_portal_auth
def connect_gmail():
    """
    Initiate Gmail OAuth flow.
    
    Returns:
        JSON with authorization_url to redirect user to
    """
    user_id = g.user_id
    tenant_id = g.tenant_id
    
    if not gmail_oauth_service.is_configured():
        return error_response(
            "Gmail integration is not configured. Contact your administrator.",
            status=503,
        )
    
    try:
        auth_url = email_integration_service.initiate_gmail_connection(user_id, tenant_id)
        return jsonify({"authorization_url": auth_url}), 200
    except Exception as e:
        logger.error(f"Failed to initiate Gmail OAuth: {e}")
        return error_response(f"Failed to initiate Gmail connection: {str(e)}", status=500)


@bp.route("/callback/gmail", methods=["GET"])
def gmail_callback():
    """
    Handle Gmail OAuth callback.
    
    This is called by Google after user authorizes the app.
    Redirects to frontend with success or error.
    """
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")
    
    frontend_url = settings.frontend_base_url or "http://localhost:5173"
    # Redirect to portal settings page
    redirect_path = "/portal/settings"
    
    if error:
        logger.warning(f"Gmail OAuth error: {error}")
        params = urlencode({"error": error, "provider": "gmail"})
        return redirect(f"{frontend_url}{redirect_path}?{params}")
    
    if not code or not state:
        params = urlencode({"error": "missing_params", "provider": "gmail"})
        return redirect(f"{frontend_url}{redirect_path}?{params}")
    
    try:
        integration = email_integration_service.complete_gmail_connection(code, state)
        params = urlencode({
            "success": "true",
            "provider": "gmail",
            "email": integration.email_address,
        })
        return redirect(f"{frontend_url}{redirect_path}?{params}")
        
    except Exception as e:
        logger.error(f"Gmail OAuth callback failed: {e}")
        params = urlencode({"error": str(e)[:100], "provider": "gmail"})
        return redirect(f"{frontend_url}{redirect_path}?{params}")


# ============================================================================
# Outlook OAuth Flow
# ============================================================================

@bp.route("/connect/outlook", methods=["GET"])
@require_portal_auth
def connect_outlook():
    """
    Initiate Outlook OAuth flow.
    
    Returns:
        JSON with authorization_url to redirect user to
    """
    user_id = g.user_id
    tenant_id = g.tenant_id
    
    if not outlook_oauth_service.is_configured():
        return error_response(
            "Outlook integration is not configured. Contact your administrator.",
            status=503,
        )
    
    try:
        auth_url = email_integration_service.initiate_outlook_connection(user_id, tenant_id)
        return jsonify({"authorization_url": auth_url}), 200
    except Exception as e:
        logger.error(f"Failed to initiate Outlook OAuth: {e}")
        return error_response(f"Failed to initiate Outlook connection: {str(e)}", status=500)


@bp.route("/callback/outlook", methods=["GET"])
def outlook_callback():
    """
    Handle Outlook OAuth callback.
    
    This is called by Microsoft after user authorizes the app.
    Redirects to frontend with success or error.
    """
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")
    error_description = request.args.get("error_description")
    
    frontend_url = settings.frontend_base_url or "http://localhost:5173"
    # Redirect to portal settings page (handle both /portal prefix and direct access)
    redirect_path = "/portal/settings"
    
    if error:
        logger.warning(f"Outlook OAuth error: {error} - {error_description}")
        params = urlencode({"error": error_description or error, "provider": "outlook"})
        return redirect(f"{frontend_url}{redirect_path}?{params}")
    
    if not code or not state:
        params = urlencode({"error": "missing_params", "provider": "outlook"})
        return redirect(f"{frontend_url}{redirect_path}?{params}")
    
    try:
        integration = email_integration_service.complete_outlook_connection(code, state)
        params = urlencode({
            "success": "true",
            "provider": "outlook",
            "email": integration.email_address,
        })
        return redirect(f"{frontend_url}{redirect_path}?{params}")
        
    except Exception as e:
        logger.error(f"Outlook OAuth callback failed: {e}")
        params = urlencode({"error": str(e)[:100], "provider": "outlook"})
        return redirect(f"{frontend_url}{redirect_path}?{params}")


# ============================================================================
# Integration Management
# ============================================================================

@bp.route("/<int:integration_id>", methods=["DELETE"])
@require_portal_auth
def disconnect_integration(integration_id: int):
    """
    Disconnect and delete an email integration.
    
    Args:
        integration_id: Integration ID to disconnect
        
    Returns:
        Success message
    """
    user_id = g.user_id
    tenant_id = g.tenant_id
    
    try:
        email_integration_service.disconnect_integration(integration_id, user_id, tenant_id)
        return jsonify({"message": "Integration disconnected successfully"}), 200
    except ValueError as e:
        return error_response(str(e), status=404)
    except Exception as e:
        logger.error(f"Failed to disconnect integration: {e}")
        return error_response(f"Failed to disconnect: {str(e)}", status=500)


@bp.route("/<int:integration_id>/toggle", methods=["PATCH"])
@require_portal_auth
def toggle_integration(integration_id: int):
    """
    Toggle integration active status.
    
    Request Body:
        is_active: boolean
        
    Returns:
        Updated integration object
    """
    user_id = g.user_id
    tenant_id = g.tenant_id
    
    data = request.get_json()
    is_active = data.get("is_active")
    
    if is_active is None:
        return error_response("is_active field is required", status=400)
    
    try:
        integration = email_integration_service.toggle_integration(
            integration_id, user_id, tenant_id, bool(is_active)
        )
        return jsonify({
            "id": integration.id,
            "provider": integration.provider,
            "is_active": integration.is_active,
        }), 200
    except ValueError as e:
        return error_response(str(e), status=404)
    except Exception as e:
        logger.error(f"Failed to toggle integration: {e}")
        return error_response(f"Failed to toggle: {str(e)}", status=500)


@bp.route("/<int:integration_id>/sync", methods=["POST"])
@require_portal_auth
def trigger_sync(integration_id: int):
    """
    Manually trigger a sync for an integration.
    
    This will queue an Inngest job to sync the integration.
    
    Args:
        integration_id: Integration ID to sync
        
    Returns:
        Success message
    """
    user_id = g.user_id
    tenant_id = g.tenant_id
    
    try:
        integration = email_integration_service.get_integration(
            integration_id, user_id, tenant_id
        )
        
        if not integration:
            return error_response("Integration not found", status=404)
        
        if not integration.is_active:
            return error_response("Integration is not active", status=400)
        
        # Trigger Inngest sync event
        from app.inngest import inngest_client
        import inngest
        
        inngest_client.send_sync(
            inngest.Event(
                name="email/sync-user-inbox",
                data={
                    "integration_id": integration.id,
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "manual_trigger": True,
                },
            )
        )
        
        return jsonify({"message": "Sync triggered successfully"}), 200
        
    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")
        return error_response(f"Failed to trigger sync: {str(e)}", status=500)

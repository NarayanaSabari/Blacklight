"""
Inngest Client Configuration
Centralized Inngest client for background job orchestration

Supports both:
- Self-hosted Inngest server (recommended for production)
- Inngest Cloud (if INNGEST_BASE_URL is not set)
"""
from inngest import Inngest
from config.settings import settings

# Determine if running in production mode
# INNGEST_DEV=false means production mode (requires signing key)
is_production = not settings.inngest_dev

# Self-hosted Inngest:
#   - INNGEST_BASE_URL points to your self-hosted Inngest server
#   - e.g., http://inngest:8288 (Docker internal) or http://localhost:8288 (local)
# Inngest Cloud:
#   - Leave INNGEST_BASE_URL empty to use Inngest Cloud (https://inn.gs)
#
# For self-hosted production, INNGEST_BASE_URL should be set to the Inngest server URL
api_base_url = settings.inngest_base_url if settings.inngest_base_url else None
event_api_base_url = settings.inngest_base_url if settings.inngest_base_url else None

# Initialize Inngest client
inngest_client = Inngest(
    app_id="blacklight-hr",
    event_key=settings.inngest_event_key or None,
    signing_key=settings.inngest_signing_key if is_production else None,
    is_production=is_production,
    api_base_url=api_base_url,
    event_api_base_url=event_api_base_url,
)

print(f"[INNGEST] Initialized - Production Mode: {is_production}, Self-Hosted: {bool(api_base_url)}, API URL: {api_base_url or 'Inngest Cloud'}, Event Key: {'***' if settings.inngest_event_key else 'None'}")

__all__ = ["inngest_client"]

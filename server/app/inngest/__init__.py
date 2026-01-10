"""
Inngest Client Configuration
Centralized Inngest client for background job orchestration
"""
from inngest import Inngest
from config.settings import settings

# Determine if running in production mode
# INNGEST_DEV=false means production mode
is_production = not settings.inngest_dev

# For Inngest Cloud (production): api_base_url should be None
# For self-hosted Inngest (dev): api_base_url points to the Inngest server (e.g., http://localhost:8288)
# We only use api_base_url when NOT in production mode (i.e., using self-hosted Inngest)
api_base_url = None if is_production else (settings.inngest_base_url or None)

# Initialize Inngest client
inngest_client = Inngest(
    app_id="blacklight-hr",
    event_key=settings.inngest_event_key or None,
    signing_key=settings.inngest_signing_key if is_production else None,
    is_production=is_production,
    api_base_url=api_base_url,
)

print(f"[INNGEST] Initialized - Production Mode: {is_production}, API URL: {api_base_url}, Event Key: {'***' if settings.inngest_event_key else 'None'}")

__all__ = ["inngest_client"]

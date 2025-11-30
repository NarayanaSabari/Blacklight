"""
Inngest Client Configuration
Centralized Inngest client for background job orchestration
"""
from inngest import Inngest
from config.settings import settings

# Determine if running in production mode
# INNGEST_DEV=false means production mode
is_production = not settings.inngest_dev

# Initialize Inngest client
# For self-hosted Inngest, we need to specify the api_base_url
inngest_client = Inngest(
    app_id="blacklight-hr",
    event_key=settings.inngest_event_key or None,
    signing_key=settings.inngest_signing_key if is_production else None,
    is_production=is_production,
    api_base_url=settings.inngest_base_url if settings.inngest_base_url else None,
)

print(f"[INNGEST] Initialized - Production Mode: {is_production}, API URL: {settings.inngest_base_url}, Event Key: {'***' if settings.inngest_event_key else 'None'}")

__all__ = ["inngest_client"]

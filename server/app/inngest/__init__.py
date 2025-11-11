"""
Inngest Client Configuration
Centralized Inngest client for background job orchestration
"""
import os
from inngest import Inngest

# Initialize Inngest client
inngest_client = Inngest(
    app_id="blacklight-hr",
    event_key=os.getenv("INNGEST_EVENT_KEY"),  # Optional for local dev
    is_production=os.getenv("INNGEST_DEV", "true").lower() != "true",
    event_api_base_url=os.getenv("INNGEST_BASE_URL", "http://localhost:8288"),
)

__all__ = ["inngest_client"]

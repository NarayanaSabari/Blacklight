"""
Inngest Functions Registry
All background job functions are registered here
"""
from .email_sending import (
    send_invitation_email_workflow,
    send_submission_confirmation_workflow,
    send_approval_email_workflow,
    send_rejection_email_workflow,
    send_hr_notification_workflow,
    send_tenant_welcome_email_workflow,
    send_portal_user_welcome_email_workflow
)
from .scheduled_tasks import (
    check_expiring_invitations_workflow,
    generate_daily_stats_workflow,
    cleanup_stale_sessions_workflow,
    reset_completed_roles_workflow,
    update_role_candidate_counts_workflow,
    cleanup_stale_credentials_workflow,
    clear_credential_cooldowns_workflow
)
from .job_matching_tasks import (
    nightly_match_refresh_workflow,
    generate_candidate_matches_workflow,
    update_job_embeddings_workflow,
    match_jobs_to_candidates_workflow
)
from .resume_parsing import (
    parse_resume_workflow,
    polish_resume_workflow,
    parse_candidate_resume_workflow,
    polish_candidate_resume_workflow
)
from .role_normalization import (
    normalize_candidate_roles_workflow
)
from .job_import import (
    import_platform_jobs_fn,
    complete_scrape_session_fn
)
from .email_sync import (
    sync_all_integrations_workflow,
    sync_user_inbox_workflow,
    manual_sync_workflow
)

# List of all Inngest functions to be registered
INNGEST_FUNCTIONS = [
    # Email Workflows
    send_invitation_email_workflow,
    send_submission_confirmation_workflow,
    send_approval_email_workflow,
    send_rejection_email_workflow,
    send_hr_notification_workflow,
    send_tenant_welcome_email_workflow,
    send_portal_user_welcome_email_workflow,
    
    # Scheduled Tasks
    check_expiring_invitations_workflow,
    generate_daily_stats_workflow,
    cleanup_stale_sessions_workflow,
    reset_completed_roles_workflow,
    update_role_candidate_counts_workflow,
    cleanup_stale_credentials_workflow,
    clear_credential_cooldowns_workflow,
    
    # Job Matching Tasks
    nightly_match_refresh_workflow,
    generate_candidate_matches_workflow,
    update_job_embeddings_workflow,
    match_jobs_to_candidates_workflow,
    
    # Resume Parsing
    parse_resume_workflow,
    polish_resume_workflow,
    parse_candidate_resume_workflow,
    polish_candidate_resume_workflow,
    
    # Role Normalization
    normalize_candidate_roles_workflow,
    
    # Job Import (Multi-Platform)
    import_platform_jobs_fn,
    complete_scrape_session_fn,
    
    # Email Sync (Gmail/Outlook)
    sync_all_integrations_workflow,
    sync_user_inbox_workflow,
    manual_sync_workflow,
]

__all__ = ["INNGEST_FUNCTIONS"]

"""
Inngest Functions Registry
All background job functions are registered here
"""
from .email_sending import (
    send_invitation_email_workflow,
    send_submission_confirmation_workflow,
    send_approval_email_workflow,
    send_rejection_email_workflow,
    send_hr_notification_workflow
)
from .scheduled_tasks import (
    check_expiring_invitations_workflow,
    generate_daily_stats_workflow
)

# List of all Inngest functions to be registered
INNGEST_FUNCTIONS = [
    # Email Workflows
    send_invitation_email_workflow,
    send_submission_confirmation_workflow,
    send_approval_email_workflow,
    send_rejection_email_workflow,
    send_hr_notification_workflow,
    
    # Scheduled Tasks
    check_expiring_invitations_workflow,
    generate_daily_stats_workflow,
]

__all__ = ["INNGEST_FUNCTIONS"]

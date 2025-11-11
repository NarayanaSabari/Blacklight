"""
Email Sending Workflows
Reliable email delivery with automatic retries
"""
import logging
from datetime import timedelta

import inngest

from app.inngest import inngest_client

logger = logging.getLogger(__name__)


@inngest_client.create_function(
    fn_id="send-invitation-email",
    trigger=inngest.TriggerEvent(event="email/invitation"),
    retries=5,
    name="Send Invitation Email",
    rate_limit=inngest.RateLimit(limit=50, period=timedelta(minutes=1))
)
async def send_invitation_email_workflow(ctx: inngest.Context, step: inngest.Step) -> dict:
    """Send invitation email with retry logic"""
    event = ctx.event
    invitation_id = event.data.get("invitation_id")
    tenant_id = event.data.get("tenant_id")
    
    logger.info(f"[INNGEST] Sending invitation email for invitation {invitation_id}")
    
    # Extract all necessary data directly from the event
    to_email = event.data.get("to_email")
    candidate_name = event.data.get("candidate_name")
    onboarding_url = event.data.get("onboarding_url")
    expiry_date_str = event.data.get("expiry_date")

    if not all([to_email, candidate_name, onboarding_url, expiry_date_str]):
        logger.error(f"[INNGEST] Missing essential email data in event for invitation {invitation_id}. Event data: {event.data}")
        raise ValueError("Missing essential email data in Inngest event.")

    # Step 1: Send email with automatic retry
    email_result = await step.run(
        "send-email",
        send_invitation_email_step,
        tenant_id,
        { # Create a dictionary that mimics the invitation object for send_invitation_email_step
            "email": to_email,
            "first_name": candidate_name.split(' ')[0] if candidate_name and ' ' in candidate_name else candidate_name,
            "last_name": ' '.join(candidate_name.split(' ')[1:]) if candidate_name and ' ' in candidate_name else None,
            "expiry_date": expiry_date_str # Pass the formatted expiry date string
        },
        onboarding_url
    )
    
    # Step 2: Log email delivery
    await step.run(
        "log-email-sent",
        log_email_status_step,
        invitation_id,
        "invitation_sent",
        email_result
    )
    
    return {"invitation_id": invitation_id, "email_sent": email_result}


@inngest_client.create_function(
    fn_id="send-submission-confirmation",
    trigger=inngest.TriggerEvent(event="email/submission-confirmation"),
    retries=3,
    name="Send Submission Confirmation Email"
)
async def send_submission_confirmation_workflow(ctx: inngest.Context, step: inngest.Step) -> dict:
    """Send confirmation email after candidate submits"""
    event = ctx.event
    tenant_id = event.data.get("tenant_id")
    email = event.data.get("email")
    candidate_name = event.data.get("candidate_name")
    
    result = await step.run(
        "send-confirmation",
        send_confirmation_step,
        tenant_id,
        email,
        candidate_name
    )
    
    return {"email_sent": result}


@inngest_client.create_function(
    fn_id="send-approval-email",
    trigger=inngest.TriggerEvent(event="email/approval"),
    retries=3,
    name="Send Approval Email"
)
async def send_approval_email_workflow(ctx: inngest.Context, step: inngest.Step) -> dict:
    """Send approval email to candidate"""
    event = ctx.event
    tenant_id = event.data.get("tenant_id")
    email = event.data.get("email")
    candidate_name = event.data.get("candidate_name")
    
    result = await step.run(
        "send-approval",
        send_approval_step,
        tenant_id,
        email,
        candidate_name
    )
    
    return {"email_sent": result}


@inngest_client.create_function(
    fn_id="send-rejection-email",
    trigger=inngest.TriggerEvent(event="email/rejection"),
    retries=3,
    name="Send Rejection Email"
)
async def send_rejection_email_workflow(ctx: inngest.Context, step: inngest.Step) -> dict:
    """Send rejection email to candidate"""
    event = ctx.event
    tenant_id = event.data.get("tenant_id")
    email = event.data.get("email")
    candidate_name = event.data.get("candidate_name")
    reason = event.data.get("reason")
    
    result = await step.run(
        "send-rejection",
        send_rejection_step,
        tenant_id,
        email,
        candidate_name,
        reason
    )
    
    return {"email_sent": result}


@inngest_client.create_function(
    fn_id="send-hr-notification",
    trigger=inngest.TriggerEvent(event="email/hr-notification"),
    retries=3,
    name="Send HR Notification Email"
)
async def send_hr_notification_workflow(ctx: inngest.Context, step: inngest.Step) -> dict:
    """Send notification to HR team"""
    event = ctx.event
    tenant_id = event.data.get("tenant_id")
    notification_type = event.data.get("notification_type")
    data = event.data.get("data", {})
    
    result = await step.run(
        "send-hr-notification",
        send_hr_notification_step,
        tenant_id,
        notification_type,
        data
    )
    
    return {"notification_sent": result}


# Step Functions

def fetch_invitation_step(invitation_id: int, tenant_id: int) -> dict:
    """Fetch invitation from database"""
    from app.services.invitation_service import InvitationService
    
    invitation = InvitationService.get_by_id(invitation_id, tenant_id)
    if not invitation:
        raise ValueError(f"Invitation {invitation_id} not found")
    
    return {
        "id": invitation.id,
        "email": invitation.email,
        "first_name": invitation.first_name,
        "last_name": invitation.last_name,
        "token": invitation.token,
        "expires_at": invitation.expires_at.isoformat()
    }


def generate_onboarding_url_step(invitation: dict) -> str:
    """Generate onboarding URL with token"""
    import os
    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
    return f"{frontend_url}/onboarding?token={invitation['token']}"


def send_invitation_email_step(
    tenant_id: int,
    invitation: dict,
    onboarding_url: str
) -> bool:
    """Send invitation email via SMTP"""
    from app.services.email_service import EmailService
    from datetime import datetime
    
    # Check if expiry_date is already a formatted string (from event data)
    # or if it needs to be formatted from a datetime object (from fetched invitation)
    if 'expiry_date' in invitation: # This would be the expiry_date_str from event.data
        expiry_date = invitation['expiry_date']
    else:
        expires_at = datetime.fromisoformat(invitation['expires_at'])
        expiry_date = expires_at.strftime("%B %d, %Y at %I:%M %p UTC") # Ensure consistent format
    
    candidate_name = None
    if invitation.get('first_name'):
        candidate_name = f"{invitation['first_name']}"
        if invitation.get('last_name'):
            candidate_name += f" {invitation['last_name']}"
    
    return EmailService.send_invitation_email(
        tenant_id=tenant_id,
        to_email=invitation['email'],
        candidate_name=candidate_name,
        onboarding_url=onboarding_url,
        expiry_date=expiry_date
    )


def send_confirmation_step(
    tenant_id: int,
    email: str,
    candidate_name: str
) -> bool:
    """Send submission confirmation email"""
    from app.services.email_service import EmailService
    
    return EmailService.send_submission_confirmation(
        tenant_id=tenant_id,
        to_email=email,
        candidate_name=candidate_name
    )


def send_approval_step(
    tenant_id: int,
    email: str,
    candidate_name: str
) -> bool:
    """Send approval email"""
    from app.services.email_service import EmailService
    
    return EmailService.send_approval_email(
        tenant_id=tenant_id,
        to_email=email,
        candidate_name=candidate_name
    )


def send_rejection_step(
    tenant_id: int,
    email: str,
    candidate_name: str,
    reason: str = None
) -> bool:
    """Send rejection email"""
    from app.services.email_service import EmailService
    
    return EmailService.send_rejection_email(
        tenant_id=tenant_id,
        to_email=email,
        candidate_name=candidate_name,
        reason=reason
    )


def send_hr_notification_step(
    tenant_id: int,
    notification_type: str,
    data: dict
) -> bool:
    """Send notification to HR team"""
    from app.services.email_service import EmailService
    from app.services.portal_user_service import PortalUserService
    
    # Get all HR users for tenant
    hr_users = PortalUserService.get_hr_users(tenant_id)
    hr_emails = [user.email for user in hr_users]
    
    if not hr_emails:
        logger.warning(f"No HR users found for tenant {tenant_id}")
        return False
    
    # Send notification based on type
    if notification_type == "new_submission":
        return EmailService.send_hr_notification(
            tenant_id=tenant_id,
            hr_emails=hr_emails,
            candidate_name=data.get("candidate_name"),
            candidate_email=data.get("candidate_email"),
            invitation_id=data.get("invitation_id"),
            review_url=data.get("review_url")
        )
    
    return False


def log_email_status_step(
    invitation_id: int,
    action: str,
    success: bool
) -> None:
    """Log email delivery status"""
    from app.models.invitation_audit_log import InvitationAuditLog
    from app import db
    
    log = InvitationAuditLog(
        invitation_id=invitation_id,
        action=action,
        extra_data={"email_delivered": success}
    )
    
    db.session.add(log)
    db.session.commit()
    
    logger.info(f"[INNGEST] Logged email status for invitation {invitation_id}: {success}")

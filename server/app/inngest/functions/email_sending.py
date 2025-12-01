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
async def send_invitation_email_workflow(ctx: inngest.Context) -> dict:
    """Send invitation email with retry logic"""
    try:
        event = ctx.event
        invitation_id = event.data.get("invitation_id")
        tenant_id = event.data.get("tenant_id")
        
        logger.info(f"[INNGEST] Sending invitation email for invitation {invitation_id}")
        logger.info(f"[INNGEST] Event data: {event.data}")
        
        # Extract all necessary data directly from the event
        to_email = event.data.get("to_email")
        candidate_name = event.data.get("candidate_name")
        onboarding_url = event.data.get("onboarding_url")
        expiry_date_str = event.data.get("expiry_date")

        if not all([to_email, candidate_name, onboarding_url, expiry_date_str]):
            logger.error(f"[INNGEST] Missing essential email data in event for invitation {invitation_id}. Event data: {event.data}")
            raise ValueError("Missing essential email data in Inngest event.")
    except Exception as e:
        logger.error(f"[INNGEST] Error in email workflow setup: {e}", exc_info=True)
        raise

    try:
        # Step 1: Send email with automatic retry
        logger.info(f"[INNGEST] About to call send_invitation_email_step for {to_email}")
        email_result = await ctx.step.run(
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
        logger.info(f"[INNGEST] Email sent result: {email_result}")
        
        # Step 2: Log email delivery
        await ctx.step.run(
            "log-email-sent",
            log_email_status_step,
            invitation_id,
            "invitation_sent",
            email_result
        )
        
        return {"invitation_id": invitation_id, "email_sent": email_result}
    except Exception as e:
        logger.error(f"[INNGEST] Error sending invitation email: {e}", exc_info=True)
        raise


@inngest_client.create_function(
    fn_id="send-submission-confirmation",
    trigger=inngest.TriggerEvent(event="email/submission-confirmation"),
    retries=3,
    name="Send Submission Confirmation Email"
)
async def send_submission_confirmation_workflow(ctx: inngest.Context) -> dict:
    """Send confirmation email after candidate submits"""
    event = ctx.event
    tenant_id = event.data.get("tenant_id")
    email = event.data.get("email")
    candidate_name = event.data.get("candidate_name")
    
    result = await ctx.step.run(
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
async def send_approval_email_workflow(ctx: inngest.Context) -> dict:
    """Send approval email to candidate"""
    event = ctx.event
    tenant_id = event.data.get("tenant_id")
    email = event.data.get("email")
    candidate_name = event.data.get("candidate_name")
    
    result = await ctx.step.run(
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
async def send_rejection_email_workflow(ctx: inngest.Context) -> dict:
    """Send rejection email to candidate"""
    event = ctx.event
    tenant_id = event.data.get("tenant_id")
    email = event.data.get("email")
    candidate_name = event.data.get("candidate_name")
    reason = event.data.get("reason")
    
    result = await ctx.step.run(
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
async def send_hr_notification_workflow(ctx: inngest.Context) -> dict:
    """Send notification to HR team"""
    event = ctx.event
    tenant_id = event.data.get("tenant_id")
    notification_type = event.data.get("notification_type")
    data = event.data.get("data", {})
    
    result = await ctx.step.run(
        "send-hr-notification",
        send_hr_notification_step,
        tenant_id,
        notification_type,
        data
    )
    
    return {"notification_sent": result}


@inngest_client.create_function(
    fn_id="send-tenant-welcome-email",
    trigger=inngest.TriggerEvent(event="email/tenant-welcome"),
    retries=3,
    name="Send Tenant Welcome Email"
)
async def send_tenant_welcome_email_workflow(ctx: inngest.Context) -> dict:
    """
    Send welcome email to new tenant admin with temporary credentials.
    Triggered when a new tenant is created via CentralD.
    
    Event data:
        - tenant_id: int - The newly created tenant ID
        - tenant_name: str - Tenant company name
        - admin_email: str - Tenant admin email
        - admin_name: str - Tenant admin full name
        - temporary_password: str - The temporary password set during creation
        - login_url: str - URL to the portal login page
    """
    event = ctx.event
    tenant_id = event.data.get("tenant_id")
    tenant_name = event.data.get("tenant_name")
    admin_email = event.data.get("admin_email")
    admin_name = event.data.get("admin_name")
    temporary_password = event.data.get("temporary_password")
    login_url = event.data.get("login_url")
    
    logger.info(f"[INNGEST] Sending tenant welcome email to {admin_email} for tenant {tenant_name}")
    
    # Validate required data
    if not all([admin_email, admin_name, tenant_name, temporary_password, login_url]):
        logger.error(f"[INNGEST] Missing required data for tenant welcome email. Event data: {event.data}")
        return {"email_sent": False, "error": "Missing required data"}
    
    result = await ctx.step.run(
        "send-tenant-welcome",
        send_tenant_welcome_step,
        admin_email,
        admin_name,
        tenant_name,
        temporary_password,
        login_url
    )
    
    logger.info(f"[INNGEST] Tenant welcome email result for {admin_email}: {result}")
    
    return {
        "email_sent": result,
        "tenant_id": tenant_id,
        "admin_email": admin_email
    }


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
    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:5174")
    return f"{frontend_url}/onboarding?token={invitation['token']}"


def send_invitation_email_step(
    tenant_id: int,
    invitation: dict,
    onboarding_url: str
) -> bool:
    """Send invitation email via SMTP"""
    try:
        from app.services.email_service import EmailService
        from datetime import datetime
        
        logger.info(f"[INNGEST STEP] send_invitation_email_step called with tenant_id={tenant_id}, invitation={invitation}, url={onboarding_url}")
        
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
        
        logger.info(f"[INNGEST STEP] Calling EmailService.send_invitation_email to={invitation['email']}, name={candidate_name}")
        
        result = EmailService.send_invitation_email(
            tenant_id=tenant_id,
            to_email=invitation['email'],
            candidate_name=candidate_name,
            onboarding_url=onboarding_url,
            expiry_date=expiry_date
        )
        
        logger.info(f"[INNGEST STEP] Email send result: {result}")
        return result
    except Exception as e:
        logger.error(f"[INNGEST STEP] Error in send_invitation_email_step: {e}", exc_info=True)
        raise


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


def send_tenant_welcome_step(
    admin_email: str,
    admin_name: str,
    tenant_name: str,
    temporary_password: str,
    login_url: str
) -> bool:
    """Send welcome email to new tenant admin"""
    from app.services.email_service import EmailService
    
    return EmailService.send_tenant_welcome_email(
        to_email=admin_email,
        admin_name=admin_name,
        tenant_name=tenant_name,
        temporary_password=temporary_password,
        login_url=login_url
    )

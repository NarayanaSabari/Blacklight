# INNGEST (Async Jobs)

**Location:** `./server/app/inngest/`  
**Files:** 9 Python modules in `functions/`

## OVERVIEW
Inngest handles async workflows: email sending, scheduled tasks (cron), background jobs.

## KEY FUNCTIONS
| Function | Type | Purpose |
|----------|------|---------|
| `send-invitation-email` | Event | Onboarding invitation emails |
| `send-approval-email` | Event | Candidate approval notifications |
| `send-rejection-email` | Event | Candidate rejection notifications |
| `send-hr-notification` | Event | Notify HR of new submissions |
| `check-expiring-invitations` | Cron | Daily reminder emails (9 AM) |
| `generate-daily-stats` | Cron | Daily recruiting metrics (8 AM) |

## FUNCTION SIGNATURE (CRITICAL)

```python
# ✅ Correct - NO type hints on ctx parameter
@inngest_client.create_function(
    fn_id="my-function",
    trigger=inngest.TriggerEvent(event="my/event")
)
async def my_function(ctx, step):  # NO type hints!
    # ctx: Inngest context (event data, run_id, etc.)
    # step: Step functions for retries, sleep, etc.
    
    data = ctx.event.data
    # ... logic
```

```python
# ❌ Incorrect - Type hints cause runtime errors with Inngest SDK
async def my_function(ctx: inngest.Context, step: inngest.Step):
    # This breaks at runtime!
```

## TRIGGERING EVENTS

```python
from app.inngest import inngest_client
import inngest

# From services, trigger events
inngest_client.send_sync(
    inngest.Event(
        name="email/invitation",
        data={
            "invitation_id": invitation.id,
            "tenant_id": tenant_id,
            "to_email": invitation.email,
            "candidate_name": f"{invitation.first_name} {invitation.last_name}",
            "onboarding_url": f"{frontend_url}/onboarding?token={invitation.token}",
            "expiry_date": invitation.expires_at.strftime("%B %d, %Y")
        }
    )
)
```

## STEP FUNCTIONS

```python
# Step functions can be sync or async
async def my_function(ctx, step):
    # Retry on failure (up to 5 times with exponential backoff)
    result = await step.run("send-email", send_email_step, email_data)
    
    # Sleep/wait
    await step.sleep("wait-1-hour", 3600)
    
    # Conditional steps
    if result.success:
        await step.run("log-success", log_success_step, result)

# Step function itself (can be sync)
def send_email_step(email_data):
    # ... send email
    return {"success": True}
```

## CRON SCHEDULE

```python
# Cron jobs use trigger schedule
@inngest_client.create_function(
    fn_id="check-expiring-invitations",
    trigger=inngest.TriggerCron(cron="0 9 * * *")  # Daily at 9 AM
)
async def check_expiring_invitations(ctx, step):
    # ... check and send reminders
```

## RETRY & RATE LIMITING

```python
@inngest_client.create_function(
    fn_id="send-email",
    trigger=inngest.TriggerEvent(event="email/send"),
    retries=5,  # Retry up to 5 times
    rate_limit=inngest.RateLimit(
        limit=50,
        period=60  # 50 emails per minute
    )
)
async def send_email(ctx, step):
    # ... send email
```

## EMAIL SERVICE INTEGRATION

```python
from app.services.email_service import send_email

async def send_invitation_email(ctx, step):
    data = ctx.event.data
    
    # Send email via step (retries on failure)
    await step.run(
        "send-invitation",
        lambda: send_email(
            to_email=data['to_email'],
            subject="Candidate Onboarding Invitation",
            template="invitation.html",
            context=data
        )
    )
```

## ANTI-PATTERNS

1. **Type hints on ctx parameter** - Causes runtime errors, keep untyped
2. **Synchronous functions** - Must be `async def`, even if no await inside
3. **Direct email sending** - Use step functions for retries
4. **Missing error handling** - Step functions auto-retry, but handle edge cases
5. **Blocking operations** - Use step.sleep() instead of time.sleep()

## DEPLOYMENT

```bash
# Deploy Inngest worker
./deploy-inngest.sh

# Uses .env.production for config
# Inngest dashboard: http://localhost:8288 (local)
```

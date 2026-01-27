# Billing & Subscription System Analysis

**Date**: 2026-01-25  
**Analyzed By**: AI Agent (Sisyphus)  
**Status**: Current State + Recommendations

---

## Executive Summary

Blacklight has a **well-architected subscription system** with 4 pre-defined plans (FREE, STARTER, PROFESSIONAL, ENTERPRISE), multi-tenant isolation, billing cycle support, and usage tracking. The system lacks **custom tenant-specific plans**, **invoice generation**, and **automated billing workflows**.

**Key Findings**:
- ✅ Solid foundation with pre-defined plans and quota enforcement
- ✅ CentralD admin UI for plan management
- ✅ Usage monitoring and limit validation before downgrades
- ❌ **Missing**: Custom plans for specific tenants
- ❌ **Missing**: Invoice generation and payment tracking
- ❌ **Missing**: Usage-based billing (overage charges)
- ❌ **Missing**: Automated limit alerts and upgrade prompts

---

## Current Implementation

### Database Models

#### SubscriptionPlan (`server/app/models/subscription_plan.py`)
```python
class SubscriptionPlan(BaseModel):
    # Identity
    name = db.Column(db.String(50), unique=True, nullable=False)  # "FREE", "STARTER", etc.
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Pricing
    price_monthly = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    price_yearly = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Resource Limits
    max_users = db.Column(db.Integer, nullable=False)
    max_candidates = db.Column(db.Integer, nullable=False)
    max_jobs = db.Column(db.Integer, nullable=False)
    max_storage_gb = db.Column(db.Integer, nullable=False, default=1)
    
    # Features (JSON)
    features = db.Column(db.JSON, nullable=True)
    # Example: {"advanced_analytics": true, "custom_branding": false}
    
    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
```

**Current Plans** (from `server/app/seeds/subscription_plans.py`):

| Plan | Monthly | Yearly | Users | Candidates | Jobs | Storage | Features |
|------|---------|--------|-------|------------|------|---------|----------|
| FREE | $0 | $0 | 5 | 50 | 5 | 1GB | None |
| STARTER | $49 | $490 | 25 | 500 | 50 | 10GB | Analytics |
| PROFESSIONAL | $149 | $1,490 | 100 | 5,000 | 500 | 100GB | Analytics, Branding, API, Support |
| ENTERPRISE | $499 | $4,990 | 999 | 99,999 | 9,999 | 1,000GB | All + Dedicated Support, SLA |

#### Tenant (`server/app/models/tenant.py`)
```python
class Tenant(BaseModel):
    # Basic Info
    name = db.Column(db.String(200), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    
    # Status
    status = db.Column(SQLEnum(TenantStatus))  # ACTIVE, SUSPENDED, INACTIVE
    
    # Subscription
    subscription_plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'))
    subscription_start_date = db.Column(db.DateTime, nullable=False)
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    
    # Billing
    billing_cycle = db.Column(SQLEnum(BillingCycle))  # MONTHLY, YEARLY
    next_billing_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    subscription_plan = db.relationship('SubscriptionPlan', back_populates='tenants')
    subscription_history = db.relationship('TenantSubscriptionHistory', ...)
```

#### TenantSubscriptionHistory (`server/app/models/tenant_subscription_history.py`)
```python
class TenantSubscriptionHistory(BaseModel):
    """Audit trail for subscription plan changes"""
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'))
    subscription_plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'))
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    changed_by = db.Column(db.String(100))  # "pm_admin:123"
    reason = db.Column(db.Text, nullable=True)
```

---

### Backend Services & APIs

#### SubscriptionPlanService (`server/app/services/subscription_plan_service.py`)

**Read-Only Operations**:
```python
def list_plans() -> List[SubscriptionPlan]:
    """Get all active plans, sorted by sort_order"""
    
def get_plan(plan_id: int) -> SubscriptionPlan:
    """Get single plan by ID"""
    
def get_usage_stats(plan_id: int) -> Dict:
    """Get how many tenants are using this plan"""
```

**Limitation**: No create/update/delete methods for plans.

#### TenantService (`server/app/services/tenant_service.py`)

**Subscription Management**:
```python
def change_subscription_plan(
    tenant_id: int,
    new_plan_id: int,
    billing_cycle: BillingCycle,
    changed_by: str,
    reason: Optional[str]
) -> Tenant:
    """
    Change tenant's subscription plan.
    
    Validates:
    - Tenant exists
    - New plan exists and is active
    - Current usage fits within new plan limits (prevents downgrades that exceed limits)
    
    Creates:
    - TenantSubscriptionHistory entry for audit trail
    - Updates tenant.subscription_plan_id, billing_cycle, next_billing_date
    """
    
def get_usage_stats(tenant_id: int) -> Dict:
    """
    Get tenant's current resource usage.
    Returns:
    {
        "user_count": 10,
        "candidates_count": 150,
        "jobs_count": 8,
        "storage_gb": 2.5,  # TODO: Not implemented yet
        "max_users": 25,  # From plan
        "max_candidates": 500,
        "max_jobs": 50,
        "max_storage_gb": 10
    }
    """
    
def suspend_tenant(tenant_id: int, reason: str, suspended_by: str):
    """Set status to SUSPENDED (e.g., payment failure, violation)"""
    
def reactivate_tenant(tenant_id: int, reactivated_by: str):
    """Set status back to ACTIVE"""
```

#### API Endpoints

**Plan Routes** (`server/app/routes/subscription_plan_routes.py`):
```
GET /api/subscription-plans              # List all active plans
GET /api/subscription-plans/{id}         # Get plan details
GET /api/subscription-plans/{id}/usage   # Get usage stats (how many tenants on this plan)
```

**Tenant Routes** (`server/app/routes/tenant_routes.py`):
```
POST /api/tenants                        # Create tenant (assigns default FREE plan)
GET /api/tenants                         # List all tenants (PM admin)
GET /api/tenants/{id}                    # Get tenant details
PUT /api/tenants/{id}                    # Update tenant info
DELETE /api/tenants/{id}                 # Delete tenant (cascade deletes)

POST /api/tenants/{id}/change-plan       # Change subscription plan
GET /api/tenants/{id}/stats              # Get usage statistics
POST /api/tenants/{id}/suspend           # Suspend tenant
POST /api/tenants/{id}/reactivate        # Reactivate tenant
GET /api/tenants/{id}/subscription-history  # Get plan change history
```

**Authentication**: All routes require `PM_ADMIN` role.

---

### Frontend (CentralD)

#### Pages

**PlansPage** (`ui/centralD/src/pages/PlansPage.tsx`):
- Read-only view of all subscription plans
- Toggle between MONTHLY/YEARLY pricing
- Shows plan limits and features
- Color-coded cards (PROFESSIONAL plan highlighted as "Most Popular")
- **Limitation**: No ability to create/edit plans

**TenantDetailPage** (`ui/centralD/src/pages/TenantDetailPage.tsx`):
- Displays tenant info, current plan, billing cycle
- Shows usage statistics with progress bars
- "Change Plan" button opens ChangePlanDialog
- Subscription history table
- **Features**:
  - Suspend/reactivate tenant
  - View all tenant users
  - View tenant settings

#### Components

**CurrentPlanCard** (`ui/centralD/src/components/tenants/CurrentPlanCard.tsx`):
- Displays current subscription plan details
- Shows pricing, billing cycle, next billing date
- "Change Plan" button
- Visual indicators for plan tier (FREE = gray, STARTER = blue, etc.)

**TenantStatsCard** (`ui/centralD/src/components/tenants/TenantStatsCard.tsx`):
- Usage metrics dashboard
- Progress bars for:
  - Users (e.g., 10/25 = 40%)
  - Candidates (e.g., 150/500 = 30%)
  - Jobs (e.g., 8/50 = 16%)
  - Storage (TODO: Not yet tracked)
- Color coding:
  - Green: 0-70%
  - Yellow: 70-90%
  - Red: 90-100%

**ChangePlanDialog** (`ui/centralD/src/components/dialogs/ChangePlanDialog.tsx`):
- Modal for changing tenant subscription plan
- **Features**:
  - Select new plan from dropdown
  - Toggle billing cycle (MONTHLY/YEARLY)
  - Plan comparison table (current vs. new)
  - **Downgrade validation**: Shows error if current usage exceeds new plan limits
  - Price difference calculation
  - Success indicator when change is valid
- **Limitation**: Only shows 4 standard plans, no custom plans

**SubscriptionHistoryTable** (`ui/centralD/src/components/tenants/SubscriptionHistoryTable.tsx`):
- Timeline of plan changes
- Shows: plan name, start date, end date, changed by, reason
- Sortable by date

---

## Limitations & Missing Features

### 1. ❌ Custom Plans for Specific Tenants

**Current State**: Only 4 hardcoded plans exist.

**Problem**:
- Cannot create tenant-specific pricing (e.g., "Acme Corp gets 150 users for $120/month")
- Cannot override limits for individual tenants without creating a new global plan
- Sales team cannot offer custom quotes

**Example Use Case**:
> "Enterprise customer wants 200 users, 10,000 candidates, but only needs 50 jobs. They negotiate $250/month. Current system cannot accommodate this."

**Impact**: Lost sales opportunities, inflexible pricing.

---

### 2. ❌ Plan Management UI

**Current State**: Plans are seeded via Python script, no admin UI to modify.

**Problem**:
- To change a plan (e.g., increase FREE plan users from 5 to 10), must:
  1. Edit `subscription_plans.py` seed file
  2. Run migration
  3. Restart services
- No self-service for PM admins

**Impact**: Slow iteration, requires developer intervention.

---

### 3. ❌ Invoice Generation

**Current State**: No invoice model or generation.

**Problem**:
- Tenants have no record of charges
- No automated billing reminders
- Manual invoice creation required

**What's Missing**:
```python
class Invoice(BaseModel):
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'))
    invoice_number = db.Column(db.String(50), unique=True)  # "INV-2026-001"
    billing_period_start = db.Column(db.DateTime)
    billing_period_end = db.Column(db.DateTime)
    amount = db.Column(db.Numeric(10, 2))
    status = db.Column(SQLEnum(InvoiceStatus))  # DRAFT, SENT, PAID, OVERDUE
    due_date = db.Column(db.DateTime)
    paid_date = db.Column(db.DateTime, nullable=True)
    line_items = db.Column(db.JSON)  # Breakdown of charges
```

**Impact**: Manual accounting, no audit trail for payments.

---

### 4. ❌ Payment Integration

**Current State**: No payment processing.

**Problem**:
- Subscription plan changes don't trigger payments
- No automatic renewal billing
- No failed payment handling

**What's Missing**:
- Stripe/PayPal integration
- Payment method storage (credit card, ACH)
- Automatic retry on failed payments
- Dunning management (suspend after 3 failed payments)

**Impact**: Manual payment collection, revenue leakage.

---

### 5. ❌ Usage-Based Billing (Overages)

**Current State**: Hard limits only.

**Problem**:
- Tenant hits 25-user limit → blocked, cannot add 26th user
- No option to charge overage fees (e.g., $5/extra user)

**Example**:
> "Startup on STARTER plan (25 users) needs to onboard 3 more users urgently. Current system blocks them. Better: charge $15 overage fee, allow 28 users."

**What's Missing**:
```python
class UsageRecord(BaseModel):
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'))
    resource_type = db.Column(db.String(50))  # "users", "candidates", "jobs"
    recorded_at = db.Column(db.DateTime)
    quantity = db.Column(db.Integer)
    plan_limit = db.Column(db.Integer)
    overage = db.Column(db.Integer)  # quantity - plan_limit
    overage_charge = db.Column(db.Numeric(10, 2), nullable=True)
```

**Impact**: Lost revenue, poor user experience.

---

### 6. ❌ Automated Limit Alerts

**Current State**: Usage metrics visible in UI, but no proactive alerts.

**Problem**:
- Tenant doesn't know they're at 23/25 users until they try to add #26
- No email warnings at 80%, 90%, 95% usage
- No upgrade prompts

**What's Missing**:
```python
# Inngest cron job
async def check_tenant_limits():
    """
    Runs daily:
    - Check all tenants' usage vs. limits
    - Send email if usage > 80%
    - Create in-app notification
    - Suggest upgrade plan
    """
```

**Impact**: Surprise blocks, poor UX, missed upgrade opportunities.

---

### 7. ❌ Storage Tracking

**Current State**: `max_storage_gb` defined in plans, but actual usage not tracked.

**Problem**:
- Cannot enforce storage limits
- TenantStatsCard shows "TODO: Not implemented"

**What's Missing**:
```python
# In TenantService
def get_storage_usage_gb(tenant_id: int) -> float:
    """
    Calculate total storage used by tenant:
    - Sum file sizes from CandidateDocument.file_path
    - Query GCS bucket for actual sizes
    - Cache result in Redis (expensive operation)
    """
```

**Impact**: Unlimited storage usage, potential cost overruns.

---

### 8. ⚠️ Plan Change Timing

**Current State**: Plan changes are immediate.

**Problem**:
- Tenant downgrades from PROFESSIONAL to STARTER
- They lose access to 4,500 candidates instantly
- No grace period to export data

**Better Approach**:
- Schedule downgrade for next billing cycle
- Allow "pending" plan changes
- Grace period for data export

**Impact**: Data loss, poor UX.

---

## Recommended Improvements

### Phase 1: Custom Plans (High Priority)

**Goal**: Allow PM admins to create tenant-specific custom plans.

#### Database Changes

**Migration**: Add custom plan support to `SubscriptionPlan`

```python
# Migration: Add is_custom and custom_for_tenant_id
class SubscriptionPlan(BaseModel):
    # ... existing fields
    
    is_custom = db.Column(db.Boolean, nullable=False, default=False, index=True)
    custom_for_tenant_id = db.Column(
        db.Integer,
        db.ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=True,  # NULL for standard plans
        index=True
    )
    
    # Relationships
    custom_tenant = db.relationship(
        'Tenant',
        foreign_keys=[custom_for_tenant_id],
        back_populates='custom_plans'
    )
```

**Validation Rules**:
- Standard plans (`is_custom=False`): Cannot be edited or deleted, `custom_for_tenant_id` must be NULL
- Custom plans (`is_custom=True`): Can be edited/deleted, `custom_for_tenant_id` must be set
- Plan names for custom plans: `{tenant_slug}_custom_{timestamp}` (ensure uniqueness)

#### Backend Services

**New Methods in `SubscriptionPlanService`**:

```python
def create_custom_plan(
    self,
    tenant_id: int,
    base_plan_id: Optional[int],  # Clone from existing plan
    plan_data: Dict[str, Any],
    created_by: str
) -> SubscriptionPlan:
    """
    Create tenant-specific custom plan.
    
    Steps:
    1. Validate tenant exists
    2. If base_plan_id provided, clone limits/features from that plan
    3. Apply custom overrides from plan_data
    4. Set is_custom=True, custom_for_tenant_id=tenant_id
    5. Generate unique name: "{tenant.slug}_custom_{uuid4()[:8]}"
    6. Save plan
    7. Optionally auto-assign to tenant
    
    Args:
        tenant_id: Tenant this plan is for
        base_plan_id: Optional plan to clone from (e.g., PROFESSIONAL)
        plan_data: {
            "display_name": "Acme Corp Custom Plan",
            "description": "Negotiated pricing for Acme",
            "price_monthly": 199.00,
            "price_yearly": 1990.00,
            "max_users": 150,
            "max_candidates": 8000,
            "max_jobs": 300,
            "max_storage_gb": 200,
            "features": {"custom_branding": true, ...}
        }
        created_by: "pm_admin:123"
    
    Returns:
        Created SubscriptionPlan
        
    Raises:
        ValueError: If tenant doesn't exist or validation fails
    """

def update_custom_plan(
    self,
    plan_id: int,
    updates: Dict[str, Any],
    updated_by: str
) -> SubscriptionPlan:
    """
    Update existing custom plan.
    
    Validates:
    - Plan exists and is_custom=True
    - If changing limits downward, check if tenant's usage still fits
    
    Raises:
        ValueError: If plan is not custom or usage exceeds new limits
    """

def delete_custom_plan(
    self,
    plan_id: int,
    deleted_by: str
) -> None:
    """
    Delete custom plan.
    
    Validates:
    - Plan is custom
    - No tenants currently using it (or optionally migrate them to default plan)
    
    Raises:
        ValueError: If plan is standard or still in use
    """

def list_plans_for_tenant(
    self,
    tenant_id: int
) -> List[SubscriptionPlan]:
    """
    Get available plans for tenant.
    
    Returns:
    - All standard plans (is_custom=False, is_active=True)
    - Custom plans for this tenant (custom_for_tenant_id=tenant_id)
    
    Excludes:
    - Custom plans for other tenants
    """
```

#### API Routes

**New Endpoints** (`/api/pm/subscription-plans`):

```python
# Create custom plan
POST /api/pm/subscription-plans/custom
Request:
{
  "tenant_id": 5,
  "base_plan_id": 3,  # Optional: clone from PROFESSIONAL
  "display_name": "Acme Corp Custom Plan",
  "description": "150 users, 8K candidates, $199/month",
  "price_monthly": 199.00,
  "price_yearly": 1990.00,
  "max_users": 150,
  "max_candidates": 8000,
  "max_jobs": 300,
  "max_storage_gb": 200,
  "features": {
    "advanced_analytics": true,
    "custom_branding": true,
    "api_access": true,
    "priority_support": true
  }
}
Response:
{
  "id": 123,
  "name": "acme_custom_a1b2c3d4",
  "display_name": "Acme Corp Custom Plan",
  "is_custom": true,
  "custom_for_tenant_id": 5,
  ...
}

# Update custom plan
PUT /api/pm/subscription-plans/{id}
Request:
{
  "price_monthly": 220.00,
  "max_users": 175
}

# Delete custom plan
DELETE /api/pm/subscription-plans/{id}
Response: 204 No Content

# List plans for tenant
GET /api/pm/tenants/{tenant_id}/available-plans
Response:
[
  {"id": 1, "name": "FREE", "is_custom": false, ...},
  {"id": 2, "name": "STARTER", "is_custom": false, ...},
  {"id": 3, "name": "PROFESSIONAL", "is_custom": false, ...},
  {"id": 4, "name": "ENTERPRISE", "is_custom": false, ...},
  {"id": 123, "name": "acme_custom_a1b2c3d4", "is_custom": true, ...}  # Only this tenant sees this
]
```

**Permissions**: All routes require `PM_ADMIN` role.

#### Frontend (CentralD)

**New Component**: `CustomPlanDialog.tsx`

**Location**: `ui/centralD/src/components/dialogs/CustomPlanDialog.tsx`

**Props**:
```typescript
interface CustomPlanDialogProps {
  mode: 'create' | 'edit';
  tenantId: number;
  plan?: SubscriptionPlan;  // For edit mode
  basePlan?: SubscriptionPlan;  // For cloning
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}
```

**UI Features**:
1. **Plan Name Input**: Display name (e.g., "Acme Corp Custom Enterprise")
2. **Base Plan Selector**: Dropdown to clone from (FREE/STARTER/PRO/ENTERPRISE)
3. **Limit Overrides**:
   - Max Users: Number input with slider
   - Max Candidates: Number input with slider
   - Max Jobs: Number input with slider
   - Max Storage: Number input (GB)
4. **Pricing Inputs**:
   - Monthly Price: Currency input ($)
   - Yearly Price: Currency input ($)
   - Auto-calculate yearly discount percentage
5. **Feature Toggles**:
   - Advanced Analytics: Checkbox
   - Custom Branding: Checkbox
   - API Access: Checkbox
   - Priority Support: Checkbox
   - (Dynamically loaded from base plan features)
6. **Description**: Textarea for internal notes
7. **Actions**:
   - "Save & Assign" button (creates plan and assigns to tenant)
   - "Save Only" button (creates plan without assigning)
   - "Cancel" button

**Validation**:
- All limits must be positive integers
- Monthly price >= $0
- Yearly price should be < (monthly * 12) for discount
- Display name required

**Update**: `TenantDetailPage.tsx`
- Add "Create Custom Plan" button next to "Change Plan"
- Show badge "Custom Plan" if tenant is on custom plan
- "Edit Custom Plan" button (only if on custom plan)

**Update**: `ChangePlanDialog.tsx`
- Fetch plans from `/api/pm/tenants/{id}/available-plans` instead of `/api/subscription-plans`
- Display custom plans with "Custom" badge
- Filter out other tenants' custom plans

**Update**: `PlansPage.tsx`
- Filter: Show only standard plans (`is_custom=false`)
- Custom plans are tenant-specific, don't show in global plan list

---

### Phase 2: Usage Monitoring Enhancements (Medium Priority)

**Goal**: Proactive alerts when tenants approach limits.

#### Automated Alerts

**New Inngest Function**: `server/app/inngest/functions/tenant_limit_alerts.py`

```python
from inngest import Inngest

@inngest_client.create_function(
    fn_id="tenant-limit-alerts",
    trigger=inngest.TriggerCron(cron="0 9 * * *")  # Daily at 9 AM
)
async def check_tenant_limits(ctx, step):
    """
    Daily cron job to check tenant resource usage.
    
    Sends alerts when usage exceeds thresholds:
    - 80%: Warning email + in-app notification
    - 90%: Urgent email + in-app notification + upgrade suggestion
    - 95%: Critical email + in-app notification + upgrade link
    - 100%: Block email + show upgrade modal on next login
    """
    tenants = await step.run("fetch-active-tenants", fetch_active_tenants)
    
    for tenant in tenants:
        usage = await step.run(f"get-usage-{tenant.id}", get_tenant_usage, tenant.id)
        
        # Check each resource type
        for resource in ['users', 'candidates', 'jobs', 'storage']:
            current = usage[f'{resource}_count']
            limit = usage[f'max_{resource}']
            percentage = (current / limit) * 100 if limit > 0 else 0
            
            if percentage >= 80:
                await step.run(
                    f"send-alert-{tenant.id}-{resource}",
                    send_limit_alert,
                    tenant,
                    resource,
                    current,
                    limit,
                    percentage
                )
```

**Email Template**: `templates/emails/limit_alert.html`

```html
Subject: [Warning] Approaching {{resource}} Limit ({{percentage}}% used)

Hi {{tenant_admin_name}},

Your {{tenant_name}} account is approaching the {{resource}} limit on your {{plan_name}} plan.

Current Usage: {{current}} / {{limit}} ({{percentage}}%)

{{#if percentage >= 95}}
🔴 CRITICAL: You're at {{percentage}}% capacity. Please upgrade immediately to avoid service disruption.
{{else if percentage >= 90}}
🟡 URGENT: You're at {{percentage}}% capacity. Consider upgrading soon.
{{else}}
⚠️ Warning: You're at {{percentage}}% capacity.
{{/if}}

{{#if suggested_plan}}
We recommend upgrading to our {{suggested_plan.display_name}} plan:
- {{suggested_plan.max_users}} users
- {{suggested_plan.max_candidates}} candidates
- {{suggested_plan.max_jobs}} jobs
- ${{suggested_plan.price_monthly}}/month

[Upgrade Now]
{{/if}}

Questions? Reply to this email or contact support.
```

#### In-App Notifications

**New Model**: `server/app/models/notification.py`

```python
class Notification(BaseModel):
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('portal_users.id'), nullable=True)  # Null = all tenant admins
    type = db.Column(db.String(50), nullable=False)  # "limit_warning", "limit_critical", etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500), nullable=True)  # CTA link
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
```

**Frontend Component**: `ui/portal/src/components/notifications/LimitWarningBanner.tsx`

```tsx
// Sticky banner at top of portal when usage > 90%
<Alert variant="warning" className="sticky top-0 z-50">
  <AlertTriangle className="h-4 w-4" />
  <AlertTitle>Approaching User Limit</AlertTitle>
  <AlertDescription>
    You're using 23/25 users (92%). 
    <Link to="/settings/billing" className="underline ml-2">
      Upgrade Plan
    </Link>
  </AlertDescription>
</Alert>
```

---

### Phase 3: Invoice Generation (Lower Priority)

**Goal**: Automated monthly/yearly invoice creation.

#### Database Model

**New Model**: `server/app/models/invoice.py`

```python
class InvoiceStatus(enum.Enum):
    DRAFT = "DRAFT"          # Created but not sent
    SENT = "SENT"            # Sent to tenant
    PAID = "PAID"            # Payment received
    OVERDUE = "OVERDUE"      # Past due date
    CANCELLED = "CANCELLED"  # Voided

class Invoice(BaseModel):
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Billing Period
    billing_period_start = db.Column(db.DateTime, nullable=False)
    billing_period_end = db.Column(db.DateTime, nullable=False)
    
    # Amounts
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax = db.Column(db.Numeric(10, 2), default=0.00)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Status
    status = db.Column(SQLEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)
    
    # Dates
    issue_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    paid_date = db.Column(db.DateTime, nullable=True)
    
    # Line Items (JSON)
    line_items = db.Column(db.JSON, nullable=False)
    # Example:
    # [
    #   {
    #     "description": "Professional Plan (Monthly)",
    #     "quantity": 1,
    #     "unit_price": 149.00,
    #     "total": 149.00
    #   },
    #   {
    #     "description": "Overage: 5 extra users @ $5/user",
    #     "quantity": 5,
    #     "unit_price": 5.00,
    #     "total": 25.00
    #   }
    # ]
    
    # Payment
    payment_method = db.Column(db.String(50), nullable=True)  # "stripe", "manual"
    payment_reference = db.Column(db.String(100), nullable=True)  # Stripe charge ID
    
    # Relationships
    tenant = db.relationship('Tenant', back_populates='invoices')
```

#### Invoice Generation Logic

**New Inngest Function**: `server/app/inngest/functions/generate_invoices.py`

```python
@inngest_client.create_function(
    fn_id="generate-monthly-invoices",
    trigger=inngest.TriggerCron(cron="0 0 1 * *")  # 1st of every month at midnight
)
async def generate_monthly_invoices(ctx, step):
    """
    Generate invoices for all active tenants.
    
    For each tenant:
    1. Check billing cycle (monthly or yearly)
    2. Calculate charges:
       - Base plan price
       - Overage fees (if applicable)
       - Taxes (if configured)
    3. Create Invoice record
    4. Send invoice email
    5. Trigger payment collection (if auto-pay enabled)
    """
    tenants = await step.run("fetch-billable-tenants", fetch_billable_tenants)
    
    for tenant in tenants:
        if tenant.billing_cycle == BillingCycle.MONTHLY:
            invoice = await step.run(
                f"generate-invoice-{tenant.id}",
                generate_invoice_for_tenant,
                tenant.id
            )
            
            await step.run(
                f"send-invoice-{tenant.id}",
                send_invoice_email,
                invoice.id
            )

def generate_invoice_for_tenant(tenant_id: int) -> Invoice:
    """
    Create invoice for tenant's current billing period.
    
    Steps:
    1. Get tenant and subscription plan
    2. Determine billing period (last month or last year)
    3. Calculate base charge (plan.price_monthly or plan.price_yearly)
    4. Check for overages (users > max_users, etc.)
    5. Calculate overage fees
    6. Calculate tax (if applicable)
    7. Create Invoice with line items
    8. Set due date (issue_date + 30 days)
    9. Set status to SENT
    """
```

#### Frontend (CentralD)

**New Page**: `InvoicesPage.tsx`
- List all invoices across all tenants
- Filter by status (PAID, OVERDUE, etc.)
- Download PDF
- Mark as paid manually

**Tenant Detail Page Update**:
- Add "Invoices" tab
- Show invoice history for this tenant
- "Generate Invoice" button for manual invoice creation

---

### Phase 4: Payment Integration (Future)

**Goal**: Automated payment collection via Stripe.

#### Stripe Integration

**New Model**: `server/app/models/payment_method.py`

```python
class PaymentMethod(BaseModel):
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'))
    stripe_payment_method_id = db.Column(db.String(100))  # "pm_xxx"
    type = db.Column(db.String(50))  # "card", "bank_account"
    last4 = db.Column(db.String(4))
    brand = db.Column(db.String(50))  # "Visa", "Mastercard"
    exp_month = db.Column(db.Integer)
    exp_year = db.Column(db.Integer)
    is_default = db.Column(db.Boolean, default=False)
```

**Stripe Webhook Handler**: `server/app/routes/webhooks.py`

```python
@bp.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events:
    - charge.succeeded: Mark invoice as PAID
    - charge.failed: Mark invoice as OVERDUE, retry
    - customer.subscription.deleted: Suspend tenant
    """
```

**Payment Flow**:
1. Invoice created → status=SENT
2. Stripe charges payment method → webhook received
3. If success: status=PAID, paid_date=now
4. If failure: status=OVERDUE, send dunning email
5. After 3 failures: Suspend tenant account

---

## Summary

### What Works Well ✅
1. **Solid foundation**: 4 pre-defined plans with clear pricing
2. **Multi-tenant isolation**: Proper scoping of subscriptions
3. **Usage tracking**: Real-time usage stats (users, candidates, jobs)
4. **Downgrade protection**: Validates usage before allowing downgrades
5. **Audit trail**: TenantSubscriptionHistory tracks all plan changes
6. **Admin UI**: CentralD provides good visibility into tenant plans

### Critical Gaps ❌
1. **No custom plans**: Cannot create tenant-specific pricing/limits
2. **No plan management UI**: Must edit seed file to change plans
3. **No invoicing**: No record of charges or payments
4. **No payment automation**: Manual payment collection
5. **No usage alerts**: Tenants discover limits when blocked
6. **Storage not tracked**: Cannot enforce storage limits

### Recommended Priority

**Immediate (Phase 1)**:
- ✅ Custom plan database schema + migration
- ✅ Custom plan backend API (create/update/delete)
- ✅ Custom plan UI in CentralD (dialog + integration)

**Next Sprint (Phase 2)**:
- ✅ Automated usage alerts (email + in-app)
- ✅ Storage usage tracking
- ✅ Upgrade prompts in portal

**Future (Phase 3-4)**:
- Invoice generation and management
- Stripe payment integration
- Usage-based billing (overages)

---

## Implementation Estimate

| Phase | Backend | Frontend | Testing | Total |
|-------|---------|----------|---------|-------|
| Phase 1 (Custom Plans) | 8 hours | 12 hours | 4 hours | **24 hours** |
| Phase 2 (Alerts) | 6 hours | 6 hours | 2 hours | **14 hours** |
| Phase 3 (Invoicing) | 12 hours | 8 hours | 4 hours | **24 hours** |
| Phase 4 (Payments) | 20 hours | 10 hours | 6 hours | **36 hours** |

**Total**: ~98 hours (~2.5 weeks for 1 developer)

---

## Conclusion

Blacklight's billing system has a **strong foundation** but lacks **flexibility for custom pricing**. Implementing custom plans (Phase 1) will unlock significant value for sales team and customer success. Usage alerts (Phase 2) will improve user experience and increase upgrade conversion. Invoicing and payment automation (Phases 3-4) can be deferred until product-market fit is established.

**Recommended Next Step**: Proceed with Phase 1 implementation (custom plans).

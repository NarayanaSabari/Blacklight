# Tenant Management System - Implementation Plan

## Overview
This plan outlines the implementation of a tenant management system for the Blacklight HR Recruiting SaaS platform. The system will enable super-admins to manage tenants (companies) through the Central Management Platform (ui/centralD), while each tenant operates independently in the main Portal application (ui/portal).

## Architecture Overview

### Multi-Tenancy Strategy
- **Database-per-tenant isolation**: Each tenant will have isolated data within the shared database using tenant_id filtering
- **Schema-based approach**: All tenant-specific tables will include a `tenant_id` foreign key
- **Central tenant registry**: A `tenants` table will store all tenant metadata and configurations
- **Separate user tables**: 
  - `pm_admin_users`: Platform Management super admins who access ui/centralD (no tenant association)
  - `portal_users`: Tenant-specific users who access ui/portal (required tenant_id, globally unique email)

### Applications
1. **Portal (ui/portal)**: Tenant-specific application for recruiters and admins
   - Users: Portal users only (from `portal_users` table)
   - Authentication: Login with email + password (email is globally unique, tenant auto-detected)
   - Data access: Scoped to user's tenant_id
   
2. **Central Dashboard (ui/centralD)**: Super-admin interface for tenant management
   - Users: Platform Management admins only (from `pm_admin_users` table)
   - Authentication: Login with email + password (no tenant required)
   - Data access: Full access to all tenants

---

## Phase 1: Database Schema & Backend Foundation

### 1.1 Database Models

#### SubscriptionPlan Model (`server/app/models/subscription_plan.py`)
```python
class SubscriptionPlan(BaseModel):
    __tablename__ = "subscription_plans"
    
    # Plan Information
    name: str (unique, required) # FREE, STARTER, PROFESSIONAL, ENTERPRISE
    display_name: str (required) # "Free Plan", "Starter Plan", etc.
    description: Text (nullable)
    
    # Pricing
    price_monthly: Decimal (required, default 0.00)
    price_yearly: Decimal (nullable)
    
    # Limits
    max_users: int (required)
    max_candidates: int (required)
    max_jobs: int (required)
    max_storage_gb: int (required, default 1)
    
    # Features (JSON for flexibility)
    features: JSON (nullable)
    # Example: {
    #   "advanced_analytics": true,
    #   "custom_branding": false,
    #   "api_access": true,
    #   "priority_support": false
    # }
    
    # Status
    is_active: Boolean (default True)
    sort_order: int (for display ordering, default 0)
    
    # Relationships
    tenants: relationship -> Tenant
    
    # Notes:
    # - Seed with default plans (FREE, STARTER, PROFESSIONAL, ENTERPRISE)
    # - Admin can create custom plans via centralD
    # - Changing plan limits affects all tenants on that plan
```

#### Tenant Model (`server/app/models/tenant.py`)
```python
class Tenant(BaseModel):
    __tablename__ = "tenants"
    
    # Basic Information
    name: str (unique, required)
    slug: str (unique, required, URL-friendly identifier)
    
    # Contact Information
    company_email: str (unique, required)
    company_phone: str (nullable)
    
    # Subscription & Status
    status: Enum (ACTIVE, SUSPENDED, INACTIVE)
    subscription_plan_id: ForeignKey (subscription_plans.id, required)
    subscription_start_date: DateTime
    subscription_end_date: DateTime (nullable)
    
    # Billing
    billing_cycle: Enum (MONTHLY, YEARLY, nullable)
    next_billing_date: DateTime (nullable)
    
    # Metadata
    settings: JSON (tenant-specific configurations)
    
    # Relationships
    subscription_plan: relationship -> SubscriptionPlan
    portal_users: relationship -> PortalUser
    subscription_history: relationship -> TenantSubscriptionHistory
    
    # Notes:
    # - Limits are accessed via subscription_plan relationship
    # - tenant.subscription_plan.max_users, etc.
```

#### TenantSubscriptionHistory Model (`server/app/models/tenant_subscription_history.py`)
```python
class TenantSubscriptionHistory(BaseModel):
    __tablename__ = "tenant_subscription_history"
    
    tenant_id: ForeignKey (tenants.id)
    subscription_plan_id: ForeignKey (subscription_plans.id)
    billing_cycle: Enum (MONTHLY, YEARLY, nullable)
    started_at: DateTime
    ended_at: DateTime (nullable)
    changed_by: ForeignKey (pm_admin_users.id)
    notes: Text (nullable)
    
    # Relationships
    tenant: relationship -> Tenant
    subscription_plan: relationship -> SubscriptionPlan
    admin: relationship -> PMAdminUser
    
    # Notes:
    # - Tracks all plan changes for audit and billing purposes
    # - ended_at is null for current active plan
```

#### PMAdminUser Model (`server/app/models/pm_admin_user.py`)
```python
class PMAdminUser(BaseModel):
    __tablename__ = "pm_admin_users"
    
    # Authentication
    email: str (unique, required, globally unique)
    password_hash: str (required)
    
    # Personal Information
    first_name: str (required)
    last_name: str (required)
    phone: str (nullable)
    
    # Status & Access
    is_active: Boolean (default True)
    last_login: DateTime (nullable)
    
    # Security
    failed_login_attempts: int (default 0)
    locked_until: DateTime (nullable)
    
    # Relationships
    audit_logs: relationship -> AuditLog
    
    # Notes:
    # - PM = Platform Management
    # - These users ONLY access ui/centralD
    # - Full super-admin privileges across all tenants
    # - No tenant_id association (they manage all tenants)
```

#### PortalUser Model (`server/app/models/portal_user.py`)
```python
class PortalUser(BaseModel):
    __tablename__ = "portal_users"
    
    # Tenant Association (REQUIRED)
    tenant_id: ForeignKey (tenants.id, required, ON DELETE CASCADE)
    
    # Authentication
    email: str (required, globally unique across all tenants)
    password_hash: str (required)
    
    # Personal Information
    first_name: str (required)
    last_name: str (required)
    phone: str (nullable)
    
    # Role & Permissions
    role: Enum (TENANT_ADMIN, RECRUITER, HIRING_MANAGER)
    
    # Status & Access
    is_active: Boolean (default True)
    last_login: DateTime (nullable)
    
    # Security
    failed_login_attempts: int (default 0)
    locked_until: DateTime (nullable)
    
    # Relationships
    tenant: relationship -> Tenant
    
    # Indexes
    __table_args__ = (
        Index('idx_portal_user_tenant_id', 'tenant_id'),
        Index('idx_portal_user_email', 'email'),
    )
    
    # Notes:
    # - These users ONLY access ui/portal
    # - Scoped to their specific tenant
    # - Email must be GLOBALLY UNIQUE (cannot duplicate across tenants)
    # - Login with email + password only (tenant auto-detected from email)
    # - Cascade delete when tenant is deleted
    # - First user created for tenant must be TENANT_ADMIN
```

### 1.2 Database Migrations
- Create Alembic migration for:
  - `subscription_plans` table (create this FIRST)
  - `tenants` table (with FK to subscription_plans)
  - `pm_admin_users` table (for centralD platform management admins)
  - `portal_users` table (for tenant users, globally unique email)
  - `tenant_subscription_history` table
- Add tenant_id to existing tenant-specific tables (candidates, jobs, interviews, etc.)
- Create indexes on tenant_id columns for performance
- Create index on subscription_plan_id in tenants table
- Add foreign key constraints with CASCADE delete for hard delete
- Create unique constraint for portal_user email (globally unique, no tenant_id in constraint)
- Create indexes for email lookups on both user tables

### 1.3 Seed Default Subscription Plans
```python
# server/app/seeds/subscription_plans.py
DEFAULT_PLANS = [
    {
        "name": "FREE",
        "display_name": "Free Plan",
        "description": "Perfect for trying out the platform",
        "price_monthly": 0.00,
        "price_yearly": 0.00,
        "max_users": 5,
        "max_candidates": 50,
        "max_jobs": 5,
        "max_storage_gb": 1,
        "features": {
            "advanced_analytics": False,
            "custom_branding": False,
            "api_access": False,
            "priority_support": False
        },
        "is_active": True,
        "sort_order": 1
    },
    {
        "name": "STARTER",
        "display_name": "Starter Plan",
        "description": "For small teams getting started",
        "price_monthly": 49.00,
        "price_yearly": 490.00,
        "max_users": 25,
        "max_candidates": 500,
        "max_jobs": 50,
        "max_storage_gb": 10,
        "features": {
            "advanced_analytics": True,
            "custom_branding": False,
            "api_access": False,
            "priority_support": False
        },
        "is_active": True,
        "sort_order": 2
    },
    {
        "name": "PROFESSIONAL",
        "display_name": "Professional Plan",
        "description": "For growing recruitment teams",
        "price_monthly": 149.00,
        "price_yearly": 1490.00,
        "max_users": 100,
        "max_candidates": 5000,
        "max_jobs": 500,
        "max_storage_gb": 100,
        "features": {
            "advanced_analytics": True,
            "custom_branding": True,
            "api_access": True,
            "priority_support": True
        },
        "is_active": True,
        "sort_order": 3
    },
    {
        "name": "ENTERPRISE",
        "display_name": "Enterprise Plan",
        "description": "For large organizations with custom needs",
        "price_monthly": 499.00,
        "price_yearly": 4990.00,
        "max_users": 999,
        "max_candidates": 99999,
        "max_jobs": 9999,
        "max_storage_gb": 1000,
        "features": {
            "advanced_analytics": True,
            "custom_branding": True,
            "api_access": True,
            "priority_support": True,
            "dedicated_support": True,
            "sla_guarantee": True
        },
        "is_active": True,
        "sort_order": 4
    }
]
```

---

## Phase 2: Backend Services & API

### 2.1 Tenant Service (`server/app/services/tenant_service.py`)

#### Core Operations
1. **Create Tenant**
   - Validate unique name, slug, email
   - Generate secure slug from company name
   - Validate subscription_plan_id exists
   - **Validate tenant admin email is globally unique** (check portal_users table)
   - Set subscription_start_date to now
   - Create tenant record
   - **Create tenant admin user in portal_users table**:
     - role: TENANT_ADMIN
     - tenant_id: newly created tenant
     - email, password_hash, first_name, last_name from request
     - is_active: True
   - Create initial subscription history entry
   - Create audit log entry
   - Return tenant object with subscription plan details and tenant admin credentials

2. **Get Tenant(s)**
   - Get single tenant by ID/slug (include subscription_plan relationship)
   - List all tenants with pagination
   - Filter by status, subscription_plan_id
   - Search by name, email
   - Include current usage stats (user count, candidate count, job count)

3. **Update Tenant**
   - Update basic information (name, email, phone, settings)
   - Cannot directly update subscription_plan_id (use change_plan instead)
   - Create audit log entry

4. **Change Subscription Plan**
   - Validate new subscription_plan_id exists
   - Check if downgrade is allowed (verify current usage fits new limits)
   - Update tenant.subscription_plan_id
   - Set new subscription dates
   - End current subscription history entry (set ended_at)
   - Create new subscription history entry
   - Create audit log entry
   - Return updated tenant with new plan details

5. **Suspend Tenant**
   - Change status to SUSPENDED
   - Prevent tenant users from logging in
   - Maintain all data (no deletion)
   - Create audit log with reason
   - Optional: Send notification email

6. **Reactivate Tenant**
   - Change status from SUSPENDED to ACTIVE
   - Re-enable user access
   - Create audit log entry

7. **Delete Tenant (Hard Delete)**
   - **CRITICAL**: This is permanent and irreversible
   - Delete cascade to all related data:
     - Portal Users (all tenant users)
     - Candidates
     - Jobs
     - Interviews
     - Documents
     - All tenant-specific data
   - Subscription history is preserved (for compliance/audit)
   - Create final audit log entry before deletion
   - Return confirmation with deleted record count

8. **Check Limits**
   - check_user_limit(tenant_id) -> bool (can add more users?)
   - check_candidate_limit(tenant_id) -> bool
   - check_job_limit(tenant_id) -> bool
   - get_usage_stats(tenant_id) -> dict (current vs max for all limits)

### 2.2 Subscription Plan Service (`server/app/services/subscription_plan_service.py`)

#### Core Operations
1. **Create Plan**
   - **DISABLED FOR PHASE 1** - Only use default plans
   - Validate unique name
   - Set limits and pricing
   - Create plan record
   - Create audit log entry

2. **Get Plan(s)**
   - Get single plan by ID/name
   - List all active plans (4 default plans only)
   - Sort by sort_order

3. **Update Plan**
   - Update pricing, limits, features, display_name
   - Note: Affects all tenants on this plan
   - Create audit log entry
   - Optional: Notify affected tenants

4. **Deactivate Plan**
   - **DISABLED FOR PHASE 1** - All default plans remain active
   - Set is_active to False
   - Prevent new tenants from selecting this plan
   - Existing tenants remain on plan
   - Create audit log entry

5. **Get Plan Usage**
   - Count tenants currently on this plan
   - Get revenue metrics (placeholder for future billing integration)

### 2.3 Pydantic Schemas

#### Subscription Plan Schemas (`server/app/schemas/subscription_plan_schema.py`)
```python
# Request Schemas
- SubscriptionPlanCreateSchema
- SubscriptionPlanUpdateSchema

# Response Schemas
- SubscriptionPlanResponseSchema
- SubscriptionPlanListResponseSchema
```

#### Tenant Schemas (`server/app/schemas/tenant_schema.py`)
```python
# Request Schemas
- TenantCreateSchema (includes subscription_plan_id, billing_cycle, tenant_admin_email, 
                      tenant_admin_password, tenant_admin_first_name, tenant_admin_last_name)
- TenantUpdateSchema
- TenantChangePlanSchema (new_plan_id, billing_cycle)
- TenantSuspendSchema (includes reason)
- TenantFilterSchema (for listing/search)

# Response Schemas
- TenantResponseSchema (includes nested subscription_plan and tenant_admin_email)
- TenantListResponseSchema (with pagination)
- TenantStatsSchema (usage statistics vs plan limits)
- TenantDeleteResponseSchema (deletion confirmation)
```

### 2.4 API Routes

#### Subscription Plan Routes (`server/app/routes/subscription_plan_routes.py`)
```
GET    /api/plans                      # List all subscription plans (4 default plans)
GET    /api/plans/:id                  # Get plan details
# POST   /api/plans                    # DISABLED - No custom plans in Phase 1
# PUT    /api/plans/:id                # DISABLED - No plan editing in Phase 1
# DELETE /api/plans/:id                # DISABLED - No plan deactivation in Phase 1
GET    /api/plans/:id/tenants          # Get tenants on this plan
```

#### Tenant Routes (`server/app/routes/tenant_routes.py`)
```
POST   /api/tenants                    # Create new tenant (includes tenant admin)
GET    /api/tenants                    # List all tenants (paginated)
GET    /api/tenants/:id                # Get tenant details (includes plan)
PUT    /api/tenants/:id                # Update tenant basic info
POST   /api/tenants/:id/change-plan    # Change subscription plan
POST   /api/tenants/:id/suspend        # Suspend tenant
POST   /api/tenants/:id/reactivate     # Reactivate tenant
DELETE /api/tenants/:id                # Hard delete tenant
GET    /api/tenants/:id/stats          # Get tenant usage stats vs limits
GET    /api/tenants/:id/history        # Get subscription history
GET    /api/tenants/:id/check-limits   # Check if tenant can add users/candidates/jobs
```

#### Portal User Routes (`server/app/routes/portal_user_routes.py`)
```
POST   /api/portal/users               # Create new user (TENANT_ADMIN only)
GET    /api/portal/users               # List tenant users (paginated)
GET    /api/portal/users/:id           # Get user details
PUT    /api/portal/users/:id           # Update user
DELETE /api/portal/users/:id           # Delete user (TENANT_ADMIN only)
POST   /api/portal/users/:id/reset-password  # Reset user password (TENANT_ADMIN only)
```

#### PM Admin Routes (`server/app/routes/pm_admin_routes.py`)
```
POST   /api/pm-admin/reset-tenant-admin-password  # Reset TENANT_ADMIN password
GET    /api/pm-admin/users             # List all PM admin users
# Additional PM admin management endpoints
```

### 2.5 Middleware & Security

#### Platform Management Admin Middleware
```python
# server/app/middleware/pm_admin.py
- Verify PM admin user is authenticated
- Check if user exists in pm_admin_users table
- Verify is_active flag
- Return 403 if not authorized
- Used ONLY for centralD API endpoints
```

#### Portal Authentication Middleware
```python
# server/app/middleware/portal_auth.py
- Verify portal user is authenticated
- Check if user exists in portal_users table
- Extract tenant_id from user (email uniquely identifies tenant)
- Verify tenant is ACTIVE (not suspended)
- Verify user is_active flag
- Return 403 if tenant is suspended or user inactive
- Used for ALL portal API endpoints
```

#### Tenant Context Middleware
```python
# server/app/middleware/tenant_context.py
- Extract tenant_id from authenticated portal user
- Validate tenant exists and is ACTIVE
- Attach tenant and tenant_id to request context
- All queries auto-filter by tenant_id
- Ensures data isolation between tenants
```

### 2.6 Portal User Service (`server/app/services/portal_user_service.py`)

#### Core Operations
1. **Create Portal User**
   - **ONLY TENANT_ADMIN can create users** (check role in middleware)
   - Validate email is globally unique
   - Check tenant user limit (current_users < max_users from plan)
   - Validate role (RECRUITER, HIRING_MANAGER - not TENANT_ADMIN)
   - Create user with tenant_id from authenticated user
   - Hash password
   - Create audit log entry
   - Return user object

2. **Get Portal User(s)**
   - Get users for authenticated user's tenant only
   - List with pagination, filtering by role
   - Search by name, email

3. **Update Portal User**
   - TENANT_ADMIN can update any user in their tenant
   - Users can update their own profile (limited fields)
   - Cannot change email (globally unique constraint)
   - Create audit log entry

4. **Delete Portal User**
   - ONLY TENANT_ADMIN can delete users
   - Cannot delete self
   - Must have at least one TENANT_ADMIN per tenant
   - Soft or hard delete based on requirements
   - Create audit log entry

5. **Reset Portal User Password**
   - ONLY TENANT_ADMIN can reset passwords for users in their tenant
   - Generate new password or allow TENANT_ADMIN to set password
   - Send password reset notification to user
   - Force password change on next login (optional)
   - Create audit log entry
   - Note: TENANT_ADMIN cannot reset their own password via portal

### 2.7 Authentication Services

#### PM Admin Authentication Service (`server/app/services/pm_admin_auth_service.py`)
```python
- login(email, password) -> PMAdminUser + JWT token
- logout(admin_id)
- refresh_token(token)
- validate_token(token) -> PMAdminUser
- JWT payload: { admin_id, email, type: 'pm_admin' }
```

#### Portal Authentication Service (`server/app/services/portal_auth_service.py`)
```python
- login(email, password) -> PortalUser + JWT token
  # Note: No tenant_slug needed - email is globally unique
  # Lookup user by email, get tenant_id from user record
- logout(user_id)
- refresh_token(token)
- validate_token(token) -> PortalUser
- JWT payload: { user_id, tenant_id, email, role, type: 'portal' }
```

---

## Phase 3: Frontend - Central Dashboard (ui/centralD)

### 3.1 Authentication

#### Admin Login
- **AdminLoginPage**: `/login`
  - Email and password fields
  - Remember me option
  - Form validation with Zod
  - Store admin JWT in localStorage/secure cookie
  - Redirect to `/tenants` on success

#### Admin Context
```typescript
// src/contexts/AdminAuthContext.tsx
- Provides: currentAdmin, isAuthenticated, login, logout
- Validates JWT on mount
- Auto-refresh token before expiry
```

### 3.2 Pages & Routes

```
/login                             # PM Admin login page
/plans                             # Subscription plans view (READ-ONLY, no create/edit)
/tenants                           # Tenant list view
/tenants/new                       # Create tenant form (includes tenant admin creation)
/tenants/:id                       # Tenant details & edit
/tenants/:id/stats                 # Usage analytics
/tenants/:id/users                 # Tenant's portal users list
/tenants/:id/users/:userId/reset-password  # Reset TENANT_ADMIN password
/profile                           # PM Admin profile settings
```

### 3.3 Components (Using shadcn/ui + Tailwind)

#### Plans Page (READ-ONLY)
- **PlansTable**: Data table displaying 4 default plans
  - Columns: Plan Name, Price (Monthly/Yearly), Users, Candidates, Jobs, Storage, Features
  - View-only - no create, edit, or delete actions
  - Show tenant count per plan

#### Tenant List Page
- **TenantTable**: Data table with:
  - Columns: Name, Email, Status, Plan, Users, Created Date
  - Filters: Status, Plan, Search
  - Sort: Name, Created Date
  - Actions: View, Edit, Suspend/Activate, Delete
- **TenantStats**: Summary cards (Total, Active, Suspended)
- **CreateTenantButton**: Opens creation dialog

#### Tenant Create/Edit Form
- **TenantForm**: Form with validation using shadcn Form + Zod
  - **Company Information Section**:
    - Company name
    - Company email
    - Company phone
  - **Subscription Plan Section**:
    - Subscription plan selector (Select/Dropdown with plan details)
      - Display: plan name, price, limits
      - Show feature comparison
    - Billing cycle selector (Monthly/Yearly radio buttons)
    - Show calculated pricing based on selection
  - **Tenant Admin Account Section** (NEW):
    - Admin email (globally unique)
    - Admin password (with strength indicator)
    - Confirm password
    - Admin first name
    - Admin last name
    - Note: "This will be the primary administrator for this tenant"
- **FormValidation**: Real-time validation with error messages
  - Check email uniqueness against portal_users table
  - Password strength requirements

#### Tenant Details Page
- **TenantHeader**: Name, status badge, action buttons
- **TenantInfoCard**: Display all tenant information
- **CurrentPlanCard**: 
  - Plan name, price, billing cycle
  - "Change Plan" button
  - Show plan features
  - Display pricing based on billing cycle
- **TenantStatsCard**: Usage metrics with progress bars
  - Users: X / max_users (from plan)
  - Candidates: X / max_candidates (from plan)
  - Jobs: X / max_jobs (from plan)
  - Storage: X GB / max_storage_gb (from plan)
  - Visual indicators (green < 80%, yellow 80-95%, red > 95%)
- **TenantUsersTable**: List of portal users for this tenant
  - Show TENANT_ADMIN users
  - "Reset Password" action for TENANT_ADMIN (PM admin only)
- **SubscriptionHistoryTable**: Timeline of plan changes
- **DangerZone**: Suspend and Delete actions with confirmations

#### Change Plan Dialog
- **PlanSelector**: Dropdown with 4 default plans only
  - Show plan details (name, price, limits)
  - Display price for selected billing cycle
- **BillingCycleToggle**: Monthly/Yearly radio buttons
  - Update pricing display when changed
- **PlanComparisonTable**: Side-by-side comparison
  - Current plan vs selected plan
  - Highlight limit changes
  - Show price difference
- **DowngradeWarning**: If usage exceeds new plan limits
  - "Cannot downgrade: You have 50 users but new plan allows 25"
  - List all violations
  - Prevent downgrade until usage is reduced
- **Confirmation**: Summary of changes and new billing

#### Confirmation Dialogs
- **SuspendDialog**: AlertDialog with reason textarea
- **DeleteDialog**: AlertDialog with:
  - Warning text about permanent deletion
  - Type-to-confirm input (enter tenant name)
  - Checkbox: "I understand this cannot be undone"
  - Red destructive button

### 3.4 State Management
- **React Query (TanStack Query)** for server state
  - Queries: getPlans, getTenants, getTenant, getTenantStats, getTenantUsers
  - Mutations: createTenant, updateTenant, changeTenantPlan, suspendTenant, deleteTenant, resetTenantAdminPassword
  - Auto-refetch and cache invalidation

### 3.5 API Client
```typescript
// src/lib/api/plans.ts
- fetchPlans() // Read-only, returns 4 default plans
- fetchPlan(id: string)
// No create, update, or deactivate in Phase 1

// src/lib/api/tenants.ts
- fetchTenants(params: FilterParams)
- fetchTenant(id: string)
- createTenant(data: TenantCreateData) // Includes tenant admin details
- updateTenant(id: string, data: TenantUpdateData)
- changeTenantPlan(id: string, planId: string, billingCycle: string)
- suspendTenant(id: string, reason: string)
- reactivateTenant(id: string)
- deleteTenant(id: string)
- fetchTenantStats(id: string)
- fetchTenantUsers(tenantId: string)
- checkTenantLimits(tenantId: string)
- checkEmailAvailability(email: string) // Check if email is available
- resetTenantAdminPassword(userId: string, newPassword: string)

// src/lib/api/pm-admin-auth.ts
- pmAdminLogin(email: string, password: string)
- pmAdminLogout()
- refreshPMAdminToken()
- getCurrentPMAdmin()
```

---

## Phase 4: Frontend - Portal (ui/portal)

### 4.1 Authentication

#### Portal User Login
- **PortalLoginPage**: `/login`
  - Email field (globally unique - no tenant slug needed)
  - Password field
  - Form validation with Zod
  - Store portal JWT in localStorage/secure cookie
  - Backend looks up tenant from email
  - Redirect to dashboard on success

#### Portal User Context
```typescript
// src/contexts/PortalAuthContext.tsx
- Provides: currentUser, tenant, isAuthenticated, login, logout
- Validates JWT on mount
- Auto-refresh token before expiry
- Checks tenant status (suspended/active)
- Tenant info extracted from JWT (includes tenant_id)
```

### 4.2 Tenant Context
- Display current tenant name in header
- Show subscription plan badge with plan name
- Show limit warnings:
  - Users approaching limit: "You're using 23/25 users. Upgrade to add more."
  - At limit: "User limit reached. Upgrade your plan to add more users."
- Tenant-specific branding (if configured in settings)
- Link to upgrade plan (for TENANT_ADMIN role)

### 4.3 Tenant Middleware
- Check tenant status on every request
- If SUSPENDED: Show "Account Suspended" page with contact info
- If INACTIVE: Redirect to error page
- If user is_active = false: Show "Account Disabled" message
- **Limit Enforcement**:
  - Before creating user: check if tenant.portal_users.count() < tenant.subscription_plan.max_users
  - Before creating candidate: check candidate limit
  - Before creating job: check job limit
  - Show upgrade prompt if limit reached

### 4.4 Role-Based Access Control
```typescript
// src/hooks/usePermissions.ts
- Check user role (TENANT_ADMIN, RECRUITER, HIRING_MANAGER)
- Control access to features:
  - TENANT_ADMIN: 
    - Full access to tenant settings
    - User management (create, update, delete users)
    - ONLY role that can add new users
    - View subscription plan and usage stats
  - RECRUITER: 
    - Candidate management
    - Job postings
    - Cannot manage users
  - HIRING_MANAGER: 
    - View candidates
    - Schedule interviews
    - Cannot manage users or jobs
```

### 4.5 User Management (TENANT_ADMIN only)
- **UsersPage**: `/users`
  - List all users in tenant
  - Create new user button (check limit first)
  - Actions: Edit, Deactivate, Delete, Reset Password
- **CreateUserForm**: 
  - Email (validate globally unique)
  - Password
  - First name, last name
  - Role selector (RECRUITER, HIRING_MANAGER - NOT TENANT_ADMIN)
  - Phone (optional)
- **ResetPasswordDialog**:
  - TENANT_ADMIN can reset password for RECRUITER and HIRING_MANAGER
  - Generate new password or allow manual entry
  - Show success message with new password
  - Option to send email notification
- **Limit Check**: Show warning if approaching user limit
  - "You have 23/25 users. Upgrade to add more."

### 4.6 Password Reset Restrictions
- **TENANT_ADMIN Password Reset**:
  - CANNOT reset own password via portal
  - Must contact PM admin via centralD
  - Prevents security bypass
- **Other User Password Reset**:
  - TENANT_ADMIN can reset passwords for RECRUITER and HIRING_MANAGER
  - Audit log created for each password reset
  - User notified of password change

---

## Phase 5: Testing Strategy

### 5.1 Backend Tests

#### Unit Tests (`tests/unit/`)
- `test_subscription_plan_service.py`: Plan read operations (no create/update/delete)
- `test_subscription_plan_schemas.py`: Plan schema validation
- `test_tenant_service.py`: All CRUD operations including tenant admin creation
- `test_tenant_schemas.py`: Schema validation including tenant admin fields
- `test_tenant_limit_checks.py`: Limit validation logic
- `test_plan_change.py`: Plan upgrade/downgrade logic with limit enforcement
- `test_pm_admin_user_service.py`: PM Admin authentication and management
- `test_portal_user_service.py`: Portal user authentication and management (globally unique email)
- `test_pm_admin_auth_service.py`: PM Admin login/logout/token validation
- `test_portal_auth_service.py`: Portal login/logout/token validation (no tenant_slug)
- `test_portal_user_permissions.py`: TENANT_ADMIN can create users, others cannot
- `test_password_reset.py`: 
  - TENANT_ADMIN can reset user passwords
  - TENANT_ADMIN cannot reset own password
  - PM Admin can reset TENANT_ADMIN passwords
- Test edge cases (duplicate emails globally, invalid plans, downgrades with violations, etc.)

#### Integration Tests (`tests/integration/`)
- `test_subscription_plan_api.py`: Plan API endpoints (read-only)
- `test_tenant_api.py`: Full tenant API endpoint testing including tenant admin creation
- `test_pm_admin_auth_api.py`: PM Admin authentication endpoints
- `test_portal_auth_api.py`: Portal authentication endpoints (login with email only)
- `test_plan_change_workflow.py`: Complete plan change flow with downgrade prevention
- `test_limit_enforcement.py`: Verify limits are enforced at API level
- `test_portal_user_management.py`: TENANT_ADMIN can CRUD users, others get 403
- `test_email_uniqueness.py`: Verify email is globally unique across all portal users
- `test_password_reset_api.py`:
  - TENANT_ADMIN can reset user passwords via API
  - Non-admin users get 403
  - PM Admin can reset TENANT_ADMIN passwords
  - Audit logs created for password resets
- Test cascade delete behavior (verify portal_users are deleted when tenant deleted)
- Test tenant isolation (portal users can't access other tenants' data)
- Test PM admin authorization (only pm_admin_users can access tenant management)
- Test portal user email global uniqueness (no duplicates across tenants)
- Test downgrade prevention when usage exceeds new plan limits
- Test tenant admin creation during tenant creation
- Test at least one TENANT_ADMIN must exist per tenant

### 5.2 Frontend Tests
- Component rendering tests (React Testing Library)
- Form validation tests
- User interaction tests (create, edit, delete flows)
- API integration tests (MSW for mocking)

---

## Phase 6: Deployment & Rollout

### 6.1 Database Migration
```bash
# Create migration
python manage.py create-migration "add_tenant_management_system"

# Review migration
# Edit if needed

# Apply migration
python manage.py migrate
```

### 6.2 Seed Initial Data
```python
# Seed subscription plans FIRST (required before tenants)
python manage.py seed-plans

# Create default PM admin user (pm_admin_users table)
python manage.py seed-pm-admin --email admin@blacklight.com --password <secure>

# Create sample tenants for testing (requires plans to exist)
# Note: Each tenant creation automatically creates a TENANT_ADMIN user
python manage.py seed-tenants --count 3

# Create additional portal users for each tenant (as TENANT_ADMIN)
# Note: Email must be globally unique
python manage.py seed-portal-users --tenant-id 1 --count 5 --role RECRUITER
```

### 6.3 Environment Configuration
```env
# Platform Management Admin Authentication
PM_ADMIN_JWT_SECRET_KEY=<secure-random-key>
PM_ADMIN_JWT_EXPIRY_HOURS=24

# Portal Authentication
PORTAL_JWT_SECRET_KEY=<secure-random-key>
PORTAL_JWT_EXPIRY_HOURS=8

# Default PM Admin User (for initial setup)
DEFAULT_PM_ADMIN_EMAIL=admin@blacklight.com
DEFAULT_PM_ADMIN_PASSWORD=<secure-password>

# Default Plan (for tenant creation if not specified)
DEFAULT_SUBSCRIPTION_PLAN=FREE

# Note: Plan limits are now stored in the database (subscription_plans table)
# and can be managed via the admin UI. No need for individual env vars.
```

---

## Security Considerations

### 1. Authorization
- **Strict Separation**: PM Admin users (centralD) and portal users (portal) use completely separate tables and JWT tokens
- **PM Admin Access**: Only pm_admin_users can access tenant management APIs
- **Tenant Isolation**: Portal users can ONLY access their own tenant's data via tenant_id filtering
- **JWT Token Types**: Include `type: 'pm_admin'` or `type: 'portal'` in payload to prevent token misuse
- **Role-Based Access**: Portal users have different permissions based on role:
  - **TENANT_ADMIN**: Only role that can manage users (create, update, delete)
  - **RECRUITER**: Candidate and job management
  - **HIRING_MANAGER**: View-only access to candidates and interviews
- **User Creation**: Only TENANT_ADMIN can create new users for their tenant

### 2. Validation
- Sanitize all inputs (prevent SQL injection, XSS)
- Validate email formats, phone numbers
- Ensure slug is URL-safe (alphanumeric + hyphens)
- Email uniqueness:
  - PM Admin emails: Globally unique
  - Portal user emails: **GLOBALLY UNIQUE** (cannot duplicate across any tenant)
  - Validate email uniqueness before creating tenant admin or any portal user

### 3. Audit Logging
- Log all tenant operations (create, update, suspend, delete)
- Log tenant admin creation during tenant creation
- Log all PM admin authentication events (login, logout, failed attempts)
- Log all portal user creation/modification by TENANT_ADMIN
- Include: actor (pm_admin_user_id or portal_user_id), timestamp, changes made, IP address
- Store in separate audit_logs table
- PM Admin users can view audit logs for compliance

### 4. Hard Delete Safety
- Require double confirmation in UI
- Type-to-confirm mechanism (enter tenant name)
- Optional: Archive data to cold storage before delete
- Log deletion with full metadata (admin_id, timestamp, reason)
- Cascade delete all portal_users and tenant-specific data
- Preserve subscription_history for compliance

### 5. Authentication Security
- **Password Hashing**: Use bcrypt with appropriate salt rounds
- **Failed Login Protection**: Lock account after 5 failed attempts for 30 minutes
- **Token Expiry**: Admin tokens expire after 24 hours, portal tokens after 8 hours
- **Refresh Tokens**: Implement refresh token flow to avoid frequent re-logins
- **Session Management**: Track active sessions and allow forced logout

---

## Success Metrics

### Performance
- Tenant list page loads in < 500ms
- Tenant creation completes in < 2s
- Hard delete (with cascade) completes in < 10s

### Data Integrity
- Zero data leaks between tenants
- All cascade deletes complete successfully
- Audit logs capture 100% of operations

### User Experience
- Intuitive UI for tenant management
- Clear feedback for all operations
- Proper error handling and messages

---

## Future Enhancements (Out of Scope for Phase 1)

1. **Soft Delete Option**: Add `deleted_at` timestamp for archiving
2. **Bulk Operations**: Suspend/delete multiple tenants
3. **Tenant Analytics Dashboard**: Charts for usage trends
4. **Automated Billing Integration**: Stripe/payment gateway (Phase 2+)
5. **Tenant Self-Service**: Allow tenants to upgrade/downgrade plans
6. **Email Notifications**: Automated emails for suspension, deletion, password resets
7. **Backup Before Delete**: Auto-export tenant data before hard delete
8. **Custom Branding**: Logo, colors per tenant
9. **API Rate Limiting**: Per-tenant rate limits
10. **Webhook Events**: Notify external systems of tenant changes
11. **Custom Subscription Plans**: Allow PM admins to create custom plans (Phase 2+)
12. **Two-Factor Authentication**: For PM admins and optionally for portal users (Phase 2+)
13. **Self-Service Password Reset**: Email-based password reset for all users (Phase 2+)
14. **Advanced Plan Management**: Edit plan limits, pricing, features (Phase 2+)

---

## Implementation Timeline

### Week 1: Backend Foundation
- Day 1-2: Database models (Tenant, AdminUser, PortalUser) and migrations
- Day 3-4: Tenant service and authentication services (admin + portal)
- Day 5: API routes, middleware (super admin, portal auth, tenant context)

### Week 2: Backend Testing & Polish
- Day 1-2: Unit tests for services (tenant, admin auth, portal auth)
- Day 3-4: Integration tests for API endpoints
- Day 5: Bug fixes, edge cases, and security hardening

### Week 3: Central Dashboard UI (ui/centralD)
- Day 1: Admin authentication (login page, auth context, protected routes)
- Day 2-3: Tenant list and table components with filters
- Day 4: Create/edit tenant forms
- Day 5: Tenant details page, stats, and delete functionality

### Week 4: Portal UI & Integration (ui/portal)
- Day 1: Portal authentication (login with tenant slug, auth context)
- Day 2: Tenant context, suspended/inactive states, role-based access
- Day 3-4: E2E testing (admin workflows, portal workflows, data isolation)
- Day 5: Documentation, deployment prep, final polish

---

## Open Questions for Approval

1. **Subscription Plans**: ✅ **UPDATED** - Plans now stored in database with full CRUD. Limits enforced via plan relationship.

2. **Tenant Slug**: Auto-generate from name, or let super admin choose? (Recommend auto-generate with option to override)

3. **Hard Delete Confirmation**: Should we require typing the tenant name exactly, or just a confirmation checkbox? (Recommend: type tenant name)

4. **Cascade Delete Scope**: Confirm entities to delete with tenant:
   - ✅ Portal Users (all users belonging to tenant)
   - ✅ Candidates
   - ✅ Jobs  
   - ✅ Interviews
   - ✅ All tenant-specific data
   - ✅ Preserve subscription_history (for compliance)

5. **Audit Log Retention**: Should audit logs for deleted tenants be preserved? (Recommend: yes, for compliance)

6. **Default Admin Creation**: Should we create a default admin user during initial setup via migration/seed, or require manual creation? (Recommend: seed command for security)

7. **Tenant Limits**: ✅ **UPDATED** - Hard limits enforced. Portal returns 403 with upgrade prompt when limit reached.

8. **Portal User Email**: ✅ **UPDATED** - Email is globally unique across ALL tenants. Login requires only email + password (no tenant slug needed).

9. **Admin User Management**: Should we implement CRUD for admin_users in Phase 1, or just use seed commands? (Recommend: Phase 1 includes admin user management for centralD)

10. **Password Reset**: ✅ **APPROVED** - Portal users: TENANT_ADMIN can reset passwords for users in their tenant. TENANT_ADMIN password: Can only be reset by PM_admin_users via centralD.

11. **Two-Factor Authentication**: ✅ **APPROVED** - Not needed for Phase 1.

12. **Plan Changes**: ✅ **APPROVED** - Prevent downgrades if current usage exceeds new plan limits. Show clear error message.

13. **Custom Plans**: ✅ **APPROVED** - No custom plans in Phase 1. Only use the 4 default plans (FREE, STARTER, PROFESSIONAL, ENTERPRISE).

14. **Plan Pricing Display**: ✅ **APPROVED** - Show pricing in tenant creation form along with plan limits for transparency.

15. **Billing Integration**: ✅ **APPROVED** - No billing integration for Phase 1. Build billing-agnostic with hooks for future integration.

16. **Tenant Admin Creation**: ✅ **APPROVED** - Tenant admin is created automatically when tenant is created via centralD. Admin details (email, password, name) required in tenant creation form.

17. **User Management Permissions**: ✅ **APPROVED** - Only TENANT_ADMIN role can create/manage users. Other roles (RECRUITER, HIRING_MANAGER) cannot access user management.

---

## Dependencies

### Backend
- SQLAlchemy (already installed)
- Alembic (already installed)
- Pydantic (already installed)
- PyJWT (for JWT tokens) - **TO BE INSTALLED**
- bcrypt or passlib (for password hashing) - **TO BE INSTALLED**

### Frontend (Both ui/centralD and ui/portal)
- shadcn/ui (already installed)
- Tailwind CSS (already installed)
- React Query (@tanstack/react-query) - **TO BE INSTALLED**
- Zod (for form validation) - **TO BE INSTALLED**
- React Hook Form (for forms) - **TO BE INSTALLED**
- React Router (for routing) - **TO BE INSTALLED**
- Axios or Fetch (for API calls) - **TO BE INSTALLED if not present**

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Accidental hard delete | High | Type-to-confirm, double confirmation, audit logs |
| Data leak between tenants | Critical | Strict middleware, separate user tables, tenant_id filtering, thorough testing |
| Portal user accessing PM admin APIs | Critical | Separate JWT token types, middleware checks user table |
| PM admin token used in portal | High | Token type validation in middleware |
| Performance issues with cascade delete | Medium | Add database indexes, implement batch deletion if needed, test with large datasets |
| PM admin account compromise | High | Implement 2FA (Phase 2), IP whitelisting, audit all actions, account lockout |
| Portal user email conflicts | Low | Global unique constraint on email, clear error messages during registration |
| Non-admin users creating users | Medium | Strict role checks in middleware, only TENANT_ADMIN can access user management endpoints |
| Tenant suspension bypass | Medium | Check tenant status on every portal API request, invalidate existing tokens |
| Plan limit bypass | Medium | Enforce limits at API level, double-check in service layer, audit violations |
| Downgrade with excess usage | Medium | Validate current usage before allowing plan change, show clear error messages |
| Changing plan affects all tenants | High | Warn admin when updating plan limits, show affected tenant count, require confirmation |

---

## Approval Checklist

- [ ] Database schema design approved
- [ ] API endpoints structure approved
- [ ] Hard delete approach confirmed (no soft delete)
- [ ] UI/UX flow approved
- [ ] Security measures adequate
- [ ] Timeline realistic
- [ ] Open questions answered ✅
- [ ] Password reset workflow approved (TENANT_ADMIN resets user passwords, PM Admin resets TENANT_ADMIN passwords)
- [ ] Plan management scope confirmed (4 default plans only, no custom plans in Phase 1)
- [ ] Billing integration deferred to Phase 2
- [ ] Pricing display in forms confirmed

---

**Status**: ⏳ Awaiting Final Approval

**Next Steps**: Upon approval, begin implementation with Phase 1 (Database Schema & Backend Foundation)

---

## Summary of Approved Decisions

1. ✅ **Portal Login**: Email + password only (no tenant slug)
2. ✅ **User Tables**: `pm_admin_users` and `portal_users` (globally unique emails)
3. ✅ **Tenant Admin Creation**: Automatic during tenant creation
4. ✅ **User Management**: Only TENANT_ADMIN can create/manage users
5. ✅ **Password Reset**: 
   - TENANT_ADMIN → resets user passwords
   - PM Admin → resets TENANT_ADMIN passwords
6. ✅ **Subscription Plans**: 4 default plans only (FREE, STARTER, PROFESSIONAL, ENTERPRISE)
7. ✅ **Plan Management**: Read-only in Phase 1, no custom plans
8. ✅ **Pricing Display**: Show pricing in forms alongside limits
9. ✅ **Downgrade Protection**: Prevent downgrades if usage exceeds new limits
10. ✅ **Billing**: No integration in Phase 1, build with hooks for future
11. ✅ **2FA**: Not needed in Phase 1
12. ✅ **Hard Delete**: Permanent deletion with type-to-confirm

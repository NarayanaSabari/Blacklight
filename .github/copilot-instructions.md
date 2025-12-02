# Blacklight AI Coding Agent Instructions

# Project Overview
Blacklight is a multi-tenant HR Bench Sales recruiting platform that streamlines candidate onboarding, management, and assignment workflows. The system supports email-based candidate invitations with self-onboarding portals, automated document collection, approval workflows, and candidate-to-recruiter assignments.

The platform includes two web applications:
- **Main Application (ui/portal)**: 
    - Tenant-specific HR/Recruiter interfaces with role-based access control
    - Candidate Management: Upload resumes, send email invitations, track onboarding status
    - Candidate Onboarding Workflow: Review submissions, approve/reject candidates, manage documents
    - Candidate Assignment: Assign approved candidates to recruiters/team leads
    - Your Candidates: View and manage assigned candidates with filtering
    - Email Invitations: Track invitation status, resend invites, manage expiry
    - Roles: TENANT_ADMIN, MANAGER, TEAM_LEAD, RECRUITER (each with specific permissions)
    
- **Central Management Platform (ui/centralD)**: 
    - Super-admin (PM_ADMIN) interface for platform management
    - Tenant CRUD: Create, update, delete tenants with subscription management
    - Global analytics and monitoring across all tenants
    - System-wide configurations and updates

## Key Workflows

### 1. Candidate Invitation & Self-Onboarding
**Actors**: HR/Admin (portal), Candidate (public onboarding portal)

**Flow**:
1. HR sends email invitation to candidate via `/api/invitations` (POST)
2. System triggers Inngest background job `email/invitation` to send email with unique token
3. Candidate receives email with onboarding link: `{FRONTEND_URL}/onboarding?token={token}`
4. Candidate fills out profile, uploads resume and documents at public onboarding portal
5. On submission, status changes to `submitted` and HR receives notification email
6. Invitation marked as `completed` after successful submission

**Key Endpoints**:
- `POST /api/invitations` - Create invitation (triggers email)
- `GET /api/invitations/by-token?token={token}` - Public endpoint to validate token
- `POST /api/invitations/{invitation_id}/submit` - Public endpoint for candidate submission
- `GET /api/invitations?status={status}` - List invitations with filtering
- `POST /api/invitations/{invitation_id}/resend` - Resend invitation email

### 2. Candidate Onboarding Review & Approval
**Actors**: MANAGER, TEAM_LEAD, TENANT_ADMIN

**Flow**:
1. After candidate submits, HR reviews submission in Onboarding Workflow tab
2. HR can view candidate details, uploaded documents (resume, ID proof, work authorization)
3. HR approves or rejects with optional reason
4. On approval: candidate status → `approved`, candidate record created, approval email sent
5. On rejection: status → `rejected`, rejection email sent with reason
6. Approved candidates appear in "All Candidates" tab and available for assignment

**Key Endpoints**:
- `GET /api/candidate-onboarding/invitations?status=submitted` - Get pending submissions
- `POST /api/candidate-onboarding/invitations/{invitation_id}/approve` - Approve candidate
- `POST /api/candidate-onboarding/invitations/{invitation_id}/reject` - Reject with reason
- `GET /api/candidate-onboarding/stats` - Get workflow statistics (pending, approved, rejected)

### 3. Candidate Assignment Management
**Actors**: MANAGER (HR), TEAM_LEAD, RECRUITER

**Assignment Hierarchy**:
- **HR → Team Lead**: HR can assign candidates directly to team leads
- **HR → Recruiter**: HR can assign candidates directly to recruiters
- **Team Lead → Recruiter**: Team Leads can reassign candidates to their team recruiters
- **Automatic Visibility**: When HR assigns to a recruiter, that recruiter's team lead automatically sees the candidate

**Flow**:
1. **HR Assignment**:
   - HR assigns approved candidate to Team Lead or Recruiter via `/api/candidate-assignments`
   - Assignment is created with status `ACTIVE` immediately (no acceptance/decline workflow)
   - If assigned to Recruiter with a team lead, the team lead can also view this candidate
   
2. **Team Lead Reassignment**:
   - Team Lead can view all candidates assigned to them
   - Team Lead can reassign candidates to any recruiter in their team
   - Original assignment remains visible to team lead for oversight
   
3. **Recruiter View**:
   - Recruiter sees candidates assigned directly by HR
   - Recruiter sees candidates reassigned by their team lead
   - Both appear in "Your Candidates" page with `ACTIVE` status

**Key Endpoints**:
- `POST /api/candidate-assignments` - Create assignment (HR or Team Lead)
- `GET /api/candidate-assignments/my-assigned?user_id={id}&status_filter={status}` - Get user's assigned candidates
- `PUT /api/candidate-assignments/{assignment_id}` - Update assignment (for reassignment)
- `DELETE /api/candidate-assignments/{assignment_id}` - Remove assignment
- `GET /api/candidate-assignments/stats` - Assignment statistics

### 4. Candidate Management (CRUD)
**Actors**: All roles with appropriate permissions

**Flow**:
1. Create candidate: Manual entry or resume upload with AI parsing (spaCy NLP)
2. Update candidate: Edit profile, skills, experience, documents
3. Delete candidate: Soft delete with cascading to related records
4. View/Search: Filter by status, skills, search by name/email

**Key Endpoints**:
- `POST /api/candidates` - Create candidate (manual or resume upload)
- `GET /api/candidates/{id}` - Get candidate details
- `PUT /api/candidates/{id}` - Update candidate
- `DELETE /api/candidates/{id}` - Delete candidate (with document cleanup)
- `GET /api/candidates?status={status}&search={query}` - List/search candidates
- `GET /api/candidates/stats` - Candidate statistics

### 5. Document Management
**Actors**: All roles, Public (for onboarding submissions)

**Flow**:
1. Documents uploaded to local storage: `server/uploads/{tenant_id}/resumes/`, `server/uploads/{tenant_id}/documents/`
2. Resume parsing: Extract name, email, phone, skills, experience using spaCy
3. Document types: `resume`, `id_proof`, `work_authorization`, `educational_certificates`, `other`
4. Public upload during onboarding uses token-based authentication

**Key Endpoints**:
- `POST /api/candidates/{candidate_id}/documents` - Upload document (authenticated)
- `POST /api/public/invitations/{invitation_id}/documents` - Upload during onboarding (public)
- `GET /api/candidates/{candidate_id}/documents` - List candidate documents
- `GET /api/documents/{document_id}/download` - Download document
- `DELETE /api/documents/{document_id}` - Delete document

## Project Architecture

Blacklight is a monorepo with a production-ready Flask backend (`server/`) and React frontend UIs (`ui/`). The server follows **Flask Application Factory** pattern with strict separation of concerns.

### Frontend Design Patterns

**UI Component System**
- **ONLY use shadcn/ui components** - Never install or use other UI libraries (Material-UI, Ant Design, Chakra, etc.)
- **ONLY use Tailwind CSS for styling** - No CSS-in-JS, styled-components, or custom CSS files except for global styles
- All components are in `ui/[portal|centralD]/src/components/ui/` - use these shadcn primitives
- Customize shadcn components via Tailwind utility classes, not inline styles
- Follow shadcn's composition patterns for building complex UIs from primitives

**Styling Guidelines**
- Use Tailwind utility classes exclusively: `className="flex items-center gap-4 p-6"`
- Leverage Tailwind's responsive modifiers: `md:grid-cols-2 lg:grid-cols-3`
- Use CSS variables from shadcn theme in `index.css` for colors (e.g., `bg-primary`, `text-muted-foreground`)
- Never write custom CSS classes unless absolutely necessary for animations
- Maintain consistent spacing using Tailwind's spacing scale (4, 8, 12, 16, etc.)

**Component Patterns**
```tsx
// Good: shadcn + Tailwind
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"

function MyComponent() {
  return (
    <Card className="w-full max-w-2xl">
      <CardHeader className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Title</h2>
      </CardHeader>
      <CardContent>
        <Button variant="default" size="lg" className="w-full">
          Action
        </Button>
      </CardContent>
    </Card>
  )
}

// Bad: Custom UI library or inline styles
import { MaterialButton } from "@mui/material"  // ❌ Never do this
<div style={{display: "flex"}}>  // ❌ Use Tailwind instead
```

### Core Architectural Patterns

**App Factory Pattern (`server/app/__init__.py`)**
- Use `create_app(config=None)` - never instantiate Flask directly
- Config auto-selected from `config.settings.Settings` based on `ENVIRONMENT` env var
- Extensions initialized globally (`db`, `cors`, `redis_client`) but bound to app in factory
- All blueprints registered in `register_blueprints()`

**Layer Separation (Critical)**
```
Routes (app/routes/) -> Services (app/services/) -> Models (app/models/)
                ↓
            Schemas (app/schemas/) for validation
```
- **Routes**: HTTP handling only, delegate to services
- **Services**: Business logic, transactions, no HTTP concerns
- **Models**: SQLAlchemy ORM, inherit from `BaseModel` for timestamps
- **Schemas**: Pydantic for request/response validation (use `.model_validate()`)

**Configuration Management**
- Three configs: `DevelopmentConfig`, `ProductionConfig`, `TestingConfig` (all extend `BaseConfig`)
- `config/settings.py` uses Pydantic `BaseSettings` for env validation with type safety
- Access via `app.config["KEY"]` in routes, or `settings` global in services

## Critical Developer Workflows

**Database Migrations (Alembic)**
```bash
# Create migration after model changes
python manage.py create-migration "description"

# Apply migrations
python manage.py migrate

# Initialize fresh DB
python manage.py init && python manage.py seed
```

**Docker Development (Preferred)**
```bash
docker-compose up -d              # Starts Flask, PostgreSQL, Redis, pgAdmin, Redis Commander
docker-compose logs -f app        # Follow app logs
docker-compose exec app python manage.py <command>
```

**Testing**
```bash
pytest                            # Run all tests
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests only
pytest --cov=app --cov-report=html  # With coverage
```

**Native Development**
```bash
# After activating venv with Python 3.11.9
pip install -r requirements-dev.txt
flask run                         # Development server with hot-reload
```

## Role-Based Access Control (RBAC)

**Portal Roles & Permissions**:
- **TENANT_ADMIN**: Full access to all tenant features, user management, settings
  - Permissions: All candidates.*, invitations.*, assignments.*, users.*, settings.*
  
- **MANAGER**: Can manage candidates, send invitations, approve onboarding, assign candidates
  - Permissions: candidates.view, candidates.create, candidates.update, candidates.delete
  - invitations.view, invitations.create, invitations.resend
  - onboarding.view, onboarding.approve, onboarding.reject
  - assignments.view, assignments.create, assignments.update
  
- **TEAM_LEAD**: Similar to MANAGER but may have team-specific restrictions
  - Permissions: candidates.view, candidates.create, candidates.update
  - invitations.view, invitations.create
  - assignments.view, assignments.create
  
- **RECRUITER**: View assigned candidates, basic candidate operations
  - Permissions: candidates.view, assignments.view

**Central Platform Roles**:
- **PM_ADMIN**: Super-admin with full platform access
  - Permissions: tenants.*, pm_admin.*, all platform management

**Middleware Stack**:
1. `@require_portal_auth` - Validates JWT token from Authorization header
2. `@with_tenant_context` - Extracts tenant_id from token, adds to `g.tenant_id`
3. `@require_permission('permission.name')` - Checks if user has specific permission
4. `@require_pm_admin` - Validates PM_ADMIN access for central platform

**Example Route Protection**:
```python
@candidate_bp.route('/<int:candidate_id>', methods=['DELETE'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.delete')
def delete_candidate(candidate_id: int):
    tenant_id = g.tenant_id  # From middleware
    success = candidate_service.delete_candidate(candidate_id, tenant_id)
    return jsonify({'message': 'Deleted'}), 200
```

## Background Jobs with Inngest

**Inngest Integration**: Asynchronous job processing for emails, scheduled tasks, and workflows

**Email Workflows** (`app/inngest/functions/email_sending.py`):
- `send-invitation-email`: Triggered by `email/invitation` event
  - Sends onboarding invitation with token link
  - Retries: 5 times with exponential backoff
  - Rate limit: 50 emails/minute
  
- `send-submission-confirmation`: Triggered by `email/submission-confirmation` event
  - Confirms candidate submission received
  
- `send-approval-email`: Triggered by `email/approval` event
  - Notifies candidate of approval
  
- `send-rejection-email`: Triggered by `email/rejection` event
  - Notifies candidate of rejection with reason
  
- `send-hr-notification`: Triggered by `email/hr-notification` event
  - Notifies HR team of new submissions

**Scheduled Tasks** (`app/inngest/functions/scheduled_tasks.py`):
- `check-expiring-invitations`: Cron job (daily 9 AM)
  - Sends reminder emails for invitations expiring in 24 hours
  
- `generate-daily-stats`: Cron job (daily 8 AM)
  - Calculates daily recruiting metrics per tenant
  - Stores in Redis with 30-day expiry

**Triggering Events**:
```python
from app.inngest import inngest_client
import inngest

# Send email invitation
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

**Inngest Function Signature**: 
- All async workflow functions use: `async def function_name(ctx, step):`
- No type hints required (Inngest SDK compatibility)
- Step functions are synchronous unless explicitly async

**Email Service** (`app/services/email_service.py`):
- SMTP configuration: Per-tenant or global from .env
- Required env vars: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- Retry logic: 3 attempts with exponential backoff
- Supports both tenant-specific SMTP and fallback to global config

## Project-Specific Conventions

**Error Handling**
- Use `error_response(message, status, details)` helper in routes (see `app/routes/api.py`)
- All errors return JSON: `{"error": "Error", "message": "...", "status": 400, "details": {...}}`
- Service layer raises `ValueError` for business logic errors, routes catch and convert to HTTP

**Database Patterns**
```python
# Models inherit from BaseModel (id, created_at, updated_at auto-included)
class MyModel(BaseModel):
    __tablename__ = "my_table"
    
# Service layer handles transactions
db.session.add(obj)
db.session.commit()  # Always in services, not routes

# Use SQLAlchemy 2.0 style queries
db.session.get(User, user_id)  # Not User.query.get()
db.paginate(db.select(User), page=1, per_page=10)

# Avoid session cache issues - use direct SELECT for critical operations
from sqlalchemy import select
stmt = select(Candidate).where(Candidate.id == id)
candidate = db.session.scalar(stmt)

# Always expire session after deletes to prevent stale cache
db.session.delete(obj)
db.session.commit()
db.session.expire_all()  # Ensures fresh data on next query
```

**Frontend State Management (React Query)**
```typescript
// Use staleTime: 0 for data that changes frequently
const { data } = useQuery({
  queryKey: ['candidates', filters],
  queryFn: () => candidateApi.listCandidates(filters),
  staleTime: 0,  // Always refetch to ensure fresh data
});

// Use refetchQueries instead of invalidateQueries for immediate updates
const deleteMutation = useMutation({
  mutationFn: (id) => candidateApi.deleteCandidate(id),
  onSuccess: async () => {
    await queryClient.refetchQueries({ queryKey: ['candidates'] });
    await queryClient.refetchQueries({ queryKey: ['candidate-stats'] });
  },
  onError: async () => {
    // Force refetch even on error to sync with actual DB state
    await queryClient.refetchQueries({ queryKey: ['candidates'] });
  }
});
```

**Resume Parsing with spaCy**
- Model: `en_core_web_sm` (must be installed in virtual environment)
- Installation: `uv pip install spacy && .venv/bin/python -m spacy download en_core_web_sm`
- Extracts: name, email, phone, skills, experience, education from PDF/DOCX
- Service: `app/services/resume_parser.py` using `app/utils/text_extractor.py`

**Validation & Serialization**
```python
# Request validation
schema = UserCreateSchema.model_validate(request.get_json())

# Response serialization
response = UserResponseSchema.model_validate(user)
return jsonify(response.model_dump()), 200
```

**Audit Logging**
- All CUD operations auto-logged via `AuditLogService.log_action()`
- Called in service layer after commit, not in routes
- Format: `{"action": "CREATE/UPDATE/DELETE", "entity_type": "User", "entity_id": 1, "changes": {...}}`

**Redis Caching**
```python
from app.utils.redis_client import cached

@cached(ttl=3600, key_prefix="users")
def expensive_operation(user_id):
    # Auto-cached with key: users:expensive_operation:user_id
    pass
```

**Middleware**
- Request logging middleware adds `request.request_id` (UUID) to all requests
- Response includes `X-Request-ID` header for tracing
- JSON content-type validation for POST/PUT/PATCH

## Testing Patterns

**Fixture Usage (`tests/conftest.py`)**
```python
def test_example(client, sample_user, db):
    # client: Flask test client
    # sample_user: Pre-created User instance
    # db: Database session with auto-cleanup
    response = client.get(f"/api/users/{sample_user.id}")
```

**Test Markers**
- `@pytest.mark.unit` - No external dependencies
- `@pytest.mark.integration` - Requires DB, Redis, etc.
- `@pytest.mark.slow` - Long-running tests

**Database in Tests**
- Testing config uses SQLite in-memory (`:memory:`)
- `db` fixture auto-creates/drops tables per test (function scope)
- Never mock the database - use real transactions for integration tests

## Key Files Reference

- `server/app/__init__.py` - App factory, extension initialization
- `server/config/settings.py` - Pydantic settings with validation
- `server/app/routes/api.py` - RESTful endpoint patterns
- `server/app/services/__init__.py` - Service layer with business logic
- `server/manage.py` - CLI for DB operations (init, seed, migrate, drop)
- `server/tests/conftest.py` - Pytest fixtures and test setup
- `server/docker-compose.yml` - Local dev stack
- `server/.env.example` - All configurable environment variables

## External Dependencies

**PostgreSQL** - Primary database (default port 5432)
**Redis** - Caching & sessions (DB 0 for cache, DB 1 for sessions)
**Gunicorn** - Production WSGI server (4 workers, sync mode)
**Nginx** - Reverse proxy with rate limiting in production

## Common Pitfalls

1. **Don't instantiate Flask directly** - Always use `create_app()`
2. **Don't commit in routes** - Database transactions belong in services
3. **Don't use old query API** - Use SQLAlchemy 2.0 style (`db.select()`, `db.session.get()`)
4. **Don't skip Pydantic validation** - All request bodies must validate via schemas
5. **Don't forget audit logging** - Call `AuditLogService.log_action()` after CUD operations
6. **Don't use `db.session.get()` for delete operations** - Use direct SELECT query to avoid session cache
7. **Don't use type hints in Inngest function signatures** - Use `async def func(ctx, step):` pattern
8. **Don't forget to expire session after deletes** - Call `db.session.expire_all()` after commit
9. **Don't use long staleTime in React Query** - Use 0 or low values for frequently changing data
10. **Don't forget to clear Python cache on Inngest changes** - Stop Docker, remove `__pycache__`, restart

## Environment Variables Priority

1. Actual environment variables
2. `.env` file (via python-dotenv)
3. Pydantic Field defaults in `config/settings.py`

Production requires: `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `REDIS_CACHE_URL`

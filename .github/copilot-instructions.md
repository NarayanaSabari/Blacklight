# Blacklight AI Coding Agent Instructions

# Project Overview
This is a HR Recruiting App, a multi-tenant, role-based web application designed for HR Bench Sales recruiters. The platform streamlines the recruitment process by providing tools for candidate management, job postings, interview scheduling, and client communications. It supports multiple tenants (companies) with isolated data and configurations, ensuring secure and efficient operations.

The platform includes two web applications:
- Main Application (ui/portal): 
	- Tenant-specific recruiter and admin interfaces
    - Candidate tracking, job management, interview scheduling, and reporting tools.
    - Role-based access control for recruiters, hiring managers, and admins.
    - Tenant user management and settings.
- Central Management Platform (ui/centralD): 
	- Super-admin interface for managing tenants, users, and global settings.
    - Analytics dashboard for monitoring platform usage and performance across tenants.
    - System-wide configurations and updates.

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
```

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

## Environment Variables Priority

1. Actual environment variables
2. `.env` file (via python-dotenv)
3. Pydantic Field defaults in `config/settings.py`

Production requires: `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `REDIS_CACHE_URL`

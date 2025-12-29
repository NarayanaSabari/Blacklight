# AGENTS.md - Development Guide for AI Agents

## 1. Project Overview
**Blacklight** is a monorepo multi-tenant HR/Recruiting platform.
- **Backend**: Flask (Python 3.11+), SQLAlchemy 2.0, PostgreSQL, Redis, Inngest (Async jobs).
- **Frontend**: React (Vite), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query.
- **Structure**:
  - `server/`: Flask backend
  - `ui/portal/`: Main recruiter portal
  - `ui/centralD/`: Super-admin dashboard
- **Deployment**: Production deployment via `./deploy.sh` script with `.env.production` config.

## 2. Production Deployment

### Deploy to Production
- **Deploy Script**: `./deploy.sh` (handles all deployment operations)
- **Environment Config**: `.env.production` (copy from `.env.production.example`)
- **Start Services**: `./deploy.sh start`
- **View Logs**: `./deploy.sh logs [service]`
- **Stop Services**: `./deploy.sh stop`
- **Run Migrations**: `./deploy.sh migrate`
- **Seed Database**: `./deploy.sh seed`
- **Rebuild Backend**: `./deploy.sh rebuild-backend`
- **Rebuild Frontend**: `./deploy.sh rebuild-frontend [portal|central]`
- **Access Inngest Dashboard**: `http://localhost:8288` (after deployment)

### Environment Variables
- All production env vars in `.env.production` (organized by container)
- Use **SCREAMING_SNAKE_CASE** for all environment variable names
- Credentials file: `./credentials/gcs-credentials.json` (GCS service account)

## 3. Build, Lint & Test Commands

### Backend (`/server`)
*Run commands from the `server` directory.*

- **Environment Setup**: Ensure `.venv` is active and requirements are installed (`pip install -r requirements-dev.txt`).
- **Run Server**: `flask run` (Starts on port 5000)
- **Linting**:
  - `flake8 .` (Check style)
  - `black .` (Formatter)
  - `isort .` (Import sorting)
- **Testing (pytest)**:
  - **Run All Tests**: `pytest`
  - **Run Single File**: `pytest tests/test_candidates.py`
  - **Run Single Function**: `pytest tests/test_candidates.py::test_create_candidate`
  - **With Coverage**: `pytest --cov=app`
  - **Important**: Tests use an in-memory SQLite DB by default (via `conftest.py`).

### Frontend (`/ui/portal` & `/ui/centralD`)
*Run commands from the respective `ui` directory.*

- **Install**: `npm install`
- **Dev Server**: `npm run dev` (Portal: usually port 5173, CentralD: 5174)
- **Linting**: `npm run lint` (ESLint)
- **Type Check**: `tsc -b`
- **Build**: `npm run build`

## 4. Code Style & Conventions

### Python (Backend)
- **Style**: Follow PEP 8. Max line length 100 (configured in `.flake8`).
- **Imports**: Sorted by `isort`. Standard lib -> Third party -> Local app.
- **Type Hints**: **MANDATORY** for all function signatures.
  - `def get_user(user_id: int) -> Optional[User]:`
- **Naming**: `snake_case` for variables/functions, `PascalCase` for classes.
- **Error Handling**: 
  - Services raise `ValueError` (or custom exceptions).
  - Routes catch exceptions and return `error_response(msg, status)` (JSON).

### TypeScript/React (Frontend)
- **Components**: Functional components only. `PascalCase` filenames.
- **Styling**: **Strictly Tailwind CSS**. No custom CSS files or `style={{}}` unless for dynamic values.
- **UI Library**: **shadcn/ui** ONLY. Do not install Material UI, Chakra, etc.
- **State**: Use `TanStack Query` (React Query) for server state. `staleTime: 0` for volatile data.
- **Imports**: Use path aliases `@/components/...`, `@/lib/...`.

## 5. Architecture & Patterns

### Flask Application Factory
- **EntryPoint**: `server/app/__init__.py` -> `create_app()`.
- **Do NOT** instantiate Flask globally (`app = Flask(__name__)` ❌).
- **Blueprints**: All routes registered via blueprints.

### Service Layer Pattern (Strict Separation)
1. **Routes** (`app/routes/`): Handle HTTP request/response, validation, and auth. **NO DB commits here.**
2. **Services** (`app/services/`): Business logic, DB transactions (`session.add`, `session.commit`).
3. **Models** (`app/models/`): SQLAlchemy definitions. Inherit from `BaseModel`.
4. **Schemas** (`app/schemas/`): Pydantic models for request/response validation.

**Example Flow**:
`Route (validate input) -> Service (perform logic + commit) -> Route (serialize output)`

### Database (SQLAlchemy 2.0)
- **Syntax**: Use 2.0 style selectors.
  - ✅ `stmt = select(User).where(User.id == 1); user = db.session.scalar(stmt)`
  - ❌ `User.query.get(1)` (Deprecated)
- **Migrations**: Always run `python manage.py create-migration "message"` after model changes.

### Authentication & RBAC
- **Middleware**:
  - `@require_portal_auth`: Validates JWT.
  - `@with_tenant_context`: Sets `g.tenant_id`.
  - `@require_permission('candidates.create')`: Checks RBAC.

## 6. Critical Pitfalls & Rules

1.  **Never commit in routes**: Database transactions belong strictly in the Service layer.
2.  **Inngest Functions**: 
    - Must be `async def`.
    - Do **not** type hint the `ctx` argument (causes runtime issues with Inngest Python SDK).
3.  **Path Handling**: Always use `pathlib` or `os.path.join`.
4.  **Session Management**: Call `db.session.expire_all()` after operations to ensure data freshness.
5.  **Security**: Never commit secrets. Use `os.environ.get()` or `current_app.config`.

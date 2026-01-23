# SERVER (Flask Backend)

**Location:** `./server/`  
**Language:** Python 3.11+  
**Framework:** Flask with Application Factory pattern

## STRUCTURE
```
server/
├── app/
│   ├── models/          # SQLAlchemy ORM (36 files) → see app/models/AGENTS.md
│   ├── services/        # Business logic (47 files) → see app/services/AGENTS.md  
│   ├── routes/          # API endpoints (29 files) → see app/routes/AGENTS.md
│   ├── schemas/         # Pydantic validation (18 files)
│   ├── inngest/         # Async jobs (9 files) → see app/inngest/AGENTS.md
│   ├── middleware/      # Auth, tenant context, RBAC
│   └── utils/           # Redis client, helpers
├── config/              # Environment-based configs (Pydantic)
├── migrations/          # Alembic DB migrations (23 versions)
├── tests/               # Pytest suite (SQLite in-memory)
└── manage.py            # CLI: init, seed, migrate, drop
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| DB models | `app/models/` | Inherit from BaseModel, multi-tenant |
| Business logic | `app/services/` | ALL commits happen here |
| API endpoints | `app/routes/` | NO commits, delegate to services |
| Request validation | `app/schemas/` | Pydantic .model_validate() |
| Async jobs | `app/inngest/` | Email, cron jobs |
| Auth/RBAC | `app/middleware/` | JWT, tenant context, permissions |

## CRITICAL RULES

### Database Transactions
- **NEVER commit in routes** - routes delegate to services
- **ALL commits in services** - `db.session.add()`, `db.session.commit()`
- **Expire after deletes** - call `db.session.expire_all()` after delete commits
- **SQLAlchemy 2.0 syntax** - use `db.session.get()`, NOT `Model.query.get()`

### Application Factory
- **Entry point**: `app/__init__.py` → `create_app()`
- **DO NOT** instantiate Flask globally
- Extensions initialized in factory, blueprints registered there

### Multi-Tenancy
- **Middleware**: `@with_tenant_context` extracts `tenant_id` from JWT → `g.tenant_id`
- **ALL operations** scoped by `tenant_id`
- Models have `tenant_id` foreign key (indexed with other fields)

## ANTI-PATTERNS (THIS PROJECT)

1. **Commits in routes** - FORBIDDEN. Services only.
2. **Old SQLAlchemy syntax** - NO `User.query.get()`, use 2.0 style
3. **Missing session expiry** - After deletes, MUST call `db.session.expire_all()`
4. **Type hints on Inngest ctx** - Causes runtime errors, keep `async def func(ctx, step):`
5. **Global Flask app** - Use `create_app()` factory pattern

## COMMANDS

```bash
# From server/ directory
flask run                              # Dev server (port 5000)
pytest                                 # All tests
pytest --cov=app                       # With coverage
python manage.py create-migration "X"  # After model changes
python manage.py migrate               # Apply migrations
flake8 . && black . && isort .         # Lint + format
```

## KEY FILES
- `manage.py` - CLI commands (init, seed, migrate, drop)
- `wsgi.py` - Production entry point (Gunicorn)
- `app/__init__.py` - Application factory
- `config/settings.py` - Pydantic environment settings
- `conftest.py` - Pytest fixtures (in-memory SQLite)

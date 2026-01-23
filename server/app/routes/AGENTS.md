# ROUTES (API Endpoints)

**Location:** `./server/app/routes/`  
**Files:** 29 Python modules (blueprints)

## OVERVIEW
HTTP request/response handling ONLY. Delegate ALL business logic to services. **NO database commits in routes.**

## KEY ROUTES
| Route | Lines | Purpose |
|-------|-------|---------|
| `scraper_monitoring_routes.py` | 1796 | Scraper monitoring dashboard |
| `candidate_routes.py` | 1596 | Candidate CRUD API |
| `job_match_routes.py` | 1169 | Job matching endpoints |
| `scraper_routes.py` | 1041 | Web scraper control |

## MIDDLEWARE STACK

Apply in this order:
```python
@blueprint.route('/endpoint', methods=['POST'])
@require_portal_auth          # 1. Validate JWT token
@with_tenant_context           # 2. Extract tenant_id → g.tenant_id
@require_permission('X.create') # 3. Check RBAC permission
def create_endpoint():
    tenant_id = g.tenant_id    # Available from middleware
    user_id = g.current_user.id
```

### Middleware Details
- `@require_portal_auth` - Validates JWT from `Authorization: Bearer <token>`
- `@with_tenant_context` - Extracts `tenant_id`, adds to `g.tenant_id`
- `@require_permission('perm.name')` - Checks user has permission
- `@require_pm_admin` - For centralD PM_ADMIN routes

## ROUTE PATTERN

```python
from app.routes.api import error_response
from app.services import candidate_service
from app.schemas.candidate import CandidateCreateSchema, CandidateResponseSchema

@candidate_bp.route('/', methods=['POST'])
@require_portal_auth
@with_tenant_context
@require_permission('candidates.create')
def create_candidate():
    # 1. Validate request
    try:
        data = CandidateCreateSchema.model_validate(request.get_json())
    except ValidationError as e:
        return error_response("Validation failed", 400, e.errors())
    
    # 2. Delegate to service (NO commit here)
    try:
        candidate = candidate_service.create_candidate(
            data.model_dump(),
            tenant_id=g.tenant_id
        )
    except ValueError as e:
        return error_response(str(e), 400)
    
    # 3. Serialize response
    response = CandidateResponseSchema.model_validate(candidate)
    return jsonify(response.model_dump()), 201
```

## ERROR HANDLING

```python
from app.routes.api import error_response

# error_response(message: str, status: int, details: dict = None)
# Returns: {"error": "Error", "message": "...", "status": 400, "details": {...}}

try:
    result = some_service.do_thing()
except ValueError as e:
    return error_response(str(e), 400)
except Exception as e:
    app.logger.error(f"Unexpected error: {e}")
    return error_response("Internal server error", 500)
```

## REQUEST VALIDATION

```python
# Use Pydantic schemas
from app.schemas.candidate import CandidateCreateSchema

data = CandidateCreateSchema.model_validate(request.get_json())
# Now data is validated and typed
```

## RESPONSE SERIALIZATION

```python
# Use Pydantic schemas for consistent responses
from app.schemas.candidate import CandidateResponseSchema

response = CandidateResponseSchema.model_validate(candidate)
return jsonify(response.model_dump()), 200

# For lists
responses = [CandidateResponseSchema.model_validate(c) for c in candidates]
return jsonify([r.model_dump() for r in responses]), 200
```

## BLUEPRINT REGISTRATION

All blueprints registered in `app/__init__.py`:
```python
from app.routes.candidate_routes import candidate_bp
app.register_blueprint(candidate_bp, url_prefix='/api/candidates')
```

## ANTI-PATTERNS

1. **db.session.commit() in routes** - FORBIDDEN. Services only.
2. **db.session.add() in routes** - FORBIDDEN. Services only.
3. **Business logic in routes** - Delegate to services
4. **Missing @with_tenant_context** - tenant_id required for multi-tenant ops
5. **Skipping validation** - Always use Pydantic schemas
6. **Building error dicts manually** - Use `error_response()` helper

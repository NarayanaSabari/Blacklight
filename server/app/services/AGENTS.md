# SERVICES (Business Logic Layer)

**Location:** `./server/app/services/`  
**Files:** 47 Python modules

## OVERVIEW
Service layer handles ALL business logic and database transactions. Routes delegate here. NO HTTP concerns.

## KEY SERVICES
| Service | Lines | Purpose |
|---------|-------|---------|
| `invitation_service.py` | 1377 | Candidate invitations, onboarding workflow |
| `submission_service.py` | 1160 | Candidate submission handling |
| `job_matching_service.py` | 1126 | AI-powered job matching logic |
| `candidate_service.py` | 1071 | Candidate CRUD, resume parsing |
| `tenant_service.py` | 947 | Tenant management, subscription |
| `candidate_assignment_service.py` | 919 | Assign candidates to recruiters |
| `email_sync_service.py` | 921 | Email integration (IMAP/SMTP) |

## PATTERNS

### Transaction Ownership
```python
# Services ONLY place where commits happen
def create_candidate(data: dict, tenant_id: int) -> Candidate:
    candidate = Candidate(**data, tenant_id=tenant_id)
    db.session.add(candidate)
    db.session.commit()  # ✅ ONLY in services
    db.session.refresh(candidate)
    return candidate
```

### Multi-Tenant Scoping
```python
# ALL operations filtered by tenant_id
def get_candidates(tenant_id: int) -> list[Candidate]:
    stmt = select(Candidate).where(Candidate.tenant_id == tenant_id)
    return db.session.scalars(stmt).all()
```

### Session Expiry After Deletes
```python
# MUST expire session after delete to clear cache
def delete_candidate(candidate_id: int, tenant_id: int) -> bool:
    stmt = select(Candidate).where(
        Candidate.id == candidate_id,
        Candidate.tenant_id == tenant_id
    )
    candidate = db.session.scalar(stmt)
    
    db.session.delete(candidate)
    db.session.commit()
    db.session.expire_all()  # ✅ CRITICAL after deletes
    return True
```

### Error Handling
```python
# Services raise ValueError for business logic errors
# Routes catch and convert to HTTP responses
def approve_candidate(invitation_id: int, tenant_id: int):
    invitation = get_invitation(invitation_id, tenant_id)
    
    if invitation.status != 'pending_review':
        raise ValueError(f"Cannot approve invitation with status {invitation.status}")
    
    # ... business logic
    db.session.commit()
```

## ANTI-PATTERNS

1. **Routes calling db.session.commit()** - Services only
2. **Forgetting db.session.expire_all()** - After deletes, prevents stale cache
3. **Using db.session.get() for deletes** - Session cache can be stale, use SELECT query
4. **Missing tenant_id filter** - ALL queries must scope by tenant
5. **HTTP response building** - Services return data, routes handle HTTP

## METHOD SIGNATURES

Standard patterns:
```python
# Create
def create_X(data: dict, tenant_id: int) -> Model

# Read
def get_X(x_id: int, tenant_id: int) -> Optional[Model]
def list_X(tenant_id: int, filters: dict) -> list[Model]

# Update  
def update_X(x_id: int, data: dict, tenant_id: int) -> Model

# Delete
def delete_X(x_id: int, tenant_id: int) -> bool
```

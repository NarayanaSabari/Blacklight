# MODELS (SQLAlchemy ORM)

**Location:** `./server/app/models/`  
**Files:** 36 Python modules

## OVERVIEW
SQLAlchemy 2.0 models with multi-tenant architecture. All inherit from BaseModel.

## KEY MODELS
| Model | Purpose |
|-------|---------|
| `Candidate` | Candidate profiles, resumes, skills |
| `Invitation` | Email invitations for onboarding |
| `User` | Portal users (TENANT_ADMIN, MANAGER, RECRUITER, etc.) |
| `Tenant` | Multi-tenant isolation, subscriptions |
| `Job` | Job postings, requirements |
| `Submission` | Candidate-job submissions |
| `CandidateAssignment` | Assign candidates to recruiters |
| `PlatformUser` | PM_ADMIN users for centralD |

## PATTERNS

### BaseModel Inheritance
```python
# ALL models inherit from BaseModel
# Auto-includes: id, created_at, updated_at
from app.models.base import BaseModel

class MyModel(BaseModel):
    __tablename__ = "my_table"
    
    # No need to define id, created_at, updated_at
    name = db.Column(db.String(255), nullable=False)
```

### Multi-Tenant Pattern
```python
# Most models have tenant_id foreign key
class Candidate(BaseModel):
    __tablename__ = "candidates"
    
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    # ... other fields
    
    # Index tenant_id with frequently queried fields
    __table_args__ = (
        db.Index('idx_candidates_tenant_status', 'tenant_id', 'status'),
    )
```

### Relationships
```python
# Use back_populates for bidirectional relationships
class Tenant(BaseModel):
    candidates = db.relationship(
        'Candidate',
        back_populates='tenant',
        lazy='dynamic'  # Don't auto-load
    )

class Candidate(BaseModel):
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'))
    tenant = db.relationship('Tenant', back_populates='candidates')
```

### Soft Deletes
```python
# Some models use soft delete pattern
class Candidate(BaseModel):
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Query must filter out soft-deleted records
    # stmt = select(Candidate).where(
    #     Candidate.tenant_id == tenant_id,
    #     Candidate.is_deleted == False
    # )
```

## SQLALCHEMY 2.0 SYNTAX

```python
# ✅ Correct (2.0 style)
stmt = select(User).where(User.id == user_id)
user = db.session.scalar(stmt)

users = db.session.scalars(select(User).where(User.tenant_id == tenant_id)).all()

# ❌ Incorrect (deprecated)
user = User.query.get(user_id)
users = User.query.filter_by(tenant_id=tenant_id).all()
```

## INDEXING STRATEGY

Index patterns:
```python
__table_args__ = (
    # Tenant isolation + frequently filtered fields
    db.Index('idx_X_tenant_status', 'tenant_id', 'status'),
    db.Index('idx_X_tenant_created', 'tenant_id', 'created_at'),
    
    # Unique constraints with tenant scoping
    db.UniqueConstraint('tenant_id', 'email', name='uq_X_tenant_email'),
)
```

## ANTI-PATTERNS

1. **Missing tenant_id** - Most models need multi-tenant scoping
2. **Forgetting indexes** - tenant_id + other fields should be indexed together
3. **Old query syntax** - Use SQLAlchemy 2.0 style
4. **Eager loading** - Default to lazy='dynamic' for collections
5. **Missing back_populates** - Relationships should be bidirectional

# Critical Issues Analysis - Blacklight Backend

**Generated**: 2026-01-23  
**Scope**: Full backend codebase audit

---

## EXECUTIVE SUMMARY

Found **5 categories** of critical architectural violations across the codebase:

| Category | Count | Severity | Status |
|----------|-------|----------|--------|
| Route commits | 19 | 🔴 CRITICAL | 57% fixed (25/44) |
| Route rollbacks | 20 | 🟠 HIGH | Not started |
| Route db.session.add() | 4 | 🔴 CRITICAL | Not started |
| Route db.session.delete() | 1 | 🔴 CRITICAL | Not started |
| Old SQLAlchemy syntax | 105 | 🟡 MEDIUM | Not started |
| Missing expire_all() | ~14 | 🟠 HIGH | Not started |

**Total Issues**: ~163 violations

---

## 1. ROUTE COMMITS (19 remaining)

**Rule Violated**: Routes MUST NOT call `db.session.commit()`. All commits belong in services.

### Remaining Files:
```
server/app/routes/candidate_routes.py:98          (line 98)
server/app/routes/candidate_routes.py:389         (line 389)
server/app/routes/candidate_routes.py:547         (line 547)
server/app/routes/candidate_routes.py:717         (line 717)
server/app/routes/candidate_routes.py:758         (line 758)
server/app/routes/candidate_routes.py:943         (line 943)
server/app/routes/candidate_routes.py:1040        (line 1040)
server/app/routes/candidate_routes.py:1507        (line 1507)
server/app/routes/candidate_routes.py:1584        (line 1584)

server/app/routes/scraper_monitoring_routes.py:521    (line 521)
server/app/routes/scraper_monitoring_routes.py:569    (line 569)
server/app/routes/scraper_monitoring_routes.py:607    (line 607)
server/app/routes/scraper_monitoring_routes.py:662    (line 662)
server/app/routes/scraper_monitoring_routes.py:715    (line 715)
server/app/routes/scraper_monitoring_routes.py:1292   (line 1292)
server/app/routes/scraper_monitoring_routes.py:1329   (line 1329)
server/app/routes/scraper_monitoring_routes.py:1369   (line 1369)
server/app/routes/scraper_monitoring_routes.py:1402   (line 1402)
server/app/routes/scraper_monitoring_routes.py:1445   (line 1445)
```

### Impact:
- **Architectural**: Violates service layer pattern
- **Testing**: Routes become untestable (DB coupling)
- **Transactions**: No proper transaction boundaries
- **Rollback**: If later code fails, partial commits leave DB inconsistent

### Fix Strategy:
Same pattern as completed files:
1. Identify business logic in route
2. Create/extend service method with commit
3. Route delegates to service
4. Route handles HTTP serialization only

---

## 2. ROUTE ROLLBACKS (20 instances)

**Rule Violated**: Routes MUST NOT call `db.session.rollback()`. Services handle rollbacks.

### Affected Files:
```
server/app/routes/candidate_routes.py:631
server/app/routes/invitation_routes.py:117
server/app/routes/invitation_routes.py:278
server/app/routes/invitation_routes.py:339
server/app/routes/invitation_routes.py:372
server/app/routes/invitation_routes.py:532
server/app/routes/invitation_routes.py:713
server/app/routes/invitation_routes.py:798
server/app/routes/job_match_routes.py:780
server/app/routes/job_match_routes.py:1131
server/app/routes/scraper_monitoring_routes.py:541
server/app/routes/scraper_monitoring_routes.py:581
server/app/routes/scraper_monitoring_routes.py:618
server/app/routes/scraper_monitoring_routes.py:687
server/app/routes/scraper_monitoring_routes.py:721
server/app/routes/scraper_monitoring_routes.py:1302
server/app/routes/scraper_monitoring_routes.py:1339
server/app/routes/scraper_monitoring_routes.py:1379
server/app/routes/scraper_monitoring_routes.py:1412
server/app/routes/scraper_monitoring_routes.py:1455
```

### Impact:
- Routes managing transaction lifecycle (wrong layer)
- Service exceptions don't trigger proper cleanup
- Inconsistent error handling

### Fix Strategy:
- Remove all `db.session.rollback()` from routes
- Services handle rollback in exception blocks
- Routes just catch exceptions and return error responses

---

## 3. ROUTE DB.SESSION.ADD() (4 instances)

**Rule Violated**: Routes MUST NOT call `db.session.add()`. This is business logic.

### Locations:
```
server/app/routes/candidate_routes.py:97
server/app/routes/candidate_routes.py:716
server/app/routes/candidate_routes.py:753
server/app/routes/scraper_monitoring_routes.py:520
```

### Impact:
- Route is creating database objects (business logic leak)
- Violates single responsibility principle
- Makes testing impossible without DB

### Fix Strategy:
Move entity creation to services:
```python
# ❌ BEFORE (in route)
candidate = Candidate(**data)
db.session.add(candidate)
db.session.commit()

# ✅ AFTER (in service)
def create_candidate(self, data: dict, tenant_id: int) -> Candidate:
    candidate = Candidate(**data, tenant_id=tenant_id)
    db.session.add(candidate)
    db.session.commit()
    return candidate
```

---

## 4. ROUTE DB.SESSION.DELETE() (1 instance)

**Rule Violated**: Routes MUST NOT call `db.session.delete()`. Deletion is business logic.

### Location:
```
server/app/routes/scraper_monitoring_routes.py:1401
```

### Impact:
- Same as db.session.add() - business logic in wrong layer

### Fix Strategy:
Create service method for deletion:
```python
# Service
def delete_entry(self, entry_id: int) -> bool:
    entry = db.session.get(Entry, entry_id)
    if not entry:
        raise ValueError("Entry not found")
    db.session.delete(entry)
    db.session.commit()
    db.session.expire_all()  # Clear cache
    return True
```

---

## 5. OLD SQLALCHEMY SYNTAX (105 instances)

**Rule Violated**: Must use SQLAlchemy 2.0 style queries. Old `Model.query` syntax is deprecated.

### Distribution:
- **Routes**: 12 instances
- **Services**: 50 instances  
- **Other files**: 43 instances

### Sample Violations:
```python
# ❌ OLD (deprecated)
user = User.query.get(user_id)
users = User.query.filter_by(tenant_id=tenant_id).all()
session = ScrapeSession.query.filter_by(session_id=uuid).first()

# ✅ NEW (SQLAlchemy 2.0)
user = db.session.get(User, user_id)
users = db.session.scalars(select(User).where(User.tenant_id == tenant_id)).all()
session = db.session.scalar(select(ScrapeSession).where(ScrapeSession.session_id == uuid))
```

### Impact:
- **Deprecation**: Will break in future SQLAlchemy versions
- **Performance**: Old syntax has overhead
- **Type Safety**: New syntax better with type checkers

### Files with Most Violations:
```
server/app/routes/scraper_monitoring_routes.py (7 instances)
server/app/routes/scraper_routes.py (5 instances)
server/app/services/* (50 instances across multiple files)
```

---

## 6. MISSING DB.SESSION.EXPIRE_ALL() (~14 instances)

**Rule Violated**: MUST call `db.session.expire_all()` after delete operations.

### Statistics:
- **Delete operations in services**: 20
- **expire_all() calls**: 6
- **Missing**: ~14 instances

### Why This Matters:
SQLAlchemy caches objects in session. After deletion:
```python
# Without expire_all()
user = db.session.get(User, 1)  # Returns cached (deleted) object
# user is NOT None, even though deleted from DB!

# With expire_all()
db.session.delete(user)
db.session.commit()
db.session.expire_all()  # Clears cache
user = db.session.get(User, 1)  # None (correct)
```

### Impact:
- **Data Integrity**: Queries return stale/deleted objects
- **Testing**: Tests fail intermittently
- **Production Bugs**: Race conditions, phantom reads

### Services to Audit:
Need to check all services with delete operations for missing `expire_all()`.

---

## PRIORITY MATRIX

### P0 - Critical (Blocking Issues)
1. **Route commits** (19 remaining)
   - Breaks service layer pattern
   - Must fix before production

2. **Route db.session.add()** (4 instances)
   - Same severity as commits

3. **Route db.session.delete()** (1 instance)
   - Same severity as commits

### P1 - High (Architecture Violations)
4. **Route rollbacks** (20 instances)
   - Couples routes to DB transaction management
   - Should be fixed with commits

5. **Missing expire_all()** (~14 instances)
   - Causes subtle data integrity bugs
   - Hard to debug in production

### P2 - Medium (Technical Debt)
6. **Old SQLAlchemy syntax** (105 instances)
   - Deprecated, will break eventually
   - Can be migrated incrementally

---

## RECOMMENDED FIX ORDER

### Phase 1: Complete Route Refactoring (CURRENT)
- ✅ Fixed: 25 commits across 9 files (57%)
- 🔄 In Progress: 19 commits in 2 files
  - `candidate_routes.py` (9 commits)
  - `scraper_monitoring_routes.py` (10 commits)
- **Also fix while refactoring**:
  - 4x `db.session.add()` 
  - 1x `db.session.delete()`
  - 20x `db.session.rollback()`

**Estimated Effort**: 2-3 sessions (similar to completed work)

### Phase 2: Service Layer Cleanup
- Audit all 20 delete operations
- Add missing `db.session.expire_all()` calls (~14 instances)
- Add proper error handling in services

**Estimated Effort**: 1 session

### Phase 3: SQLAlchemy Migration (Optional)
- Replace old `.query` syntax with 2.0 style
- 105 instances to migrate
- Can be done incrementally

**Estimated Effort**: 3-4 sessions (mechanical changes)

---

## VERIFICATION COMMANDS

```bash
# Route commits
grep -rn "db.session.commit()" server/app/routes/*.py | grep -v "AGENTS.md" | wc -l

# Route rollbacks
grep -rn "db.session.rollback()" server/app/routes/*.py | grep -v "AGENTS.md" | wc -l

# Route adds
grep -rn "db.session.add(" server/app/routes/*.py | grep -v "AGENTS.md" | wc -l

# Route deletes
grep -rn "db.session.delete(" server/app/routes/*.py | grep -v "AGENTS.md" | wc -l

# Old query syntax
grep -rn "\.query\." server/app/ --include="*.py" | wc -l

# Service deletes
grep -n "db.session.delete(" server/app/services/*.py | wc -l

# expire_all calls
grep -n "db.session.expire_all()" server/app/services/*.py | wc -l
```

---

## FILES REQUIRING IMMEDIATE ATTENTION

### 1. candidate_routes.py
- **9 commits** (route layer violations)
- **3 db.session.add()** calls
- **1 db.session.rollback()** call
- **Most complex route file** - 1596 lines

### 2. scraper_monitoring_routes.py  
- **10 commits** (route layer violations)
- **1 db.session.add()** call
- **1 db.session.delete()** call
- **10 db.session.rollback()** calls
- **Largest route file** - 1796 lines

### 3. invitation_routes.py
- **7 db.session.rollback()** calls
- No commits (already clean from previous work?)

### 4. job_match_routes.py
- **2 db.session.rollback()** calls
- Already has commits removed (from our work)

---

## RISK ASSESSMENT

### Current State Risks:

**Data Integrity** 🔴 HIGH
- Missing expire_all() can cause phantom reads
- Partial commits without proper transaction boundaries

**Maintainability** 🔴 HIGH  
- Business logic scattered across routes and services
- Impossible to unit test routes (DB required)

**Scalability** 🟠 MEDIUM
- Old SQLAlchemy syntax has performance overhead
- Deprecated APIs will break in future versions

**Production Incidents** 🟠 MEDIUM
- Race conditions from stale cache
- Inconsistent error handling

### Post-Fix Benefits:

✅ **Testability**: Routes become pure HTTP handlers  
✅ **Transactions**: Proper boundaries in service layer  
✅ **Cache Safety**: expire_all() prevents phantom reads  
✅ **Type Safety**: SQLAlchemy 2.0 syntax better typed  
✅ **Maintainability**: Clear separation of concerns

---

## INNGEST FUNCTIONS (NOT A VIOLATION)

**Finding**: 24 commits found in `server/app/inngest/**/*.py`

**Status**: ✅ **ACCEPTABLE**

**Reason**: Inngest functions are async background workers, not HTTP routes. They're allowed to have commits because they:
1. Run in separate transaction contexts
2. Have retry/failure handling built-in
3. Are not part of HTTP request/response cycle
4. Follow different architectural patterns (event-driven)

**No action required** for Inngest commits.

---

## NEXT STEPS

1. **Continue Phase 1**: Finish last 2 route files
   - `candidate_routes.py` (9 commits + 3 adds + 1 rollback)
   - `scraper_monitoring_routes.py` (10 commits + 1 add + 1 delete + 10 rollbacks)

2. **Service Layer Audit**: Fix missing expire_all() (~14 instances)

3. **SQLAlchemy Migration**: (Optional) Migrate to 2.0 syntax (105 instances)

4. **Final Verification**: Run all commands to ensure 0 violations

---

**Document Status**: Complete analysis  
**Last Updated**: 2026-01-23  
**Analyst**: Sisyphus (AI Agent)

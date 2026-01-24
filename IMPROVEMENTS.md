# BLACKLIGHT - SCALABILITY & CODE QUALITY IMPROVEMENTS

**Generated**: 2026-01-23  
**Codebase Analyzed**: 155 Python files (60K+ lines), 173 TypeScript files  
**Analysis Scope**: Database queries, transactions, caching, security, error handling, frontend performance, async jobs

---

## TABLE OF CONTENTS

1. [Critical Issues (Fix Immediately)](#1-critical-issues-fix-immediately)
2. [High Priority - Database & Performance](#2-high-priority---database--performance)
3. [High Priority - Security](#3-high-priority---security)
4. [Medium Priority - Code Quality](#4-medium-priority---code-quality)
5. [Medium Priority - Frontend Performance](#5-medium-priority---frontend-performance)
6. [Low Priority - Technical Debt](#6-low-priority---technical-debt)
7. [Implementation Checklist](#7-implementation-checklist)

---

## 1. CRITICAL ISSUES (Fix Immediately)

### 🔴 1.1 Bare Exception Handling (Security Risk)

**Issue**: Bare `except:` clause silently swallows all exceptions including system exits.

**Location**: `server/app/services/ai_role_normalization_service.py:691`
```python
except:
    pass  # ❌ DANGEROUS - catches KeyboardInterrupt, SystemExit
```

**Impact**: 
- Hides critical errors (database connection failures, out of memory)
- Can prevent graceful shutdown
- Makes debugging impossible

**Fix**:
```python
except Exception as e:
    logger.error(f"Role normalization failed: {e}", exc_info=True)
    # Decide: re-raise, return default, or handle gracefully
```

**Also found in**: `server/app/inngest/functions/role_normalization.py:203,265`

---

### 🔴 1.2 Commits in Routes (Architecture Violation)

**Issue**: Database commits happening in route handlers instead of service layer.

**Locations**:
- `server/app/routes/job_match_routes.py:797, 1143`
- `server/app/routes/scraper_routes.py:363, 390, 523`
- `server/app/routes/candidate_routes.py:98, 389, 547, 717, 758, 943, 1040, 1507, 1584`
- `server/app/routes/pm_admin_routes.py:99`
- `server/app/routes/public_document_routes.py:208`
- `server/app/routes/email_jobs_routes.py:208, 240`
- `server/app/routes/candidate_resume_routes.py:257, 568`
- `server/app/routes/global_role_routes.py:228, 267, 345, 403, 574`
- `server/app/routes/scraper_monitoring_routes.py:521, 569, 607, 662, 715, 1292, 1329, 1369, 1402, 1445`
- `server/app/routes/embedding_routes.py:102, 151, 326, 361`
- `server/app/routes/public_onboarding_routes.py:195`
- `server/app/routes/scraper_credential_routes.py:375, 398, 437`
- `server/app/routes/invitation_routes.py:52`

**Impact**:
- Violates service layer pattern
- Makes testing difficult
- No transaction management
- Business logic leaks into HTTP layer

**Fix**: Move ALL `db.session.commit()` calls to service methods. Routes should only call services.

```python
# ❌ BEFORE (in route)
@app.route('/candidates/<int:id>', methods=['DELETE'])
def delete_candidate(id):
    candidate = db.session.get(Candidate, id)
    db.session.delete(candidate)
    db.session.commit()  # ❌ NO!
    return jsonify({'status': 'deleted'})

# ✅ AFTER (in route)
@app.route('/candidates/<int:id>', methods=['DELETE'])
def delete_candidate(id):
    candidate_service.delete_candidate(id, g.tenant_id)  # ✅ Service handles commit
    return jsonify({'status': 'deleted'})
```

**Effort**: High (50+ locations across 13 route files)

---

### 🔴 1.3 Missing Cache Stampede Protection

**Issue**: Multiple concurrent requests hitting cache miss will all execute expensive operations.

**Location**: `server/app/utils/redis_client.py:183-220` - The `@cached` decorator

**Current Code**:
```python
def cached(key_prefix: str, ttl: int = 3600):
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{args}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # ❌ Multiple requests will all execute this expensive function
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

**Impact**: During cache miss, 100 concurrent requests = 100 DB queries instead of 1

**Fix**: Implement Redis-based locking
```python
def cached(key_prefix: str, ttl: int = 3600, lock_timeout: int = 10):
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{args}"
            lock_key = f"{cache_key}:lock"
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # ✅ Acquire lock with timeout
            if redis_client.set(lock_key, "1", nx=True, ex=lock_timeout):
                try:
                    # This process computes the value
                    result = func(*args, **kwargs)
                    redis_client.setex(cache_key, ttl, json.dumps(result))
                    return result
                finally:
                    redis_client.delete(lock_key)
            else:
                # Another process is computing, wait and retry
                for _ in range(lock_timeout * 2):
                    time.sleep(0.5)
                    cached = redis_client.get(cache_key)
                    if cached:
                        return json.loads(cached)
                # Fallback: compute anyway
                return func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## 2. HIGH PRIORITY - Database & Performance

### 🟠 2.1 N+1 Query Problems

**Issue**: Queries inside loops causing hundreds of database round-trips.

#### **Location**: `server/app/services/job_matching_service.py:941`
```python
for match_result in match_results:  # Loop over 100+ results
    db.session.add(match_result)
    db.session.commit()  # ❌ Commit per iteration = 100+ commits
```

**Impact**: Job matching for 100 candidates = 100 separate transactions

**Fix**:
```python
for match_result in match_results:
    db.session.add(match_result)
db.session.commit()  # ✅ Single commit at the end
```

#### **Location**: `server/app/services/email_sync_service.py:196-210`
```python
for email in emails:  # Loop over 100+ emails
    # Multiple DB queries per email without eager loading
    candidate_roles = db.session.scalars(select(Candidate.preferred_roles).where(...)).all()
```

**Fix**: Pre-load all tenant roles ONCE before the loop (already done with Redis cache, but add fallback)

#### **Location**: `server/app/services/candidate_assignment_service.py:547`
```python
for candidate in broadcast_candidates:  # ❌ Query inside loop
    assignments = db.session.scalars(select(Assignment).where(
        Assignment.candidate_id == candidate.id
    )).all()
```

**Fix**: Use single query with `IN` clause
```python
candidate_ids = [c.id for c in broadcast_candidates]
assignments_map = defaultdict(list)
assignments = db.session.scalars(select(Assignment).where(
    Assignment.candidate_id.in_(candidate_ids)
)).all()
for assignment in assignments:
    assignments_map[assignment.candidate_id].append(assignment)
```

**Total Found**: 15+ locations across services

---

### 🟠 2.2 Missing Database Indexes

**Issue**: Frequently queried columns without indexes cause full table scans.

#### **Missing Composite Indexes**:

**Candidate Model**:
```python
# Current indexes in candidate.py
__table_args__ = (
    Index('idx_candidates_tenant_status', 'tenant_id', 'status'),
    # ❌ Missing: tenant_id + created_at (for sorted lists)
    # ❌ Missing: tenant_id + onboarding_status (frequent filter)
    # ❌ Missing: tenant_id + manager_id (manager dashboards)
    # ❌ Missing: tenant_id + recruiter_id (recruiter dashboards)
)
```

**Fix**:
```python
__table_args__ = (
    Index('idx_candidates_tenant_status', 'tenant_id', 'status'),
    Index('idx_candidates_tenant_created', 'tenant_id', 'created_at'),
    Index('idx_candidates_tenant_onboarding', 'tenant_id', 'onboarding_status'),
    Index('idx_candidates_manager', 'manager_id', 'tenant_id'),
    Index('idx_candidates_recruiter', 'recruiter_id', 'tenant_id'),
    Index('idx_candidates_visible_team', 'is_visible_to_all_team', 'tenant_id') 
)
```

**JobPosting Model** - Missing:
- `(status, posted_date)` - active jobs sorted by date
- `(is_remote, status)` - remote job searches
- `(source_tenant_id, is_email_sourced)` - email-sourced job lookups

**CandidateJobMatch Model** - Missing:
- `(tenant_id, created_at)` - recent matches
- `(candidate_id, match_grade)` - best matches per candidate

**Submission Model** - Missing:
- `(tenant_id, status, created_at)` - submission pipelines
- `(candidate_id, status)` - candidate submission history

**Effort**: Medium (add 20-30 indexes via migration)

---

### 🟠 2.3 Missing Eager Loading

**Issue**: Lazy loading causes N+1 queries when accessing relationships.

**Location**: `server/app/services/candidate_service.py:559-582`
```python
# ❌ Each line triggers separate query
resumes = list(db.session.scalars(resume_stmt).all())
documents = db.session.scalars(doc_stmt).all()
assignments = db.session.scalars(assignment_stmt).all()
notifications = db.session.scalars(notification_stmt).all()
job_matches = db.session.scalars(job_match_stmt).all()
```

**Fix**: Use `selectinload` or `joinedload`
```python
from sqlalchemy.orm import selectinload

stmt = select(Candidate).where(
    Candidate.id == candidate_id,
    Candidate.tenant_id == tenant_id
).options(
    selectinload(Candidate.resumes),
    selectinload(Candidate.documents),
    selectinload(Candidate.assignments).selectinload(CandidateAssignment.recruiter),
    selectinload(Candidate.job_matches).selectinload(CandidateJobMatch.job_posting)
)
candidate = db.session.scalar(stmt)
# ✅ All relationships loaded in single query
```

**Total Found**: 30+ locations where relationships are accessed without eager loading

---

### 🟠 2.4 Missing Pagination

**Issue**: Queries load entire tables without limits.

**Locations**:
- `server/app/services/job_matching_service.py:901` - Loads ALL active jobs
- `server/app/services/job_matching_service.py:1011` - Loads ALL candidates
- `server/app/services/email_sync_service.py:863,879` - Loads ALL candidate roles
- `server/app/services/scrape_queue_service.py:896` - Loads ALL stale sessions

**Fix**: Add limits or cursor-based pagination
```python
# ❌ BEFORE
jobs = db.session.execute(jobs_query).scalars().all()  # Could be 100K jobs

# ✅ AFTER
jobs = db.session.execute(
    jobs_query.limit(1000)  # Process in batches
).scalars().all()
```

---

### 🟠 2.5 Inefficient SELECT * Patterns

**Issue**: Loading all columns when only few are needed.

**Example**: `server/app/services/email_sync_service.py:863`
```python
# ❌ Loads all candidate columns (50+ fields)
stmt = select(Candidate).where(Candidate.tenant_id == tenant_id)
candidates = list(db.session.scalars(stmt).all())

# Only need preferred_roles
for candidate in candidates:
    roles = candidate.preferred_roles  # ❌ Wasted data transfer
```

**Fix**:
```python
# ✅ Select only needed columns
stmt = select(Candidate.preferred_roles).where(
    Candidate.tenant_id == tenant_id,
    Candidate.preferred_roles.isnot(None)
)
all_roles = []
for (roles,) in db.session.execute(stmt).all():
    all_roles.extend(roles)
```

**Impact**: Current approach loads ~50KB per candidate, fix loads ~500 bytes

---

### 🟠 2.6 Inconsistent Redis TTL Strategies

**Issue**: Cache TTLs don't match data volatility.

| Cache Type | Current TTL | Appropriate TTL | Reasoning |
|------------|-------------|-----------------|-----------|
| Tenant roles | 1 hour | ✅ Correct | Balances freshness & performance |
| Portal auth tokens | 8 hours | ✅ Reasonable | Security vs UX |
| PM admin auth tokens | 24 hours | ⚠️ Too long | Should match portal (8 hours) |
| Refresh tokens | 14-30 days | ⚠️ Too long | Max 7 days recommended |
| Stats cache | 30 days | ❌ Way too long | Daily metrics = 24 hours max |

**Fix**:
```python
# In server/app/inngest/functions/scheduled_tasks.py:364
STATS_CACHE_TTL = 86400  # 24 hours, not 30 days

# In auth services - standardize refresh token TTL
REFRESH_TOKEN_TTL = 604800  # 7 days
```

---

## 3. HIGH PRIORITY - Security

### 🟠 3.1 Missing Tenant Isolation in Queries

**Issue**: Queries without `tenant_id` filter can leak data across tenants.

**Locations to Review** (potential risks):
- `server/app/services/job_matching_service.py:901` - JobPosting is global, but ensure matches are tenant-scoped
- Any query on `portal_users`, `candidates`, `submissions` WITHOUT `tenant_id` filter

**Audit Required**: Run SQL logging to verify all queries include tenant filters.

**Fix**: Add code linter rule to enforce tenant_id in WHERE clauses.

---

### 🟠 3.2 Inconsistent Error Logging

**Issue**: Using `print()` instead of structured logging makes production debugging impossible.

**Locations**:
- `server/app/services/candidate_service.py:143,167,691` - Uses `print()` and `traceback.print_exc()`
- Multiple service files use `print()` for debug output (55+ instances)

**Fix**: Replace all `print()` with `logger.error/warning/info`
```python
# ❌ BEFORE
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

# ✅ AFTER
except Exception as e:
    logger.error(f"Error processing candidate: {e}", exc_info=True, extra={
        'candidate_id': candidate_id,
        'tenant_id': tenant_id
    })
```

**Effort**: Medium (55+ locations, can be automated with find/replace)

---

### 🟠 3.3 Silent Redis Failures

**Issue**: Auth services check `if redis_client:` and skip caching on failure without logging.

**Locations**:
- `server/app/services/portal_auth_service.py:72,204`
- `server/app/services/pm_admin_auth_service.py:72,204,247,294`

**Impact**: Users experience inconsistent behavior (logout on one server, still logged in on another)

**Fix**:
```python
try:
    redis_client.setex(token_key, ttl, user_data)
except Exception as e:
    logger.error(f"Redis failure during token storage: {e}", extra={
        'user_id': user_id,
        'tenant_id': tenant_id
    })
    # Continue - authentication still works without cache
```

---

## 4. MEDIUM PRIORITY - Code Quality

### 🟡 4.1 Missing Error Context

**Issue**: Generic error messages without user-friendly context.

**Example**: `server/app/services/submission_service.py:606-607`
```python
if new_status not in SubmissionStatus.all():
    raise ValueError(f"Invalid status: {new_status}. Must be one of: {', '.join(SubmissionStatus.all())}")
    # ✅ Good - clear error message
```

**But**: Most `except Exception` blocks just log error without returning helpful message to user.

**Fix**: Use custom exception classes
```python
class CandidateNotFoundError(Exception):
    """Raised when candidate doesn't exist or user lacks access."""
    pass

class TenantIsolationError(Exception):
    """Raised when attempting to access data from wrong tenant."""
    pass
```

---

### 🟡 4.2 Inconsistent Error Response Formats

**Status**: ✅ Generally good - routes use `error_response()` helper

**Found**: Standardized pattern across routes
```python
from app.utils.response import error_response

return error_response("Candidate not found", 404)
```

**Action**: Ensure ALL routes use this helper (audit needed)

---

### 🟡 4.3 Missing Cleanup in Finally Blocks

**Issue**: Only 2 `finally` blocks found in entire codebase.

**Locations**:
- Most cleanup happens in `except` blocks (database rollbacks, file deletion)
- Risk: If exception occurs during cleanup, resources leak

**Recommendation**: Use context managers
```python
# ✅ Better pattern
from contextlib import contextmanager

@contextmanager
def temp_file_context(file_key):
    temp_path = None
    try:
        temp_path = download_to_temp(file_key)
        yield temp_path
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

# Usage
with temp_file_context(file_key) as temp_path:
    process_file(temp_path)
# ✅ Guaranteed cleanup
```

---

### 🟡 4.4 Missing `db.session.expire_all()` After Deletes

**Status**: ✅ Fixed in `candidate_service.py:588` (recently added)

**Verify**: Check other delete operations have this pattern
```python
db.session.delete(entity)
db.session.commit()
db.session.expire_all()  # ✅ Clear SQLAlchemy session cache
```

**Locations to Audit**: All services with delete operations

---

## 5. MEDIUM PRIORITY - Frontend Performance

### 🟡 5.1 Missing staleTime Configuration (300+ instances)

**Issue**: React Query defaults to refetching on every component mount/focus.

**Impact**: Unnecessary API calls, poor performance, increased backend load

**Locations**: ~50 files in `ui/portal/src/pages/` and `ui/portal/src/hooks/`

**Examples**:
- `ui/portal/src/pages/jobs/JobDetailPage.tsx` - Multiple `useQuery` calls without `staleTime`
- `ui/portal/src/pages/candidates/CandidateDetailPage.tsx` - Same issue
- `ui/portal/src/hooks/useTeam.ts` - Missing across all queries

**Fix**:
```tsx
// ❌ BEFORE - refetches on every mount
const { data: candidates } = useQuery({
  queryKey: ['candidates', filters],
  queryFn: () => candidateApi.listCandidates(filters)
})

// ✅ AFTER - only refetch when data is stale
const { data: candidates } = useQuery({
  queryKey: ['candidates', filters],
  queryFn: () => candidateApi.listCandidates(filters),
  staleTime: 5 * 60 * 1000  // 5 minutes for relatively stable data
})

// For volatile data (real-time updates needed)
const { data: notifications } = useQuery({
  queryKey: ['notifications'],
  queryFn: () => notificationApi.list(),
  staleTime: 0,  // Always refetch
  refetchInterval: 30000  // Poll every 30 seconds
})
```

**Effort**: High (300+ locations, but can create script)

---

### 🟡 5.2 Missing refetchQueries After Mutations

**Issue**: Mutations don't trigger data refresh, causing stale UI.

**Example**: `ui/portal/src/pages/candidates/CandidateDetailPage.tsx`
```tsx
// ❌ BEFORE
const deleteMutation = useMutation({
  mutationFn: (id) => candidateApi.deleteCandidate(id),
  onSuccess: () => {
    toast.success('Deleted')
    // ❌ No refetch - UI shows deleted candidate
  }
})

// ✅ AFTER
const deleteMutation = useMutation({
  mutationFn: (id) => candidateApi.deleteCandidate(id),
  onSuccess: async () => {
    toast.success('Deleted')
    await queryClient.refetchQueries({ queryKey: ['candidates'] })
    await queryClient.refetchQueries({ queryKey: ['candidate-stats'] })
  }
})
```

**Total Found**: 100+ mutations missing refetch logic

---

### 🟡 5.3 Missing Prefetch for Navigation

**Issue**: Clicking links triggers loading spinners when data could be prefetched.

**Example**: Job list → Job detail page
```tsx
// In JobListItem component
function JobListItem({ job }) {
  const queryClient = useQueryClient()
  
  return (
    <Link 
      to={`/jobs/${job.id}`}
      onMouseEnter={() => {
        // ✅ Prefetch on hover
        queryClient.prefetchQuery({
          queryKey: ['job', job.id],
          queryFn: () => jobApi.getJob(job.id),
          staleTime: 5 * 60 * 1000
        })
      }}
    >
      {job.title}
    </Link>
  )
}
```

**Benefit**: Instant page loads, better UX

---

### 🟡 5.4 Missing Optimistic Updates

**Issue**: Mutations show loading state unnecessarily when we know the result.

**Example**: Toggle favorite, update status
```tsx
// ✅ Add optimistic update
const toggleFavoriteMutation = useMutation({
  mutationFn: (id) => candidateApi.toggleFavorite(id),
  onMutate: async (id) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: ['candidates'] })
    
    // Snapshot previous value
    const previous = queryClient.getQueryData(['candidates'])
    
    // Optimistically update
    queryClient.setQueryData(['candidates'], (old) => 
      old.map(c => c.id === id ? { ...c, is_favorite: !c.is_favorite } : c)
    )
    
    return { previous }
  },
  onError: (err, id, context) => {
    // Rollback on error
    queryClient.setQueryData(['candidates'], context.previous)
  }
})
```

---

### 🟡 5.5 Improperly Structured queryKeys

**Issue**: Query keys don't include tenant context, risking cross-tenant data leaks.

**Example**:
```tsx
// ❌ BEFORE - missing tenant_id
queryKey: ['candidates', filters]

// ✅ AFTER - include tenant for isolation
queryKey: ['candidates', tenantId, filters]
```

**Also**: Keys should be consistent across app
```tsx
// ✅ Standardized structure
const queryKeys = {
  candidates: {
    all: (tenantId) => ['candidates', tenantId],
    list: (tenantId, filters) => [...queryKeys.candidates.all(tenantId), 'list', filters],
    detail: (tenantId, id) => [...queryKeys.candidates.all(tenantId), 'detail', id]
  }
}
```

---

### 🟡 5.6 Large Components (1000+ lines)

**Issue**: Components too large to maintain/test.

**Examples**:
- `CandidateDetailPage.tsx` - 2138 lines
- `CandidateOnboardingFlow_v2.tsx` - 1918 lines
- `TeamJobsPage.tsx` - 1362 lines
- `ManualResumeTailorPage.tsx` - 1042 lines

**Fix**: Break into smaller components
```tsx
// BEFORE: One 2000-line component
function CandidateDetailPage() {
  // Everything in one file
}

// AFTER: Split into logical sections
function CandidateDetailPage() {
  return (
    <>
      <CandidateHeader />
      <CandidatePersonalInfo />
      <CandidateWorkExperience />
      <CandidateEducation />
      <CandidateDocuments />
      <CandidateSubmissions />
    </>
  )
}
```

---

### 🟡 5.7 Missing React.memo for Expensive Components

**Issue**: Components re-render unnecessarily when props haven't changed.

**Example**:
```tsx
// ❌ BEFORE - re-renders on every parent update
export function CandidateCard({ candidate, onSelect }) {
  // Expensive rendering logic
}

// ✅ AFTER - only re-renders when candidate or onSelect changes
export const CandidateCard = React.memo(function CandidateCard({ candidate, onSelect }) {
  // Same logic
}, (prevProps, nextProps) => {
  return prevProps.candidate.id === nextProps.candidate.id &&
         prevProps.onSelect === nextProps.onSelect
})
```

**Candidates**: List item components, modal components, form fields

---

## 6. LOW PRIORITY - Technical Debt

### 🟢 6.1 Deprecated Code

**Issue**: `JobPosting.extracted_keywords` marked deprecated but not removed.

**Location**: `server/app/models/job_posting.py:53-55`
```python
# DEPRECATED: extracted_keywords is no longer used
# Will be dropped in migration ff6b8764e616
extracted_keywords = db.Column(JSONB, nullable=True, default=dict)
```

**Action**: Create and run migration to drop column

---

### 🟢 6.2 Missing Database Constraints

**Issue**: Data integrity enforced in application code, not database.

**Examples**:
- Email uniqueness per tenant (should be `UniqueConstraint(tenant_id, email)`)
- Status enums not enforced at DB level
- Foreign keys without `ondelete` behavior

**Fix**: Add constraints in models
```python
__table_args__ = (
    UniqueConstraint('tenant_id', 'email', name='uq_candidate_email_per_tenant'),
    CheckConstraint("status IN ('active', 'inactive', 'pending')", name='chk_valid_status'),
)
```

---

### 🟢 6.3 Inngest Jobs - Missing Patterns

Based on analysis, most Inngest jobs are well-structured BUT:

**Missing**:
- Explicit timeout configurations (rely on Inngest defaults)
- Idempotency keys for job deduplication
- Rate limiting on external API calls (Gmail, Outlook)

**Recommendations**:
```python
@inngest_client.create_function(
    fn_id="sync-email",
    timeout="5m",  # ✅ Explicit timeout
    retries=3,      # ✅ Explicit retry count
    rate_limit={    # ✅ Rate limiting
        "limit": 100,
        "period": "1h"
    }
)
async def sync_email(ctx, step):
    # Use ctx.run_id as idempotency key
    idempotency_key = f"email-sync-{ctx.run_id}"
    # ...
```

---

## 7. IMPLEMENTATION CHECKLIST

### Phase 1: Critical Fixes (Week 1)
- [ ] Fix bare except clauses (3 locations)
- [ ] Move commits from routes to services (50+ locations)
- [ ] Add cache stampede protection to `@cached` decorator
- [ ] Add missing composite indexes (20-30 indexes)

### Phase 2: Database Performance (Week 2)
- [ ] Fix N+1 queries with batch operations (15+ locations)
- [ ] Add eager loading with selectinload (30+ locations)
- [ ] Add pagination to unbounded queries (10+ locations)
- [ ] Optimize SELECT statements to load only needed columns

### Phase 3: Security Hardening (Week 3)
- [ ] Audit all queries for tenant_id filters
- [ ] Replace print() with logger (55+ locations)
- [ ] Add error logging for Redis failures
- [ ] Standardize error response formats

### Phase 4: Frontend Performance (Week 4-5)
- [ ] Add staleTime to all useQuery calls (300+ instances)
- [ ] Add refetchQueries to all mutations (100+ instances)
- [ ] Implement prefetch on navigation
- [ ] Add optimistic updates to toggle/status changes
- [ ] Standardize queryKey structure with tenant isolation

### Phase 5: Code Quality (Week 6)
- [ ] Break down large components (4 files > 1000 lines)
- [ ] Add React.memo to list item components
- [ ] Replace finally block patterns with context managers
- [ ] Add custom exception classes
- [ ] Remove deprecated code and create migrations

### Phase 6: Monitoring & Testing (Week 7)
- [ ] Add cache hit rate metrics
- [ ] Add query performance logging
- [ ] Create integration tests for tenant isolation
- [ ] Load test critical endpoints
- [ ] Set up Sentry for error tracking

---

## ESTIMATED IMPACT

### Performance Improvements
- **Database**: 60-80% reduction in query count (fixing N+1s)
- **API Latency**: 40-60% faster response times (caching + indexes)
- **Frontend**: 50-70% reduction in API calls (staleTime + prefetch)

### Security Improvements
- **Zero cross-tenant data leaks** (tenant_id filters enforced)
- **100% error visibility** (structured logging)
- **Cache consistency** (stampede protection + invalidation)

### Developer Productivity
- **2x faster debugging** (proper logging + error context)
- **50% fewer bugs** (database constraints + validation)
- **Easier onboarding** (smaller components + clear patterns)

---

## PRIORITY MATRIX

| Issue | Impact | Effort | Priority | Start Date |
|-------|--------|--------|----------|------------|
| Bare except clauses | 🔴 Critical | Low | **P0** | Immediate |
| Commits in routes | 🔴 Critical | High | **P0** | Week 1 |
| Cache stampede | 🔴 Critical | Medium | **P0** | Week 1 |
| N+1 queries | 🟠 High | Medium | **P1** | Week 2 |
| Missing indexes | 🟠 High | Medium | **P1** | Week 2 |
| Missing eager loading | 🟠 High | High | **P1** | Week 2 |
| Tenant isolation | 🟠 High | High | **P1** | Week 3 |
| Logging issues | 🟠 High | Medium | **P1** | Week 3 |
| Frontend staleTime | 🟡 Medium | High | **P2** | Week 4 |
| Frontend refetch | 🟡 Medium | High | **P2** | Week 4 |
| Large components | 🟡 Medium | High | **P2** | Week 5 |
| Deprecated code | 🟢 Low | Low | **P3** | Week 6 |

---

## NOTES

- This analysis is based on static code review and pattern detection
- Production metrics (slow query logs, APM data) will reveal additional issues
- Prioritize fixes based on actual user impact and production incidents
- Consider creating automated linters for critical patterns (e.g., enforce tenant_id filters)
- Schedule regular code quality reviews (quarterly) to prevent regression

---

**Last Updated**: 2026-01-23  
**Next Review**: 2026-02-23 (after Phase 1-3 completion)

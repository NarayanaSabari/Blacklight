# Critical Fixes Progress - Phase 1: Route Refactoring

**Objective**: Remove ALL `db.session.commit()` calls from route files. Routes must delegate to services.

**Rule**: ALL database commits belong in the service layer, NEVER in routes.

---

## Overall Progress

**Total Violations**: 44 commits across route files  
**Fixed**: 25 commits (57% complete)  
**Remaining**: 19 commits (43%)

---

## Completed Files (9 files, 25 commits fixed)

### Session 1 (3 commits)
1. ✅ **pm_admin_routes.py** (1 commit)
   - Moved PM admin login commit to PMAdminAuthService

2. ✅ **public_onboarding_routes.py** (1 commit)
   - Removed buggy code (non-existent field)

3. ✅ **public_document_routes.py** (1 commit)
   - Removed buggy code (non-existent field)

### Session 2 (6 commits)
4. ✅ **email_jobs_routes.py** (2 commits)
   - Extended EmailJobService with 2 methods
   - Moved email job creation/update commits

5. ✅ **candidate_resume_routes.py** (2 commits)
   - Extended CandidateResumeService with 2 methods
   - Moved resume upload/update commits

6. ✅ **job_match_routes.py** (2 commits)
   - Extended JobMatchingService with 2 methods
   - Moved job matching result commits

### Session 3 (6 commits)
7. ✅ **scraper_routes.py** (3 commits)
   - Created NEW ScraperService
   - Moved session management commits (start, complete, fail)

8. ✅ **scraper_credential_routes.py** (3 commits)
   - Extended ScraperCredentialService
   - Moved credential create/update/delete commits

### Session 4 (10 commits)
9. ✅ **embedding_routes.py** (4 commits)
   - Extended EmbeddingService
   - Methods added: `save_candidate_embedding()`, `save_job_embedding()`
   - Refactored bulk generation and regeneration endpoints

10. ✅ **global_role_routes.py** (5 commits)
   - Created NEW GlobalRoleService
   - Methods: `update_priority()`, `approve_role()`, `reject_role()`, `delete_role()`, `add_to_queue()`
   - Refactored 5 PM_ADMIN role management endpoints

---

## Remaining Files (2 files, 19 commits)

### Next Priority
1. **candidate_routes.py** (9 commits)
   - Candidate CRUD operations
   - Most complex remaining file

2. **scraper_monitoring_routes.py** (10 commits)
   - Scraper monitoring dashboard
   - Session state updates

---

## Services Created/Extended

### New Services Created (2)
1. **ScraperService** - Session workflow management
2. **GlobalRoleService** - Role management operations

### Services Extended (5)
1. **EmailJobService** - Email job operations
2. **CandidateResumeService** - Resume management
3. **JobMatchingService** - Match result handling
4. **ScraperCredentialService** - Credential management
5. **EmbeddingService** - Embedding generation/save

---

## Verification Commands

```bash
# Count remaining violations
grep -rn "db.session.commit()" server/app/routes/*.py | grep -v "AGENTS.md" | wc -l
# Expected: 19

# List by file
grep -rn "db.session.commit()" server/app/routes/*.py | grep -v "AGENTS.md" | awk -F: '{print $1}' | sort | uniq -c | sort -rn

# Verify specific file is clean
grep -c "db.session.commit()" server/app/routes/embedding_routes.py
# Expected: 0
```

---

## Key Patterns Applied

### Service Method Pattern
```python
# Service handles commit
def save_entity(self, entity_id: int) -> Entity:
    entity = db.session.get(Entity, entity_id)
    if not entity:
        raise ValueError(f"Entity {entity_id} not found")
    
    # Business logic
    entity.status = 'completed'
    db.session.commit()  # ✅ ONLY in service
    db.session.refresh(entity)
    return entity
```

### Route Delegation Pattern
```python
# Route delegates to service
try:
    service = EntityService()
    entity = service.save_entity(entity_id)
    return jsonify(entity.to_dict()), 200
except ValueError as e:
    return jsonify({"error": str(e)}), 404
except Exception as e:
    logger.error(f"Error: {e}")
    return jsonify({"error": "Internal error"}), 500
```

### Key Changes
- **BEFORE**: Route calls `entity.status = X; db.session.commit()` ❌
- **AFTER**: Route calls `service.update_status(entity_id)` ✅
- Service returns data, route serializes to JSON
- No `db.session.rollback()` in routes - service handles it

---

## Next Steps

1. Tackle `candidate_routes.py` (9 commits)
   - Most complex file remaining
   - May need CandidateService extension

2. Finish `scraper_monitoring_routes.py` (10 commits)
   - Session state management
   - Monitoring operations

3. Final verification
   - Run full LSP diagnostics
   - Ensure 0 commits in all route files
   - Document any pre-existing issues

---

**Last Updated**: 2026-01-23 (Session 4 completed)

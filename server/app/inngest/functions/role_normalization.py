"""
AI Role Normalization Inngest Workflow

Handles async role normalization for candidates after approval.
Normalizes preferred roles to global_roles table for job scraping.
"""
import logging
import inngest
from typing import List, Dict, Any

from app.inngest import inngest_client

logger = logging.getLogger(__name__)


@inngest_client.create_function(
    fn_id="normalize-candidate-roles",
    trigger=inngest.TriggerEvent(event="role/normalize-candidate"),
    name="Normalize Candidate Roles",
    retries=3
)
async def normalize_candidate_roles_workflow(ctx: inngest.Context):
    """
    Async workflow to normalize candidate preferred roles.
    
    Triggered after candidate approval to:
    1. Normalize each preferred role to canonical form
    2. Create/update entries in global_roles table
    3. Link candidate to global roles for job matching
    
    Event data:
    {
        "candidate_id": 123,
        "tenant_id": 456,
        "preferred_roles": ["Senior Python Developer", "Backend Engineer"],
        "trigger_source": "approval" | "profile_update" | "manual"
    }
    """
    event_data = ctx.event.data
    candidate_id = event_data.get("candidate_id")
    tenant_id = event_data.get("tenant_id")
    preferred_roles = event_data.get("preferred_roles", [])
    trigger_source = event_data.get("trigger_source", "manual")
    
    logger.info(
        f"[ROLE-NORM] Starting normalization for candidate {candidate_id} "
        f"(tenant {tenant_id}, trigger: {trigger_source}, roles: {preferred_roles})"
    )
    
    if not preferred_roles:
        logger.warning(f"[ROLE-NORM] No preferred roles for candidate {candidate_id}")
        return {
            "status": "skipped",
            "reason": "No preferred roles",
            "candidate_id": candidate_id
        }
    
    # Step 1: Validate candidate exists
    candidate_valid = await ctx.step.run(
        "validate-candidate",
        validate_candidate_step,
        candidate_id,
        tenant_id
    )
    
    if not candidate_valid:
        logger.error(f"[ROLE-NORM] Candidate {candidate_id} not found or invalid")
        return {
            "status": "failed",
            "error": "Candidate not found",
            "candidate_id": candidate_id
        }
    
    # Step 2: Normalize each role
    normalization_results = []
    for raw_role in preferred_roles:
        if raw_role and raw_role.strip():
            result = await ctx.step.run(
                f"normalize-role-{raw_role[:20]}",
                normalize_single_role_step,
                candidate_id,
                raw_role.strip()
            )
            normalization_results.append(result)
    
    # Step 3: Log summary
    successful = [r for r in normalization_results if r.get("success")]
    failed = [r for r in normalization_results if not r.get("success")]
    
    logger.info(
        f"[ROLE-NORM] Completed for candidate {candidate_id}: "
        f"{len(successful)} normalized, {len(failed)} failed"
    )
    
    return {
        "status": "completed",
        "candidate_id": candidate_id,
        "total_roles": len(preferred_roles),
        "normalized": len(successful),
        "failed": len(failed),
        "results": normalization_results
    }


def validate_candidate_step(candidate_id: int, tenant_id: int) -> bool:
    """Validate candidate exists and belongs to tenant."""
    from app import db
    from app.models.candidate import Candidate
    
    try:
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            return False
        if candidate.tenant_id != tenant_id:
            return False
        return True
    except Exception as e:
        logger.error(f"[ROLE-NORM] Candidate validation failed: {e}")
        return False


def normalize_single_role_step(candidate_id: int, raw_role: str) -> Dict[str, Any]:
    """Normalize a single role for a candidate."""
    from app import db
    from app.services.ai_role_normalization_service import AIRoleNormalizationService
    
    try:
        # Instantiate the service
        role_normalizer = AIRoleNormalizationService()
        
        logger.info(f"[ROLE-NORM] Normalizing '{raw_role}' for candidate {candidate_id}")
        
        # Perform normalization
        global_role, similarity, method = role_normalizer.normalize_candidate_role(
            raw_role=raw_role,
            candidate_id=candidate_id
        )
        
        logger.info(
            f"[ROLE-NORM] ✅ '{raw_role}' -> '{global_role.name}' "
            f"(similarity: {similarity:.2%}, method: {method})"
        )
        
        return {
            "success": True,
            "raw_role": raw_role,
            "normalized_name": global_role.name,
            "global_role_id": global_role.id,
            "similarity": similarity,
            "method": method
        }
    except Exception as e:
        # Rollback any failed transaction
        try:
            db.session.rollback()
        except:
            pass
        
        logger.error(f"[ROLE-NORM] ❌ Failed to normalize '{raw_role}': {e}")
        
        return {
            "success": False,
            "raw_role": raw_role,
            "error": str(e)
        }

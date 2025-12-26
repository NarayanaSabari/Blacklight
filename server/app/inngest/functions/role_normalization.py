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
async def normalize_candidate_roles_workflow(ctx: inngest.Context) -> dict:
    """
    Async workflow to normalize candidate preferred roles.
    
    Triggered after candidate approval or profile update to:
    1. Sync removed roles (unlink candidate from roles they no longer have)
    2. Normalize each preferred role to canonical form
    3. Create/update entries in global_roles table
    4. Link candidate to global roles for job matching
    5. Create RoleLocationQueue entries for each role+location combination
    
    Event data:
    {
        "candidate_id": 123,
        "tenant_id": 456,
        "preferred_roles": ["Senior Python Developer", "Backend Engineer"],
        "preferred_locations": ["New York, NY", "Remote"],  # Optional
        "trigger_source": "approval" | "profile_update" | "manual"
    }
    """
    event_data = ctx.event.data
    candidate_id = event_data.get("candidate_id")
    tenant_id = event_data.get("tenant_id")
    preferred_roles = event_data.get("preferred_roles", [])
    preferred_locations = event_data.get("preferred_locations", [])
    trigger_source = event_data.get("trigger_source", "manual")
    
    logger.info(
        f"[ROLE-NORM] Starting normalization for candidate {candidate_id} "
        f"(tenant {tenant_id}, trigger: {trigger_source}, roles: {preferred_roles}, locations: {preferred_locations})"
    )
    
    # Step 1: Validate candidate exists
    candidate_valid = await ctx.step.run(
        "validate-candidate",
        lambda: validate_candidate_step(candidate_id, tenant_id)
    )
    
    if not candidate_valid:
        logger.error(f"[ROLE-NORM] Candidate {candidate_id} not found or invalid")
        return {
            "status": "failed",
            "error": "Candidate not found",
            "candidate_id": candidate_id
        }
    
    # Step 2: Sync removed roles - unlink candidate from roles they no longer have
    sync_result = await ctx.step.run(
        "sync-removed-roles",
        lambda: sync_removed_roles_step(candidate_id, preferred_roles)
    )
    
    # Step 3: If no roles, we're done (just cleaned up)
    if not preferred_roles:
        logger.info(f"[ROLE-NORM] No preferred roles for candidate {candidate_id}, cleanup done")
        return {
            "status": "completed",
            "candidate_id": candidate_id,
            "total_roles": 0,
            "roles_removed": sync_result.get("removed_count", 0),
            "normalized": 0,
            "failed": 0
        }
    
    # Step 4: Normalize each role (with location queue entries)
    normalization_results = []
    for raw_role in preferred_roles:
        if raw_role and raw_role.strip():
            role_to_normalize = raw_role.strip()
            result = await ctx.step.run(
                f"normalize-role-{role_to_normalize[:20].replace(' ', '-')}",
                lambda r=role_to_normalize, locs=preferred_locations: normalize_single_role_step(candidate_id, r, locs)
            )
            normalization_results.append(result)
    
    # Step 5: Log summary
    successful = [r for r in normalization_results if r.get("success")]
    failed = [r for r in normalization_results if not r.get("success")]
    
    logger.info(
        f"[ROLE-NORM] Completed for candidate {candidate_id}: "
        f"{sync_result.get('removed_count', 0)} removed, "
        f"{len(successful)} normalized, {len(failed)} failed"
    )
    
    return {
        "status": "completed",
        "candidate_id": candidate_id,
        "total_roles": len(preferred_roles),
        "roles_removed": sync_result.get("removed_count", 0),
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


def sync_removed_roles_step(candidate_id: int, current_preferred_roles: List[str]) -> Dict[str, Any]:
    """
    Sync removed roles - unlink candidate from roles they no longer have.
    
    Strategy: Clear all existing links and let normalization re-create them.
    This ensures the candidate_count is accurate after role changes.
    
    Args:
        candidate_id: The candidate to sync
        current_preferred_roles: List of currently preferred role strings
        
    Returns:
        Dict with removed_count and details
    """
    from app import db
    from app.models.global_role import GlobalRole
    from app.models.candidate_global_role import CandidateGlobalRole
    
    try:
        # Get all existing links for this candidate
        existing_links = db.session.query(CandidateGlobalRole).filter(
            CandidateGlobalRole.candidate_id == candidate_id
        ).all()
        
        if not existing_links:
            logger.info(f"[ROLE-NORM] No existing role links for candidate {candidate_id}")
            return {"removed_count": 0, "removed_roles": []}
        
        removed_roles = []
        
        # Remove all existing links and decrement counts
        # The normalization step will re-create the ones that should exist
        for link in existing_links:
            global_role = db.session.get(GlobalRole, link.global_role_id)
            
            if global_role:
                # Decrement candidate count
                if global_role.candidate_count and global_role.candidate_count > 0:
                    global_role.candidate_count -= 1
                    logger.info(
                        f"[ROLE-NORM] Decremented candidate_count for '{global_role.name}' "
                        f"to {global_role.candidate_count}"
                    )
                
                removed_roles.append({
                    "global_role_name": global_role.name,
                    "global_role_id": global_role.id,
                    "remaining_candidates": global_role.candidate_count or 0
                })
            
            # Delete the link
            db.session.delete(link)
        
        db.session.commit()
        logger.info(
            f"[ROLE-NORM] Cleared {len(removed_roles)} role links for candidate {candidate_id}. "
            f"Normalization will re-create valid links."
        )
        
        return {
            "removed_count": len(removed_roles),
            "removed_roles": removed_roles
        }
        
    except Exception as e:
        logger.error(f"[ROLE-NORM] Error syncing removed roles: {e}")
        try:
            db.session.rollback()
        except:
            pass
        return {
            "removed_count": 0,
            "removed_roles": [],
            "error": str(e)
        }


def normalize_single_role_step(
    candidate_id: int, 
    raw_role: str, 
    preferred_locations: List[str] = None
) -> Dict[str, Any]:
    """
    Normalize a single role for a candidate.
    
    Also creates RoleLocationQueue entries for each role+location combination
    if preferred_locations are provided.
    
    Args:
        candidate_id: The candidate's ID
        raw_role: The raw role string to normalize
        preferred_locations: Optional list of preferred work locations
    """
    from app import db
    from app.services.ai_role_normalization_service import AIRoleNormalizationService
    
    try:
        # Instantiate the service
        role_normalizer = AIRoleNormalizationService()
        
        logger.info(
            f"[ROLE-NORM] Normalizing '{raw_role}' for candidate {candidate_id} "
            f"(locations: {preferred_locations or []})"
        )
        
        # Perform normalization with location queue entries
        global_role, similarity, method = role_normalizer.normalize_candidate_role(
            raw_role=raw_role,
            candidate_id=candidate_id,
            preferred_locations=preferred_locations
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
            "method": method,
            "location_queue_entries": len(preferred_locations) if preferred_locations else 0
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

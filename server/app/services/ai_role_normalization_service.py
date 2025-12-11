"""
AI Role Normalization Service

Implements Option B: Embedding Similarity First, Then AI normalization.

The workflow:
1. Generate embedding for input role name
2. Search for similar existing roles using vector similarity
3. If similarity >= 85%: Use existing role (fast path)
4. If no match: Call Gemini AI to normalize, create new role (slow path)

This approach provides:
- 90% of cases: Fast embedding similarity match (no AI cost)
- 10% of cases: Gemini AI for new roles (ensures quality)
"""
import logging
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime

import google.generativeai as genai
from sqlalchemy import text

from app import db
from app.models.global_role import GlobalRole
from app.models.candidate_global_role import CandidateGlobalRole
from app.services.embedding_service import EmbeddingService
from config.settings import settings

logger = logging.getLogger(__name__)


class AIRoleNormalizationService:
    """
    Option B: Embedding similarity first, then AI normalization.
    
    - 90% of cases: Fast embedding similarity match
    - 10% of cases: Gemini AI for new roles
    """
    
    SIMILARITY_THRESHOLD = 0.85  # 85% similarity for auto-match
    
    # AI model for role normalization
    GEMINI_MODEL = "gemini-1.5-flash"
    
    def __init__(self):
        """Initialize service with embedding service and Gemini API."""
        self.embedding_service = EmbeddingService()
        
        # Configure Gemini for AI normalization
        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.ai_model = genai.GenerativeModel(self.GEMINI_MODEL)
        else:
            self.ai_model = None
            logger.warning("Google API key not configured - AI normalization disabled")
    
    def normalize_candidate_role(
        self,
        raw_role: str,
        candidate_id: int
    ) -> Tuple[GlobalRole, float, str]:
        """
        Normalize a candidate's preferred role and link to candidate.
        
        Args:
            raw_role: Raw role name from candidate (e.g., "Senior Python Developer")
            candidate_id: Candidate ID to link
        
        Returns:
            Tuple of (GlobalRole, similarity_score, method)
            method: "embedding_match" or "ai_created"
        """
        logger.info(f"Normalizing role '{raw_role}' for candidate {candidate_id}")
        
        # Step 1: Generate embedding for input role
        role_embedding = self.embedding_service.generate_embedding(
            raw_role,
            task_type="SEMANTIC_SIMILARITY"
        )
        
        # Step 2: Search for similar existing roles (FAST PATH)
        similar_role = self._find_similar_role(role_embedding)
        
        if similar_role:
            global_role = similar_role["role"]
            similarity = similar_role["similarity"]
            method = "embedding_match"
            
            logger.info(
                f"Found existing role '{global_role.name}' with {similarity:.2%} similarity"
            )
            
            # Add raw_role to aliases if not already there
            if raw_role.lower() not in [alias.lower() for alias in (global_role.aliases or [])]:
                aliases = list(global_role.aliases or [])
                aliases.append(raw_role)
                global_role.aliases = aliases
        else:
            # Step 3: No match - call Gemini AI to normalize (SLOW PATH)
            canonical_name = self._ai_normalize_role(raw_role)
            
            logger.info(f"AI normalized '{raw_role}' to '{canonical_name}'")
            
            # Check if AI-normalized name already exists
            existing = GlobalRole.query.filter_by(name=canonical_name).first()
            
            if existing:
                # AI normalized to an existing role
                global_role = existing
                similarity = 1.0  # Exact match after AI
                
                # Add raw_role to aliases
                if raw_role.lower() not in [alias.lower() for alias in (existing.aliases or [])]:
                    aliases = list(existing.aliases or [])
                    aliases.append(raw_role)
                    existing.aliases = aliases
            else:
                # Create new global role
                role_embedding_for_new = self.embedding_service.generate_embedding(
                    canonical_name,
                    task_type="SEMANTIC_SIMILARITY"
                )
                
                global_role = GlobalRole(
                    name=canonical_name,
                    embedding=role_embedding_for_new,
                    aliases=[raw_role] if raw_role.lower() != canonical_name.lower() else [],
                    queue_status='pending',
                    priority='normal'
                )
                db.session.add(global_role)
                similarity = 1.0
            
            method = "ai_created"
        
        # Step 4: Link candidate to role
        self._link_candidate_to_role(candidate_id, global_role)
        
        db.session.commit()
        
        return global_role, similarity, method
    
    def _find_similar_role(self, embedding: List[float]) -> Optional[Dict[str, Any]]:
        """
        Find similar existing role using vector similarity search.
        
        Args:
            embedding: 768-dimensional embedding vector
        
        Returns:
            Dict with "role" and "similarity" if found, None otherwise
        """
        # Convert embedding to PostgreSQL array format
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        
        # Use pgvector cosine similarity (1 - distance gives similarity)
        query = text("""
            SELECT id, name, 
                   1 - (embedding <=> :embedding::vector) as similarity
            FROM global_roles
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT 1
        """)
        
        result = db.session.execute(query, {"embedding": embedding_str}).fetchone()
        
        if result and result.similarity >= self.SIMILARITY_THRESHOLD:
            role = db.session.get(GlobalRole, result.id)
            return {
                "role": role,
                "similarity": result.similarity
            }
        
        return None
    
    def _ai_normalize_role(self, raw_role: str) -> str:
        """
        Use Gemini AI to normalize a role name to canonical form.
        
        Args:
            raw_role: Raw role name (e.g., "Sr. Python Dev")
        
        Returns:
            Canonical role name (e.g., "Python Developer")
        """
        if not self.ai_model:
            # Fallback: basic normalization without AI
            return self._basic_normalize(raw_role)
        
        prompt = f"""Normalize this job title to a standard, canonical form.

Job Title: "{raw_role}"

Rules:
1. Remove seniority prefixes (Sr., Senior, Jr., Junior, Lead) - just return base role
2. Use common industry-standard names
3. Expand abbreviations (Dev → Developer, Eng → Engineer)
4. Remove company-specific variations
5. Keep it concise (2-3 words max)

Examples:
- "Sr. Python Dev" → "Python Developer"
- "Senior Full Stack Engineer" → "Full Stack Developer"
- "Junior React.js Developer" → "React Developer"
- "Lead DevOps Eng" → "DevOps Engineer"
- "Staff Software Engineer" → "Software Engineer"

Return ONLY the normalized job title, nothing else."""

        try:
            response = self.ai_model.generate_content(prompt)
            normalized = response.text.strip().strip('"').strip("'")
            
            # Validate response
            if normalized and len(normalized) <= 100:
                return normalized
            else:
                logger.warning(f"AI returned invalid response: {response.text}")
                return self._basic_normalize(raw_role)
        except Exception as e:
            logger.error(f"AI normalization failed: {e}")
            return self._basic_normalize(raw_role)
    
    def _basic_normalize(self, raw_role: str) -> str:
        """
        Basic normalization without AI (fallback).
        
        Applies simple transformations:
        - Title case
        - Remove common prefixes
        - Expand abbreviations
        """
        # Common abbreviations
        abbreviations = {
            'sr.': 'Senior',
            'sr': 'Senior',
            'jr.': 'Junior',
            'jr': 'Junior',
            'dev': 'Developer',
            'eng': 'Engineer',
            'mgr': 'Manager',
            'dir': 'Director',
            'vp': 'Vice President',
            'svp': 'Senior Vice President',
        }
        
        # Seniority prefixes to remove
        seniority_prefixes = ['senior', 'junior', 'lead', 'staff', 'principal', 'chief']
        
        words = raw_role.lower().split()
        normalized_words = []
        
        for word in words:
            # Skip seniority prefixes
            if word in seniority_prefixes:
                continue
            
            # Expand abbreviations
            if word in abbreviations:
                word = abbreviations[word].lower()
                if word in seniority_prefixes:
                    continue
            
            normalized_words.append(word)
        
        # Title case the result
        return ' '.join(word.capitalize() for word in normalized_words)
    
    def _link_candidate_to_role(self, candidate_id: int, global_role: GlobalRole):
        """
        Link a candidate to a global role.
        
        Creates CandidateGlobalRole record and increments candidate_count.
        """
        # Check if link already exists
        existing_link = CandidateGlobalRole.query.filter_by(
            candidate_id=candidate_id,
            global_role_id=global_role.id
        ).first()
        
        if existing_link:
            logger.debug(f"Candidate {candidate_id} already linked to role {global_role.id}")
            return
        
        # Create link
        link = CandidateGlobalRole(
            candidate_id=candidate_id,
            global_role_id=global_role.id
        )
        db.session.add(link)
        
        # Increment candidate count
        global_role.increment_candidate_count()
        
        logger.info(
            f"Linked candidate {candidate_id} to role '{global_role.name}' "
            f"(count now: {global_role.candidate_count})"
        )
    
    def normalize_candidate_roles(
        self,
        candidate_id: int,
        preferred_roles: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Normalize and link all preferred roles for a candidate.
        
        Args:
            candidate_id: Candidate ID
            preferred_roles: List of role names from candidate
        
        Returns:
            List of normalization results
        """
        results = []
        
        for raw_role in preferred_roles:
            if not raw_role or not raw_role.strip():
                continue
            
            try:
                global_role, similarity, method = self.normalize_candidate_role(
                    raw_role.strip(),
                    candidate_id
                )
                
                results.append({
                    "raw_role": raw_role,
                    "normalized_role": global_role.name,
                    "global_role_id": global_role.id,
                    "similarity": similarity,
                    "method": method
                })
            except Exception as e:
                logger.error(f"Failed to normalize role '{raw_role}': {e}")
                results.append({
                    "raw_role": raw_role,
                    "error": str(e)
                })
        
        return results
    
    def find_similar_roles(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find roles similar to a query string.
        
        Useful for autocomplete/suggestions in UI.
        
        Args:
            query: Search query
            limit: Max results
        
        Returns:
            List of similar roles with similarity scores
        """
        # Generate embedding for query
        query_embedding = self.embedding_service.generate_embedding(
            query,
            task_type="SEMANTIC_SIMILARITY"
        )
        
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Find similar roles
        sql = text("""
            SELECT id, name, category, candidate_count,
                   1 - (embedding <=> :embedding::vector) as similarity
            FROM global_roles
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)
        
        results = db.session.execute(
            sql,
            {"embedding": embedding_str, "limit": limit}
        ).fetchall()
        
        return [
            {
                "id": r.id,
                "name": r.name,
                "category": r.category,
                "candidate_count": r.candidate_count,
                "similarity": r.similarity
            }
            for r in results
        ]
    
    @staticmethod
    def merge_roles(
        source_role_ids: List[int],
        target_role_id: int
    ) -> Dict[str, Any]:
        """
        Merge multiple source roles into a target role.
        
        Used when PM_ADMIN identifies duplicate roles.
        
        Args:
            source_role_ids: List of role IDs to merge from (will be deleted)
            target_role_id: Role to merge into (will keep)
        
        Returns:
            Merge result with statistics
        """
        target_role = db.session.get(GlobalRole, target_role_id)
        
        if not target_role:
            raise ValueError(f"Target role {target_role_id} not found")
        
        total_candidates_updated = 0
        merged_roles = []
        all_new_aliases = list(target_role.aliases or [])
        
        for source_role_id in source_role_ids:
            source_role = db.session.get(GlobalRole, source_role_id)
            
            if not source_role:
                logger.warning(f"Source role {source_role_id} not found, skipping")
                continue
            
            if source_role_id == target_role_id:
                logger.warning(f"Skipping merge of role {source_role_id} into itself")
                continue
            
            logger.info(f"Merging role '{source_role.name}' into '{target_role.name}'")
            
            # Update all candidate links to point to target role
            candidates_updated = CandidateGlobalRole.query.filter_by(
                global_role_id=source_role_id
            ).update({"global_role_id": target_role_id})
            
            total_candidates_updated += candidates_updated
            
            # Add source role name and aliases to target role aliases
            if source_role.name not in all_new_aliases:
                all_new_aliases.append(source_role.name)
            for alias in (source_role.aliases or []):
                if alias not in all_new_aliases:
                    all_new_aliases.append(alias)
            
            # Update statistics
            target_role.candidate_count += source_role.candidate_count
            target_role.total_jobs_scraped += source_role.total_jobs_scraped
            
            merged_roles.append(source_role.name)
            
            # Delete source role
            db.session.delete(source_role)
        
        # Update target role aliases
        target_role.aliases = all_new_aliases
        
        db.session.commit()
        
        return {
            "merged_roles": merged_roles,
            "target_role": target_role.name,
            "target_role_id": target_role_id,
            "candidates_updated": total_candidates_updated,
            "new_aliases": all_new_aliases
        }

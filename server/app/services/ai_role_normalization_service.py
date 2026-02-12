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
from sqlalchemy import text, select

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
    
    def __init__(self):
        """Initialize service with embedding service and Gemini API."""
        self.embedding_service = EmbeddingService()
        
        # Use Gemini model from config (defaults to gemini-2.5-flash)
        self.gemini_model_name = settings.gemini_model
        
        # Configure Gemini for AI normalization
        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.ai_model = genai.GenerativeModel(self.gemini_model_name)
            logger.info(f"AI Role Normalization using model: {self.gemini_model_name}")
        else:
            self.ai_model = None
            logger.warning("Google API key not configured - AI normalization disabled")
    
    def normalize_candidate_role(
        self,
        raw_role: str,
        candidate_id: int,
        preferred_locations: Optional[List[str]] = None
    ) -> Tuple[GlobalRole, float, str]:
        """
        Normalize a candidate's preferred role and link to candidate.
        
        Args:
            raw_role: Raw role name from candidate (e.g., "Senior Python Developer")
            candidate_id: Candidate ID to link
            preferred_locations: Optional list of candidate's preferred work locations
                                 Used to create RoleLocationQueue entries for scraping
        
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
            stmt = select(GlobalRole).where(GlobalRole.name == canonical_name)
            existing = db.session.scalar(stmt)
            
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
                    queue_status='pending',  # New roles need PM_ADMIN review
                    priority='normal'
                )
                db.session.add(global_role)
                similarity = 1.0
            
            method = "ai_created"
        
        # Step 4: Link candidate to role (with location queue entries if provided)
        self._link_candidate_to_role(candidate_id, global_role, preferred_locations)
        
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
        try:
            # Convert embedding to PostgreSQL array format
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
            
            # Use pgvector cosine similarity (1 - distance gives similarity)
            # Note: Use CAST() instead of :: to avoid SQLAlchemy parameter parsing issues
            query = text("""
                SELECT id, name, 
                       1 - (embedding <=> CAST(:embedding AS vector)) as similarity
                FROM global_roles
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:embedding AS vector)
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
        except Exception as e:
            # If vector search fails (e.g., table doesn't exist, pgvector not installed),
            # rollback and return None to fall back to AI normalization
            logger.warning(f"Vector similarity search failed, falling back to AI: {e}")
            db.session.rollback()
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
    
    def _link_candidate_to_role(
        self, 
        candidate_id: int, 
        global_role: GlobalRole,
        preferred_locations: Optional[List[str]] = None
    ):
        """
        Link a candidate to a global role.
        
        Creates CandidateGlobalRole record and increments candidate_count.
        Also ensures the role is in the scraping queue.
        If preferred_locations are provided, creates RoleLocationQueue entries
        for each role+location combination.
        
        Args:
            candidate_id: The candidate's ID
            global_role: The GlobalRole to link to
            preferred_locations: Optional list of candidate's preferred work locations
        """
        # Check if link already exists
        stmt = select(CandidateGlobalRole).where(
            CandidateGlobalRole.candidate_id == candidate_id,
            CandidateGlobalRole.global_role_id == global_role.id
        )
        existing_link = db.session.scalar(stmt)
        
        if existing_link:
            logger.debug(f"Candidate {candidate_id} already linked to role {global_role.id}")
            # Still ensure role is in queue even if link exists
            self._ensure_role_in_queue(global_role)
            # Create location queue entries even if role link exists
            if preferred_locations:
                self._ensure_role_location_queue_entries(global_role, preferred_locations)
            return
        
        # Create link
        link = CandidateGlobalRole(
            candidate_id=candidate_id,
            global_role_id=global_role.id
        )
        db.session.add(link)
        
        # Increment candidate count
        global_role.increment_candidate_count()
        
        # Ensure role is in the scraping queue
        self._ensure_role_in_queue(global_role)
        
        # Create RoleLocationQueue entries for each role+location combination
        if preferred_locations:
            self._ensure_role_location_queue_entries(global_role, preferred_locations)
        
        logger.info(
            f"Linked candidate {candidate_id} to role '{global_role.name}' "
            f"(count now: {global_role.candidate_count})"
        )
    
    def _ensure_role_in_queue(self, global_role: GlobalRole):
        """
        Ensure a role is in the scraping queue.
        
        If the role is not already pending/approved/processing, set it to pending.
        New roles need PM_ADMIN review before scraping.
        """
        # Only add to queue if not already queued
        if global_role.queue_status not in ['pending', 'approved', 'processing']:
            old_status = global_role.queue_status
            global_role.queue_status = 'pending'  # New additions need review
            logger.info(
                f"Added role '{global_role.name}' to scraping queue "
                f"(was: {old_status or 'none'}, now: pending)"
            )
    
    def _ensure_role_location_queue_entries(
        self, 
        global_role: GlobalRole, 
        locations: List[str]
    ):
        """
        Ensure RoleLocationQueue entries exist for each role+location combination.
        
        Creates queue entries for location-specific job scraping:
        - DevOps Engineer + New York → one queue entry
        - DevOps Engineer + Los Angeles → another queue entry
        
        If an entry already exists, increments candidate_count.
        
        Args:
            global_role: The GlobalRole to create location entries for
            locations: List of location strings (e.g., ["New York, NY", "Remote"])
        """
        from app.models.role_location_queue import RoleLocationQueue
        
        if not locations:
            return
        
        for location in locations:
            if not location or not location.strip():
                continue
            
            normalized_location = location.strip()
            
            # Check if entry already exists
            stmt = select(RoleLocationQueue).where(
                RoleLocationQueue.global_role_id == global_role.id,
                RoleLocationQueue.location == normalized_location
            )
            existing_entry = db.session.scalar(stmt)
            
            if existing_entry:
                # Increment candidate count for existing entry
                existing_entry.increment_candidate_count()
                logger.info(
                    f"Incremented candidate count for role+location: "
                    f"'{global_role.name}' + '{normalized_location}' "
                    f"(count now: {existing_entry.candidate_count})"
                )
            else:
                # Create new queue entry
                new_entry = RoleLocationQueue(
                    global_role_id=global_role.id,
                    location=normalized_location,
                    queue_status='pending',  # New entries need review
                    priority='normal',
                    candidate_count=1
                )
                db.session.add(new_entry)
                logger.info(
                    f"Created role+location queue entry: "
                    f"'{global_role.name}' + '{normalized_location}'"
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
        # Note: Use CAST() instead of :: to avoid SQLAlchemy parameter parsing issues
        sql = text("""
            SELECT id, name, category, candidate_count,
                   1 - (embedding <=> CAST(:embedding AS vector)) as similarity
            FROM global_roles
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
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
            from sqlalchemy import update
            stmt = update(CandidateGlobalRole).where(
                CandidateGlobalRole.global_role_id == source_role_id
            ).values(global_role_id=target_role_id)
            candidates_updated = db.session.execute(stmt).rowcount
            
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
        db.session.expire_all()
        
        return {
            "merged_roles": merged_roles,
            "target_role": target_role.name,
            "target_role_id": target_role_id,
            "candidates_updated": total_candidates_updated,
            "new_aliases": all_new_aliases
        }
    
    def normalize_job_title(
        self,
        job_title: str,
        job_posting_id: int
    ) -> Tuple[Optional[GlobalRole], float, str]:
        """
        Normalize a job posting's title and link it to a GlobalRole via RoleJobMapping.
        
        This enables job matching: candidates with matching preferred roles will
        automatically see jobs linked to the same GlobalRole.
        
        Args:
            job_title: Raw job title (e.g., "Senior Python Developer")
            job_posting_id: Job posting ID to link
        
        Returns:
            Tuple of (GlobalRole, similarity_score, method)
            method: "embedding_match" or "ai_created"
            Returns (None, 0.0, "error") if normalization fails
        """
        from app.models.role_job_mapping import RoleJobMapping
        from app.models.job_posting import JobPosting
        
        logger.info(f"Normalizing job title '{job_title}' for job {job_posting_id}")
        
        try:
            # Step 1: Generate embedding for job title
            job_embedding = self.embedding_service.generate_embedding(
                job_title,
                task_type="SEMANTIC_SIMILARITY"
            )
            
            # Step 2: Search for similar existing roles (FAST PATH)
            similar_role = self._find_similar_role(job_embedding)
            
            if similar_role:
                global_role = similar_role["role"]
                similarity = similar_role["similarity"]
                method = "embedding_match"
                
                logger.info(
                    f"Found existing role '{global_role.name}' with {similarity:.2%} similarity for job title"
                )
                
                # Add job title to aliases if not already there
                if job_title.lower() not in [alias.lower() for alias in (global_role.aliases or [])]:
                    aliases = list(global_role.aliases or [])
                    aliases.append(job_title)
                    global_role.aliases = aliases
            else:
                # Step 3: No match - call Gemini AI to normalize (SLOW PATH)
                canonical_name = self._ai_normalize_role(job_title)
                
                logger.info(f"AI normalized job title '{job_title}' to '{canonical_name}'")
                
                # Check if AI-normalized name already exists
                stmt = select(GlobalRole).where(GlobalRole.name == canonical_name)
                existing = db.session.scalar(stmt)
                
                if existing:
                    # AI normalized to an existing role
                    global_role = existing
                    similarity = 1.0  # Exact match after AI
                    
                    # Add job title to aliases
                    if job_title.lower() not in [alias.lower() for alias in (existing.aliases or [])]:
                        aliases = list(existing.aliases or [])
                        aliases.append(job_title)
                        existing.aliases = aliases
                else:
                    # Create new global role
                    role_embedding = self.embedding_service.generate_embedding(
                        canonical_name,
                        task_type="SEMANTIC_SIMILARITY"
                    )
                    
                    global_role = GlobalRole(
                        name=canonical_name,
                        embedding=role_embedding,
                        aliases=[job_title] if job_title.lower() != canonical_name.lower() else [],
                        queue_status='approved',  # Job-sourced roles are auto-approved (real jobs exist)
                        priority='normal'
                    )
                    db.session.add(global_role)
                    db.session.flush()  # Get ID
                    similarity = 1.0
                
                method = "ai_created"
            
            # Step 4: Link job to role via RoleJobMapping
            self._link_job_to_role(job_posting_id, global_role)
            
            # Step 5: Update job's normalized_role_id directly
            job = db.session.get(JobPosting, job_posting_id)
            if job:
                job.normalized_role_id = global_role.id
            
            # Use flush() instead of commit() - let the caller manage the transaction
            # This is called from email_job_parser_service which batches multiple operations
            # and commits at the end
            db.session.flush()
            
            logger.info(
                f"✅ Job {job_posting_id} linked to role '{global_role.name}' "
                f"(similarity: {similarity:.2%}, method: {method})"
            )
            
            return global_role, similarity, method
            
        except Exception as e:
            logger.error(f"Failed to normalize job title '{job_title}': {e}", exc_info=True)
            # Don't rollback here - let the caller handle the transaction
            # Rollback here would undo ALL pending work including the job posting
            return None, 0.0, "error"
    
    def _link_job_to_role(self, job_posting_id: int, global_role: GlobalRole):
        """
        Link a job posting to a global role via RoleJobMapping.
        
        Creates RoleJobMapping record and increments total_jobs_scraped.
        """
        from app.models.role_job_mapping import RoleJobMapping
        
        # Check if link already exists
        stmt = select(RoleJobMapping).where(
            RoleJobMapping.job_posting_id == job_posting_id,
            RoleJobMapping.global_role_id == global_role.id
        )
        existing_link = db.session.scalar(stmt)
        
        if existing_link:
            logger.debug(f"Job {job_posting_id} already linked to role {global_role.id}")
            return
        
        # Create link
        link = RoleJobMapping(
            job_posting_id=job_posting_id,
            global_role_id=global_role.id
        )
        db.session.add(link)
        
        # Increment job count for the role
        if global_role.total_jobs_scraped is None:
            global_role.total_jobs_scraped = 0
        global_role.total_jobs_scraped += 1
        
        logger.info(
            f"Linked job {job_posting_id} to role '{global_role.name}' "
            f"(total jobs: {global_role.total_jobs_scraped})"
        )

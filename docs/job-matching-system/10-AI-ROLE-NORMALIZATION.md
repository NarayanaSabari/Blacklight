# AI Role Normalization

The AI Role Normalization system uses **Option B: Embedding Similarity First, Then AI** to standardize job titles/roles across different sources, enabling efficient role-based queue management and better matching.

## Problem Statement

Job titles vary significantly across different sources:
- "Software Engineer" vs "Software Developer" vs "SDE"
- "Full Stack Developer" vs "Full-Stack Engineer" vs "Fullstack Dev"
- "Sr. React Developer" vs "Senior ReactJS Developer" vs "React.js Sr Developer"

Without normalization:
- Same role appears as multiple separate queue entries
- Scraper scrapes "Python Developer" and "Python Dev" as different roles
- Candidates selecting similar roles don't benefit from shared job results

## Solution: Option B - Embedding Similarity First, Then AI

**Chosen Approach**: Check vector similarity against existing roles first. Only call Gemini AI if no match found.

### Why Option B?

| Approach | Cost | Speed | Accuracy |
|----------|------|-------|----------|
| Option A: Always AI | $$$$ | Slow | Very High |
| **Option B: Embedding → AI** | $$ | Fast | High |
| Option C: Embedding Only | $ | Fastest | Medium |

Option B provides the best balance:
- **90% of cases**: Embedding similarity finds existing role (fast, free)
- **10% of cases**: New role → call Gemini AI to suggest canonical name

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OPTION B: ROLE NORMALIZATION FLOW                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Candidate Input: "Senior Python Developer"                        │
│                          │                                          │
│                          ▼                                          │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │ Step 1: Generate Embedding (768-dim vector)                │    │
│   │         Using Google Gemini models/embedding-001           │    │
│   └───────────────────────────────────────────────────────────┘    │
│                          │                                          │
│                          ▼                                          │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │ Step 2: Vector Similarity Search                           │    │
│   │         SELECT * FROM global_roles                         │    │
│   │         WHERE 1 - (embedding <=> input) >= 0.85            │    │
│   └───────────────────────────────────────────────────────────┘    │
│                          │                                          │
│                     ┌────┴────┐                                     │
│                     │ Match?  │                                     │
│                     └────┬────┘                                     │
│                   YES    │    NO                                    │
│            ┌─────────────┴─────────────┐                            │
│            ▼                           ▼                            │
│   ┌─────────────────┐     ┌──────────────────────────────────┐     │
│   │ Use Existing    │     │ Step 3: Call Gemini AI           │     │
│   │ GlobalRole      │     │ "Normalize: Senior Python Dev"   │     │
│   │ ("Python        │     │ AI Response: "Python Developer"  │     │
│   │  Developer")    │     │                                  │     │
│   │                 │     │ → Create new GlobalRole          │     │
│   │ Link candidate  │     │ → Generate embedding             │     │
│   │ via candidate_  │     │ → Link candidate                 │     │
│   │ global_roles    │     └──────────────────────────────────┘     │
│   └─────────────────┘                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Models

### GlobalRole Model (Updated for Queue)

```python
# app/models/global_role.py

class GlobalRole(BaseModel):
    """Canonical/normalized job role for role-based queue."""
    
    __tablename__ = "global_roles"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)  # "Python Developer"
    
    # Vector embedding for similarity search (role normalization)
    embedding = Column(Vector(768), nullable=False)
    
    # Metadata
    aliases = Column(ARRAY(String), default=[])  # ["Python Dev", "Python Engineer"]
    category = Column(String(100), nullable=True)  # "Engineering", "Data Science"
    
    # Queue Management (role-based, not candidate-based)
    candidate_count = Column(Integer, default=0)  # Incremented when candidate links
    queue_status = Column(String(20), default="pending")  # pending, processing, completed
    priority = Column(String(20), default="normal")  # urgent, high, normal, low
    
    # Statistics
    total_jobs_scraped = Column(Integer, default=0)
    last_scraped_at = Column(DateTime, nullable=True)
    
    # Relationships
    candidates = relationship("CandidateGlobalRole", back_populates="global_role")
    
    __table_args__ = (
        Index(
            "idx_global_roles_embedding", 
            "embedding", 
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
        Index("idx_global_roles_queue", "queue_status", "priority", "candidate_count"),
    )
```

### CandidateGlobalRole Model (Linking Table)

```python
# app/models/candidate_global_role.py

class CandidateGlobalRole(BaseModel):
    """Links candidates to their normalized preferred roles."""
    
    __tablename__ = "candidate_global_roles"
    
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    global_role_id = Column(Integer, ForeignKey("global_roles.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="global_roles")
    global_role = relationship("GlobalRole", back_populates="candidates")
    
    __table_args__ = (
        UniqueConstraint("candidate_id", "global_role_id", name="uq_candidate_role"),
    )
```

## Role Normalization Service (Option B Implementation)

### Core Service

```python
# app/services/ai_role_normalization_service.py

import google.generativeai as genai
from typing import Tuple, Optional, List
from app.models import GlobalRole, CandidateGlobalRole
from app.services.embedding_service import EmbeddingService
from app import db
from sqlalchemy import text

class AIRoleNormalizationService:
    """
    Option B: Embedding similarity first, then AI normalization.
    
    - 90% of cases: Fast embedding similarity match
    - 10% of cases: Gemini AI for new roles
    """
    
    SIMILARITY_THRESHOLD = 0.85  # 85% similarity for auto-match
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    def normalize_candidate_role(
        self,
        raw_role: str,
        candidate_id: int
    ) -> Tuple[GlobalRole, float, str]:
        """
        Normalize a candidate's preferred role and link to candidate.
        
        Returns:
            Tuple of (GlobalRole, similarity_score, method)
            method: "embedding_match" or "ai_created"
        """
        
        # Step 1: Generate embedding for input role
        role_embedding = self.embedding_service.generate_role_embedding(raw_role)
        
        # Step 2: Search for similar existing roles (FAST PATH)
        similar_role = self._find_similar_role(role_embedding)
        
        if similar_role:
            global_role = similar_role["role"]
            similarity = similar_role["similarity"]
            method = "embedding_match"
        else:
            # Step 3: No match - call Gemini AI to normalize (SLOW PATH)
            canonical_name = self._ai_normalize_role(raw_role)
            
            # Check if AI-normalized name already exists
            existing = GlobalRole.query.filter_by(name=canonical_name).first()
            
            if existing:
                global_role = existing
                similarity = 1.0
                method = "ai_match_existing"
            else:
                # Create new role with the AI-normalized name
                global_role = self._create_global_role(
                    canonical_name,
                    role_embedding,
                    raw_role
                )
                similarity = 1.0
                method = "ai_created"
        
        # Step 4: Link candidate to global role
        self._link_candidate_to_role(candidate_id, global_role.id)
        
        return global_role, similarity, method
    
    def _find_similar_role(
        self,
        embedding: List[float],
        threshold: float = None
    ) -> Optional[dict]:
        """Find the most similar global role using vector search."""
        
        threshold = threshold or self.SIMILARITY_THRESHOLD
        embedding_str = f"[{','.join(map(str, embedding))}]"
        
        query = text("""
            SELECT 
                id,
                name,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM global_roles
            WHERE embedding IS NOT NULL
              AND 1 - (embedding <=> :embedding::vector) >= :threshold
            ORDER BY similarity DESC
            LIMIT 1
        """)
        
        result = db.session.execute(
            query,
            {"embedding": embedding_str, "threshold": threshold}
        ).first()
        
        if result:
            role = db.session.get(GlobalRole, result.id)
            return {"role": role, "similarity": result.similarity}
        
        return None
    
    def _ai_normalize_role(self, raw_role: str) -> str:
        """
        Use Gemini AI to normalize a role name.
        Called only when embedding similarity doesn't find a match.
        """
        
        prompt = f"""
        Normalize this job role to a canonical form:
        
        Input: "{raw_role}"
        
        Rules:
        1. Remove seniority prefixes (Sr., Junior, Lead, etc.)
        2. Use common industry terms (Developer, Engineer, Designer)
        3. Keep technology stack if essential (React Developer, Python Developer)
        4. Return ONLY the normalized role name, nothing else
        
        Examples:
        - "Sr. Python Software Engineer" → "Python Developer"
        - "Junior Full-Stack Web Developer" → "Full Stack Developer"
        - "Lead DevOps Infrastructure Specialist" → "DevOps Engineer"
        - "React.js Frontend Dev III" → "React Developer"
        
        Normalized role name:
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Clean the response
        normalized = response.text.strip().strip('"').strip("'")
        
        return normalized
    
    def _create_global_role(
        self,
        name: str,
        embedding: List[float],
        original_input: str
    ) -> GlobalRole:
        """Create a new GlobalRole with queue status pending."""
        
        category = self._detect_category(name)
        
        role = GlobalRole(
            name=name,
            embedding=embedding,
            aliases=[original_input] if original_input != name else [],
            category=category,
            candidate_count=0,
            queue_status="pending",
            priority="normal"
        )
        
        db.session.add(role)
        db.session.commit()
        
        return role
    
    def _link_candidate_to_role(
        self,
        candidate_id: int,
        global_role_id: int
    ):
        """Create candidate-role link and update counts."""
        
        # Check if link already exists
        existing = CandidateGlobalRole.query.filter_by(
            candidate_id=candidate_id,
            global_role_id=global_role_id
        ).first()
        
        if existing:
            return  # Already linked
        
        # Create link
        link = CandidateGlobalRole(
            candidate_id=candidate_id,
            global_role_id=global_role_id
        )
        db.session.add(link)
        
        # Increment candidate count on role
        role = db.session.get(GlobalRole, global_role_id)
        role.candidate_count = (role.candidate_count or 0) + 1
        
        # Ensure role is in queue if it has candidates
        if role.queue_status == "completed":
            role.queue_status = "pending"  # Re-queue for fresh jobs
        
        db.session.commit()
    
    @staticmethod
    def _detect_category(title: str) -> Optional[str]:
        """Detect job category from title."""
        
        title_lower = title.lower()
        
        categories = {
            "Engineering": ["developer", "engineer", "programmer", "architect", "devops", "sre"],
            "Design": ["designer", "ux", "ui", "graphic", "visual"],
            "Data": ["data", "analyst", "scientist", "ml", "machine learning", "ai"],
            "Product": ["product manager", "pm", "product owner", "po"],
            "Management": ["manager", "director", "vp", "head of", "chief"],
            "QA": ["qa", "quality", "test", "automation", "sdet"],
            "DevOps": ["devops", "infrastructure", "cloud", "platform", "sre"],
            "Security": ["security", "infosec", "cybersecurity", "penetration"],
        }
        
        for category, keywords in categories.items():
            if any(kw in title_lower for kw in keywords):
                return category
        
        return "Other"
```

## Integration with Onboarding

### Using Role Normalization in Candidate Onboarding

```python
# app/services/candidate_onboarding_service.py

from app.services.ai_role_normalization_service import AIRoleNormalizationService

class CandidateOnboardingService:
    
    @staticmethod
    def process_candidate_roles(
        candidate_id: int,
        preferred_roles: List[str]
    ) -> List[dict]:
        """
        Process candidate's preferred roles during onboarding.
        Normalizes each role and links to candidate.
        """
        
        normalization_service = AIRoleNormalizationService()
        results = []
        
        for raw_role in preferred_roles:
            global_role, similarity, method = normalization_service.normalize_candidate_role(
                raw_role=raw_role,
                candidate_id=candidate_id
            )
            
            results.append({
                "input": raw_role,
                "normalized_to": global_role.name,
                "global_role_id": global_role.id,
                "similarity": similarity,
                "method": method,
                "queue_status": global_role.queue_status
            })
        
        return results
```

### Onboarding API Integration

```python
# app/routes/candidate_onboarding_routes.py

@candidate_onboarding_bp.route('/submit', methods=['POST'])
@require_portal_auth
def submit_onboarding():
    """Submit candidate onboarding with role normalization."""
    
    data = request.get_json()
    preferred_roles = data.get("preferred_roles", [])
    
    # ... other onboarding processing ...
    
    # Normalize roles
    role_results = CandidateOnboardingService.process_candidate_roles(
        candidate_id=candidate.id,
        preferred_roles=preferred_roles
    )
    
    return jsonify({
        "message": "Onboarding submitted",
        "candidate_id": candidate.id,
        "roles_normalized": role_results
    }), 201
```

## Role Merging (PM_ADMIN)

### Merge Duplicate Roles

When PM_ADMIN identifies duplicate roles, they can be merged:

```python
@staticmethod
def merge_roles(
    source_role_id: int,
    target_role_id: int,
    admin_id: int
) -> GlobalRole:
    """Merge source role into target role."""
    
    source = db.session.get(GlobalRole, source_role_id)
    target = db.session.get(GlobalRole, target_role_id)
    
    if not source or not target:
        raise ValueError("Role not found")
    
    # Update all mappings from source to target
    RoleJobMapping.query.filter_by(
        global_role_id=source_role_id
    ).update({
        "global_role_id": target_role_id
    })
    
    # Update all jobs using source role
    JobPosting.query.filter_by(
        normalized_role_id=source_role_id
    ).update({
        "normalized_role_id": target_role_id
    })
    
    # Aggregate job counts
    target.job_count = (target.job_count or 0) + (source.job_count or 0)
    
    # Mark source as merged
    source.status = "merged"
    source.merged_into_id = target_role_id
    
    db.session.commit()
    
    # Log the merge action
    AuditLogService.log_action(
        action="MERGE_ROLE",
        entity_type="GlobalRole",
        entity_id=source_role_id,
        changes={
            "merged_into": target_role_id,
            "merged_by": admin_id
        }
    )
    
    return target
```

## Role Review Queue

### Queue for New Roles

```python
@staticmethod
def get_pending_roles(limit: int = 50) -> List[Dict]:
    """Get roles pending review."""
    
    roles = GlobalRole.query.filter_by(
        status="pending_review"
    ).order_by(
        GlobalRole.job_count.desc(),  # High usage first
        GlobalRole.created_at.asc()
    ).limit(limit).all()
    
    results = []
    for role in roles:
        # Find similar existing roles for merge suggestions
        if role.embedding:
            similar = RoleNormalizationService._find_similar_roles(
                role.embedding,
                threshold=0.75,  # Lower threshold for suggestions
                limit=3
            )
        else:
            similar = []
        
        results.append({
            "role": role,
            "similar_roles": similar,
            "mappings_count": RoleJobMapping.query.filter_by(
                global_role_id=role.id
            ).count()
        })
    
    return results
```

### Approve/Reject Actions

```python
@staticmethod
def approve_role(role_id: int, admin_id: int) -> GlobalRole:
    """Approve a pending role."""
    
    role = db.session.get(GlobalRole, role_id)
    if not role:
        raise ValueError("Role not found")
    
    role.status = "active"
    db.session.commit()
    
    AuditLogService.log_action(
        action="APPROVE_ROLE",
        entity_type="GlobalRole",
        entity_id=role_id,
        changes={"approved_by": admin_id}
    )
    
    return role


@staticmethod
def deprecate_role(
    role_id: int,
    replacement_role_id: int,
    admin_id: int
) -> GlobalRole:
    """Deprecate a role and migrate to replacement."""
    
    role = db.session.get(GlobalRole, role_id)
    replacement = db.session.get(GlobalRole, replacement_role_id)
    
    if not role or not replacement:
        raise ValueError("Role not found")
    
    # Update all references
    RoleJobMapping.query.filter_by(
        global_role_id=role_id
    ).update({
        "global_role_id": replacement_role_id
    })
    
    role.status = "deprecated"
    role.merged_into_id = replacement_role_id
    
    db.session.commit()
    
    return role
```

## Integration with Job Import

### Auto-Normalize on Import

```python
# In job_import_service.py

def import_job(job_data: Dict, source: str) -> JobPosting:
    """Import a job and auto-normalize its role."""
    
    raw_title = job_data.get("title", "")
    
    # Normalize the role
    global_role, similarity = role_normalization_service.normalize_role(
        raw_title=raw_title,
        source=source,
        auto_create=True
    )
    
    job = JobPosting(
        title=raw_title,
        normalized_role_id=global_role.id if global_role else None,
        role_match_confidence=similarity,
        # ... other fields
    )
    
    db.session.add(job)
    db.session.commit()
    
    return job
```

## Similarity Threshold Guidelines

| Threshold | Use Case | Risk |
|-----------|----------|------|
| 95%+ | Exact match, auto-approve | Very low false positives |
| 85-94% | High confidence, auto-map | Low false positives |
| 75-84% | Suggest for review | Moderate false positives |
| 60-74% | Manual review required | High uncertainty |
| <60% | Create new role | Different concept |

## Performance Optimization

### Batch Normalization

```python
@staticmethod
def batch_normalize_roles(
    titles: List[Tuple[str, str]],  # (raw_title, source)
    batch_size: int = 100
) -> Dict[str, GlobalRole]:
    """Normalize multiple titles efficiently."""
    
    results = {}
    
    # First pass: check existing mappings
    unmapped = []
    for raw_title, source in titles:
        existing = RoleJobMapping.query.filter_by(
            raw_title=raw_title,
            source=source
        ).first()
        
        if existing:
            results[raw_title] = existing.global_role
        else:
            unmapped.append((raw_title, source))
    
    # Second pass: batch embedding generation
    if unmapped:
        titles_to_embed = [t[0] for t in unmapped]
        embeddings = embedding_service.generate_batch_embeddings(titles_to_embed)
        
        for (raw_title, source), embedding in zip(unmapped, embeddings):
            global_role, _ = RoleNormalizationService._match_or_create(
                raw_title, source, embedding
            )
            results[raw_title] = global_role
    
    return results
```

### Caching

```python
from app.utils.redis_client import cached

@cached(ttl=3600, key_prefix="role_norm")
def get_cached_mapping(raw_title: str, source: str) -> Optional[int]:
    """Get cached role mapping."""
    
    mapping = RoleJobMapping.query.filter_by(
        raw_title=raw_title,
        source=source
    ).first()
    
    return mapping.global_role_id if mapping else None
```

## API Endpoints

### Role Management Endpoints

```python
# app/routes/role_api.py

@role_bp.route('/normalize', methods=['POST'])
@require_pm_admin
def normalize_role():
    """Normalize a job title to global role."""
    
    data = request.get_json()
    raw_title = data.get("title")
    source = data.get("source")
    
    global_role, similarity = role_normalization_service.normalize_role(
        raw_title, source
    )
    
    return jsonify({
        "global_role": {
            "id": global_role.id,
            "name": global_role.name,
            "normalized_name": global_role.normalized_name,
            "category": global_role.category,
            "seniority_level": global_role.seniority_level
        },
        "similarity": similarity
    }), 200


@role_bp.route('/pending', methods=['GET'])
@require_pm_admin
def get_pending_roles():
    """Get roles pending review."""
    
    roles = role_normalization_service.get_pending_roles()
    
    return jsonify({
        "roles": [
            {
                "role": RoleSchema.model_validate(r["role"]).model_dump(),
                "similar_roles": [
                    {
                        "id": s["role"].id,
                        "name": s["role"].name,
                        "similarity": round(s["similarity"] * 100, 1)
                    }
                    for s in r["similar_roles"]
                ],
                "usage_count": r["mappings_count"]
            }
            for r in roles
        ]
    }), 200


@role_bp.route('/<int:role_id>/merge', methods=['POST'])
@require_pm_admin
def merge_role(role_id: int):
    """Merge this role into another."""
    
    data = request.get_json()
    target_id = data.get("target_role_id")
    
    merged = role_normalization_service.merge_roles(
        source_role_id=role_id,
        target_role_id=target_id,
        admin_id=g.pm_admin.id
    )
    
    return jsonify({
        "message": "Roles merged successfully",
        "target_role": RoleSchema.model_validate(merged).model_dump()
    }), 200
```

## See Also

- [04-EMBEDDING-SYSTEM.md](./04-EMBEDDING-SYSTEM.md) - Embedding generation for role vectors
- [11-CENTRALD-DASHBOARD.md](./11-CENTRALD-DASHBOARD.md) - Role review queue UI
- [05-MATCHING-ALGORITHM.md](./05-MATCHING-ALGORITHM.md) - How normalized roles improve matching

# Phase 2: Embedding System

## Overview

The embedding system converts text (candidate profiles, job descriptions, role names) into 768-dimensional vectors for semantic similarity search. This enables understanding meaning beyond keyword matching.

---

## Google Gemini Integration

### Model Selection

| Model | Dimensions | Use Case |
|-------|------------|----------|
| `models/embedding-001` | 768 | Production (recommended) |
| `models/text-embedding-004` | 768 | Alternative, newer model |

### Configuration

```python
# server/app/services/embedding_service.py
import google.generativeai as genai
from typing import List, Optional
import os

class EmbeddingService:
    """
    Generates semantic embeddings using Google Gemini API.
    """
    
    MODEL_NAME = "models/embedding-001"
    EMBEDDING_DIMENSION = 768
    
    def __init__(self):
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable required")
        genai.configure(api_key=api_key)
    
    def generate_embedding(
        self, 
        text: str, 
        task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> List[float]:
        """
        Generate a 768-dimensional embedding for text.
        
        Args:
            text: Input text to embed
            task_type: Gemini task type for optimization
                - RETRIEVAL_DOCUMENT: For documents (jobs, profiles)
                - RETRIEVAL_QUERY: For search queries
                - SEMANTIC_SIMILARITY: For comparison
        
        Returns:
            List of 768 floats
        """
        result = genai.embed_content(
            model=self.MODEL_NAME,
            content=text,
            task_type=task_type
        )
        return result['embedding']
```

### Task Types Explained

| Task Type | When to Use |
|-----------|-------------|
| `RETRIEVAL_DOCUMENT` | Job postings, candidate profiles (being searched) |
| `RETRIEVAL_QUERY` | Search queries, role names (doing the searching) |
| `SEMANTIC_SIMILARITY` | Role normalization, comparison tasks |

---

## Candidate Embedding Generation

### Text Construction

Build embedding text from candidate profile fields:

```python
def generate_candidate_embedding(self, candidate) -> List[float]:
    """
    Generate embedding for candidate profile.
    
    Constructs text from:
    - Current title (most important for matching)
    - Experience level
    - Skills list
    - Professional summary (truncated)
    """
    parts = []
    
    # Title - primary signal
    if candidate.current_title:
        parts.append(f"Title: {candidate.current_title}")
    
    # Experience level
    if candidate.total_experience_years:
        parts.append(f"Experience: {candidate.total_experience_years} years")
    
    # Skills - critical for matching
    if candidate.skills:
        skills_str = ', '.join(candidate.skills[:20])  # Limit to top 20
        parts.append(f"Skills: {skills_str}")
    
    # Professional summary (truncated to avoid noise)
    if candidate.professional_summary:
        summary = candidate.professional_summary[:500]
        parts.append(f"Summary: {summary}")
    
    # Preferred roles (for role-based matching)
    if candidate.preferred_roles:
        roles_str = ', '.join(candidate.preferred_roles[:5])
        parts.append(f"Target Roles: {roles_str}")
    
    profile_text = ". ".join(parts)
    
    # Use RETRIEVAL_DOCUMENT since this is a document being searched
    return self.generate_embedding(profile_text, task_type="RETRIEVAL_DOCUMENT")
```

### Example Input/Output

**Input Profile:**
```
Candidate:
- current_title: "Senior Software Engineer"
- total_experience_years: 7
- skills: ["Python", "React", "AWS", "PostgreSQL", "Docker"]
- professional_summary: "Full-stack developer with expertise in cloud..."
```

**Generated Text:**
```
Title: Senior Software Engineer. Experience: 7 years. 
Skills: Python, React, AWS, PostgreSQL, Docker. 
Summary: Full-stack developer with expertise in cloud...
```

**Output:** 768-dimensional vector `[0.234, -0.567, 0.891, ...]`

---

## Job Embedding Generation

### Text Construction

```python
def generate_job_embedding(self, job) -> List[float]:
    """
    Generate embedding for job posting.
    
    Constructs text from:
    - Job title (primary signal)
    - Required skills
    - Experience requirements
    - Description (truncated)
    """
    parts = []
    
    # Title - primary signal
    parts.append(f"Job Title: {job.title}")
    
    # Company (provides context)
    if job.company:
        parts.append(f"Company: {job.company}")
    
    # Required skills - critical
    if job.skills:
        skills_str = ', '.join(job.skills[:20])
        parts.append(f"Required Skills: {skills_str}")
    
    # Experience requirements
    if job.experience_min:
        exp_str = f"{job.experience_min}"
        if job.experience_max:
            exp_str += f"-{job.experience_max}"
        parts.append(f"Experience Required: {exp_str} years")
    
    # Description (truncated to key content)
    if job.description:
        # Take first 500 chars - usually contains key info
        desc = job.description[:500]
        parts.append(f"Description: {desc}")
    
    job_text = ". ".join(parts)
    
    return self.generate_embedding(job_text, task_type="RETRIEVAL_DOCUMENT")
```

---

## Role Embedding Generation

### For AI Role Normalization

```python
def generate_role_embedding(self, role_name: str) -> List[float]:
    """
    Generate embedding for role name.
    Used for AI-based role normalization.
    
    Uses SEMANTIC_SIMILARITY task type since we're comparing
    role names for similarity.
    """
    return self.generate_embedding(role_name, task_type="SEMANTIC_SIMILARITY")
```

---

## Vector Storage with pgvector

### Why pgvector?

| Factor | pgvector | Pinecone/Qdrant |
|--------|----------|-----------------|
| Infrastructure | Same DB | Separate service |
| Transactions | ACID with data | Eventually consistent |
| Scale | <100K vectors | Millions+ |
| Cost | Free (PostgreSQL) | Per-query pricing |
| Latency | ~10-50ms | ~5-20ms |

### Setup

```sql
-- Enable extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column
ALTER TABLE job_postings 
ADD COLUMN embedding VECTOR(768);

-- Create index (after data is loaded)
CREATE INDEX idx_job_postings_embedding 
ON job_postings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

### Index Types

| Index | Use Case | Trade-off |
|-------|----------|-----------|
| **IVFFlat** | <100K vectors | Good accuracy, moderate speed |
| **HNSW** | >100K vectors | Faster, uses more memory |

### IVFFlat Configuration

```sql
-- lists = sqrt(row_count) is a good starting point
-- For 50,000 jobs: lists ≈ 100

CREATE INDEX idx_job_postings_embedding 
ON job_postings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Set probes for accuracy/speed tradeoff
-- Higher probes = more accurate, slower
SET ivfflat.probes = 10;  -- Default, good balance
```

---

## Similarity Search Queries

### Find Similar Jobs (for a candidate)

```python
def find_similar_jobs(
    self, 
    candidate_embedding: List[float], 
    limit: int = 50
) -> List[JobPosting]:
    """
    Find jobs most similar to candidate profile.
    Uses cosine distance (1 - cosine_similarity).
    """
    from app.models import JobPosting
    from app import db
    
    results = db.session.execute(
        db.select(JobPosting)
        .where(JobPosting.status == 'active')
        .order_by(JobPosting.embedding.cosine_distance(candidate_embedding))
        .limit(limit)
    ).scalars().all()
    
    return results
```

### Find Similar Roles (for normalization)

```python
def find_similar_roles(
    self, 
    role_embedding: List[float], 
    similarity_threshold: float = 0.85
) -> Optional[GlobalRole]:
    """
    Find canonical role similar to input role.
    Returns None if no match above threshold.
    """
    from app.models import GlobalRole
    from app import db
    
    result = db.session.execute(
        db.select(
            GlobalRole,
            (1 - GlobalRole.embedding.cosine_distance(role_embedding)).label('similarity')
        )
        .order_by(GlobalRole.embedding.cosine_distance(role_embedding))
        .limit(1)
    ).first()
    
    if result and result.similarity >= similarity_threshold:
        return result.GlobalRole
    return None
```

### Calculate Similarity Score

```python
def calculate_semantic_similarity(
    self, 
    embedding_a: List[float], 
    embedding_b: List[float]
) -> float:
    """
    Calculate cosine similarity between two embeddings.
    Returns value between 0-100.
    """
    dot_product = sum(a * b for a, b in zip(embedding_a, embedding_b))
    magnitude_a = sum(a * a for a in embedding_a) ** 0.5
    magnitude_b = sum(b * b for b in embedding_b) ** 0.5
    
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    
    cosine_similarity = dot_product / (magnitude_a * magnitude_b)
    
    # Normalize to 0-100 scale
    return max(0.0, min(100.0, cosine_similarity * 100.0))
```

---

## Batch Embedding Generation

### For Job Import

```python
def generate_embeddings_batch(
    self, 
    texts: List[str], 
    batch_size: int = 100,
    delay: float = 0.1
) -> List[List[float]]:
    """
    Generate embeddings in batches with rate limiting.
    
    Args:
        texts: List of texts to embed
        batch_size: Texts per API call
        delay: Seconds between batches (rate limiting)
    
    Returns:
        List of embeddings (same order as input)
    """
    import time
    
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        # Gemini supports batch embedding
        result = genai.embed_content(
            model=self.MODEL_NAME,
            content=batch,
            task_type="RETRIEVAL_DOCUMENT"
        )
        
        embeddings.extend(result['embedding'])
        
        # Rate limiting
        if i + batch_size < len(texts):
            time.sleep(delay)
    
    return embeddings
```

### Update Jobs Without Embeddings

```python
def backfill_job_embeddings(self, batch_size: int = 100):
    """
    Generate embeddings for jobs that don't have them.
    Run as background task.
    """
    from app.models import JobPosting
    from app import db
    
    jobs_without_embedding = JobPosting.query.filter(
        JobPosting.embedding.is_(None),
        JobPosting.status == 'active'
    ).limit(batch_size).all()
    
    for job in jobs_without_embedding:
        embedding = self.generate_job_embedding(job)
        job.embedding = embedding
    
    db.session.commit()
    
    return len(jobs_without_embedding)
```

---

## Error Handling & Retry Logic

```python
import time
from functools import wraps

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retry with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
        return wrapper
    return decorator

class EmbeddingService:
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def generate_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT"):
        """Generate embedding with automatic retry."""
        result = genai.embed_content(
            model=self.MODEL_NAME,
            content=text,
            task_type=task_type
        )
        return result['embedding']
```

---

## Performance Optimization

### Caching Hot Embeddings

```python
from app.utils.redis_client import cached

class EmbeddingService:
    @cached(ttl=86400, key_prefix="candidate_embedding")  # 24 hour cache
    def get_candidate_embedding(self, candidate_id: int) -> List[float]:
        """
        Get or generate candidate embedding.
        Cached in Redis for frequently accessed candidates.
        """
        candidate = db.session.get(Candidate, candidate_id)
        
        if candidate.embedding:
            return list(candidate.embedding)
        
        embedding = self.generate_candidate_embedding(candidate)
        candidate.embedding = embedding
        db.session.commit()
        
        return embedding
```

### Embedding Comparison Metrics

| Metric | Query Time | Accuracy |
|--------|------------|----------|
| Cosine Distance | Fast | Best for normalized vectors |
| L2 (Euclidean) | Fast | Good for unnormalized |
| Inner Product | Fastest | Requires normalized vectors |

**Recommendation:** Use `vector_cosine_ops` (cosine distance) for Gemini embeddings.

---

## Monitoring & Debugging

### Check Embedding Quality

```python
def diagnose_embedding(self, embedding: List[float]):
    """
    Diagnose potential issues with an embedding.
    """
    import numpy as np
    
    arr = np.array(embedding)
    
    return {
        "dimensions": len(embedding),
        "expected_dimensions": 768,
        "is_valid": len(embedding) == 768,
        "magnitude": float(np.linalg.norm(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "has_nan": bool(np.isnan(arr).any()),
        "has_inf": bool(np.isinf(arr).any()),
    }
```

### Log Embedding Generation

```python
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def generate_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT"):
        logger.info(f"Generating embedding: text_length={len(text)}, task_type={task_type}")
        
        start_time = time.time()
        result = genai.embed_content(
            model=self.MODEL_NAME,
            content=text,
            task_type=task_type
        )
        elapsed = time.time() - start_time
        
        logger.info(f"Embedding generated: dimensions={len(result['embedding'])}, time={elapsed:.2f}s")
        
        return result['embedding']
```

---

## Environment Variables

```bash
# Required
GOOGLE_API_KEY=your-gemini-api-key

# Optional (for tuning)
EMBEDDING_BATCH_SIZE=100
EMBEDDING_RATE_LIMIT_DELAY=0.1
EMBEDDING_MAX_RETRIES=3
```

---

## Next: [05-MATCHING-ALGORITHM.md](./05-MATCHING-ALGORITHM.md) - Multi-Factor Scoring Algorithm

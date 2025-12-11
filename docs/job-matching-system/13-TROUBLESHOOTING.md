# Troubleshooting Guide

This guide covers common issues and their solutions for the Job Matching System.

## Embedding Issues

### Problem: Embeddings Not Generated

**Symptoms:**
- `embedding` column is NULL in database
- Job matching returns no results
- Error logs show "Failed to generate embedding"

**Causes & Solutions:**

1. **Missing Gemini API Key**
   ```bash
   # Check environment variable
   echo $GEMINI_API_KEY
   
   # Solution: Add to .env
   GEMINI_API_KEY=your-api-key-here
   ```

2. **API Rate Limiting**
   ```python
   # Error: 429 Too Many Requests
   
   # Solution: Add retry logic with exponential backoff
   # This is already implemented in EmbeddingService
   # Check logs for rate limit warnings
   ```

3. **Invalid API Key**
   ```python
   # Test API key validity
   from app.services.embedding_service import EmbeddingService
   
   try:
       embedding = EmbeddingService.generate_text_embedding("test")
       print("API key is valid" if embedding else "Key invalid")
   except Exception as e:
       print(f"Error: {e}")
   ```

4. **Network Issues**
   ```bash
   # Test connectivity to Gemini API
   curl -X POST "https://generativelanguage.googleapis.com/v1/models/embedding-001:embedContent?key=$GEMINI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"content": {"parts": [{"text": "test"}]}}'
   ```

### Problem: Vector Dimension Mismatch

**Symptoms:**
- Database errors about vector dimensions
- "operator does not exist: vector <-> vector"

**Solution:**
```sql
-- Check existing vector dimensions
SELECT column_name, udt_name 
FROM information_schema.columns 
WHERE table_name = 'candidates' AND column_name = 'embedding';

-- If dimensions don't match (should be 768):
ALTER TABLE candidates 
ALTER COLUMN embedding TYPE vector(768);

ALTER TABLE job_postings 
ALTER COLUMN embedding TYPE vector(768);
```

---

## Database Issues

### Problem: pgvector Extension Not Found

**Symptoms:**
- "ERROR: extension "vector" does not exist"
- Migration fails

**Solution:**
```sql
-- Connect as superuser
psql -U postgres -d blacklight

-- Install extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Problem: Slow Vector Searches

**Symptoms:**
- Job matching takes > 5 seconds
- High database CPU usage

**Solutions:**

1. **Create IVFFlat Index**
   ```sql
   -- Check if index exists
   SELECT indexname FROM pg_indexes 
   WHERE tablename = 'candidates' AND indexdef LIKE '%ivfflat%';
   
   -- Create if missing
   CREATE INDEX idx_candidates_embedding 
   ON candidates 
   USING ivfflat (embedding vector_cosine_ops) 
   WITH (lists = 100);
   ```

2. **Tune Index Lists Parameter**
   ```sql
   -- For tables with >100k rows, increase lists
   DROP INDEX idx_candidates_embedding;
   CREATE INDEX idx_candidates_embedding 
   ON candidates 
   USING ivfflat (embedding vector_cosine_ops) 
   WITH (lists = 300);
   ```

3. **Analyze Table**
   ```sql
   ANALYZE candidates;
   ANALYZE job_postings;
   ```

### Problem: Session Cache Issues After Delete

**Symptoms:**
- Deleted records still appear in queries
- Inconsistent data between requests

**Solution:**
```python
# Always expire session after deletes
db.session.delete(obj)
db.session.commit()
db.session.expire_all()  # Critical!

# Or use fresh queries
from sqlalchemy import select
stmt = select(Candidate).where(Candidate.id == id)
candidate = db.session.execute(stmt).scalar_one_or_none()
```

---

## Inngest Workflow Issues

### Problem: Functions Not Triggering

**Symptoms:**
- Events sent but functions don't run
- Empty Inngest dashboard

**Solutions:**

1. **Check Inngest Dev Server**
   ```bash
   # Ensure Inngest dev server is running
   docker-compose logs inngest
   
   # Or start manually
   npx inngest-cli dev
   ```

2. **Verify Event Key**
   ```python
   # Check event key in config
   print(settings.INNGEST_EVENT_KEY)
   
   # Ensure it matches Inngest dashboard
   ```

3. **Check Function Registration**
   ```python
   # All functions must be imported in __init__.py
   # app/inngest/__init__.py
   
   from app.inngest.functions.job_matching import *
   from app.inngest.functions.email_sending import *
   ```

4. **Clear Python Cache**
   ```bash
   # Inngest may use cached function definitions
   find . -type d -name "__pycache__" -exec rm -rf {} +
   docker-compose restart app
   ```

### Problem: Function Retries Exhausted

**Symptoms:**
- "Run out of retries" in Inngest dashboard
- Jobs stuck in failed state

**Solution:**
```python
# Check function logs in Inngest dashboard
# Common causes:
# 1. Database connection timeout
# 2. External API failure
# 3. Validation errors

# Increase retries for flaky operations
@inngest_client.create_function(
    fn_id="my-function",
    trigger=inngest.TriggerEvent(event="my/event"),
    retries=5,  # Increase from default 3
)
async def my_function(ctx, step):
    ...
```

### Problem: Type Hints Cause Errors

**Symptoms:**
- "TypeError: 'type' object is not subscriptable"
- Function fails immediately

**Solution:**
```python
# DON'T use type hints in Inngest functions
# Bad:
async def my_function(ctx: inngest.Context, step: inngest.Step):
    ...

# Good:
async def my_function(ctx, step):
    ...
```

---

## Job Matching Issues

### Problem: Low Match Scores

**Symptoms:**
- All matches show < 50% score
- Good candidates not matched to relevant jobs

**Diagnose:**
```python
# Check individual score components
from app.services.job_matching_service import JobMatchingService

scores = JobMatchingService.calculate_match_components(candidate, job)
print(f"Skills: {scores['skills']}")
print(f"Experience: {scores['experience']}")
print(f"Location: {scores['location']}")
print(f"Salary: {scores['salary']}")
print(f"Semantic: {scores['semantic']}")
```

**Solutions:**

1. **Skills Not Matching**
   ```python
   # Check skill format
   print(candidate.skills)  # Should be list
   print(job.required_skills)  # Should be list
   
   # Ensure lowercase comparison
   # Skills should be normalized in service layer
   ```

2. **Missing Embeddings**
   ```python
   # Regenerate embeddings
   from app.services.embedding_service import EmbeddingService
   
   EmbeddingService.generate_candidate_embedding(candidate)
   EmbeddingService.generate_job_embedding(job)
   ```

3. **Adjust Weights**
   ```bash
   # If skills are most important, increase weight
   export MATCH_SKILL_WEIGHT=0.50
   export MATCH_EXPERIENCE_WEIGHT=0.20
   export MATCH_LOCATION_WEIGHT=0.10
   export MATCH_SALARY_WEIGHT=0.10
   export MATCH_SEMANTIC_WEIGHT=0.10
   ```

### Problem: Too Many Matches

**Symptoms:**
- Candidates getting 100+ job matches
- UI slow loading matches

**Solution:**
```python
# Increase threshold
MATCH_SCORE_THRESHOLD=70  # Up from 60

# Reduce limit
TOP_MATCHES_LIMIT=25  # Down from 50
```

---

## API Issues

### Problem: 401 Unauthorized on Scraper Endpoints

**Symptoms:**
- External scraper can't authenticate
- "Invalid or expired API key"

**Diagnose:**
```bash
# Test API key
curl -X GET "http://localhost:5000/api/scrape-queue/next" \
  -H "X-Scraper-API-Key: your-key-here"
```

**Solutions:**

1. **Verify Key Exists**
   ```python
   from app.models import ScraperApiKey
   
   key = ScraperApiKey.query.filter_by(key="your-key").first()
   print(f"Active: {key.is_active}")
   print(f"Expires: {key.expires_at}")
   ```

2. **Check Key Format**
   ```python
   # Keys should start with "sk_"
   # If using hashed keys, verify hash matches
   ```

3. **Regenerate Key**
   ```python
   from app.services import scraper_api_key_service
   
   new_key = scraper_api_key_service.create_key("New Scraper")
   print(f"New key: {new_key.key}")  # Save this!
   ```

### Problem: 500 Internal Server Error

**Symptoms:**
- Random 500 errors
- "Internal Server Error" with no details

**Diagnose:**
```bash
# Check application logs
docker-compose logs -f app

# Or check log file
tail -f logs/app.log
```

**Common Causes:**

1. **Database Connection Pool Exhausted**
   ```python
   # Increase pool size in config
   SQLALCHEMY_POOL_SIZE=20
   SQLALCHEMY_MAX_OVERFLOW=10
   ```

2. **Memory Issues**
   ```bash
   # Check container memory
   docker stats
   
   # Increase memory limit in docker-compose.yml
   services:
     app:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

---

## Frontend Issues

### Problem: Stale Data After Mutations

**Symptoms:**
- UI doesn't update after create/update/delete
- Need to refresh page to see changes

**Solution:**
```typescript
// Use refetchQueries instead of invalidateQueries
const deleteMutation = useMutation({
  mutationFn: (id) => api.delete(id),
  onSuccess: async () => {
    // Force immediate refetch
    await queryClient.refetchQueries({ queryKey: ['items'] })
  }
})

// Also set staleTime: 0
const { data } = useQuery({
  queryKey: ['items'],
  queryFn: api.getItems,
  staleTime: 0,  // Always consider data stale
})
```

### Problem: UI Shows Wrong Candidate Count

**Symptoms:**
- Stats card shows different count than table
- Counts don't update after operations

**Solution:**
```typescript
// Refetch both list and stats
onSuccess: async () => {
  await queryClient.refetchQueries({ queryKey: ['candidates'] })
  await queryClient.refetchQueries({ queryKey: ['candidate-stats'] })
}
```

---

## Redis Issues

### Problem: Cache Not Invalidating

**Symptoms:**
- Old data returned after updates
- Inconsistent responses

**Solutions:**

1. **Manual Cache Clear**
   ```python
   from app.utils.redis_client import redis_client
   
   # Clear specific cache
   redis_client.delete("job_search:*")
   
   # Clear all cache (careful in production!)
   redis_client.flushdb()
   ```

2. **Check TTL Settings**
   ```python
   # Verify cache TTL
   from app.utils.redis_client import CacheTTL
   
   print(f"Job search cache: {CacheTTL.JOB_SEARCH_RESULTS}s")
   ```

### Problem: Redis Connection Refused

**Symptoms:**
- "Connection refused" errors
- App starts but caching fails

**Solution:**
```bash
# Check Redis is running
docker-compose ps redis

# Check Redis connectivity
redis-cli ping

# Verify REDIS_URL
echo $REDIS_URL
```

---

## Performance Optimization

### Slow Job Import

```python
# Use batch inserts
from sqlalchemy import insert

jobs_data = [...]  # List of job dicts
stmt = insert(JobPosting).values(jobs_data)
db.session.execute(stmt)
db.session.commit()
```

### Slow Match Generation

```python
# Pre-filter candidates by basic criteria
candidates = Candidate.query.filter(
    Candidate.embedding.isnot(None),
    Candidate.status == 'active'
).all()

# Use batch embedding generation
embeddings = EmbeddingService.batch_generate(texts)
```

---

## Logging & Debugging

### Enable Debug Logging

```python
# In development
import logging
logging.getLogger('app.services.job_matching').setLevel(logging.DEBUG)
logging.getLogger('app.services.embedding').setLevel(logging.DEBUG)
```

### Request Tracing

```python
# All requests have X-Request-ID header
# Use this for log correlation

# Example log search
grep "request_id.*abc123" logs/app.log
```

### SQL Query Logging

```python
# In development config
SQLALCHEMY_ECHO = True  # Logs all SQL queries
```

## See Also

- [12-CONFIGURATION.md](./12-CONFIGURATION.md) - Configuration reference
- [07-INNGEST-WORKFLOWS.md](./07-INNGEST-WORKFLOWS.md) - Background job details
- [08-API-ENDPOINTS.md](./08-API-ENDPOINTS.md) - API reference

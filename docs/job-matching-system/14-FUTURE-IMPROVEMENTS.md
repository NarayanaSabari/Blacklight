# Future Improvements

This document outlines planned enhancements and the roadmap for the Job Matching System.

## Roadmap Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEVELOPMENT ROADMAP                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Q1 2025                    Q2 2025                    Q3 2025             │
│  ─────────                  ─────────                  ─────────           │
│  • Real-time ingestion      • LTR model               • Multi-language     │
│  • Two-stage retrieval      • Explainable matches     • Global expansion   │
│  • Webhook notifications    • A/B testing framework   • ML personalization │
│                                                                             │
│  Q4 2025                    2026+                                          │
│  ─────────                  ──────                                         │
│  • Candidate feedback loop  • Full ML ranking                              │
│  • Interview scheduling     • Predictive matching                          │
│  • ATS integrations         • Career path suggestions                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Real-Time Ingestion (Q1 2025)

### Current State
- Batch import via JSON files
- Scheduled scraping intervals
- Manual trigger for job matching

### Target State
- Real-time job ingestion via webhooks
- Streaming updates from job boards
- Instant match recalculation

### Implementation Plan

#### 1.1 Webhook-Based Ingestion

```python
# app/routes/webhooks.py

@webhook_bp.route('/jobs/ingest', methods=['POST'])
@require_webhook_signature
def ingest_job_webhook():
    """Real-time job ingestion from job boards."""
    
    data = request.get_json()
    
    # Validate webhook signature
    if not verify_signature(request):
        return error_response("Invalid signature", 401)
    
    # Queue for processing
    inngest_client.send_sync(
        inngest.Event(
            name="jobs/real-time-ingest",
            data={
                "source": data['source'],
                "jobs": data['jobs']
            }
        )
    )
    
    return jsonify({"status": "queued"}), 202
```

#### 1.2 Change Data Capture (CDC)

```python
# Listen for database changes
# Using PostgreSQL LISTEN/NOTIFY

import asyncpg

async def listen_for_job_changes():
    conn = await asyncpg.connect(DATABASE_URL)
    
    await conn.add_listener('job_inserted', handle_new_job)
    await conn.add_listener('candidate_updated', handle_candidate_update)
```

#### 1.3 Expected Benefits
- 90% reduction in time-to-match (from 1 hour to < 5 minutes)
- Fresher job listings for candidates
- Reduced batch processing load

---

## Phase 2: Two-Stage Retrieval (Q1 2025)

### Current State
- Single-pass vector similarity search
- Full scoring on all candidates

### Target State
- Fast candidate retrieval (Stage 1)
- Detailed scoring on top candidates (Stage 2)

### Implementation Plan

#### 2.1 Stage 1: Approximate Nearest Neighbors

```python
def stage1_retrieve(job_embedding, limit: int = 1000) -> List[int]:
    """Fast ANN retrieval using pgvector."""
    
    # Use probes parameter for speed vs accuracy tradeoff
    db.session.execute("SET ivfflat.probes = 10")
    
    candidates = db.session.execute(
        select(Candidate.id).where(
            Candidate.embedding.isnot(None),
            Candidate.status == 'active'
        ).order_by(
            Candidate.embedding.cosine_distance(job_embedding)
        ).limit(limit)
    ).scalars().all()
    
    return candidates
```

#### 2.2 Stage 2: Detailed Scoring

```python
def stage2_score(candidate_ids: List[int], job: JobPosting) -> List[Match]:
    """Detailed multi-factor scoring on Stage 1 results."""
    
    candidates = Candidate.query.filter(
        Candidate.id.in_(candidate_ids)
    ).all()
    
    matches = []
    for candidate in candidates:
        score = calculate_full_match_score(candidate, job)
        if score >= MATCH_THRESHOLD:
            matches.append(Match(
                candidate_id=candidate.id,
                job_id=job.id,
                score=score
            ))
    
    return sorted(matches, key=lambda m: m.score, reverse=True)[:50]
```

#### 2.3 Expected Benefits
- 5x faster matching for large candidate pools
- Better accuracy on final matches
- Scalable to millions of candidates

---

## Phase 3: Learning-to-Rank Model (Q2 2025)

### Current State
- Fixed weight formula
- No learning from user feedback

### Target State
- ML-based ranking model
- Trained on recruiter interactions
- Continuous improvement

### Implementation Plan

#### 3.1 Feature Engineering

```python
class MatchFeatures:
    """Features for LTR model."""
    
    @staticmethod
    def extract(candidate: Candidate, job: JobPosting) -> Dict[str, float]:
        return {
            # Skill features
            "skill_overlap_count": len(set(candidate.skills) & set(job.required_skills)),
            "skill_overlap_ratio": skill_overlap_ratio(candidate, job),
            "skill_fuzzy_score": fuzzy_skill_score(candidate, job),
            
            # Experience features
            "experience_diff": candidate.years_of_experience - job.min_experience,
            "experience_ratio": candidate.years_of_experience / max(job.min_experience, 1),
            
            # Semantic features
            "embedding_similarity": cosine_similarity(
                candidate.embedding, job.embedding
            ),
            "title_similarity": text_similarity(candidate.current_title, job.title),
            
            # Location features
            "same_city": 1.0 if candidate.city == job.location else 0.0,
            "same_state": 1.0 if candidate.state == job.state else 0.0,
            "remote_match": 1.0 if job.remote_allowed else 0.0,
            
            # Salary features
            "salary_in_range": salary_in_range(candidate, job),
            
            # Engagement features
            "candidate_response_rate": candidate.response_rate or 0.5,
            "job_click_rate": job.click_rate or 0.5,
        }
```

#### 3.2 Model Training

```python
from lightgbm import LGBMRanker

class LTRModel:
    def __init__(self):
        self.model = LGBMRanker(
            objective="lambdarank",
            metric="ndcg",
            n_estimators=100,
            learning_rate=0.1
        )
    
    def train(self, features: np.ndarray, labels: np.ndarray, groups: np.ndarray):
        """Train on historical recruiter decisions."""
        self.model.fit(
            features, 
            labels,  # 1 = viewed/contacted, 0 = skipped
            group=groups  # Group by job posting
        )
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        return self.model.predict(features)
```

#### 3.3 Expected Benefits
- 20-30% improvement in match relevance
- Personalized ranking per recruiter
- Continuous improvement from feedback

---

## Phase 4: Explainable Matches (Q2 2025)

### Current State
- Only shows overall match score
- No explanation of why matched

### Target State
- Detailed match explanations
- Highlight matching skills
- Show score breakdown

### Implementation Plan

#### 4.1 Match Explanation Service

```python
class MatchExplanation:
    """Generate human-readable match explanations."""
    
    @staticmethod
    def generate(candidate: Candidate, job: JobPosting, score: float) -> Dict:
        components = JobMatchingService.calculate_match_components(candidate, job)
        
        explanation = {
            "overall_score": score,
            "grade": get_grade(score),
            "summary": generate_summary(candidate, job, score),
            "strengths": [],
            "improvements": [],
            "skill_matches": [],
            "score_breakdown": components
        }
        
        # Identify strengths
        if components['skills'] >= 80:
            explanation['strengths'].append({
                "factor": "skills",
                "message": f"Strong skill match ({components['skills']}%)",
                "matched_skills": get_matched_skills(candidate, job)
            })
        
        # Identify areas for improvement
        if components['experience'] < 60:
            explanation['improvements'].append({
                "factor": "experience",
                "message": f"Experience gap: Job requires {job.min_experience}+ years",
                "candidate_value": candidate.years_of_experience
            })
        
        return explanation
```

#### 4.2 UI Integration

```tsx
// ui/portal/src/components/MatchExplanation.tsx

interface MatchExplanationProps {
  match: JobMatch
  explanation: Explanation
}

export function MatchExplanation({ match, explanation }: MatchExplanationProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Badge variant="default" className="text-lg">
          {explanation.grade}
        </Badge>
        <span className="text-2xl font-bold">{explanation.overall_score}%</span>
      </div>
      
      <p className="text-muted-foreground">{explanation.summary}</p>
      
      {/* Strengths */}
      <div>
        <h4 className="font-medium flex items-center gap-2">
          <CheckCircle className="h-4 w-4 text-green-500" />
          Why This Match Works
        </h4>
        <ul className="mt-2 space-y-1">
          {explanation.strengths.map((strength, i) => (
            <li key={i} className="text-sm">{strength.message}</li>
          ))}
        </ul>
      </div>
      
      {/* Score Breakdown */}
      <div className="grid grid-cols-5 gap-2">
        {Object.entries(explanation.score_breakdown).map(([key, value]) => (
          <div key={key} className="text-center">
            <div className="text-lg font-bold">{value}%</div>
            <div className="text-xs text-muted-foreground capitalize">{key}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## Phase 5: A/B Testing Framework (Q2 2025)

### Goal
- Test different matching algorithms
- Measure recruiter satisfaction
- Data-driven optimization

### Implementation

```python
class ABTestService:
    """A/B testing for matching algorithms."""
    
    @staticmethod
    def assign_variant(user_id: int, experiment: str) -> str:
        """Consistently assign user to variant."""
        
        hash_input = f"{user_id}:{experiment}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        variant_number = int(hash_value[:8], 16) % 100
        
        # Get experiment config
        experiment_config = get_experiment(experiment)
        
        cumulative = 0
        for variant, percentage in experiment_config['variants'].items():
            cumulative += percentage
            if variant_number < cumulative:
                return variant
        
        return 'control'
    
    @staticmethod
    def track_metric(
        experiment: str, 
        variant: str, 
        metric: str, 
        value: float
    ):
        """Track A/B test metrics."""
        
        redis_client.hincrby(
            f"ab:{experiment}:{variant}:count:{metric}",
            value
        )
```

---

## Phase 6: Multi-Language Support (Q3 2025)

### Goal
- Support non-English job postings
- Cross-language matching
- Localized UI

### Implementation

```python
class MultilingualEmbedding:
    """Generate embeddings for multiple languages."""
    
    SUPPORTED_LANGUAGES = ['en', 'es', 'de', 'fr', 'zh', 'ja']
    
    @staticmethod
    def detect_language(text: str) -> str:
        """Detect text language."""
        from langdetect import detect
        return detect(text)
    
    @staticmethod
    def generate_embedding(text: str, language: str = None) -> List[float]:
        """Generate embedding with language awareness."""
        
        if language is None:
            language = MultilingualEmbedding.detect_language(text)
        
        # Use multilingual model
        # Gemini supports multiple languages
        return EmbeddingService.generate_text_embedding(text)
```

---

## Phase 7: Candidate Feedback Loop (Q4 2025)

### Goal
- Collect candidate feedback on matches
- Use feedback to improve model
- Personalized recommendations

### Implementation

```python
@candidates_bp.route('/matches/<int:match_id>/feedback', methods=['POST'])
@require_portal_auth
def submit_match_feedback(match_id: int):
    """Collect candidate feedback on match quality."""
    
    data = request.get_json()
    
    feedback = MatchFeedback(
        match_id=match_id,
        user_id=g.user.id,
        rating=data.get('rating'),  # 1-5
        relevance=data.get('relevance'),  # relevant, somewhat, not_relevant
        applied=data.get('applied', False),
        reason=data.get('reason'),  # Why not interested
    )
    
    db.session.add(feedback)
    db.session.commit()
    
    # Queue for model retraining
    inngest_client.send_sync(
        inngest.Event(
            name="ml/feedback-received",
            data={"feedback_id": feedback.id}
        )
    )
    
    return jsonify({"message": "Feedback recorded"}), 201
```

---

## Phase 8: ATS Integrations (Q4 2025)

### Goal
- Integrate with major ATS platforms
- Sync candidates bidirectionally
- Unified workflow

### Planned Integrations
- Greenhouse
- Lever
- Workday
- BambooHR
- iCIMS

### Implementation Pattern

```python
class ATSConnector(ABC):
    """Base class for ATS integrations."""
    
    @abstractmethod
    def sync_candidates(self) -> List[Candidate]:
        """Pull candidates from ATS."""
        pass
    
    @abstractmethod
    def push_application(self, candidate_id: int, job_id: int):
        """Push application to ATS."""
        pass
    
    @abstractmethod
    def get_job_status(self, job_id: int) -> str:
        """Get job posting status from ATS."""
        pass


class GreenhouseConnector(ATSConnector):
    def __init__(self, api_key: str):
        self.client = GreenhouseClient(api_key)
    
    def sync_candidates(self):
        candidates = self.client.get_candidates()
        return [self._map_candidate(c) for c in candidates]
```

---

## Technical Debt Items

### High Priority
1. **Add comprehensive unit tests for matching algorithm**
2. **Implement proper error boundaries in frontend**
3. **Add request rate limiting per tenant**
4. **Optimize batch embedding generation**

### Medium Priority
1. **Migrate to async SQLAlchemy**
2. **Add OpenTelemetry tracing**
3. **Implement proper connection pooling for external APIs**
4. **Add database query caching layer**

### Low Priority
1. **Refactor skill matching to use ML model**
2. **Add GraphQL API option**
3. **Implement WebSocket for real-time updates**
4. **Add support for resume PDF parsing improvements**

---

## Metrics & Success Criteria

### Current Baseline
- Match generation time: ~5 seconds per candidate
- Match relevance (user feedback): 65%
- Job import throughput: 500 jobs/minute

### Target Metrics (End of 2025)
- Match generation time: < 500ms per candidate
- Match relevance: > 85%
- Job import throughput: 5000 jobs/minute
- Candidate engagement with matches: > 40%

---

## Contributing

To contribute to these improvements:

1. Check the [GitHub Issues](https://github.com/org/blacklight/issues) for open tasks
2. Review the [CONTRIBUTING.md](../../CONTRIBUTING.md) guide
3. Submit PRs with comprehensive tests
4. Update documentation for any API changes

## See Also

- [01-OVERVIEW.md](./01-OVERVIEW.md) - System overview
- [05-MATCHING-ALGORITHM.md](./05-MATCHING-ALGORITHM.md) - Current algorithm details
- [07-INNGEST-WORKFLOWS.md](./07-INNGEST-WORKFLOWS.md) - Background processing

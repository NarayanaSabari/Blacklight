# Phase 3: Matching Algorithm

## Overview

The matching algorithm calculates a composite score (0-100) based on five weighted factors. This document details the scoring logic, weights, and grade system.

---

## Scoring Weights

| Factor | Weight | Description |
|--------|--------|-------------|
| **Skills Match** | 40% | Overlap between candidate and job skills |
| **Experience Match** | 25% | Years of experience vs requirements |
| **Location Match** | 15% | Location preference compatibility |
| **Salary Match** | 10% | Expected vs offered salary alignment |
| **Semantic Similarity** | 10% | Embedding cosine similarity |

### Weight Configuration

```python
# server/app/services/job_matching_service.py

class JobMatchingService:
    # Scoring weights (must sum to 1.0)
    WEIGHT_SKILLS = 0.40
    WEIGHT_EXPERIENCE = 0.25
    WEIGHT_LOCATION = 0.15
    WEIGHT_SALARY = 0.10
    WEIGHT_SEMANTIC = 0.10
```

---

## Final Score Calculation

```python
def calculate_match_score(
    self, 
    candidate, 
    job, 
    candidate_embedding, 
    job_embedding
) -> dict:
    """
    Calculate overall match score and component scores.
    
    Returns:
        {
            "match_score": 82.5,
            "skill_match_score": 80.0,
            "experience_match_score": 100.0,
            "location_match_score": 75.0,
            "salary_match_score": 70.0,
            "semantic_similarity": 78.0,
            "matched_skills": ["Python", "AWS", "React"],
            "missing_skills": ["Kubernetes"],
            "match_reasons": ["Good skill match (3/4)", ...],
            "grade": "A"
        }
    """
    # Calculate component scores
    skill_result = self.calculate_skill_match(candidate.skills, job.skills)
    exp_score = self.calculate_experience_match(
        candidate.total_experience_years, 
        job.experience_min, 
        job.experience_max
    )
    loc_score = self.calculate_location_match(
        candidate.location, 
        candidate.preferred_locations,
        job.location, 
        job.is_remote
    )
    sal_score = self.calculate_salary_match(
        candidate.expected_salary, 
        job.salary_min, 
        job.salary_max
    )
    sem_score = self.calculate_semantic_similarity(
        candidate_embedding, 
        job_embedding
    )
    
    # Weighted sum
    overall_score = (
        skill_result['score'] * self.WEIGHT_SKILLS +
        exp_score * self.WEIGHT_EXPERIENCE +
        loc_score * self.WEIGHT_LOCATION +
        sal_score * self.WEIGHT_SALARY +
        sem_score * self.WEIGHT_SEMANTIC
    )
    
    return {
        "match_score": round(overall_score, 2),
        "skill_match_score": round(skill_result['score'], 2),
        "experience_match_score": round(exp_score, 2),
        "location_match_score": round(loc_score, 2),
        "salary_match_score": round(sal_score, 2),
        "semantic_similarity": round(sem_score, 2),
        "matched_skills": skill_result['matched'],
        "missing_skills": skill_result['missing'],
        "match_reasons": self.generate_reasons(
            skill_result, exp_score, loc_score, sal_score, sem_score
        ),
        "grade": self.score_to_grade(overall_score)
    }
```

---

## Match Grades

| Grade | Score Range | Meaning | Action |
|-------|-------------|---------|--------|
| **A+** | 90-100 | Excellent match | Priority outreach |
| **A** | 80-89 | Very good match | Strong candidate |
| **B** | 70-79 | Good match | Worth considering |
| **C** | 60-69 | Fair match | Review if needed |
| **D** | 50-59 | Poor match | Low priority |
| **F** | <50 | Not recommended | Filter out |

```python
def score_to_grade(self, score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"
```

---

## Component 1: Skills Matching (40%)

### Three-Strategy Approach

1. **Exact Match** - Case-insensitive string equality
2. **Synonym Match** - Predefined skill synonyms
3. **Fuzzy Match** - 85% string similarity threshold

### Synonym Dictionary

```python
SKILL_SYNONYMS = {
    # Cloud platforms
    'aws': ['amazon web services', 'amazon aws', 'ec2', 's3'],
    'gcp': ['google cloud', 'google cloud platform'],
    'azure': ['microsoft azure', 'azure cloud'],
    
    # Programming languages
    'js': ['javascript', 'es6', 'ecmascript'],
    'ts': ['typescript'],
    'py': ['python', 'python3'],
    'golang': ['go', 'go lang'],
    
    # Frameworks
    'react': ['reactjs', 'react.js', 'react native'],
    'vue': ['vuejs', 'vue.js'],
    'angular': ['angularjs', 'angular.js'],
    'node': ['nodejs', 'node.js'],
    'django': ['django rest framework', 'drf'],
    'rails': ['ruby on rails', 'ror'],
    
    # Databases
    'postgres': ['postgresql', 'pg', 'psql'],
    'mysql': ['mariadb'],
    'mongodb': ['mongo', 'mongo db'],
    'redis': ['redis cache'],
    
    # DevOps
    'k8s': ['kubernetes', 'kube'],
    'docker': ['docker compose', 'containerization'],
    'ci/cd': ['cicd', 'jenkins', 'github actions', 'gitlab ci'],
    'terraform': ['tf', 'infrastructure as code', 'iac'],
    
    # Other
    'ml': ['machine learning'],
    'ai': ['artificial intelligence'],
    'nlp': ['natural language processing'],
    'api': ['rest api', 'restful', 'graphql'],
}
```

### Matching Algorithm

```python
def calculate_skill_match(
    self, 
    candidate_skills: List[str], 
    job_skills: List[str]
) -> dict:
    """
    Calculate skill match score using three strategies.
    
    Returns:
        {
            "score": 80.0,
            "matched": ["Python", "AWS", "React"],
            "missing": ["Kubernetes"],
            "match_details": {
                "Python": "exact",
                "AWS": "synonym (amazon web services)",
                "React": "exact"
            }
        }
    """
    if not job_skills:
        return {"score": 50.0, "matched": [], "missing": []}
    
    candidate_skills_lower = [s.lower().strip() for s in (candidate_skills or [])]
    job_skills_lower = [s.lower().strip() for s in job_skills]
    
    matched = []
    match_details = {}
    
    for job_skill in job_skills:
        job_skill_lower = job_skill.lower().strip()
        
        # Strategy 1: Exact match
        if job_skill_lower in candidate_skills_lower:
            matched.append(job_skill)
            match_details[job_skill] = "exact"
            continue
        
        # Strategy 2: Synonym match
        synonym_match = self._check_synonym_match(job_skill_lower, candidate_skills_lower)
        if synonym_match:
            matched.append(job_skill)
            match_details[job_skill] = f"synonym ({synonym_match})"
            continue
        
        # Strategy 3: Fuzzy match (85% threshold)
        fuzzy_match = self._check_fuzzy_match(job_skill_lower, candidate_skills_lower, threshold=0.85)
        if fuzzy_match:
            matched.append(job_skill)
            match_details[job_skill] = f"fuzzy ({fuzzy_match})"
    
    missing = [s for s in job_skills if s not in matched]
    score = (len(matched) / len(job_skills)) * 100.0
    
    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "match_details": match_details
    }

def _check_synonym_match(
    self, 
    job_skill: str, 
    candidate_skills: List[str]
) -> Optional[str]:
    """Check if any candidate skill is a synonym of job skill."""
    # Check if job skill is in synonym dictionary
    if job_skill in self.SKILL_SYNONYMS:
        synonyms = self.SKILL_SYNONYMS[job_skill]
        for candidate_skill in candidate_skills:
            if candidate_skill in synonyms:
                return candidate_skill
    
    # Reverse check: candidate skill might be the canonical form
    for canonical, synonyms in self.SKILL_SYNONYMS.items():
        if job_skill in synonyms:
            if canonical in candidate_skills:
                return canonical
            for syn in synonyms:
                if syn in candidate_skills:
                    return syn
    
    return None

def _check_fuzzy_match(
    self, 
    job_skill: str, 
    candidate_skills: List[str], 
    threshold: float = 0.85
) -> Optional[str]:
    """Check fuzzy string similarity."""
    from difflib import SequenceMatcher
    
    for candidate_skill in candidate_skills:
        ratio = SequenceMatcher(None, job_skill, candidate_skill).ratio()
        if ratio >= threshold:
            return candidate_skill
    
    return None
```

### Examples

| Job Requires | Candidate Has | Match Type | Result |
|--------------|---------------|------------|--------|
| Python | Python | Exact | ✅ |
| AWS | Amazon Web Services | Synonym | ✅ |
| Kubernetes | k8s | Synonym | ✅ |
| React | ReactJS | Synonym | ✅ |
| PostgreSQL | Postgres | Synonym | ✅ |
| JavaScript | JavaScripts | Fuzzy (94%) | ✅ |
| Go | Golang | Synonym | ✅ |
| Rust | - | No match | ❌ |

---

## Component 2: Experience Matching (25%)

### Scoring Logic

```python
def calculate_experience_match(
    self, 
    candidate_years: Optional[int], 
    job_min: Optional[int], 
    job_max: Optional[int]
) -> float:
    """
    Calculate experience match score.
    
    Handles:
    - Underqualified (penalty based on gap)
    - Qualified (full score)
    - Overqualified (slight penalty)
    """
    # No data case
    if candidate_years is None or job_min is None:
        return 50.0  # Neutral score
    
    # Meets or exceeds minimum
    if candidate_years >= job_min:
        if job_max is None:
            return 100.0  # No max, candidate qualifies
        
        # Check overqualification
        years_over = candidate_years - job_max
        if years_over <= 0:
            return 100.0  # Within range
        elif years_over <= 2:
            return 95.0   # Slightly over
        elif years_over <= 5:
            return 85.0   # Moderately over
        elif years_over <= 10:
            return 70.0   # Significantly over
        else:
            return 60.0   # Very overqualified
    
    # Underqualified - score based on gap
    gap = job_min - candidate_years
    if gap == 1:
        return 85.0
    elif gap == 2:
        return 70.0
    elif gap == 3:
        return 55.0
    else:
        return 40.0  # 4+ years short
```

### Scoring Table

| Scenario | Gap | Score |
|----------|-----|-------|
| Meets minimum | 0 | 100% |
| 1 year short | -1 | 85% |
| 2 years short | -2 | 70% |
| 3 years short | -3 | 55% |
| 4+ years short | -4+ | 40% |
| 1-2 years over max | +1-2 | 95% |
| 3-5 years over max | +3-5 | 85% |
| 6-10 years over max | +6-10 | 70% |
| 11+ years over max | +11+ | 60% |

---

## Component 3: Location Matching (15%)

### Scoring Logic

```python
def calculate_location_match(
    self, 
    candidate_location: Optional[str],
    candidate_preferred: Optional[List[str]],
    job_location: Optional[str], 
    is_remote: bool
) -> float:
    """
    Calculate location match score.
    
    Considers:
    - Remote work preference
    - Same city/state
    - Relocation willingness
    """
    # Normalize inputs
    c_loc = (candidate_location or "").lower().strip()
    c_prefs = [p.lower().strip() for p in (candidate_preferred or [])]
    j_loc = (job_location or "").lower().strip()
    
    # Check for "remote" preference
    candidate_wants_remote = 'remote' in c_loc or 'remote' in c_prefs
    
    # Remote job handling
    if is_remote:
        if candidate_wants_remote or not c_prefs:
            return 100.0  # Remote job + candidate OK with remote
        return 90.0  # Remote job, candidate prefers onsite but can work
    
    # No location data
    if not j_loc or not c_loc:
        return 50.0  # Neutral
    
    # Candidate wants remote but job is onsite
    if candidate_wants_remote and not is_remote:
        return 40.0  # Mismatch
    
    # Extract city and state
    c_parts = c_loc.replace(",", " ").split()
    j_parts = j_loc.replace(",", " ").split()
    
    # Same city check (simple substring)
    if c_loc in j_loc or j_loc in c_loc:
        return 100.0
    
    # Check preferred locations
    for pref in c_prefs:
        if pref in j_loc or j_loc in pref:
            return 100.0
    
    # Same state check (2-letter code at end)
    c_state = c_parts[-1] if c_parts else ""
    j_state = j_parts[-1] if j_parts else ""
    
    if len(c_state) == 2 and len(j_state) == 2 and c_state == j_state:
        return 75.0  # Same state, different city
    
    # Different location
    return 30.0
```

### Scoring Table

| Scenario | Score |
|----------|-------|
| Remote job + candidate wants remote | 100% |
| Remote job + candidate flexible | 90% |
| Same city | 100% |
| In candidate's preferred locations | 100% |
| Same state, different city | 75% |
| Candidate wants remote, job is onsite | 40% |
| Different locations | 30% |
| No location data | 50% |

---

## Component 4: Salary Matching (10%)

### Scoring Logic

```python
def calculate_salary_match(
    self, 
    candidate_expected: Optional[str], 
    job_min: Optional[int], 
    job_max: Optional[int]
) -> float:
    """
    Calculate salary match score.
    
    Parses candidate's expected salary string and compares
    to job's salary range.
    """
    # No job salary data
    if job_min is None and job_max is None:
        return 50.0  # Neutral
    
    # Parse candidate expectation
    if not candidate_expected:
        return 80.0  # Flexible/no expectation = slightly positive
    
    candidate_min, candidate_max = self._parse_salary_string(candidate_expected)
    
    if candidate_min is None:
        return 80.0  # Couldn't parse = flexible
    
    job_max_effective = job_max or job_min
    job_min_effective = job_min or job_max
    
    # Check overlap
    if candidate_max and job_min_effective:
        # Candidate's max >= job's min means potential overlap
        if candidate_max >= job_min_effective and candidate_min <= job_max_effective:
            return 100.0  # Ranges overlap
    
    # Candidate min > job max (candidate wants more)
    if job_max_effective and candidate_min > job_max_effective:
        gap_pct = (candidate_min - job_max_effective) / job_max_effective
        if gap_pct < 0.10:
            return 75.0  # Within 10%
        elif gap_pct < 0.20:
            return 60.0  # 10-20% gap
        elif gap_pct < 0.30:
            return 45.0  # 20-30% gap
        else:
            return 30.0  # >30% gap
    
    # Candidate wants less than job offers (positive)
    return 100.0

def _parse_salary_string(self, salary_str: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse salary string into min/max integers.
    
    Handles formats like:
    - "$150K - $180K"
    - "150000-180000"
    - "$150K+"
    - "150K"
    """
    import re
    
    # Remove currency symbols and spaces
    clean = salary_str.upper().replace("$", "").replace(",", "").strip()
    
    # Find all numbers
    numbers = re.findall(r'(\d+\.?\d*)K?', clean)
    
    if not numbers:
        return None, None
    
    # Convert to integers
    values = []
    for num in numbers:
        val = float(num)
        if 'K' in clean.upper():
            val *= 1000
        elif val < 1000:
            val *= 1000  # Assume K if small number
        values.append(int(val))
    
    if len(values) == 1:
        return values[0], values[0]
    return min(values), max(values)
```

### Scoring Table

| Scenario | Score |
|----------|-------|
| Ranges overlap fully | 100% |
| Candidate flexible (no expectation) | 80% |
| Gap <10% | 75% |
| Gap 10-20% | 60% |
| Gap 20-30% | 45% |
| Gap >30% | 30% |
| No salary data | 50% |

---

## Component 5: Semantic Similarity (10%)

### Calculation

```python
def calculate_semantic_similarity(
    self, 
    candidate_embedding: List[float], 
    job_embedding: List[float]
) -> float:
    """
    Calculate cosine similarity between embeddings.
    Returns 0-100 score.
    """
    if not candidate_embedding or not job_embedding:
        return 50.0  # Neutral if missing
    
    # Cosine similarity = (A · B) / (||A|| * ||B||)
    dot_product = sum(a * b for a, b in zip(candidate_embedding, job_embedding))
    magnitude_a = sum(a * a for a in candidate_embedding) ** 0.5
    magnitude_b = sum(b * b for b in job_embedding) ** 0.5
    
    if magnitude_a == 0 or magnitude_b == 0:
        return 50.0
    
    cosine_sim = dot_product / (magnitude_a * magnitude_b)
    
    # Cosine similarity ranges from -1 to 1
    # Normalize to 0-100 scale
    # Typical embedding similarity is 0.5-0.95
    normalized = max(0.0, min(100.0, (cosine_sim + 1) * 50))
    
    return normalized
```

### What Semantic Similarity Captures

- Job title similarity (e.g., "Software Engineer" ≈ "SWE")
- Industry/domain overlap
- Technology stack context
- Professional experience alignment

---

## Generate Match Reasons

```python
def generate_reasons(
    self, 
    skill_result: dict, 
    exp_score: float, 
    loc_score: float, 
    sal_score: float, 
    sem_score: float
) -> List[str]:
    """Generate human-readable match explanations."""
    reasons = []
    
    # Skills
    matched = len(skill_result['matched'])
    total = matched + len(skill_result['missing'])
    if total > 0:
        if skill_result['score'] >= 80:
            reasons.append(f"✅ Strong skill match ({matched}/{total} skills)")
        elif skill_result['score'] >= 60:
            reasons.append(f"🟡 Partial skill match ({matched}/{total} skills)")
        else:
            reasons.append(f"⚠️ Skill gap ({matched}/{total} skills)")
    
    # Experience
    if exp_score >= 90:
        reasons.append("✅ Experience level matches well")
    elif exp_score >= 70:
        reasons.append("🟡 Close to required experience")
    else:
        reasons.append("⚠️ Experience gap")
    
    # Location
    if loc_score >= 90:
        reasons.append("✅ Location match")
    elif loc_score >= 60:
        reasons.append("🟡 Location flexible")
    else:
        reasons.append("⚠️ Location mismatch")
    
    # Salary
    if sal_score >= 80:
        reasons.append("✅ Salary expectation aligns")
    elif sal_score >= 60:
        reasons.append("🟡 Salary negotiable")
    else:
        reasons.append("⚠️ Salary gap")
    
    return reasons
```

---

## Full Example

### Input

**Candidate:**
```python
{
    "skills": ["Python", "AWS", "React", "PostgreSQL"],
    "total_experience_years": 5,
    "location": "San Francisco, CA",
    "preferred_locations": ["Remote", "San Francisco"],
    "expected_salary": "$150K - $170K"
}
```

**Job:**
```python
{
    "skills": ["Python", "AWS", "Kubernetes", "React", "PostgreSQL"],
    "experience_min": 4,
    "experience_max": 8,
    "location": "Remote",
    "is_remote": True,
    "salary_min": 140000,
    "salary_max": 180000
}
```

### Calculation

| Component | Calculation | Score |
|-----------|-------------|-------|
| Skills | 4/5 matched (Python, AWS, React, PostgreSQL) | 80% |
| Experience | 5 years in 4-8 range | 100% |
| Location | Remote job + candidate wants remote | 100% |
| Salary | $150-170K in $140-180K range | 100% |
| Semantic | Cosine similarity | 75% |

**Weighted Score:**
```
(80 × 0.40) + (100 × 0.25) + (100 × 0.15) + (100 × 0.10) + (75 × 0.10)
= 32 + 25 + 15 + 10 + 7.5
= 89.5 → Grade: A
```

---

## Next: [06-SKILL-MATCHING.md](./06-SKILL-MATCHING.md) - Deep Dive into Skill Matching

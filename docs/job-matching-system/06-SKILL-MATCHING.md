# Phase 3: Skill Matching Deep Dive

## Overview

Skill matching is the most heavily weighted component (40%) of the matching algorithm. This document provides detailed coverage of the three-strategy approach.

---

## Strategy Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SKILL MATCHING STRATEGIES                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Job Skill: "Kubernetes"                                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Strategy 1: EXACT MATCH                                             │   │
│  │ ───────────────────────                                             │   │
│  │ candidate_skill.lower() == job_skill.lower()                        │   │
│  │                                                                     │   │
│  │ "kubernetes" == "kubernetes" → ✅ MATCH                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              │ No match                                     │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Strategy 2: SYNONYM MATCH                                           │   │
│  │ ─────────────────────────                                           │   │
│  │ Check SKILL_SYNONYMS dictionary                                     │   │
│  │                                                                     │   │
│  │ "kubernetes" synonyms: ["k8s", "kube"]                              │   │
│  │ Candidate has "k8s" → ✅ MATCH                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              │ No match                                     │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Strategy 3: FUZZY MATCH (85% threshold)                             │   │
│  │ ────────────────────────────────────────                            │   │
│  │ SequenceMatcher ratio >= 0.85                                       │   │
│  │                                                                     │   │
│  │ "kubernetes" vs "kubernetis" = 0.95 → ✅ MATCH (typo tolerance)     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              │ No match                                     │
│                              ▼                                              │
│                         ❌ MISSING SKILL                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Synonym Dictionary

```python
# server/app/services/job_matching_service.py

SKILL_SYNONYMS = {
    # ===================
    # CLOUD PLATFORMS
    # ===================
    'aws': [
        'amazon web services', 
        'amazon aws', 
        'ec2', 
        's3', 
        'lambda', 
        'cloudwatch',
        'aws lambda'
    ],
    'gcp': [
        'google cloud', 
        'google cloud platform', 
        'gce', 
        'bigquery', 
        'google compute engine'
    ],
    'azure': [
        'microsoft azure', 
        'azure cloud', 
        'azure devops',
        'azure functions'
    ],
    
    # ===================
    # PROGRAMMING LANGUAGES
    # ===================
    'javascript': ['js', 'es6', 'es2015', 'ecmascript', 'es5', 'es7'],
    'typescript': ['ts'],
    'python': ['py', 'python3', 'python2', 'cpython'],
    'golang': ['go', 'go lang', 'go-lang'],
    'c++': ['cpp', 'cplusplus', 'c plus plus'],
    'c#': ['csharp', 'c sharp', 'dotnet'],
    '.net': ['dotnet', 'dot net', '.net core', 'dotnet core'],
    'ruby': ['rb'],
    'rust': ['rustlang'],
    'scala': ['scala lang'],
    'kotlin': ['kt'],
    'swift': ['swift lang', 'swiftui'],
    'objective-c': ['objc', 'objective c'],
    'php': ['php7', 'php8'],
    'perl': ['perl5', 'perl6'],
    
    # ===================
    # FRONTEND FRAMEWORKS
    # ===================
    'react': ['reactjs', 'react.js', 'react native', 'react-native'],
    'vue': ['vuejs', 'vue.js', 'vue3', 'nuxt', 'nuxtjs'],
    'angular': ['angularjs', 'angular.js', 'angular2', 'angular 2'],
    'svelte': ['sveltejs', 'sveltekit'],
    'next.js': ['nextjs', 'next'],
    'gatsby': ['gatsbyjs'],
    'ember': ['emberjs', 'ember.js'],
    'backbone': ['backbonejs', 'backbone.js'],
    'jquery': ['jq'],
    
    # ===================
    # BACKEND FRAMEWORKS
    # ===================
    'node': ['nodejs', 'node.js', 'express', 'expressjs'],
    'express': ['expressjs', 'express.js'],
    'django': ['django rest framework', 'drf', 'django-rest'],
    'flask': ['flask api'],
    'fastapi': ['fast api', 'fast-api'],
    'rails': ['ruby on rails', 'ror', 'ruby rails'],
    'spring': ['spring boot', 'springboot', 'spring framework'],
    'laravel': ['laravel php'],
    'asp.net': ['asp net', 'aspnet'],
    'nestjs': ['nest.js', 'nest'],
    'koa': ['koajs', 'koa.js'],
    'hapi': ['hapijs'],
    'gin': ['gin-gonic', 'gin golang'],
    'fiber': ['gofiber', 'fiber golang'],
    
    # ===================
    # DATABASES
    # ===================
    'postgresql': ['postgres', 'pg', 'psql', 'pgsql'],
    'mysql': ['mariadb', 'maria db', 'mysql server'],
    'mongodb': ['mongo', 'mongo db', 'mongoose'],
    'redis': ['redis cache', 'redis db'],
    'elasticsearch': ['elastic search', 'elastic', 'es'],
    'cassandra': ['apache cassandra'],
    'dynamodb': ['dynamo db', 'amazon dynamodb'],
    'oracle': ['oracle db', 'oracle database', 'plsql', 'pl/sql'],
    'sql server': ['mssql', 'ms sql', 'microsoft sql'],
    'sqlite': ['sqlite3'],
    'couchdb': ['couch db', 'apache couchdb'],
    'neo4j': ['neo 4j'],
    'firestore': ['firebase firestore', 'cloud firestore'],
    
    # ===================
    # DEVOPS & INFRASTRUCTURE
    # ===================
    'kubernetes': ['k8s', 'kube', 'kubectl'],
    'docker': ['docker compose', 'docker-compose', 'containerization', 'containers'],
    'terraform': ['tf', 'infrastructure as code', 'iac', 'hcl'],
    'ansible': ['ansible playbook'],
    'puppet': ['puppet enterprise'],
    'chef': ['chef infra'],
    'jenkins': ['jenkins ci', 'jenkinsfile'],
    'gitlab ci': ['gitlab-ci', 'gitlab ci/cd'],
    'github actions': ['gh actions'],
    'circle ci': ['circleci'],
    'travis ci': ['travis-ci', 'travisci'],
    'ci/cd': ['cicd', 'continuous integration', 'continuous delivery', 'continuous deployment'],
    'nginx': ['nginx server'],
    'apache': ['apache server', 'httpd'],
    'linux': ['unix', 'ubuntu', 'centos', 'debian', 'rhel'],
    'bash': ['shell', 'shell script', 'sh', 'zsh'],
    'prometheus': ['prometheus monitoring'],
    'grafana': ['grafana dashboard'],
    'datadog': ['data dog'],
    
    # ===================
    # MESSAGE QUEUES
    # ===================
    'kafka': ['apache kafka'],
    'rabbitmq': ['rabbit mq', 'amqp'],
    'sqs': ['amazon sqs', 'aws sqs'],
    'pubsub': ['google pubsub', 'gcp pubsub', 'pub/sub'],
    
    # ===================
    # DATA & ML
    # ===================
    'machine learning': ['ml'],
    'artificial intelligence': ['ai'],
    'deep learning': ['dl'],
    'natural language processing': ['nlp'],
    'computer vision': ['cv'],
    'tensorflow': ['tf', 'tf2'],
    'pytorch': ['torch'],
    'scikit-learn': ['sklearn', 'scikit learn'],
    'pandas': ['pd'],
    'numpy': ['np'],
    'spark': ['apache spark', 'pyspark'],
    'hadoop': ['apache hadoop', 'hdfs'],
    
    # ===================
    # API & PROTOCOLS
    # ===================
    'rest api': ['restful', 'rest', 'restful api'],
    'graphql': ['graph ql'],
    'grpc': ['g rpc', 'google rpc'],
    'websocket': ['websockets', 'ws'],
    'oauth': ['oauth2', 'oauth 2.0'],
    'jwt': ['json web token'],
    
    # ===================
    # TESTING
    # ===================
    'unit testing': ['unit tests'],
    'jest': ['jestjs'],
    'pytest': ['py.test'],
    'mocha': ['mochajs'],
    'cypress': ['cypress.io'],
    'selenium': ['selenium webdriver'],
    'playwright': ['playwright testing'],
    
    # ===================
    # VERSION CONTROL
    # ===================
    'git': ['github', 'gitlab', 'bitbucket', 'version control'],
    
    # ===================
    # AGILE & PROJECT
    # ===================
    'agile': ['scrum', 'kanban', 'agile methodology'],
    'jira': ['atlassian jira'],
    
    # ===================
    # OTHER
    # ===================
    'html': ['html5'],
    'css': ['css3', 'scss', 'sass', 'less'],
    'tailwind': ['tailwindcss', 'tailwind css'],
    'bootstrap': ['bootstrap css', 'bootstrap 5'],
    'webpack': ['webpackjs'],
    'vite': ['vitejs'],
    'babel': ['babeljs'],
}
```

---

## Fuzzy Matching Implementation

```python
from difflib import SequenceMatcher
from typing import Optional, List

def fuzzy_match_skill(
    job_skill: str, 
    candidate_skills: List[str], 
    threshold: float = 0.85
) -> Optional[str]:
    """
    Find best fuzzy match for a job skill among candidate skills.
    
    Args:
        job_skill: The skill required by the job
        candidate_skills: List of candidate's skills (already lowercased)
        threshold: Minimum similarity ratio (0-1)
    
    Returns:
        Matched candidate skill or None
    """
    best_match = None
    best_ratio = threshold
    
    for candidate_skill in candidate_skills:
        ratio = SequenceMatcher(
            None, 
            job_skill.lower(), 
            candidate_skill.lower()
        ).ratio()
        
        if ratio >= best_ratio:
            best_ratio = ratio
            best_match = candidate_skill
    
    return best_match
```

### Fuzzy Match Examples

| Job Skill | Candidate Skill | Ratio | Match? |
|-----------|-----------------|-------|--------|
| "kubernetes" | "kubernetis" | 0.95 | ✅ Yes (typo) |
| "postgresql" | "postgressql" | 0.91 | ✅ Yes (typo) |
| "javascript" | "java" | 0.67 | ❌ No (different) |
| "react" | "react.js" | 0.77 | ❌ No (caught by synonym) |
| "python" | "pythons" | 0.92 | ✅ Yes (typo) |
| "nodejs" | "node" | 0.80 | ❌ No (caught by synonym) |

---

## Skill Normalization

### Pre-Processing Steps

```python
def normalize_skill(skill: str) -> str:
    """
    Normalize skill for consistent matching.
    
    Steps:
    1. Lowercase
    2. Strip whitespace
    3. Remove special characters
    4. Handle common variations
    """
    import re
    
    # Lowercase and strip
    normalized = skill.lower().strip()
    
    # Remove version numbers (keep base technology)
    # "python 3.9" → "python"
    normalized = re.sub(r'\s*\d+(\.\d+)*\s*$', '', normalized)
    
    # Normalize common patterns
    # "node.js" → "nodejs"
    normalized = normalized.replace('.js', 'js')
    normalized = normalized.replace('.net', 'dotnet')
    
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    
    return normalized
```

---

## Skill Extraction from Job Descriptions

### Parsing Skills from Text

```python
def extract_skills_from_text(text: str) -> List[str]:
    """
    Extract skills from job description or requirements.
    
    Uses:
    - Known skill patterns
    - Common skill delimiters
    - NLP-based extraction (spaCy)
    """
    import re
    
    # Common skill keywords (expandable list)
    KNOWN_SKILLS = set([
        'python', 'java', 'javascript', 'typescript', 'go', 'rust', 'c++',
        'react', 'angular', 'vue', 'node', 'django', 'flask', 'spring',
        'aws', 'gcp', 'azure', 'docker', 'kubernetes', 'terraform',
        'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
        'git', 'linux', 'bash', 'sql', 'graphql', 'rest',
        # Add more...
    ])
    
    text_lower = text.lower()
    found_skills = []
    
    # Pattern: Look for skills in common formats
    # - "Requirements: Python, Java, AWS"
    # - "Skills: Python • Java • AWS"
    # - "Experience with Python, Java, and AWS"
    
    for skill in KNOWN_SKILLS:
        # Word boundary match
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            # Capitalize properly
            found_skills.append(skill.title() if len(skill) > 2 else skill.upper())
    
    return list(set(found_skills))
```

---

## Scoring Edge Cases

### Empty Skills Lists

```python
def calculate_skill_match(candidate_skills, job_skills):
    # No job skills = neutral (can't judge)
    if not job_skills:
        return {
            "score": 50.0,
            "matched": [],
            "missing": [],
            "reason": "No skills specified in job posting"
        }
    
    # No candidate skills = 0 match
    if not candidate_skills:
        return {
            "score": 0.0,
            "matched": [],
            "missing": job_skills,
            "reason": "Candidate has no skills listed"
        }
    
    # Normal matching...
```

### Partial Skill Matches

For multi-word skills, handle partial matches:

```python
def is_partial_match(job_skill: str, candidate_skill: str) -> bool:
    """
    Check if skills partially match.
    
    Examples:
    - "React Native" matches "React"
    - "AWS Lambda" matches "AWS"
    - "Python Django" matches "Django"
    """
    job_words = set(job_skill.lower().split())
    candidate_words = set(candidate_skill.lower().split())
    
    # If any word matches, consider it partial
    return bool(job_words & candidate_words)
```

---

## Skill Categories

Optionally weight skills by category importance:

```python
SKILL_CATEGORIES = {
    'core_programming': {
        'weight': 1.2,  # 20% bonus
        'skills': ['python', 'java', 'javascript', 'typescript', 'go', 'rust']
    },
    'frameworks': {
        'weight': 1.0,
        'skills': ['react', 'angular', 'vue', 'django', 'spring', 'flask']
    },
    'devops': {
        'weight': 1.0,
        'skills': ['docker', 'kubernetes', 'terraform', 'aws', 'gcp', 'azure']
    },
    'databases': {
        'weight': 0.9,
        'skills': ['postgresql', 'mysql', 'mongodb', 'redis']
    },
    'tools': {
        'weight': 0.7,  # Lower importance
        'skills': ['git', 'jira', 'vscode']
    }
}
```

---

## Testing Skill Matching

### Unit Test Examples

```python
# tests/test_skill_matching.py

import pytest
from app.services.job_matching_service import JobMatchingService

class TestSkillMatching:
    def setup_method(self):
        self.service = JobMatchingService()
    
    def test_exact_match(self):
        result = self.service.calculate_skill_match(
            candidate_skills=['Python', 'AWS', 'React'],
            job_skills=['Python', 'AWS', 'React']
        )
        assert result['score'] == 100.0
        assert len(result['matched']) == 3
        assert len(result['missing']) == 0
    
    def test_synonym_match(self):
        result = self.service.calculate_skill_match(
            candidate_skills=['Amazon Web Services', 'k8s', 'ReactJS'],
            job_skills=['AWS', 'Kubernetes', 'React']
        )
        assert result['score'] == 100.0
    
    def test_fuzzy_match_typo(self):
        result = self.service.calculate_skill_match(
            candidate_skills=['Kubernetis'],  # Typo
            job_skills=['Kubernetes']
        )
        assert result['score'] == 100.0
    
    def test_partial_match(self):
        result = self.service.calculate_skill_match(
            candidate_skills=['Python', 'AWS'],
            job_skills=['Python', 'AWS', 'Kubernetes', 'Docker']
        )
        assert result['score'] == 50.0  # 2/4 skills
        assert 'Kubernetes' in result['missing']
        assert 'Docker' in result['missing']
    
    def test_no_match(self):
        result = self.service.calculate_skill_match(
            candidate_skills=['Java', 'Oracle', 'Spring'],
            job_skills=['Python', 'MongoDB', 'Django']
        )
        assert result['score'] == 0.0
        assert len(result['matched']) == 0
    
    def test_case_insensitive(self):
        result = self.service.calculate_skill_match(
            candidate_skills=['PYTHON', 'aws', 'React'],
            job_skills=['python', 'AWS', 'REACT']
        )
        assert result['score'] == 100.0
    
    def test_empty_job_skills(self):
        result = self.service.calculate_skill_match(
            candidate_skills=['Python', 'AWS'],
            job_skills=[]
        )
        assert result['score'] == 50.0  # Neutral
    
    def test_empty_candidate_skills(self):
        result = self.service.calculate_skill_match(
            candidate_skills=[],
            job_skills=['Python', 'AWS']
        )
        assert result['score'] == 0.0
```

---

## Performance Optimization

### Pre-compute Synonym Lookups

```python
class SkillMatcher:
    def __init__(self):
        # Build reverse lookup for O(1) synonym checking
        self.synonym_lookup = {}
        for canonical, synonyms in SKILL_SYNONYMS.items():
            self.synonym_lookup[canonical.lower()] = canonical.lower()
            for syn in synonyms:
                self.synonym_lookup[syn.lower()] = canonical.lower()
    
    def get_canonical_skill(self, skill: str) -> str:
        """Get canonical form of a skill in O(1)."""
        return self.synonym_lookup.get(skill.lower(), skill.lower())
```

---

## Next: [07-INNGEST-WORKFLOWS.md](./07-INNGEST-WORKFLOWS.md) - Background Job Workflows

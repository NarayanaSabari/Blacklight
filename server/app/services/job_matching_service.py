"""
Job Matching Service
AI-powered matching engine to find best job matches for candidates.

Uses multi-factor scoring:
- Skills Match (40%): Overlap between candidate and job skills
- Experience Match (25%): Years of experience vs requirements
- Location Match (15%): Location preference vs job location  
- Salary Match (10%): Expected salary vs offered salary
- Semantic Similarity (10%): Resume/profile vs job description (embeddings)
"""
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from sqlalchemy import select, and_, func
from difflib import SequenceMatcher

from app import db
from app.models.candidate import Candidate
from app.models.job_posting import JobPosting
from app.models.candidate_job_match import CandidateJobMatch
from config.settings import settings

logger = logging.getLogger(__name__)


class JobMatchingService:
    """
    Service for matching candidates to jobs using AI-powered multi-factor scoring.
    
    The matching algorithm evaluates candidates against job postings across multiple
    dimensions and produces a comprehensive match score with detailed breakdown.
    """
    
    # Scoring weights (must sum to 1.0)
    WEIGHT_SKILLS = 0.40
    WEIGHT_EXPERIENCE = 0.25
    WEIGHT_LOCATION = 0.15
    WEIGHT_SALARY = 0.10
    WEIGHT_SEMANTIC = 0.10
    
    # Match grade thresholds
    GRADE_A_PLUS = 90  # Excellent match
    GRADE_A = 80       # Very good match
    GRADE_B = 70       # Good match
    GRADE_C = 60       # Fair match
    GRADE_D = 50       # Poor match
    
    # Skill synonyms dictionary for flexible matching
    # Complete dictionary as documented in 06-SKILL-MATCHING.md
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
    
    # Fuzzy match threshold (0-1, higher = stricter)
    FUZZY_MATCH_THRESHOLD = 0.85
    
    def __init__(self, tenant_id: int):
        """
        Initialize JobMatchingService for a specific tenant.
        
        Args:
            tenant_id: Tenant ID for multi-tenant isolation
        """
        self.tenant_id = tenant_id
    
    def calculate_match_score(
        self,
        candidate: Candidate,
        job_posting: JobPosting
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive match score between candidate and job.
        
        Combines multiple factors:
        - Skills match (40%)
        - Experience match (25%)
        - Location match (15%)
        - Salary match (10%)
        - Semantic similarity (10%)
        
        Args:
            candidate: Candidate instance
            job_posting: JobPosting instance
            
        Returns:
            Dictionary with:
            - overall_score: Final score 0-100
            - skill_match_score: Skills score 0-100
            - experience_match_score: Experience score 0-100
            - location_match_score: Location score 0-100
            - salary_match_score: Salary score 0-100
            - semantic_similarity: Semantic score 0-100
            - match_grade: Letter grade (A+, A, B, C, D)
            - matched_skills: List of matching skills
            - missing_skills: List of required skills candidate lacks
            - explanation: Human-readable explanation
        """
        # 1. Calculate skill match (40%)
        # Convert PostgreSQL ARRAY to Python list to avoid NumPy boolean ambiguity
        # Handle None, empty arrays, and convert to list safely
        try:
            candidate_skills = list(candidate.skills) if candidate.skills is not None else []
        except (TypeError, ValueError):
            candidate_skills = []
        
        try:
            job_skills = list(job_posting.skills) if job_posting.skills is not None else []
        except (TypeError, ValueError):
            job_skills = []
        
        skill_score, matched_skills, missing_skills = self.calculate_skill_match(
            candidate_skills,
            job_skills
        )
        
        # 2. Calculate experience match (25%)
        experience_score = self.calculate_experience_match(
            candidate.total_experience_years,
            job_posting.experience_min,
            job_posting.experience_max
        )
        
        # 3. Calculate location match (15%)
        # Determine if candidate wants remote
        candidate_remote_preference = False
        preferred_locations = list(candidate.preferred_locations) if candidate.preferred_locations is not None else []
        if preferred_locations:
            candidate_remote_preference = any(
                'remote' in loc.lower() for loc in preferred_locations
            )
        
        location_score = self.calculate_location_match(
            candidate.location,
            candidate_remote_preference,
            job_posting.location,
            job_posting.is_remote or False
        )
        
        # 4. Calculate salary match (10%)
        # Parse candidate expected salary if it's a string
        candidate_min_salary = None
        candidate_max_salary = None
        
        if candidate.expected_salary:
            # Try to extract numeric values from expected_salary string
            # Format might be: "$100,000", "$100K-$120K", "100000-120000", etc.
            import re
            salary_str = candidate.expected_salary.replace(',', '').replace('$', '').replace('K', '000').replace('k', '000')
            numbers = re.findall(r'\d+', salary_str)
            if len(numbers) >= 2:
                candidate_min_salary = int(numbers[0])
                candidate_max_salary = int(numbers[1])
            elif len(numbers) == 1:
                candidate_min_salary = int(numbers[0])
                candidate_max_salary = int(numbers[0])
        
        salary_score = self.calculate_salary_match(
            candidate_min_salary,
            candidate_max_salary,
            job_posting.salary_min,
            job_posting.salary_max
        )
        
        # 5. Calculate semantic similarity (10%)
        semantic_score = self.calculate_semantic_similarity(
            candidate.embedding,
            job_posting.embedding
        )
        
        # Calculate weighted overall score
        overall_score = (
            skill_score * self.WEIGHT_SKILLS +
            experience_score * self.WEIGHT_EXPERIENCE +
            location_score * self.WEIGHT_LOCATION +
            salary_score * self.WEIGHT_SALARY +
            semantic_score * self.WEIGHT_SEMANTIC
        )
        
        # Determine match grade
        if overall_score >= self.GRADE_A_PLUS:
            match_grade = 'A+'
        elif overall_score >= self.GRADE_A:
            match_grade = 'A'
        elif overall_score >= self.GRADE_B:
            match_grade = 'B'
        elif overall_score >= self.GRADE_C:
            match_grade = 'C'
        elif overall_score >= self.GRADE_D:
            match_grade = 'D'
        else:
            match_grade = 'F'
        
        # Generate human-readable explanation
        explanation_parts = []
        
        if skill_score >= 80:
            explanation_parts.append(f"Excellent skills match ({len(matched_skills)}/{len(job_skills)} skills)")
        elif skill_score >= 60:
            explanation_parts.append(f"Good skills match ({len(matched_skills)}/{len(job_skills)} skills)")
        else:
            explanation_parts.append(f"Limited skills match ({len(matched_skills)}/{len(job_skills)} skills)")
        
        if experience_score >= 90:
            explanation_parts.append("experience level is ideal")
        elif experience_score >= 70:
            explanation_parts.append("experience level is suitable")
        else:
            explanation_parts.append("experience level may not align")
        
        if location_score >= 90:
            explanation_parts.append("location is perfect fit")
        elif location_score >= 60:
            explanation_parts.append("location is acceptable")
        else:
            explanation_parts.append("location may require relocation")
        
        if salary_score >= 90:
            explanation_parts.append("salary expectations align well")
        elif salary_score >= 60:
            explanation_parts.append("salary expectations are reasonable")
        else:
            explanation_parts.append("salary expectations may need negotiation")
        
        explanation = f"Candidate is a {match_grade} match: {', '.join(explanation_parts)}."
        
        return {
            'overall_score': round(overall_score, 2),
            'skill_match_score': round(skill_score, 2),
            'experience_match_score': round(experience_score, 2),
            'location_match_score': round(location_score, 2),
            'salary_match_score': round(salary_score, 2),
            'semantic_similarity': round(semantic_score, 2),
            'match_grade': match_grade,
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'explanation': explanation
        }
    
    def calculate_skill_match(self, candidate_skills: List[str], job_skills: List[str]) -> Tuple[float, List[str], List[str]]:
        """
        Calculate skill match score between candidate and job.
        
        Uses three matching strategies:
        1. Exact match (case-insensitive)
        2. Fuzzy match using string similarity (for typos/variations)
        3. Synonym match (AWS = Amazon Web Services, etc.)
        
        Args:
            candidate_skills: List of candidate's skills
            job_skills: List of required job skills
            
        Returns:
            Tuple of (match_score_0_to_100, matched_skills_list, missing_skills_list)
        """
        # Handle None or empty lists
        if job_skills is None or len(job_skills) == 0:
            return 100.0, [], []
        
        if candidate_skills is None or len(candidate_skills) == 0:
            return 0.0, [], list(job_skills)
        
        # Normalize all skills to lowercase and strip whitespace
        # Filter out None, empty strings, and ensure all are strings
        candidate_skills_normalized = [str(s).lower().strip() for s in candidate_skills if s is not None and str(s).strip()]
        job_skills_normalized = [str(s).lower().strip() for s in job_skills if s is not None and str(s).strip()]
        
        matched_skills = []
        missing_skills = []
        
        for job_skill in job_skills_normalized:
            is_matched = False
            
            # Strategy 1: Exact match
            if job_skill in candidate_skills_normalized:
                matched_skills.append(job_skill)
                is_matched = True
                continue
            
            # Strategy 2: Synonym match
            if not is_matched:
                # Check if job_skill is in our synonym dictionary
                for base_skill, synonyms in self.SKILL_SYNONYMS.items():
                    # Check if job skill matches base or any synonym
                    if job_skill == base_skill or job_skill in synonyms:
                        # Check if candidate has base or any synonym
                        if base_skill in candidate_skills_normalized or any(syn in candidate_skills_normalized for syn in synonyms):
                            matched_skills.append(job_skill)
                            is_matched = True
                            break
                
                # Also check reverse: if candidate skill is base, job might be synonym
                if not is_matched:
                    for candidate_skill in candidate_skills_normalized:
                        if candidate_skill in self.SKILL_SYNONYMS:
                            synonyms = self.SKILL_SYNONYMS[candidate_skill]
                            if job_skill in synonyms:
                                matched_skills.append(job_skill)
                                is_matched = True
                                break
            
            # Strategy 3: Fuzzy match (for typos/minor variations)
            if not is_matched:
                for candidate_skill in candidate_skills_normalized:
                    similarity = SequenceMatcher(None, job_skill, candidate_skill).ratio()
                    if similarity >= self.FUZZY_MATCH_THRESHOLD:
                        matched_skills.append(job_skill)
                        is_matched = True
                        break
            
            # If still not matched, add to missing skills
            if not is_matched:
                missing_skills.append(job_skill)
        
        # Calculate percentage score
        match_percentage = (len(matched_skills) / len(job_skills_normalized)) * 100.0
        
        return match_percentage, matched_skills, missing_skills
    
    def calculate_experience_match(
        self,
        candidate_years: Optional[int],
        job_min_years: Optional[int],
        job_max_years: Optional[int]
    ) -> float:
        """
        Calculate experience matching score.
        
        Scoring logic:
        - Candidate meets min requirement: 100%
        - Candidate slightly below min (1-2 years): 75-90%
        - Candidate well below min: 50%
        - Candidate overqualified: 90% (may be flight risk)
        
        Args:
            candidate_years: Candidate's years of experience
            job_min_years: Job's minimum required years
            job_max_years: Job's maximum desired years
            
        Returns:
            Score 0-100
        """
        # Edge case: No experience requirements
        if job_min_years is None or job_min_years == 0:
            return 100.0
        
        # Edge case: No candidate experience data
        if candidate_years is None:
            return 50.0  # Neutral score - could be entry level or missing data
        
        # Edge case: Negative years (data error)
        if candidate_years < 0:
            candidate_years = 0
        if job_min_years < 0:
            job_min_years = 0
        if job_max_years and job_max_years < 0:
            job_max_years = None
        
        # Case 1: Candidate meets minimum requirement
        if candidate_years >= job_min_years:
            # Perfect match: Within range or meets minimum
            if job_max_years is None or candidate_years <= job_max_years:
                # Exact match bonus: candidate experience matches min exactly
                if candidate_years == job_min_years:
                    return 100.0
                
                # Within range: gradually decrease score as experience increases
                # This handles the "sweet spot" - not too junior, not too senior
                if job_max_years:
                    range_size = job_max_years - job_min_years
                    if range_size > 0:
                        position_in_range = (candidate_years - job_min_years) / range_size
                        # Score decreases from 100 to 95 as we move through range
                        return 100.0 - (position_in_range * 5.0)
                
                return 100.0  # Meets minimum, no max specified
            
            # Case 2: Overqualified (exceeds maximum)
            if job_max_years:
                years_over = candidate_years - job_max_years
                
                # Slightly overqualified (1-2 years over): 95%
                if years_over <= 2:
                    return 95.0
                
                # Moderately overqualified (3-5 years over): 85%
                elif years_over <= 5:
                    return 85.0
                
                # Significantly overqualified (6-10 years over): 75%
                elif years_over <= 10:
                    return 75.0
                
                # Very overqualified (11+ years over): 60%
                # May be flight risk, salary expectations too high, or bored
                else:
                    return 60.0
        
        # Case 3: Candidate below minimum requirement
        else:
            years_short = job_min_years - candidate_years
            
            # Slightly below (1 year short): 85%
            if years_short == 1:
                return 85.0
            
            # Moderately below (2 years short): 70%
            elif years_short == 2:
                return 70.0
            
            # 3 years short: 55%
            elif years_short == 3:
                return 55.0
            
            # 4+ years short: 40%
            # Significantly under-qualified
            else:
                return 40.0
    
    def calculate_location_match(
        self,
        candidate_location: Optional[str],
        candidate_remote_preference: bool,
        job_location: Optional[str],
        job_is_remote: bool
    ) -> float:
        """
        Calculate location matching score.
        
        Matching levels:
        - Exact match (city + state): 100%
        - Same state: 80%
        - Remote job + candidate wants remote: 100%
        - Different locations but job is remote: 90%
        - Different locations, not remote: 30-50%
        
        Args:
            candidate_location: Candidate's location (city, state format)
            candidate_remote_preference: Whether candidate wants remote
            job_location: Job's location
            job_is_remote: Whether job is remote
            
        Returns:
            Score 0-100
        """
        # Case 1: Remote job scenarios
        if job_is_remote:
            # Perfect match: Remote job + candidate wants remote
            if candidate_remote_preference:
                return 100.0
            
            # Good match: Remote job but candidate doesn't specifically want remote
            # (candidate is flexible, might prefer office but remote is acceptable)
            return 90.0
        
        # Case 2: Candidate wants remote but job is not remote
        if candidate_remote_preference and not job_is_remote:
            # Mismatch: Candidate wants remote, job requires onsite
            return 40.0
        
        # Case 3: Both onsite - compare locations
        # Edge case: Missing location data
        if not candidate_location or not job_location:
            return 50.0  # Neutral score when location data missing
        
        # Normalize locations for comparison
        candidate_location_lower = candidate_location.lower().strip()
        job_location_lower = job_location.lower().strip()
        
        # Exact match: Same city and state
        if candidate_location_lower == job_location_lower:
            return 100.0
        
        # Parse locations (format: "City, State" or "City, ST")
        candidate_parts = [part.strip() for part in candidate_location_lower.split(',')]
        job_parts = [part.strip() for part in job_location_lower.split(',')]
        
        # State match: Different cities but same state
        if len(candidate_parts) >= 2 and len(job_parts) >= 2:
            candidate_state = candidate_parts[-1]  # Last part is state
            job_state = job_parts[-1]
            
            # Same state, different city
            if candidate_state == job_state:
                return 75.0
        
        # Check if locations contain common keywords (partial match)
        # e.g., "New York" in both "New York, NY" and "New York City, NY"
        if len(candidate_parts) > 0 and len(job_parts) > 0:
            candidate_city = candidate_parts[0]
            job_city = job_parts[0]
            
            # Fuzzy city match (e.g., "san francisco" vs "san fran")
            if candidate_city in job_city or job_city in candidate_city:
                return 85.0
        
        # No match: Different locations, not remote
        # Score depends on flexibility (we assume some flexibility)
        return 30.0
    
    def calculate_salary_match(
        self,
        candidate_expected_min: Optional[int],
        candidate_expected_max: Optional[int],
        job_salary_min: Optional[int],
        job_salary_max: Optional[int]
    ) -> float:
        """
        Calculate salary matching score.
        
        Scoring logic:
        - Job max >= candidate min: 100% (meets expectations)
        - Job max slightly below candidate min: 70-90%
        - Job max well below candidate min: 40-60%
        - No salary data: 50% (neutral)
        
        Args:
            candidate_expected_min: Candidate's minimum expected salary
            candidate_expected_max: Candidate's maximum expected salary
            job_salary_min: Job's minimum offered salary
            job_salary_max: Job's maximum offered salary
            
        Returns:
            Score 0-100
        """
        # Edge case: No salary data from either side
        if (not candidate_expected_min and not candidate_expected_max and 
            not job_salary_min and not job_salary_max):
            return 50.0  # Neutral score - salary not a factor
        
        # Edge case: Candidate has no expectations (open to negotiation)
        if not candidate_expected_min and not candidate_expected_max:
            return 80.0  # Good match - candidate is flexible
        
        # Edge case: Job has no salary information
        if not job_salary_min and not job_salary_max:
            return 50.0  # Neutral - can't evaluate fit
        
        # Use max values for primary comparison (most relevant)
        # If max not available, use min
        candidate_min = candidate_expected_min or candidate_expected_max or 0
        candidate_max = candidate_expected_max or candidate_expected_min or 0
        job_min = job_salary_min or job_salary_max or 0
        job_max = job_salary_max or job_salary_min or 0
        
        # Sanitize negative values
        if candidate_min < 0:
            candidate_min = 0
        if candidate_max < 0:
            candidate_max = 0
        if job_min < 0:
            job_min = 0
        if job_max < 0:
            job_max = 0
        
        # Case 1: Perfect overlap - ranges intersect
        # Check if there's any overlap between salary ranges
        ranges_overlap = (
            (job_min <= candidate_max and job_max >= candidate_min) or
            (candidate_min <= job_max and candidate_max >= job_min)
        )
        
        if ranges_overlap:
            # Calculate overlap percentage
            overlap_start = max(job_min, candidate_min)
            overlap_end = min(job_max, candidate_max)
            
            if overlap_end >= overlap_start:
                # Ranges overlap - excellent match
                # Score based on how much job max exceeds candidate min
                if job_max >= candidate_min:
                    # Job can meet or exceed candidate's minimum expectation
                    if job_max >= candidate_max:
                        # Job max exceeds candidate max - perfect match
                        return 100.0
                    else:
                        # Job max is between candidate min and max
                        # Score proportionally: 90-100%
                        range_size = candidate_max - candidate_min
                        if range_size > 0:
                            position = (job_max - candidate_min) / range_size
                            return 90.0 + (position * 10.0)
                        return 95.0
        
        # Case 2: Job max below candidate min (underpaying)
        if job_max < candidate_min:
            gap = candidate_min - job_max
            gap_percentage = (gap / candidate_min) * 100 if candidate_min > 0 else 100
            
            # Small gap (< 10%): 75% score
            if gap_percentage < 10:
                return 75.0
            
            # Moderate gap (10-20%): 60% score
            elif gap_percentage < 20:
                return 60.0
            
            # Large gap (20-30%): 45% score
            elif gap_percentage < 30:
                return 45.0
            
            # Very large gap (30%+): 30% score
            else:
                return 30.0
        
        # Case 3: Candidate max below job min (candidate expects too little)
        # This is actually good for employer but might indicate
        # candidate is junior or undervaluing themselves
        if candidate_max > 0 and candidate_max < job_min:
            # Candidate's expectations are below job's minimum
            # Score: 85% (good for employer, but might indicate experience mismatch)
            return 85.0
        
        # Default: Neutral match
        return 70.0
    
    def calculate_semantic_similarity(
        self,
        candidate_embedding: Optional[List[float]],
        job_embedding: Optional[List[float]]
    ) -> float:
        """
        Calculate semantic similarity using embedding vectors.
        
        Uses cosine similarity between:
        - Candidate: Resume/profile text embedding
        - Job: Job description embedding
        
        Args:
            candidate_embedding: 768-dim vector from candidate profile
            job_embedding: 768-dim vector from job description
            
        Returns:
            Score 0-100 (cosine similarity * 100)
        """
        # Edge case: Missing embeddings
        if candidate_embedding is None or job_embedding is None:
            return 50.0  # Neutral score when embeddings unavailable
        
        # Convert to list if numpy array to avoid ambiguity
        if hasattr(candidate_embedding, 'tolist'):
            candidate_embedding = candidate_embedding.tolist()
        if hasattr(job_embedding, 'tolist'):
            job_embedding = job_embedding.tolist()
        
        # Check for empty embeddings
        if len(candidate_embedding) == 0 or len(job_embedding) == 0:
            return 50.0
        
        # Validate embedding dimensions
        if len(candidate_embedding) != 768 or len(job_embedding) != 768:
            raise ValueError(
                f"Invalid embedding dimensions: candidate={len(candidate_embedding)}, job={len(job_embedding)} (expected 768)"
            )
        
        # Calculate cosine similarity
        # cosine_similarity = (A · B) / (||A|| * ||B||)
        
        # Dot product
        dot_product = sum(a * b for a, b in zip(candidate_embedding, job_embedding))
        
        # Magnitudes
        magnitude_candidate = sum(a * a for a in candidate_embedding) ** 0.5
        magnitude_job = sum(b * b for b in job_embedding) ** 0.5
        
        # Avoid division by zero
        if magnitude_candidate == 0 or magnitude_job == 0:
            return 0.0
        
        # Cosine similarity (-1 to 1, typically 0 to 1 for text embeddings)
        cosine_similarity = dot_product / (magnitude_candidate * magnitude_job)
        
        # Normalize to 0-100 scale
        # Cosine similarity ranges from -1 to 1, but for text embeddings typically 0-1
        # We map [0, 1] -> [0, 100]
        similarity_score = max(0.0, min(100.0, cosine_similarity * 100.0))
        
        return similarity_score
    
    def generate_matches_for_candidate(
        self,
        candidate_id: int,
        limit: int = 50,
        min_score: float = 50.0
    ) -> List[CandidateJobMatch]:
        """
        Generate and store job matches for a single candidate.
        
        Process:
        1. Get all ACTIVE jobs
        2. Calculate match score for each job
        3. Filter by min_score threshold
        4. Store top N matches in database
        5. Return sorted matches
        
        Args:
            candidate_id: Candidate ID
            limit: Maximum number of matches to store
            min_score: Minimum match score threshold (0-100)
            
        Returns:
            List of CandidateJobMatch instances sorted by score (desc)
        """
        logger.info(f"Generating matches for candidate {candidate_id} (min_score={min_score}, limit={limit})")
        
        # 1. Fetch candidate
        candidate = db.session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")
        
        # Verify candidate belongs to this tenant
        if candidate.tenant_id != self.tenant_id:
            raise ValueError(f"Candidate {candidate_id} does not belong to tenant {self.tenant_id}")
        
        # 2. Fetch all ACTIVE jobs (jobs are global, not tenant-specific)
        jobs_query = select(JobPosting).where(
            JobPosting.status == 'ACTIVE'
        )
        jobs = db.session.execute(jobs_query).scalars().all()
        
        if not jobs:
            logger.warning("No active jobs found in database")
            return []
        
        logger.info(f"Found {len(jobs)} active jobs to match against")
        
        # 3. Calculate match scores for all jobs
        match_results = []
        for job in jobs:
            try:
                score_data = self.calculate_match_score(candidate, job)
                
                # Filter by minimum score
                if score_data['overall_score'] >= min_score:
                    match_results.append({
                        'job': job,
                        'score_data': score_data
                    })
            except Exception as e:
                logger.error(f"Error calculating match for job {job.id}: {str(e)}")
                continue
        
        logger.info(f"Found {len(match_results)} jobs above minimum score threshold")
        
        # 4. Sort by score (descending) and limit
        match_results.sort(key=lambda x: x['score_data']['overall_score'], reverse=True)
        match_results = match_results[:limit]
        
        # 5. Delete existing matches for this candidate (refresh strategy)
        db.session.execute(
            db.delete(CandidateJobMatch).where(
                CandidateJobMatch.candidate_id == candidate_id
            )
        )
        db.session.commit()
        
        # 6. Create new match records
        created_matches = []
        for match_result in match_results:
            job = match_result['job']
            score_data = match_result['score_data']
            
            # Generate match reasons from explanation
            match_reasons = [score_data['explanation']]
            
            match = CandidateJobMatch(
                candidate_id=candidate_id,
                job_posting_id=job.id,
                match_score=score_data['overall_score'],
                skill_match_score=score_data['skill_match_score'],
                experience_match_score=score_data['experience_match_score'],
                location_match_score=score_data['location_match_score'],
                salary_match_score=score_data['salary_match_score'],
                semantic_similarity=score_data['semantic_similarity'],
                matched_skills=score_data['matched_skills'],
                missing_skills=score_data['missing_skills'],
                match_reasons=match_reasons,
                status='SUGGESTED',
                is_recommended=score_data['overall_score'] >= 70.0,  # Grade B or higher
                recommendation_reason=f"Grade {score_data['match_grade']} match - {score_data['explanation']}",
                matched_at=datetime.utcnow()
            )
            
            db.session.add(match)
            created_matches.append(match)
        
        # 7. Commit all matches
        db.session.commit()
        
        logger.info(f"Successfully created {len(created_matches)} matches for candidate {candidate_id}")
        
        return created_matches
    
    def generate_matches_for_all_candidates(
        self,
        batch_size: int = 10,
        min_score: float = 50.0
    ) -> Dict[str, Any]:
        """
        Generate matches for all candidates in the tenant.
        
        Processes candidates in batches for memory efficiency.
        
        Args:
            batch_size: Number of candidates to process at once
            min_score: Minimum match score threshold
            
        Returns:
            Dictionary with statistics:
            - total_candidates: Number of candidates processed
            - total_matches: Total matches generated
            - avg_matches_per_candidate: Average matches per candidate
            - processing_time_seconds: Total processing time
            - successful_candidates: Number successfully processed
            - failed_candidates: Number that failed
        """
        import time
        start_time = time.time()
        
        logger.info(f"Starting bulk match generation for tenant {self.tenant_id}")
        
        # Fetch all active candidates for this tenant
        candidates_query = select(Candidate).where(
            and_(
                Candidate.tenant_id == self.tenant_id,
                Candidate.status.in_(['NEW', 'SCREENING', 'APPROVED'])  # Active candidates
            )
        )
        candidates = db.session.execute(candidates_query).scalars().all()
        
        total_candidates = len(candidates)
        logger.info(f"Found {total_candidates} active candidates to process")
        
        if total_candidates == 0:
            return {
                'total_candidates': 0,
                'successful_candidates': 0,
                'failed_candidates': 0,
                'total_matches': 0,
                'avg_matches_per_candidate': 0.0,
                'processing_time_seconds': 0.0
            }
        
        # Process in batches
        successful_count = 0
        failed_count = 0
        total_matches = 0
        
        for i in range(0, total_candidates, batch_size):
            batch = candidates[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_candidates + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} candidates)")
            
            for candidate in batch:
                try:
                    matches = self.generate_matches_for_candidate(
                        candidate_id=candidate.id,
                        min_score=min_score
                    )
                    total_matches += len(matches)
                    successful_count += 1
                    logger.debug(f"Generated {len(matches)} matches for candidate {candidate.id}")
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to generate matches for candidate {candidate.id}: {str(e)}")
                    continue
            
            # Small delay between batches to avoid overwhelming database
            if i + batch_size < total_candidates:
                time.sleep(0.1)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        avg_matches = total_matches / successful_count if successful_count > 0 else 0.0
        
        logger.info(
            f"Bulk match generation complete: {successful_count}/{total_candidates} candidates processed, "
            f"{total_matches} total matches in {processing_time:.2f}s"
        )
        
        return {
            'total_candidates': total_candidates,
            'successful_candidates': successful_count,
            'failed_candidates': failed_count,
            'total_matches': total_matches,
            'avg_matches_per_candidate': round(avg_matches, 2),
            'processing_time_seconds': round(processing_time, 2)
        }
    
    def get_matches_for_candidate(
        self,
        candidate_id: int,
        limit: int = 20,
        status_filter: Optional[str] = None
    ) -> List[CandidateJobMatch]:
        """
        Get stored matches for a candidate.
        
        Args:
            candidate_id: Candidate ID
            limit: Maximum number of matches to return
            status_filter: Filter by job status (ACTIVE, EXPIRED, etc.)
            
        Returns:
            List of CandidateJobMatch instances with related job data
        """
        query = select(CandidateJobMatch).where(
            CandidateJobMatch.candidate_id == candidate_id
        ).order_by(CandidateJobMatch.overall_score.desc())
        
        if status_filter:
            query = query.join(JobPosting).where(JobPosting.status == status_filter)
        
        query = query.limit(limit)
        
        return list(db.session.scalars(query).all())
    
    def get_matches_for_recruiter_candidates(
        self,
        recruiter_id: int,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get aggregated job matches for all candidates assigned to a recruiter.
        
        Returns jobs that are good matches for ANY of the recruiter's candidates,
        ranked by total match score and number of matching candidates.
        
        Args:
            recruiter_id: Recruiter/user ID
            limit: Maximum number of jobs to return
            
        Returns:
            Dictionary with:
            - jobs: List of jobs with match statistics
            - total_jobs: Total matching jobs found
            - total_candidates: Number of recruiter's candidates
        """
        # TODO: Implement later - requires candidate assignment data
        pass
    
    @staticmethod
    def update_match_status(
        match_id: int,
        tenant_id: int,
        status: str,
        notes: Optional[str] = None,
        rejection_reason: Optional[str] = None
    ) -> CandidateJobMatch:
        """
        Update match status and related timestamps.
        
        Args:
            match_id: Match ID
            tenant_id: Tenant ID for verification
            status: New status (SUGGESTED, VIEWED, APPLIED, REJECTED, SHORTLISTED)
            notes: Optional notes
            rejection_reason: Optional rejection reason (for REJECTED status)
            
        Returns:
            Updated CandidateJobMatch
            
        Raises:
            ValueError: If match not found or tenant mismatch
        """
        valid_statuses = ['SUGGESTED', 'VIEWED', 'APPLIED', 'REJECTED', 'SHORTLISTED']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        match = db.session.get(CandidateJobMatch, match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")
        
        candidate = db.session.get(Candidate, match.candidate_id)
        if candidate.tenant_id != tenant_id:
            raise ValueError("Access denied")
        
        match.status = status
        
        if status == 'VIEWED' and not match.viewed_at:
            match.viewed_at = db.func.now()
        elif status == 'APPLIED':
            match.applied_at = db.func.now()
        elif status == 'REJECTED':
            match.rejected_at = db.func.now()
            if rejection_reason:
                match.rejection_reason = rejection_reason
        
        if notes:
            match.notes = notes
        
        db.session.commit()
        
        logger.info(f"Updated match {match_id} status to {status} for tenant {tenant_id}")
        
        return match
    
    @staticmethod
    def update_ai_analysis(
        match_id: int,
        tenant_id: int,
        compatibility_score: float,
        strengths: List[str],
        gaps: List[str],
        recommendations: List[str],
        experience_analysis: str,
        culture_fit_indicators: List[str]
    ) -> CandidateJobMatch:
        """
        Update match with AI compatibility analysis results.
        
        Args:
            match_id: Match ID
            tenant_id: Tenant ID for verification
            compatibility_score: AI compatibility score
            strengths: List of candidate strengths
            gaps: List of skill/experience gaps
            recommendations: List of recommendations
            experience_analysis: Experience analysis text
            culture_fit_indicators: Culture fit observations
            
        Returns:
            Updated CandidateJobMatch
            
        Raises:
            ValueError: If match not found or tenant mismatch
        """
        match = db.session.get(CandidateJobMatch, match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")
        
        candidate = db.session.get(Candidate, match.candidate_id)
        if candidate.tenant_id != tenant_id:
            raise ValueError("Access denied")
        
        match.ai_compatibility_score = compatibility_score
        match.ai_compatibility_details = {
            'strengths': strengths,
            'gaps': gaps,
            'recommendations': recommendations,
            'experience_analysis': experience_analysis,
            'culture_fit_indicators': culture_fit_indicators
        }
        match.ai_scored_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Updated AI analysis for match {match_id}, score: {compatibility_score}")
        
        return match

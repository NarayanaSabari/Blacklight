"""
Unified Scorer Service

Single source of truth for candidate-job matching scores.
Used by both job matching (automated) and resume tailoring (on-demand).

Scoring Weights:
- Skills:     45% - Direct skill matching with synonyms and fuzzy matching
- Experience: 20% - Years of experience fit (rule-based)
- Semantic:   35% - Embedding cosine similarity

Grades (no D/F):
- A+: 90+
- A:  80-89
- B+: 75-79
- B:  70-74
- C+: 65-69
- C:  <65
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime
from difflib import SequenceMatcher
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from app import db
from app.models.candidate import Candidate
from app.models.job_posting import JobPosting
from app.models.candidate_job_match import CandidateJobMatch
from app.services.embedding_service import EmbeddingService
from config.settings import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Schemas for Scoring Results
# ============================================================================

class SkillMatchResult(BaseModel):
    """Result of skill matching"""
    score: float = Field(..., ge=0, le=100, description="Skill match score 0-100")
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    match_details: Dict[str, str] = Field(default_factory=dict)  # skill -> match_type


class UnifiedMatchScore(BaseModel):
    """Complete unified match score result
    
    Scoring Weights:
    - Skills:     45%
    - Experience: 20%
    - Semantic:   35%
    """
    overall_score: float = Field(..., ge=0, le=100, description="Overall weighted score")
    match_grade: str = Field(..., description="Letter grade: A+, A, B+, B, C+, C")
    
    # Component scores (Keywords removed - was causing slow job imports)
    skill_score: float = Field(..., ge=0, le=100)
    experience_score: float = Field(..., ge=0, le=100)
    semantic_score: float = Field(..., ge=0, le=100)
    
    # Match details
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    
    # Human-readable explanation
    match_reasons: List[str] = Field(default_factory=list)
    explanation: str = Field(default="")


class AICompatibilityResult(BaseModel):
    """Result of AI-powered detailed compatibility analysis"""
    compatibility_score: float = Field(..., ge=0, le=100)
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    experience_analysis: str = Field(default="")
    culture_fit_indicators: List[str] = Field(default_factory=list)


class UnifiedScorerService:
    """
    Unified scoring service for candidate-job matching.
    
    Provides consistent scoring across:
    - Automated job matching (when jobs are imported)
    - Resume tailoring (when recruiter requests)
    - AI compatibility analysis (on-demand)
    """
    
    # ===========================================
    # Scoring Weights (must sum to 1.0)
    # Keywords removed to speed up job imports
    # ===========================================
    WEIGHT_SKILLS = 0.45      # 45%
    WEIGHT_EXPERIENCE = 0.20  # 20%
    WEIGHT_SEMANTIC = 0.35    # 35%
    
    # ===========================================
    # Grade Thresholds (no D/F grades)
    # ===========================================
    GRADE_A_PLUS = 90
    GRADE_A = 80
    GRADE_B_PLUS = 75
    GRADE_B = 70
    GRADE_C_PLUS = 65
    # Below 65 = C (minimum grade)
    
    # Fuzzy match threshold (0-1, higher = stricter)
    FUZZY_MATCH_THRESHOLD = 0.85
    
    # ===========================================
    # Merged Skill Synonyms Dictionary
    # Combined from JobMatchingService (200+) and ResumeScorerService (~20)
    # ===========================================
    SKILL_SYNONYMS = {
        # ===================
        # CLOUD PLATFORMS
        # ===================
        'aws': [
            'amazon web services', 'amazon aws', 'ec2', 's3', 'lambda', 
            'cloudwatch', 'aws lambda', 'rds', 'cloudfront', 'route53'
        ],
        'gcp': [
            'google cloud', 'google cloud platform', 'gce', 'bigquery', 
            'google compute engine', 'cloud run', 'cloud functions'
        ],
        'azure': [
            'microsoft azure', 'azure cloud', 'azure devops', 'azure functions',
            'azure blob', 'azure sql'
        ],
        
        # ===================
        # PROGRAMMING LANGUAGES
        # ===================
        'javascript': ['js', 'es6', 'es2015', 'ecmascript', 'es5', 'es7', 'es2020'],
        'typescript': ['ts', 'typescript language'],
        'python': ['py', 'python3', 'python2', 'cpython', 'python language'],
        'golang': ['go', 'go lang', 'go-lang', 'google go'],
        'c++': ['cpp', 'cplusplus', 'c plus plus', 'c++11', 'c++17', 'c++20'],
        'c#': ['csharp', 'c sharp', 'c-sharp'],
        '.net': ['dotnet', 'dot net', '.net core', 'dotnet core', '.net framework'],
        'java': ['java8', 'java11', 'java17', 'jdk', 'jvm'],
        'ruby': ['rb', 'ruby language'],
        'rust': ['rustlang', 'rust language'],
        'scala': ['scala lang', 'scala language'],
        'kotlin': ['kt', 'kotlin language'],
        'swift': ['swift lang', 'swiftui', 'swift ui'],
        'objective-c': ['objc', 'objective c', 'obj-c'],
        'php': ['php7', 'php8', 'php language'],
        'perl': ['perl5', 'perl6', 'raku'],
        'r': ['r language', 'r programming', 'rstats'],
        'matlab': ['mat lab'],
        'julia': ['julia lang'],
        
        # ===================
        # FRONTEND FRAMEWORKS
        # ===================
        'react': ['reactjs', 'react.js', 'react native', 'react-native', 'react hooks'],
        'vue': ['vuejs', 'vue.js', 'vue3', 'nuxt', 'nuxtjs', 'vue 3'],
        'angular': ['angularjs', 'angular.js', 'angular2', 'angular 2', 'angular 14'],
        'svelte': ['sveltejs', 'sveltekit', 'svelte kit'],
        'next.js': ['nextjs', 'next', 'next js'],
        'gatsby': ['gatsbyjs', 'gatsby js'],
        'ember': ['emberjs', 'ember.js'],
        'backbone': ['backbonejs', 'backbone.js'],
        'jquery': ['jq', 'j query'],
        'redux': ['redux toolkit', 'rtk'],
        'mobx': ['mob x'],
        
        # ===================
        # BACKEND FRAMEWORKS
        # ===================
        'node': ['nodejs', 'node.js', 'node js'],
        'express': ['expressjs', 'express.js', 'express js'],
        'django': ['django rest framework', 'drf', 'django-rest', 'django rest'],
        'flask': ['flask api', 'flask python'],
        'fastapi': ['fast api', 'fast-api', 'fast api python'],
        'rails': ['ruby on rails', 'ror', 'ruby rails', 'ruby on rails'],
        'spring': ['spring boot', 'springboot', 'spring framework', 'spring mvc'],
        'laravel': ['laravel php'],
        'asp.net': ['asp net', 'aspnet', 'asp.net core', 'asp.net mvc'],
        'nestjs': ['nest.js', 'nest', 'nest js'],
        'koa': ['koajs', 'koa.js'],
        'hapi': ['hapijs', 'hapi.js'],
        'gin': ['gin-gonic', 'gin golang'],
        'fiber': ['gofiber', 'fiber golang'],
        'echo': ['echo golang'],
        
        # ===================
        # DATABASES
        # ===================
        'postgresql': ['postgres', 'pg', 'psql', 'pgsql', 'postgre'],
        'mysql': ['mariadb', 'maria db', 'mysql server'],
        'mongodb': ['mongo', 'mongo db', 'mongoose'],
        'redis': ['redis cache', 'redis db', 'in-memory cache'],
        'elasticsearch': ['elastic search', 'elastic', 'es', 'opensearch'],
        'cassandra': ['apache cassandra'],
        'dynamodb': ['dynamo db', 'amazon dynamodb', 'aws dynamodb'],
        'oracle': ['oracle db', 'oracle database', 'plsql', 'pl/sql'],
        'sql server': ['mssql', 'ms sql', 'microsoft sql', 'tsql', 't-sql'],
        'sqlite': ['sqlite3'],
        'couchdb': ['couch db', 'apache couchdb'],
        'neo4j': ['neo 4j', 'graph database'],
        'firestore': ['firebase firestore', 'cloud firestore'],
        
        # ===================
        # DEVOPS & INFRASTRUCTURE
        # ===================
        'kubernetes': ['k8s', 'kube', 'kubectl', 'k8', 'kubernetes cluster'],
        'docker': ['docker compose', 'docker-compose', 'containerization', 'containers', 'dockerfile'],
        'terraform': ['tf', 'infrastructure as code', 'iac', 'hcl', 'terraform cloud'],
        'ansible': ['ansible playbook', 'ansible automation'],
        'puppet': ['puppet enterprise'],
        'chef': ['chef infra'],
        'jenkins': ['jenkins ci', 'jenkinsfile', 'jenkins pipeline'],
        'gitlab ci': ['gitlab-ci', 'gitlab ci/cd', 'gitlab cicd'],
        'github actions': ['gh actions', 'github action'],
        'circle ci': ['circleci', 'circle-ci'],
        'travis ci': ['travis-ci', 'travisci'],
        'ci/cd': ['cicd', 'continuous integration', 'continuous delivery', 'continuous deployment'],
        'nginx': ['nginx server', 'nginx proxy'],
        'apache': ['apache server', 'httpd', 'apache httpd'],
        'linux': ['unix', 'ubuntu', 'centos', 'debian', 'rhel', 'fedora'],
        'bash': ['shell', 'shell script', 'sh', 'zsh', 'shell scripting'],
        'prometheus': ['prometheus monitoring'],
        'grafana': ['grafana dashboard'],
        'datadog': ['data dog', 'datadog monitoring'],
        'new relic': ['newrelic'],
        'splunk': ['splunk logging'],
        'elk': ['elk stack', 'elasticsearch logstash kibana'],
        
        # ===================
        # MESSAGE QUEUES
        # ===================
        'kafka': ['apache kafka', 'kafka streaming'],
        'rabbitmq': ['rabbit mq', 'amqp', 'rabbit'],
        'sqs': ['amazon sqs', 'aws sqs', 'simple queue service'],
        'pubsub': ['google pubsub', 'gcp pubsub', 'pub/sub', 'pub sub'],
        'celery': ['celery task queue'],
        
        # ===================
        # DATA & ML
        # ===================
        'machine learning': ['ml', 'ml engineer', 'ml engineering'],
        'artificial intelligence': ['ai', 'ai engineer'],
        'deep learning': ['dl', 'neural networks', 'nn'],
        'natural language processing': ['nlp', 'text processing'],
        'computer vision': ['cv', 'image processing'],
        'tensorflow': ['tf', 'tf2', 'tensorflow 2'],
        'pytorch': ['torch', 'py torch'],
        'scikit-learn': ['sklearn', 'scikit learn', 'sk-learn'],
        'pandas': ['pd', 'pandas python'],
        'numpy': ['np', 'numpy python'],
        'spark': ['apache spark', 'pyspark', 'spark sql'],
        'hadoop': ['apache hadoop', 'hdfs', 'mapreduce'],
        'data science': ['data analysis', 'analytics', 'data analytics'],
        'llm': ['large language model', 'large language models', 'gpt', 'chatgpt'],
        'langchain': ['lang chain'],
        
        # ===================
        # API & PROTOCOLS
        # ===================
        'rest api': ['restful', 'rest', 'restful api', 'rest apis'],
        'graphql': ['graph ql', 'gql'],
        'grpc': ['g rpc', 'google rpc'],
        'websocket': ['websockets', 'ws', 'socket.io'],
        'oauth': ['oauth2', 'oauth 2.0', 'oauth2.0'],
        'jwt': ['json web token', 'json web tokens'],
        'openapi': ['swagger', 'openapi spec'],
        
        # ===================
        # TESTING
        # ===================
        'unit testing': ['unit tests', 'unit test'],
        'jest': ['jestjs', 'jest testing'],
        'pytest': ['py.test', 'pytest testing'],
        'mocha': ['mochajs', 'mocha testing'],
        'cypress': ['cypress.io', 'cypress testing'],
        'selenium': ['selenium webdriver', 'selenium testing'],
        'playwright': ['playwright testing'],
        'testing library': ['react testing library', 'rtl'],
        'tdd': ['test driven development'],
        'bdd': ['behavior driven development'],
        
        # ===================
        # VERSION CONTROL
        # ===================
        'git': ['github', 'gitlab', 'bitbucket', 'version control'],
        
        # ===================
        # AGILE & PROJECT
        # ===================
        'agile': ['scrum', 'kanban', 'agile methodology', 'agile development'],
        'jira': ['atlassian jira'],
        'confluence': ['atlassian confluence'],
        
        # ===================
        # FRONTEND TOOLS
        # ===================
        'html': ['html5', 'html 5'],
        'css': ['css3', 'scss', 'sass', 'less', 'css 3'],
        'tailwind': ['tailwindcss', 'tailwind css'],
        'bootstrap': ['bootstrap css', 'bootstrap 5', 'bootstrap 4'],
        'webpack': ['webpackjs', 'webpack bundler'],
        'vite': ['vitejs', 'vite bundler'],
        'babel': ['babeljs', 'babel transpiler'],
        'eslint': ['es lint'],
        'prettier': ['code formatter'],
        'storybook': ['storybook js'],
        
        # ===================
        # MOBILE
        # ===================
        'react native': ['react-native', 'rn', 'react native mobile'],
        'flutter': ['flutter dart', 'flutter mobile'],
        'ionic': ['ionic framework'],
        'xamarin': ['xamarin forms'],
        'android': ['android sdk', 'android development'],
        'ios': ['ios sdk', 'ios development', 'swift ios'],
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the unified scorer service.
        
        Args:
            api_key: Google API key for embeddings and AI. If not provided, reads from settings.
        """
        self.api_key = api_key or settings.google_api_key
        
        if not self.api_key:
            logger.warning("Google API key not provided. Semantic scoring and AI analysis will be disabled.")
            self.embedding_service = None
            self.model = None
        else:
            self.embedding_service = EmbeddingService(api_key=self.api_key)
            self.model = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=self.api_key,
                temperature=0.2,
                max_output_tokens=4096,
                timeout=60,
                max_retries=2,
            )
        
        logger.info("UnifiedScorerService initialized")
    
    # ===========================================
    # Main Scoring Method
    # ===========================================
    
    def calculate_score(
        self,
        candidate: Candidate,
        job_posting: JobPosting,
        candidate_resume_text: Optional[str] = None
    ) -> UnifiedMatchScore:
        """
        Calculate unified match score between candidate and job.
        
        This is the main scoring method used by both job matching and resume tailoring.
        
        Args:
            candidate: Candidate model instance
            job_posting: JobPosting model instance
            candidate_resume_text: Optional resume text for deeper keyword matching
            
        Returns:
            UnifiedMatchScore with full breakdown
        """
        try:
            logger.info(f"Calculating unified score for candidate {candidate.id} and job {job_posting.id}")
            
            # Extract data from models
            candidate_skills = list(candidate.skills) if candidate.skills else []
            job_skills = list(job_posting.skills) if job_posting.skills else []
            
            # 1. Calculate skill match (45%)
            skill_result = self.calculate_skill_score(candidate_skills, job_skills)
            
            # 2. Calculate experience match (20%)
            experience_score = self.calculate_experience_score(
                candidate.total_experience_years or 0,
                job_posting.experience_min or 0,
                job_posting.experience_max
            )
            
            # 3. Calculate semantic similarity (35%)
            semantic_score = self.calculate_semantic_score(
                candidate.embedding,
                job_posting.embedding
            )
            
            # Calculate weighted overall score (Keywords removed to speed up job imports)
            overall_score = (
                skill_result.score * self.WEIGHT_SKILLS +
                experience_score * self.WEIGHT_EXPERIENCE +
                semantic_score * self.WEIGHT_SEMANTIC
            )
            
            # Determine grade
            match_grade = self._get_grade(overall_score)
            
            # Generate match reasons
            match_reasons = self._generate_match_reasons(
                skill_result, experience_score, semantic_score,
                candidate, job_posting
            )
            
            # Generate explanation
            explanation = self._generate_explanation(
                overall_score, match_grade, skill_result,
                experience_score, semantic_score, job_posting
            )
            
            return UnifiedMatchScore(
                overall_score=round(overall_score, 2),
                match_grade=match_grade,
                skill_score=round(skill_result.score, 2),
                experience_score=round(experience_score, 2),
                semantic_score=round(semantic_score, 2),
                matched_skills=skill_result.matched_skills,
                missing_skills=skill_result.missing_skills,
                match_reasons=match_reasons,
                explanation=explanation
            )
            
        except Exception as e:
            logger.error(f"Error calculating unified score: {e}")
            raise
    
    def calculate_and_store_match(
        self,
        candidate: Candidate,
        job_posting: JobPosting,
        candidate_resume_text: Optional[str] = None
    ) -> CandidateJobMatch:
        """
        Calculate score and store/update CandidateJobMatch record.
        
        Args:
            candidate: Candidate model instance
            job_posting: JobPosting model instance
            candidate_resume_text: Optional resume text
            
        Returns:
            CandidateJobMatch record (new or updated)
        """
        # Calculate score
        score = self.calculate_score(candidate, job_posting, candidate_resume_text)
        
        # Check for existing match
        existing_match = db.session.query(CandidateJobMatch).filter_by(
            candidate_id=candidate.id,
            job_posting_id=job_posting.id
        ).first()
        
        if existing_match:
            # Update existing match
            match = existing_match
            match.updated_at = datetime.utcnow()
        else:
            # Create new match
            match = CandidateJobMatch(
                candidate_id=candidate.id,
                job_posting_id=job_posting.id,
                matched_at=datetime.utcnow()
            )
            db.session.add(match)
        
        # Update scores
        match.match_score = Decimal(str(score.overall_score))
        match.match_grade = score.match_grade
        match.skill_match_score = Decimal(str(score.skill_score))
        match.keyword_match_score = None  # Keywords removed to speed up job imports
        match.experience_match_score = Decimal(str(score.experience_score))
        match.semantic_similarity = Decimal(str(score.semantic_score))
        
        # Update details
        match.matched_skills = score.matched_skills
        match.missing_skills = score.missing_skills
        match.matched_keywords = None  # Keywords removed
        match.missing_keywords = None  # Keywords removed
        match.match_reasons = score.match_reasons
        
        # Determine recommendation
        match.is_recommended = score.overall_score >= 60
        match.recommendation_reason = score.explanation
        
        db.session.commit()
        
        logger.info(f"Stored match: candidate={candidate.id}, job={job_posting.id}, score={score.overall_score}")
        
        return match
    
    def calculate_and_store_match_no_commit(
        self,
        candidate: Candidate,
        job_posting: JobPosting,
        candidate_resume_text: Optional[str] = None
    ) -> CandidateJobMatch:
        """
        Calculate score and store/update CandidateJobMatch record WITHOUT committing.
        
        Use this for batch operations where you want to commit all matches at once.
        The caller is responsible for calling db.session.commit().
        
        Args:
            candidate: Candidate model instance
            job_posting: JobPosting model instance
            candidate_resume_text: Optional resume text
            
        Returns:
            CandidateJobMatch record (new or updated)
        """
        # Calculate score
        score = self.calculate_score(candidate, job_posting, candidate_resume_text)
        
        # Check for existing match
        existing_match = db.session.query(CandidateJobMatch).filter_by(
            candidate_id=candidate.id,
            job_posting_id=job_posting.id
        ).first()
        
        if existing_match:
            # Update existing match
            match = existing_match
            match.updated_at = datetime.utcnow()
        else:
            # Create new match
            match = CandidateJobMatch(
                candidate_id=candidate.id,
                job_posting_id=job_posting.id,
                matched_at=datetime.utcnow()
            )
            db.session.add(match)
        
        # Update scores
        match.match_score = Decimal(str(score.overall_score))
        match.match_grade = score.match_grade
        match.skill_match_score = Decimal(str(score.skill_score))
        match.keyword_match_score = None  # Keywords removed to speed up job imports
        match.experience_match_score = Decimal(str(score.experience_score))
        match.semantic_similarity = Decimal(str(score.semantic_score))
        
        # Update details
        match.matched_skills = score.matched_skills
        match.missing_skills = score.missing_skills
        match.matched_keywords = None  # Keywords removed
        match.missing_keywords = None  # Keywords removed
        match.match_reasons = score.match_reasons
        
        # Determine recommendation
        match.is_recommended = score.overall_score >= 60
        match.recommendation_reason = score.explanation
        
        # NO commit here - caller will commit
        
        return match
    
    # ===========================================
    # Component Scoring Methods
    # ===========================================
    
    def calculate_skill_score(
        self,
        candidate_skills: List[str],
        job_skills: List[str]
    ) -> SkillMatchResult:
        """
        Calculate skill match score (40% weight).
        
        Uses three matching strategies:
        1. Exact match (case-insensitive)
        2. Synonym match (using SKILL_SYNONYMS dictionary)
        3. Fuzzy match (85% similarity threshold)
        
        Args:
            candidate_skills: List of candidate's skills
            job_skills: List of required job skills
            
        Returns:
            SkillMatchResult with score, matched/missing skills
        """
        if not job_skills:
            return SkillMatchResult(score=100.0, matched_skills=[], missing_skills=[])
        
        if not candidate_skills:
            return SkillMatchResult(score=0.0, matched_skills=[], missing_skills=job_skills)
        
        # Normalize skills
        candidate_skills_normalized = [str(s).lower().strip() for s in candidate_skills if s]
        job_skills_normalized = [str(s).lower().strip() for s in job_skills if s]
        
        matched_skills = []
        missing_skills = []
        match_details = {}
        
        for job_skill in job_skills_normalized:
            is_matched = False
            match_type = None
            
            # Strategy 1: Exact match
            if job_skill in candidate_skills_normalized:
                matched_skills.append(job_skill)
                match_details[job_skill] = 'exact'
                is_matched = True
                continue
            
            # Strategy 2: Synonym match
            if not is_matched:
                for base_skill, synonyms in self.SKILL_SYNONYMS.items():
                    # Check if job skill matches base or any synonym
                    if job_skill == base_skill or job_skill in synonyms:
                        # Check if candidate has base or any synonym
                        if base_skill in candidate_skills_normalized or \
                           any(syn in candidate_skills_normalized for syn in synonyms):
                            matched_skills.append(job_skill)
                            match_details[job_skill] = 'synonym'
                            is_matched = True
                            break
                    
                    # Also check reverse: if candidate skill is base, job might be synonym
                    if not is_matched:
                        for candidate_skill in candidate_skills_normalized:
                            if candidate_skill in self.SKILL_SYNONYMS:
                                syns = self.SKILL_SYNONYMS[candidate_skill]
                                if job_skill in syns or job_skill == candidate_skill:
                                    matched_skills.append(job_skill)
                                    match_details[job_skill] = 'synonym'
                                    is_matched = True
                                    break
                        if is_matched:
                            break
            
            # Strategy 3: Fuzzy match
            if not is_matched:
                for candidate_skill in candidate_skills_normalized:
                    similarity = SequenceMatcher(None, job_skill, candidate_skill).ratio()
                    if similarity >= self.FUZZY_MATCH_THRESHOLD:
                        matched_skills.append(job_skill)
                        match_details[job_skill] = 'fuzzy'
                        is_matched = True
                        break
            
            if not is_matched:
                missing_skills.append(job_skill)
        
        # Calculate score
        score = (len(matched_skills) / len(job_skills_normalized)) * 100 if job_skills_normalized else 100
        
        return SkillMatchResult(
            score=round(score, 2),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            match_details=match_details
        )
    
    def calculate_experience_score(
        self,
        candidate_years: int,
        job_min_years: int,
        job_max_years: Optional[int] = None
    ) -> float:
        """
        Calculate experience match score (20% weight).
        
        Rule-based scoring:
        - Meets minimum: 100%
        - 1 year short: 85%
        - 2 years short: 70%
        - 3+ years short: 55%
        - Overqualified: Small penalty
        
        Args:
            candidate_years: Candidate's years of experience
            job_min_years: Job's minimum required years
            job_max_years: Job's maximum years (optional)
            
        Returns:
            Experience score 0-100
        """
        if job_min_years == 0:
            return 100.0
        
        years_short = job_min_years - candidate_years
        
        if years_short <= 0:
            # Candidate meets or exceeds minimum
            score = 100.0
            
            # Check if overqualified (if max is specified)
            if job_max_years and candidate_years > job_max_years:
                years_over = candidate_years - job_max_years
                if years_over <= 2:
                    score = 95.0
                elif years_over <= 5:
                    score = 90.0
                elif years_over <= 10:
                    score = 85.0
                else:
                    score = 80.0
        else:
            # Candidate is short on experience
            if years_short == 1:
                score = 85.0
            elif years_short == 2:
                score = 70.0
            elif years_short == 3:
                score = 55.0
            else:
                score = 40.0
        
        return score
    
    def calculate_semantic_score(
        self,
        candidate_embedding: Optional[List[float]],
        job_embedding: Optional[List[float]]
    ) -> float:
        """
        Calculate semantic similarity score (35% weight).
        
        Uses cosine similarity between candidate and job embeddings.
        
        Args:
            candidate_embedding: Candidate's embedding vector (768 dimensions)
            job_embedding: Job posting's embedding vector (768 dimensions)
            
        Returns:
            Semantic similarity score 0-100
        """
        if candidate_embedding is None or job_embedding is None:
            return 50.0  # Default to neutral if embeddings not available
        
        try:
            # Convert to lists if needed
            cand_vec = list(candidate_embedding) if hasattr(candidate_embedding, '__iter__') else []
            job_vec = list(job_embedding) if hasattr(job_embedding, '__iter__') else []
            
            if not cand_vec or not job_vec:
                return 50.0
            
            # Calculate cosine similarity
            dot_product = sum(a * b for a, b in zip(cand_vec, job_vec))
            magnitude_cand = sum(a * a for a in cand_vec) ** 0.5
            magnitude_job = sum(b * b for b in job_vec) ** 0.5
            
            if magnitude_cand == 0 or magnitude_job == 0:
                return 50.0
            
            cosine_similarity = dot_product / (magnitude_cand * magnitude_job)
            
            # Normalize to 0-100 scale
            # Cosine similarity ranges from -1 to 1, but for text it's typically 0 to 1
            similarity_score = max(0.0, min(100.0, cosine_similarity * 100.0))
            
            return round(similarity_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating semantic score: {e}")
            return 50.0
    
    # ===========================================
    # AI Compatibility Analysis (On-Demand)
    # ===========================================
    
    def calculate_ai_compatibility(
        self,
        candidate: Candidate,
        job_posting: JobPosting
    ) -> AICompatibilityResult:
        """
        Calculate AI-powered detailed compatibility analysis.
        
        This is called on-demand when a recruiter clicks "Detailed Analysis".
        Results are cached for 24 hours in the CandidateJobMatch record.
        
        Args:
            candidate: Candidate model instance
            job_posting: JobPosting model instance
            
        Returns:
            AICompatibilityResult with detailed analysis
        """
        if not self.model:
            raise ValueError("AI model not available. Please configure GOOGLE_API_KEY.")
        
        try:
            logger.info(f"Calculating AI compatibility for candidate {candidate.id} and job {job_posting.id}")
            
            # Build candidate summary
            candidate_summary = self._build_candidate_summary(candidate)
            
            # Build job summary
            job_summary = self._build_job_summary(job_posting)
            
            # Build prompt
            prompt = f"""Analyze the compatibility between this candidate and job opportunity.

CANDIDATE PROFILE:
{candidate_summary}

JOB OPPORTUNITY:
{job_summary}

Provide a detailed compatibility analysis with:
1. COMPATIBILITY_SCORE: A score from 0-100
2. STRENGTHS: List 3-5 key strengths that make this candidate a good fit
3. GAPS: List any skill or experience gaps
4. RECOMMENDATIONS: Provide 2-3 actionable recommendations
5. EXPERIENCE_ANALYSIS: A paragraph analyzing how well the candidate's experience aligns
6. CULTURE_FIT_INDICATORS: List any positive or concerning cultural fit indicators

Format your response as JSON with these exact keys:
{{
    "compatibility_score": <number>,
    "strengths": [<list of strings>],
    "gaps": [<list of strings>],
    "recommendations": [<list of strings>],
    "experience_analysis": "<string>",
    "culture_fit_indicators": [<list of strings>]
}}"""
            
            # Call AI
            structured_llm = self.model.with_structured_output(AICompatibilityResult)
            result = structured_llm.invoke([HumanMessage(content=prompt)])
            
            logger.info(f"AI compatibility score: {result.compatibility_score}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating AI compatibility: {e}")
            raise
    
    # ===========================================
    # Helper Methods
    # ===========================================
    
    def _get_grade(self, score: float) -> str:
        """Get letter grade from score (no D/F grades)."""
        if score >= self.GRADE_A_PLUS:
            return 'A+'
        elif score >= self.GRADE_A:
            return 'A'
        elif score >= self.GRADE_B_PLUS:
            return 'B+'
        elif score >= self.GRADE_B:
            return 'B'
        elif score >= self.GRADE_C_PLUS:
            return 'C+'
        else:
            return 'C'
    
    def _generate_match_reasons(
        self,
        skill_result: SkillMatchResult,
        experience_score: float,
        semantic_score: float,
        candidate: Candidate,
        job_posting: JobPosting
    ) -> List[str]:
        """Generate human-readable match reasons."""
        reasons = []
        
        # Skills reasons
        if skill_result.score >= 80:
            reasons.append(f"Strong skills match ({len(skill_result.matched_skills)} of {len(skill_result.matched_skills) + len(skill_result.missing_skills)} skills)")
        elif skill_result.score >= 60:
            reasons.append(f"Good skills match ({len(skill_result.matched_skills)} skills aligned)")
        
        # Highlight top matched skills (max 3)
        if skill_result.matched_skills:
            top_skills = skill_result.matched_skills[:3]
            reasons.append(f"Key skills: {', '.join(top_skills)}")
        
        # Experience reasons
        if experience_score >= 90:
            reasons.append("Experience level is ideal")
        elif experience_score >= 70:
            reasons.append("Experience level is suitable")
        
        # Semantic similarity reasons
        if semantic_score >= 70:
            reasons.append("Strong overall profile alignment")
        
        return reasons
    
    def _generate_explanation(
        self,
        overall_score: float,
        match_grade: str,
        skill_result: SkillMatchResult,
        experience_score: float,
        semantic_score: float,
        job_posting: JobPosting
    ) -> str:
        """Generate human-readable explanation."""
        parts = []
        
        parts.append(f"This is a {match_grade} match for {job_posting.title}")
        
        if skill_result.score >= 80:
            parts.append(f"with excellent skills alignment ({int(skill_result.score)}%)")
        elif skill_result.score >= 60:
            parts.append(f"with good skills alignment ({int(skill_result.score)}%)")
        else:
            parts.append(f"but skills alignment could be improved ({int(skill_result.score)}%)")
        
        if skill_result.missing_skills:
            missing_preview = skill_result.missing_skills[:3]
            parts.append(f". Consider developing: {', '.join(missing_preview)}")
        
        return " ".join(parts) + "."
    
    def _build_candidate_summary(self, candidate: Candidate) -> str:
        """Build candidate summary for AI analysis."""
        parts = []
        
        if candidate.current_title:
            parts.append(f"Current Title: {candidate.current_title}")
        
        if candidate.total_experience_years:
            parts.append(f"Experience: {candidate.total_experience_years} years")
        
        if candidate.skills:
            skills_str = ", ".join(candidate.skills[:20])
            parts.append(f"Skills: {skills_str}")
        
        if candidate.professional_summary:
            parts.append(f"Summary: {candidate.professional_summary[:500]}")
        
        return "\n".join(parts)
    
    def _build_job_summary(self, job_posting: JobPosting) -> str:
        """Build job summary for AI analysis."""
        parts = []
        
        parts.append(f"Title: {job_posting.title}")
        parts.append(f"Company: {job_posting.company}")
        
        if job_posting.location:
            parts.append(f"Location: {job_posting.location}")
        
        if job_posting.experience_min:
            exp_str = f"{job_posting.experience_min}"
            if job_posting.experience_max:
                exp_str += f"-{job_posting.experience_max}"
            parts.append(f"Experience Required: {exp_str} years")
        
        if job_posting.skills:
            skills_str = ", ".join(job_posting.skills[:15])
            parts.append(f"Required Skills: {skills_str}")
        
        if job_posting.description:
            parts.append(f"Description: {job_posting.description[:1000]}")
        
        return "\n".join(parts)

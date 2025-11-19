"""
Job Import Service for parsing and importing job postings from various platforms.
Handles data extraction, validation, duplicate detection, and bulk import operations.
"""
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date
from pathlib import Path
from decimal import Decimal
import logging

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert

from app import db
from app.models.job_posting import JobPosting
from app.models.job_import_batch import JobImportBatch
from config.settings import settings

logger = logging.getLogger(__name__)


class JobImportService:
    """
    Service for importing jobs from external platforms.
    Provides utilities for parsing salary, experience, skills, and other job attributes.
    
    NOTE: Jobs are GLOBAL (shared across all tenants). Import operations are managed
    by PM_ADMIN at the platform level. No tenant-specific tracking needed.
    """
    
    # Salary parsing patterns
    SALARY_PATTERNS = {
        'annual_range': re.compile(r'\$?(\d+)[kK]?\s*-\s*\$?(\d+)[kK]?', re.IGNORECASE),
        'annual_single': re.compile(r'\$?(\d+)[kK]?(?:\s*(?:per\s+)?(?:year|annually|annum))?', re.IGNORECASE),
        'hourly_range': re.compile(r'\$?(\d+(?:\.\d+)?)\s*-\s*\$?(\d+(?:\.\d+)?)\s*(?:per\s+)?(?:hr|hour)', re.IGNORECASE),
        'hourly_single': re.compile(r'\$?(\d+(?:\.\d+)?)\s*(?:per\s+)?(?:hr|hour)', re.IGNORECASE),
        'lakhs': re.compile(r'(\d+(?:\.\d+)?)[lL]\s*-\s*(\d+(?:\.\d+)?)[lL]', re.IGNORECASE),
    }
    
    # Experience parsing patterns
    EXPERIENCE_PATTERNS = {
        'range': re.compile(r'(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)', re.IGNORECASE),
        'minimum': re.compile(r'(\d+)\+?\s*(?:years?|yrs?)(?:\s+of\s+experience)?', re.IGNORECASE),
        'up_to': re.compile(r'up\s+to\s+(\d+)\s*(?:years?|yrs?)', re.IGNORECASE),
    }
    
    # Common skill synonyms for normalization
    SKILL_SYNONYMS = {
        'aws': 'AWS',
        'amazon web services': 'AWS',
        'ec2': 'AWS EC2',
        's3': 'AWS S3',
        'kubernetes': 'Kubernetes',
        'k8s': 'Kubernetes',
        'docker': 'Docker',
        'python': 'Python',
        'java': 'Java',
        'javascript': 'JavaScript',
        'js': 'JavaScript',
        'typescript': 'TypeScript',
        'ts': 'TypeScript',
        'react': 'React',
        'reactjs': 'React',
        'nodejs': 'Node.js',
        'node': 'Node.js',
        'angular': 'Angular',
        'vue': 'Vue.js',
        'vuejs': 'Vue.js',
        'sql': 'SQL',
        'mysql': 'MySQL',
        'postgresql': 'PostgreSQL',
        'postgres': 'PostgreSQL',
        'mongodb': 'MongoDB',
        'mongo': 'MongoDB',
        'redis': 'Redis',
        'jenkins': 'Jenkins',
        'ci/cd': 'CI/CD',
        'cicd': 'CI/CD',
        'terraform': 'Terraform',
        'ansible': 'Ansible',
        'git': 'Git',
        'github': 'GitHub',
        'gitlab': 'GitLab',
        'azure': 'Azure',
        'gcp': 'Google Cloud',
        'google cloud': 'Google Cloud',
        'devops': 'DevOps',
        'machine learning': 'Machine Learning',
        'ml': 'Machine Learning',
        'ai': 'Artificial Intelligence',
        'rest': 'REST API',
        'restful': 'REST API',
        'api': 'API',
        'graphql': 'GraphQL',
        'kafka': 'Kafka',
        'spark': 'Apache Spark',
        'hadoop': 'Hadoop',
        'linux': 'Linux',
        'unix': 'Unix',
        'bash': 'Bash',
        'shell': 'Shell Script',
        'powershell': 'PowerShell',
        'c++': 'C++',
        'c#': 'C#',
        'csharp': 'C#',
        '.net': '.NET',
        'dotnet': '.NET',
        'ruby': 'Ruby',
        'rails': 'Ruby on Rails',
        'php': 'PHP',
        'go': 'Go',
        'golang': 'Go',
        'rust': 'Rust',
        'swift': 'Swift',
        'kotlin': 'Kotlin',
        'scala': 'Scala',
        'r': 'R',
        'matlab': 'MATLAB',
        'tableau': 'Tableau',
        'power bi': 'Power BI',
        'powerbi': 'Power BI',
        'salesforce': 'Salesforce',
        'sap': 'SAP',
        'oracle': 'Oracle',
        'agile': 'Agile',
        'scrum': 'Scrum',
        'jira': 'Jira',
    }
    
    # Remote work indicators
    REMOTE_KEYWORDS = [
        'remote', 'work from home', 'wfh', 'telecommute', 
        'distributed', 'anywhere', 'virtual'
    ]
    
    def __init__(self):
        """
        Initialize JobImportService.
        
        Job imports are managed at the platform level by PM_ADMIN.
        No tenant-specific context needed.
        """
    
    def parse_salary(self, salary_str: str) -> Tuple[Optional[int], Optional[int], str]:
        """
        Parse salary string and extract min, max, and currency.
        
        Args:
            salary_str: Raw salary string from job posting
            
        Returns:
            Tuple of (salary_min, salary_max, currency)
            
        Examples:
            "$120K - $150K" -> (120000, 150000, "USD")
            "$50/hr" -> (104000, 104000, "USD")  # Assuming 2080 work hours/year
            "1L - 3L" -> (100000, 300000, "INR")  # Indian Lakhs
        """
        if not salary_str or salary_str.strip().upper() in ['N/A', 'NA', 'NONE', '']:
            return None, None, 'USD'
        
        salary_str = salary_str.strip()
        currency = 'USD'  # Default currency
        
        # Check for Indian Lakhs (1L = 100,000 INR)
        lakhs_match = self.SALARY_PATTERNS['lakhs'].search(salary_str)
        if lakhs_match:
            min_lakhs = float(lakhs_match.group(1))
            max_lakhs = float(lakhs_match.group(2))
            return int(min_lakhs * 100000), int(max_lakhs * 100000), 'INR'
        
        # Check for hourly range
        hourly_range_match = self.SALARY_PATTERNS['hourly_range'].search(salary_str)
        if hourly_range_match:
            min_hourly = float(hourly_range_match.group(1))
            max_hourly = float(hourly_range_match.group(2))
            # Convert hourly to annual (assuming 2080 work hours/year)
            return int(min_hourly * 2080), int(max_hourly * 2080), currency
        
        # Check for single hourly rate
        hourly_single_match = self.SALARY_PATTERNS['hourly_single'].search(salary_str)
        if hourly_single_match:
            hourly_rate = float(hourly_single_match.group(1))
            annual = int(hourly_rate * 2080)
            return annual, annual, currency
        
        # Check for annual range
        annual_range_match = self.SALARY_PATTERNS['annual_range'].search(salary_str)
        if annual_range_match:
            min_val = int(annual_range_match.group(1))
            max_val = int(annual_range_match.group(2))
            # Handle 'K' notation (e.g., 120K -> 120000)
            if min_val < 1000:
                min_val *= 1000
            if max_val < 1000:
                max_val *= 1000
            return min_val, max_val, currency
        
        # Check for single annual value
        annual_single_match = self.SALARY_PATTERNS['annual_single'].search(salary_str)
        if annual_single_match:
            value = int(annual_single_match.group(1))
            if value < 1000:
                value *= 1000
            return value, value, currency
        
        logger.warning(f"Could not parse salary string: {salary_str}")
        return None, None, currency
    
    def parse_experience(self, experience_str: str, description: str = "") -> Tuple[Optional[int], Optional[int]]:
        """
        Parse experience requirement and extract min and max years.
        
        Args:
            experience_str: Raw experience string
            description: Job description to search for experience info
            
        Returns:
            Tuple of (experience_min, experience_max)
            
        Examples:
            "5-7 years" -> (5, 7)
            "5+ years" -> (5, None)
            "up to 3 years" -> (0, 3)
        """
        search_text = f"{experience_str or ''} {description[:1000]}"
        
        if not search_text.strip() or search_text.strip().upper() in ['N/A', 'NA', 'NONE']:
            return None, None
        
        # Check for range (e.g., "5-7 years", "3 to 5 years")
        range_match = self.EXPERIENCE_PATTERNS['range'].search(search_text)
        if range_match:
            min_exp = int(range_match.group(1))
            max_exp = int(range_match.group(2))
            return min_exp, max_exp
        
        # Check for minimum (e.g., "5+ years", "5 years of experience")
        minimum_match = self.EXPERIENCE_PATTERNS['minimum'].search(search_text)
        if minimum_match:
            min_exp = int(minimum_match.group(1))
            return min_exp, None
        
        # Check for "up to X years"
        up_to_match = self.EXPERIENCE_PATTERNS['up_to'].search(search_text)
        if up_to_match:
            max_exp = int(up_to_match.group(1))
            return 0, max_exp
        
        return None, None
    
    def normalize_skills(self, skills: List[str]) -> List[str]:
        """
        Normalize skill names using synonym mapping and remove duplicates.
        
        Args:
            skills: List of raw skill names
            
        Returns:
            List of normalized, deduplicated skill names
            
        Example:
            ["aws", "k8s", "javascript", "JS"] -> ["AWS", "Kubernetes", "JavaScript"]
        """
        if not skills:
            return []
        
        normalized = set()
        for skill in skills:
            skill_lower = skill.strip().lower()
            # Use synonym if available, otherwise capitalize original
            normalized_skill = self.SKILL_SYNONYMS.get(skill_lower, skill.strip())
            if normalized_skill:
                normalized.add(normalized_skill)
        
        return sorted(list(normalized))
    
    def extract_skills_from_description(self, description: str, existing_skills: List[str] = None) -> List[str]:
        """
        Extract additional skills from job description using keyword matching.
        
        Args:
            description: Job description text
            existing_skills: Already extracted skills to avoid duplicates
            
        Returns:
            Combined list of skills
        """
        existing_skills = existing_skills or []
        description_lower = description.lower()
        
        # Extract skills mentioned in description
        found_skills = set(existing_skills)
        for keyword, normalized_skill in self.SKILL_SYNONYMS.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, description_lower, re.IGNORECASE):
                found_skills.add(normalized_skill)
        
        return sorted(list(found_skills))
    
    def detect_remote(self, location: str, description: str, is_remote: Optional[bool] = None) -> bool:
        """
        Detect if job is remote based on location and description.
        
        Args:
            location: Job location string
            description: Job description text
            is_remote: Explicitly specified remote flag (if available)
            
        Returns:
            True if job is remote, False otherwise
        """
        if is_remote is not None:
            return is_remote
        
        # Check location and description for remote keywords
        search_text = f"{location or ''} {description[:500]}".lower()
        
        for keyword in self.REMOTE_KEYWORDS:
            if keyword in search_text:
                return True
        
        return False
    
    def parse_posted_date(self, posted_date_str: str) -> Optional[date]:
        """
        Parse posted date from various formats.
        
        Args:
            posted_date_str: Raw posted date string
            
        Returns:
            date object or None
        """
        if not posted_date_str or posted_date_str.strip().upper() in ['N/A', 'NA', 'NONE', '']:
            return None
        
        # Try common date formats
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%B %d, %Y',
            '%b %d, %Y',
        ]
        
        posted_date_str = posted_date_str.strip()
        
        for fmt in date_formats:
            try:
                return datetime.strptime(posted_date_str, fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse posted date: {posted_date_str}")
        return None
    
    def generate_keywords(self, title: str, description: str, skills: List[str]) -> List[str]:
        """
        Generate searchable keywords from job title, description, and skills.
        
        Args:
            title: Job title
            description: Job description
            skills: List of skills
            
        Returns:
            List of keywords for search indexing
        """
        keywords = set(skills)
        
        # Extract important words from title
        title_words = re.findall(r'\b[A-Za-z]{3,}\b', title)
        keywords.update(word.title() for word in title_words)
        
        # Extract key terms from description (first 500 chars)
        desc_snippet = description[:500]
        common_tech_terms = re.findall(
            r'\b(?:[A-Z]{2,}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            desc_snippet
        )
        keywords.update(common_tech_terms)
        
        # Remove common words
        stop_words = {'The', 'And', 'For', 'With', 'This', 'That', 'From', 'Are', 'Has', 'Have'}
        keywords = keywords - stop_words
        
        return sorted(list(keywords))[:50]  # Limit to 50 keywords
    
    def create_batch_record(self, platform: str, file_path: str) -> JobImportBatch:
        """
        Create a new import batch record for tracking.
        
        Args:
            platform: Platform name (indeed, dice, etc.)
            file_path: Path to the import file
            
        Returns:
            JobImportBatch instance
        """
        # Generate unique batch ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_id = f"{platform}_{timestamp}"
        
        # Create import batch for tracking
        batch = JobImportBatch(
            batch_id=batch_id,
            platform=platform,
            import_source='cli_import',
            total_jobs=0,
            import_status='IN_PROGRESS',
            started_at=datetime.now()
        )
        db.session.add(batch)
        db.session.commit()
        return batch
    
    def read_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Read and parse JSON file containing job data.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            List of job dictionaries
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise ValueError(f"Expected JSON array, got {type(data)}")
        
        logger.info(f"Read {len(data)} jobs from {file_path}")
        return data
    
    def transform_job_data(self, raw_job: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """
        Transform raw job data from platform format to database format.
        
        Args:
            raw_job: Raw job data from JSON file
            platform: Platform name for field mapping
            
        Returns:
            Transformed job data ready for database insertion
        """
        # Extract basic fields with platform-specific mappings (NO tenant_id - jobs are global)
        job_data = {
            'external_job_id': str(raw_job.get('jobId', raw_job.get('id', ''))),
            'platform': platform,
            'title': raw_job.get('title', ''),
            'company': raw_job.get('company', ''),
            'location': raw_job.get('location'),
            'description': raw_job.get('description', ''),
            'snippet': raw_job.get('snippet'),
            'job_url': raw_job.get('jobUrl', raw_job.get('url', '')),
            'apply_url': raw_job.get('applyUrl'),
            'job_type': raw_job.get('jobType'),
            'status': 'ACTIVE',
            'imported_at': datetime.utcnow(),
            'raw_metadata': raw_job.get('metadata', {}),
        }
        
        # Parse salary
        salary_str = raw_job.get('salary', '')
        salary_min, salary_max, currency = self.parse_salary(salary_str)
        job_data.update({
            'salary_range': salary_str if salary_str and salary_str.upper() != 'N/A' else None,
            'salary_min': salary_min,
            'salary_max': salary_max,
            'salary_currency': currency,
        })
        
        # Parse experience
        experience_str = raw_job.get('experience', '')
        description = job_data['description']
        exp_min, exp_max = self.parse_experience(experience_str, description)
        job_data.update({
            'experience_required': experience_str if experience_str and experience_str.upper() != 'N/A' else None,
            'experience_min': exp_min,
            'experience_max': exp_max,
        })
        
        # Parse and normalize skills
        raw_skills = raw_job.get('skills', [])
        normalized_skills = self.normalize_skills(raw_skills)
        enhanced_skills = self.extract_skills_from_description(description, normalized_skills)
        job_data['skills'] = enhanced_skills
        
        # Generate keywords
        job_data['keywords'] = self.generate_keywords(
            job_data['title'],
            description,
            enhanced_skills
        )
        
        # Detect remote work
        is_remote_flag = raw_job.get('isRemote')
        job_data['is_remote'] = self.detect_remote(
            job_data['location'],
            description,
            is_remote_flag
        )
        
        # Parse posted date
        posted_date_str = raw_job.get('postedDate', '')
        job_data['posted_date'] = self.parse_posted_date(posted_date_str)
        
        # Set requirements field if available
        job_data['requirements'] = raw_job.get('requirements')
        
        return job_data
    
    def check_duplicate(self, platform: str, external_job_id: str) -> Optional[JobPosting]:
        """
        Check if job already exists in database (globally, not per tenant).
        
        Args:
            platform: Platform name
            external_job_id: External job ID from platform
            
        Returns:
            Existing JobPosting or None
        """
        stmt = select(JobPosting).where(
            JobPosting.platform == platform,
            JobPosting.external_job_id == external_job_id
        )
        return db.session.scalar(stmt)
    
    def bulk_upsert_jobs(
        self,
        jobs_data: List[Dict[str, Any]],
        batch: JobImportBatch,
        update_existing: bool = True
    ) -> Tuple[int, int, int]:
        """
        Bulk insert or update jobs in database using PostgreSQL UPSERT.
        
        Args:
            jobs_data: List of transformed job dictionaries
            batch: Import batch record for tracking
            update_existing: Whether to update existing jobs
            
        Returns:
            Tuple of (new_count, updated_count, failed_count)
        """
        if not jobs_data:
            return 0, 0, 0
        
        new_count = 0
        updated_count = 0
        failed_count = 0
        
        # Add batch ID to all jobs
        batch_id = f"{batch.platform}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        for job in jobs_data:
            job['import_batch_id'] = batch_id
        
        try:
            if update_existing:
                # Use PostgreSQL INSERT ... ON CONFLICT DO UPDATE
                stmt = insert(JobPosting).values(jobs_data)
                
                # Define which columns to update on conflict
                update_dict = {
                    'title': stmt.excluded.title,
                    'company': stmt.excluded.company,
                    'location': stmt.excluded.location,
                    'salary_range': stmt.excluded.salary_range,
                    'salary_min': stmt.excluded.salary_min,
                    'salary_max': stmt.excluded.salary_max,
                    'salary_currency': stmt.excluded.salary_currency,
                    'description': stmt.excluded.description,
                    'snippet': stmt.excluded.snippet,
                    'requirements': stmt.excluded.requirements,
                    'posted_date': stmt.excluded.posted_date,
                    'expires_at': stmt.excluded.expires_at,
                    'job_type': stmt.excluded.job_type,
                    'is_remote': stmt.excluded.is_remote,
                    'experience_required': stmt.excluded.experience_required,
                    'experience_min': stmt.excluded.experience_min,
                    'experience_max': stmt.excluded.experience_max,
                    'skills': stmt.excluded.skills,
                    'keywords': stmt.excluded.keywords,
                    'job_url': stmt.excluded.job_url,
                    'apply_url': stmt.excluded.apply_url,
                    'status': stmt.excluded.status,
                    'raw_metadata': stmt.excluded.raw_metadata,
                    'last_synced_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                }
                
                stmt = stmt.on_conflict_do_update(
                    index_elements=['platform', 'external_job_id'],
                    set_=update_dict
                ).returning(JobPosting.id)
                
                # Execute and count results
                result = db.session.execute(stmt)
                db.session.commit()
                
                # For upsert, we need to check which were new vs updated
                # This is approximate - assumes all were processed successfully
                existing_count = db.session.scalar(
                    select(func.count(JobPosting.id)).where(
                        JobPosting.import_batch_id == batch_id
                    )
                )
                
                # Estimate: if we have fewer records than input, some were updates
                total_processed = len(jobs_data)
                new_count = total_processed
                updated_count = 0  # This is approximate with bulk upsert
                
                logger.info(f"Bulk upserted {total_processed} jobs (batch: {batch_id})")
                
            else:
                # Insert only new jobs, skip existing
                for job_data in jobs_data:
                    try:
                        existing = self.check_duplicate(
                            job_data['platform'],
                            job_data['external_job_id']
                        )
                        
                        if existing:
                            updated_count += 1
                            continue
                        
                        job = JobPosting(**job_data)
                        db.session.add(job)
                        new_count += 1
                        
                        # Commit in batches of 100
                        if (new_count + updated_count + failed_count) % 100 == 0:
                            db.session.commit()
                            
                    except Exception as e:
                        logger.error(f"Failed to insert job {job_data.get('external_job_id')}: {e}")
                        batch.add_error(job_data.get('external_job_id', 'unknown'), str(e))
                        failed_count += 1
                        db.session.rollback()
                
                db.session.commit()
                logger.info(f"Inserted {new_count} new jobs, skipped {updated_count} existing")
                
        except Exception as e:
            logger.error(f"Bulk upsert failed: {e}")
            db.session.rollback()
            raise
        
        return new_count, updated_count, failed_count
    
    def import_from_json(
        self,
        file_path: str,
        platform: str,
        update_existing: bool = True,
        batch_size: int = 500
    ) -> JobImportBatch:
        """
        Import jobs from JSON file with full processing pipeline.
        
        Args:
            file_path: Path to JSON file
            platform: Platform name (indeed, dice, techfetch, glassdoor, monster)
            update_existing: Whether to update existing jobs
            batch_size: Number of jobs to process in each batch
            
        Returns:
            Completed JobImportBatch record with statistics
            
        Example:
            service = JobImportService(tenant_id=1)
            batch = service.import_from_json(
                file_path='jobs/indeed_jobs_2025-11-12.json',
                platform='indeed',
                update_existing=True
            )
            print(f"Imported {batch.new_jobs} new jobs, updated {batch.updated_jobs}")
        """
        start_time = datetime.utcnow()
        
        # Create batch record
        batch = self.create_batch_record(platform, file_path)
        
        try:
            # Read JSON file
            raw_jobs = self.read_json_file(file_path)
            batch.total_jobs = len(raw_jobs)
            db.session.commit()
            
            # Transform all jobs
            transformed_jobs = []
            for raw_job in raw_jobs:
                try:
                    transformed = self.transform_job_data(raw_job, platform)
                    transformed_jobs.append(transformed)
                except Exception as e:
                    job_id = raw_job.get('jobId', raw_job.get('id', 'unknown'))
                    logger.error(f"Failed to transform job {job_id}: {e}")
                    batch.add_error(str(job_id), str(e))
            
            # Deduplicate within the batch (keep last occurrence)
            seen = {}
            deduplicated_jobs = []
            duplicates_removed = 0
            
            for job in transformed_jobs:
                key = (job['platform'], job['external_job_id'])
                if key in seen:
                    duplicates_removed += 1
                    logger.warning(f"Duplicate job in batch: {job['platform']} - {job['external_job_id']}")
                else:
                    seen[key] = True
                    deduplicated_jobs.append(job)
            
            if duplicates_removed > 0:
                logger.info(f"Removed {duplicates_removed} duplicate jobs from batch")
            
            transformed_jobs = deduplicated_jobs
            
            # Process in batches
            total_new = 0
            total_updated = 0
            total_failed = 0
            
            for i in range(0, len(transformed_jobs), batch_size):
                batch_data = transformed_jobs[i:i + batch_size]
                new, updated, failed = self.bulk_upsert_jobs(batch_data, batch, update_existing)
                total_new += new
                total_updated += updated
                total_failed += failed
                
                logger.info(
                    f"Processed batch {i // batch_size + 1}: "
                    f"{new} new, {updated} updated, {failed} failed"
                )
            
            # Update batch statistics
            batch.new_jobs = total_new
            batch.updated_jobs = total_updated
            batch.failed_jobs = total_failed + len(batch.error_log or {})
            batch.status = 'COMPLETED' if total_failed == 0 else 'COMPLETED_WITH_ERRORS'
            batch.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Import completed in {duration:.2f}s: "
                f"{batch.new_jobs} new, {batch.updated_jobs} updated, "
                f"{batch.failed_jobs} failed from {batch.total_jobs} total"
            )
            
            return batch
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            batch.status = 'FAILED'
            batch.completed_at = datetime.utcnow()
            batch.add_error('IMPORT_ERROR', str(e))
            db.session.commit()
            raise
    
    def get_import_statistics(self, platform: Optional[str] = None) -> Dict[str, Any]:
        """
        Get import statistics for tenant, optionally filtered by platform.
        
        Args:
            platform: Optional platform filter
            
        Returns:
            Dictionary with import statistics
        """
        query = select(JobImportBatch).where(
            JobImportBatch.tenant_id == self.tenant_id
        )
        
        if platform:
            query = query.where(JobImportBatch.platform == platform)
        
        batches = db.session.scalars(query).all()
        
        stats = {
            'total_batches': len(batches),
            'total_jobs_processed': sum(b.total_jobs for b in batches),
            'total_new_jobs': sum(b.new_jobs for b in batches),
            'total_updated_jobs': sum(b.updated_jobs for b in batches),
            'total_failed_jobs': sum(b.failed_jobs for b in batches),
            'batches_by_status': {},
            'batches_by_platform': {},
            'recent_batches': [],
        }
        
        # Group by status
        for batch in batches:
            stats['batches_by_status'][batch.status] = \
                stats['batches_by_status'].get(batch.status, 0) + 1
            stats['batches_by_platform'][batch.platform] = \
                stats['batches_by_platform'].get(batch.platform, 0) + 1
        
        # Get 10 most recent batches
        recent = sorted(batches, key=lambda b: b.created_at, reverse=True)[:10]
        stats['recent_batches'] = [
            {
                'id': b.id,
                'platform': b.platform,
                'status': b.status,
                'total_jobs': b.total_jobs,
                'new_jobs': b.new_jobs,
                'updated_jobs': b.updated_jobs,
                'failed_jobs': b.failed_jobs,
                'created_at': b.created_at.isoformat(),
                'duration_seconds': b.duration_seconds,
            }
            for b in recent
        ]
        
        return stats

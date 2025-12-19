"""Email Job Parser Service.

Uses Google Gemini AI to parse job details from email content and create
structured job postings.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import google.generativeai as genai
from sqlalchemy import select

from app import db
from app.models.job_posting import JobPosting
from app.models.processed_email import ProcessedEmail
from app.models.user_email_integration import UserEmailIntegration
from config.settings import settings

logger = logging.getLogger(__name__)


class EmailJobParserService:
    """Service for parsing job details from emails using AI."""
    
    # Prompt template for job extraction
    JOB_EXTRACTION_PROMPT = """You are an expert at extracting job posting information from emails.

Analyze the following email and extract job details. The email was identified as containing a job posting based on its subject line.

Email Subject: {subject}
Email Sender: {sender}
Email Body:
{body}

Extract the following information and return as valid JSON. Use null for any field you cannot determine:

{{
    "title": "Job title (e.g., 'Senior Python Developer')",
    "company": "Company name if mentioned",
    "location": "Job location (city, state or 'Remote')",
    "job_type": "One of: full_time, part_time, contract, contract_to_hire, or null",
    "employment_type": "One of: W2, C2C, 1099, or null",
    "duration_months": "Contract duration in months if specified, or null",
    "min_rate": "Minimum hourly rate as number if specified, or null",
    "max_rate": "Maximum hourly rate as number if specified, or null",
    "min_salary": "Minimum annual salary as number if specified, or null",
    "max_salary": "Maximum annual salary as number if specified, or null",
    "required_skills": ["List", "of", "required", "skills"],
    "preferred_skills": ["List", "of", "nice-to-have", "skills"],
    "experience_years": "Minimum years of experience required as number, or null",
    "description": "Brief job description (max 500 chars)",
    "requirements": "Key requirements as a single string",
    "remote_type": "One of: onsite, hybrid, remote, or null",
    "visa_sponsorship": "true/false if mentioned, or null",
    "client_name": "End client name if mentioned (often different from company)",
    "confidence_score": "Your confidence in this extraction from 0.0 to 1.0"
}}

Important:
- Extract factual information only, do not invent details
- For rates, extract hourly rates, not annual salary if given as hourly
- Parse skills from the requirements/description
- Return ONLY the JSON object, no other text"""

    def __init__(self):
        """Initialize the parser with Gemini AI."""
        self.gemini_model_name = settings.gemini_model
        
        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.ai_model = genai.GenerativeModel(self.gemini_model_name)
            logger.info(f"Email Job Parser using model: {self.gemini_model_name}")
        else:
            self.ai_model = None
            logger.warning("Google API key not configured - email job parsing disabled")
    
    def parse_email_to_job(
        self,
        integration: UserEmailIntegration,
        email_data: dict,
    ) -> Optional[JobPosting]:
        """
        Parse an email and create a job posting.
        
        Args:
            integration: UserEmailIntegration that received the email
            email_data: Dictionary with email details (id, subject, body, sender, etc.)
            
        Returns:
            Created JobPosting or None if parsing failed
        """
        if not self.ai_model:
            logger.error("AI model not configured")
            return None
        
        email_id = email_data.get("email_id")
        subject = email_data.get("subject", "")
        sender = email_data.get("sender", "")
        body = email_data.get("body", "")
        
        try:
            # Call AI to extract job details
            job_data = self._extract_job_details(subject, sender, body)
            
            if not job_data or not job_data.get("title"):
                logger.warning(f"Could not extract job from email {email_id}")
                self._record_processed_email(
                    integration=integration,
                    email_data=email_data,
                    result="failed",
                    skip_reason="no_job_extracted",
                    confidence=job_data.get("confidence_score") if job_data else None,
                )
                return None
            
            # Create job posting
            job = self._create_job_posting(
                integration=integration,
                email_data=email_data,
                job_data=job_data,
            )
            
            # Record processed email with success
            processed_email = self._record_processed_email(
                integration=integration,
                email_data=email_data,
                result="job_created",
                job_id=job.id,
                confidence=job_data.get("confidence_score"),
            )
            
            # Update integration stats
            integration.emails_processed_count = (integration.emails_processed_count or 0) + 1
            integration.jobs_created_count = (integration.jobs_created_count or 0) + 1
            db.session.commit()
            
            logger.info(f"Created job posting {job.id} from email {email_id}")
            return job
            
        except Exception as e:
            logger.error(f"Failed to parse email {email_id}: {e}")
            self._record_processed_email(
                integration=integration,
                email_data=email_data,
                result="error",
                skip_reason=str(e)[:500],
            )
            db.session.commit()
            return None
    
    def _extract_job_details(
        self,
        subject: str,
        sender: str,
        body: str,
    ) -> Optional[dict]:
        """
        Use AI to extract job details from email.
        
        Args:
            subject: Email subject
            sender: Email sender
            body: Email body text
            
        Returns:
            Dictionary with extracted job details or None
        """
        prompt = self.JOB_EXTRACTION_PROMPT.format(
            subject=subject,
            sender=sender,
            body=body[:8000],  # Limit body size for API
        )
        
        try:
            response = self.ai_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,  # Low temperature for factual extraction
                    max_output_tokens=2000,
                ),
            )
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Try to find JSON in response
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                return json.loads(json_match.group())
            
            # Try parsing entire response as JSON
            return json.loads(response_text)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return None
    
    def _create_job_posting(
        self,
        integration: UserEmailIntegration,
        email_data: dict,
        job_data: dict,
    ) -> JobPosting:
        """
        Create a job posting from extracted data.
        
        Args:
            integration: Source integration
            email_data: Original email data
            job_data: Extracted job details
            
        Returns:
            Created JobPosting
        """
        # Parse skills
        required_skills = job_data.get("required_skills", [])
        if isinstance(required_skills, list):
            required_skills = required_skills
        else:
            required_skills = []
        
        preferred_skills = job_data.get("preferred_skills", [])
        if isinstance(preferred_skills, list):
            preferred_skills = preferred_skills
        else:
            preferred_skills = []
        
        # Combine skills for the skills field
        all_skills = list(set(required_skills + preferred_skills))
        
        # Map job type
        job_type_map = {
            "full_time": "full_time",
            "part_time": "part_time",
            "contract": "contract",
            "contract_to_hire": "contract_to_hire",
        }
        job_type = job_type_map.get(job_data.get("job_type"), "contract")
        
        # Map remote type
        remote_type_map = {
            "onsite": "onsite",
            "hybrid": "hybrid",
            "remote": "remote",
        }
        remote_type = remote_type_map.get(job_data.get("remote_type"), "onsite")
        
        # Parse email received date
        received_at = email_data.get("received_at")
        if isinstance(received_at, str):
            try:
                received_at = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
            except Exception:
                received_at = datetime.now(timezone.utc)
        
        job = JobPosting(
            # Core fields
            title=job_data.get("title", "Untitled Position"),
            company=job_data.get("company", self._extract_company_from_sender(email_data.get("sender", ""))),
            location=job_data.get("location"),
            description=job_data.get("description", ""),
            
            # Job details
            job_type=job_type,
            remote_type=remote_type,
            skills=all_skills,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            experience_years=job_data.get("experience_years"),
            requirements=job_data.get("requirements"),
            
            # Compensation
            min_rate=job_data.get("min_rate"),
            max_rate=job_data.get("max_rate"),
            min_salary=job_data.get("min_salary"),
            max_salary=job_data.get("max_salary"),
            employment_type=job_data.get("employment_type"),
            duration_months=job_data.get("duration_months"),
            
            # Source info
            source="email",
            source_id=f"email-{email_data.get('email_id', '')}",
            
            # Email source fields
            is_email_sourced=True,
            source_tenant_id=integration.tenant_id,
            sourced_by_user_id=integration.user_id,
            source_email_id=email_data.get("email_id"),
            source_email_subject=email_data.get("subject", "")[:500],
            source_email_sender=email_data.get("sender", "")[:255],
            source_email_date=received_at,
            
            # Metadata
            status="active",
            posted_date=datetime.now(timezone.utc),
            visa_sponsorship=job_data.get("visa_sponsorship"),
            client_name=job_data.get("client_name"),
        )
        
        db.session.add(job)
        db.session.flush()  # Get job ID without committing
        
        return job
    
    def _extract_company_from_sender(self, sender: str) -> str:
        """Extract company name from email sender."""
        # Try to extract domain from email
        email_match = re.search(r"<([^>]+)>", sender)
        if email_match:
            email = email_match.group(1)
            domain = email.split("@")[-1]
            # Extract company from domain (remove common suffixes)
            company = domain.split(".")[0].replace("-", " ").replace("_", " ").title()
            return company
        
        return "Unknown"
    
    def _record_processed_email(
        self,
        integration: UserEmailIntegration,
        email_data: dict,
        result: str,
        job_id: Optional[int] = None,
        skip_reason: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> ProcessedEmail:
        """Record a processed email."""
        processed = ProcessedEmail(
            integration_id=integration.id,
            tenant_id=integration.tenant_id,
            email_message_id=email_data.get("email_id", ""),
            email_thread_id=email_data.get("thread_id"),
            email_subject=email_data.get("subject", "")[:500],
            email_sender=email_data.get("sender", "")[:255],
            processing_result=result,
            job_id=job_id,
            skip_reason=skip_reason,
            parsing_confidence=confidence,
        )
        
        db.session.add(processed)
        db.session.flush()
        
        return processed
    
    def reparse_email(
        self,
        processed_email_id: int,
        tenant_id: int,
    ) -> Optional[JobPosting]:
        """
        Re-parse a previously processed email.
        
        Args:
            processed_email_id: ID of ProcessedEmail to reparse
            tenant_id: Tenant ID for authorization
            
        Returns:
            Created JobPosting or None
        """
        stmt = select(ProcessedEmail).where(
            ProcessedEmail.id == processed_email_id,
            ProcessedEmail.tenant_id == tenant_id,
        )
        processed = db.session.scalar(stmt)
        
        if not processed:
            raise ValueError("Processed email not found")
        
        if processed.job_id:
            raise ValueError("Email already has an associated job posting")
        
        # Get the integration
        integration = db.session.get(UserEmailIntegration, processed.integration_id)
        if not integration:
            raise ValueError("Integration not found")
        
        # We don't have the original body stored, so we need to re-fetch
        # This would require implementation based on needs
        raise NotImplementedError(
            "Re-parsing requires storing original email body or re-fetching from provider"
        )


# Singleton instance
email_job_parser_service = EmailJobParserService()

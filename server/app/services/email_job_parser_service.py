"""Email Job Parser Service.

Uses Google Gemini AI to parse job details from email content and create
structured job postings.

SCALABILITY IMPROVEMENTS:
- Phase 7: Circuit breaker for Gemini API fault tolerance
- Cross-user deduplication: Uses content hash to detect same job across recruiters
"""

import hashlib
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
from app.utils.circuit_breaker import gemini_circuit_breaker, CircuitBreakerError
from config.settings import settings

logger = logging.getLogger(__name__)


class EmailJobParserService:
    """Service for parsing job details from emails using AI."""
    
    # Prompt template for job extraction - aligned with JobPosting model
    JOB_EXTRACTION_PROMPT = """You are an expert at extracting job posting information from emails.

Analyze the following email and extract job details. The email was identified as containing a job posting based on its subject line.

Email Subject: {subject}
Email Sender: {sender}
Email Body:
{body}

Extract the following information and return as valid JSON. Use null for any field you cannot determine:

{{
    "title": "Job title (e.g., 'Senior Python Developer')",
    "company": "Company name if mentioned, or null",
    "location": "Job location (city, state) or null",
    "job_type": "One of: Full-time, Part-time, Contract, Contract-to-hire, or null",
    "is_remote": true or false or null,
    "salary_range": "Salary range as string (e.g., '$100k-$150k/year' or '$50-$70/hour'), or null",
    "salary_min": "Minimum annual salary as integer (e.g., 100000), or null",
    "salary_max": "Maximum annual salary as integer (e.g., 150000), or null",
    "skills": ["List", "of", "all", "skills", "mentioned"],
    "experience_required": "Experience requirement as string (e.g., '3-5 years'), or null",
    "experience_min": "Minimum years of experience as integer (e.g., 3), or null",
    "experience_max": "Maximum years of experience as integer (e.g., 5), or null",
    "description": "Brief job description summarizing the role (max 1000 chars)",
    "requirements": "Key requirements and qualifications as a single string, or null",
    "snippet": "Short 1-2 sentence summary of the job, or null",
    "confidence_score": "Your confidence in this extraction from 0.0 to 1.0"
}}

Important:
- Extract factual information only, do not invent details
- For salary, convert hourly rates to annual (hourly * 2080) if only hourly is given
- Parse ALL skills from the requirements/description into the skills array
- is_remote should be true only if the job is fully remote, false for onsite/hybrid
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
            
            # Log extracted data for debugging
            logger.info(f"Extracted job data from email {email_id}: {json.dumps(job_data, indent=2, default=str)}")
            
            # Create job posting (or get existing if duplicate)
            job, is_new = self._create_job_posting(
                integration=integration,
                email_data=email_data,
                job_data=job_data,
            )
            
            if not job:
                logger.warning(f"Failed to create job from email {email_id}")
                return None
            
            # Only record and update stats for NEW jobs
            if is_new:
                # Record processed email with success
                self._record_processed_email(
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
            else:
                logger.info(f"Returning existing job {job.id} for email {email_id} (duplicate)")
            
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
        
        Phase 7: Protected by circuit breaker for Gemini API.
        
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
            # Phase 7: Use circuit breaker for Gemini API calls
            response = self._call_gemini_with_circuit_breaker(prompt)
            
            if not response:
                return None
            
            # Check if response has content
            if not response.candidates:
                logger.warning(f"Gemini returned no candidates. Prompt feedback: {response.prompt_feedback}")
                return None
            
            # Check for blocked content
            candidate = response.candidates[0]
            if candidate.finish_reason.name == "SAFETY":
                logger.warning(f"Gemini blocked response due to safety. Ratings: {candidate.safety_ratings}")
                return None
            
            # Check if response was truncated
            if candidate.finish_reason.name == "MAX_TOKENS":
                logger.warning("Gemini response was truncated due to max tokens")
            
            # Extract JSON from response
            response_text = response.text.strip() if response.text else ""
            
            if not response_text:
                logger.warning("Gemini returned empty response text")
                return None
            
            logger.debug(f"Gemini response: {response_text[:500]}")
            
            # Strip markdown code blocks if present
            if response_text.startswith("```"):
                # Remove ```json or ``` at start and ``` at end
                response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
                response_text = re.sub(r"\s*```$", "", response_text)
            
            # Try to find JSON object in response
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                return json.loads(json_match.group())
            
            # Try parsing entire response as JSON
            return json.loads(response_text)
        
        except CircuitBreakerError as e:
            logger.warning(f"Circuit breaker open for Gemini: {e}")
            return None
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            logger.warning(f"Response was: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"AI extraction failed: {e}", exc_info=True)
            return None
    
    @gemini_circuit_breaker
    def _call_gemini_with_circuit_breaker(self, prompt: str):
        """
        Call Gemini API with circuit breaker protection.
        
        Phase 7: Wraps Gemini calls for fault tolerance.
        If Gemini fails repeatedly, circuit opens and calls fail fast.
        
        Args:
            prompt: The prompt to send to Gemini
            
        Returns:
            Gemini response or None
        """
        return self.ai_model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,  # Low temperature for factual extraction
                max_output_tokens=4096,  # Increased for complete JSON
                response_mime_type="application/json",  # Force JSON output
            ),
        )
    
    def _create_job_posting(
        self,
        integration: UserEmailIntegration,
        email_data: dict,
        job_data: dict,
    ) -> tuple[Optional[JobPosting], bool]:
        """
        Create a job posting from extracted data.
        
        Deduplication Strategy:
        1. Content-based hash: Detects same job forwarded to multiple recruiters
           - Uses: subject + first 500 chars of body (normalized)
           - Scoped to tenant_id for multi-tenant isolation
        2. Email ID fallback: Prevents duplicates on Inngest retries
        
        Args:
            integration: Source integration
            email_data: Original email data
            job_data: Extracted job details
            
        Returns:
            Tuple of (JobPosting, is_new) - is_new is True if job was created,
            False if existing job was found (duplicate)
        """
        email_id = email_data.get("email_id", "")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        received_at_raw = email_data.get("received_at")
        
        # Generate content-based hash for cross-user deduplication
        # Normalize: lowercase, strip whitespace, take first 500 chars of body
        content_to_hash = f"{subject.lower().strip()}|{body[:500].lower().strip()}"
        content_hash = hashlib.sha256(content_to_hash.encode()).hexdigest()[:16]
        
        # Check for duplicate by content hash WITHIN the same tenant
        # This catches: Same email forwarded to multiple recruiters in tenant
        existing_by_content = JobPosting.query.filter_by(
            platform="email",
            source_tenant_id=integration.tenant_id,
        ).filter(
            JobPosting.external_job_id.like(f"email-%-{content_hash}")
        ).first()
        
        if existing_by_content:
            # Add this recruiter to the additional_source_users list
            self._add_additional_source_user(
                existing_by_content, 
                integration, 
                email_id, 
                received_at_raw
            )
            logger.info(
                f"Duplicate job detected - added user {integration.user_id} to job {existing_by_content.id}: "
                f"subject='{subject[:50]}...'"
            )
            return (existing_by_content, False)
        
        # Check for exact email ID match (same email, same user - Inngest retry)
        external_job_id = f"email-{email_id}-{content_hash}"
        
        existing_by_email = JobPosting.query.filter_by(
            platform="email",
            external_job_id=external_job_id,
        ).first()
        
        if existing_by_email:
            logger.info(f"Job already exists for email {email_id}: job_id={existing_by_email.id}")
            return (existing_by_email, False)
        
        # Parse skills from AI response
        skills = job_data.get("skills", [])
        if not isinstance(skills, list):
            skills = []
        
        # Remove duplicates
        all_skills = list(set(skills))
        
        # Map job type - normalize various formats
        job_type_raw = (job_data.get("job_type") or "").lower().replace("-", "_").replace(" ", "_")
        job_type_map = {
            "full_time": "Full-time",
            "fulltime": "Full-time",
            "part_time": "Part-time",
            "parttime": "Part-time",
            "contract": "Contract",
            "contract_to_hire": "Contract-to-hire",
            "contracttohire": "Contract-to-hire",
        }
        job_type = job_type_map.get(job_type_raw, job_data.get("job_type"))
        
        # Parse is_remote (can be boolean or string)
        is_remote_val = job_data.get("is_remote")
        if isinstance(is_remote_val, bool):
            is_remote = is_remote_val
        elif isinstance(is_remote_val, str):
            is_remote = is_remote_val.lower() in ("true", "yes", "remote")
        else:
            is_remote = False
        
        # Parse email received date
        received_at = email_data.get("received_at")
        if isinstance(received_at, str):
            try:
                received_at = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
            except Exception:
                received_at = datetime.now(timezone.utc)
        elif not received_at:
            received_at = datetime.now(timezone.utc)
        
        # Get skills from AI response or use combined list
        skills = job_data.get("skills")
        if not skills and all_skills:
            skills = all_skills
        elif not skills:
            skills = []
        
        job = JobPosting(
            # Required fields
            external_job_id=external_job_id,
            platform="email",
            title=job_data.get("title") or "Untitled Position",
            company=job_data.get("company") or self._extract_company_from_sender(email_data.get("sender", "")),
            description=job_data.get("description") or email_data.get("body", "")[:2000],
            job_url=f"email://{email_id}",  # Pseudo URL for email-sourced jobs
            
            # Basic Details
            location=job_data.get("location"),
            salary_range=job_data.get("salary_range"),
            salary_min=job_data.get("salary_min"),
            salary_max=job_data.get("salary_max"),
            
            # Job Metadata
            job_type=job_type,
            is_remote=is_remote,
            experience_required=job_data.get("experience_required"),
            experience_min=job_data.get("experience_min"),
            experience_max=job_data.get("experience_max"),
            posted_date=received_at.date() if received_at else datetime.now(timezone.utc).date(),
            
            # Skills & Content
            skills=skills if skills else None,
            snippet=job_data.get("snippet"),
            requirements=job_data.get("requirements"),
            
            # Status
            status="ACTIVE",
            
            # Email Source Fields - these exist in the model
            is_email_sourced=True,
            source_tenant_id=integration.tenant_id,
            sourced_by_user_id=integration.user_id,
            source_email_id=email_id,
            source_email_subject=email_data.get("subject", "")[:500] if email_data.get("subject") else None,
            source_email_sender=email_data.get("sender", "")[:255] if email_data.get("sender") else None,
            source_email_date=received_at,
            
            # Store extra extraction metadata
            raw_metadata={
                "source": "email",
                "confidence_score": job_data.get("confidence_score"),
                "match_reason": email_data.get("match_reason"),
                "integration_id": integration.id,
                "thread_id": email_data.get("thread_id"),
            },
        )
        
        db.session.add(job)
        db.session.flush()  # Get job ID without committing
        
        # Normalize job title and create RoleJobMapping for candidate matching
        self._normalize_and_link_job_role(job)
        
        return (job, True)  # New job created
    
    def _add_additional_source_user(
        self,
        job: JobPosting,
        integration: UserEmailIntegration,
        email_id: str,
        received_at_raw,
    ) -> None:
        """
        Add a recruiter to the additional_source_users list when duplicate is found.
        
        This tracks all recruiters who received the same job email.
        
        Args:
            job: Existing JobPosting to update
            integration: The integration of the new recruiter
            email_id: The email message ID for the new recruiter
            received_at_raw: When the email was received
        """
        # Don't add if it's the same user (Inngest retry)
        if job.sourced_by_user_id == integration.user_id:
            return
        
        # Initialize list if None
        if job.additional_source_users is None:
            job.additional_source_users = []
        
        # Check if user already in list
        existing_user_ids = [u.get("user_id") for u in job.additional_source_users]
        if integration.user_id in existing_user_ids:
            return
        
        # Parse received_at
        if isinstance(received_at_raw, str):
            received_at = received_at_raw
        elif isinstance(received_at_raw, datetime):
            received_at = received_at_raw.isoformat()
        else:
            received_at = datetime.now(timezone.utc).isoformat()
        
        # Add new source user
        job.additional_source_users = job.additional_source_users + [{
            "user_id": integration.user_id,
            "email_id": email_id,
            "received_at": received_at,
            "added_at": datetime.now(timezone.utc).isoformat(),
        }]
        
        db.session.add(job)
        db.session.flush()
    
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
    
    def _normalize_and_link_job_role(self, job: JobPosting) -> None:
        """
        Normalize job title to a GlobalRole and create RoleJobMapping.
        
        This enables automatic job matching: candidates with the same preferred
        role will see this job in their matches.
        
        Args:
            job: The JobPosting to normalize and link
        """
        if not job.title:
            logger.warning(f"Job {job.id} has no title, skipping role normalization")
            return
        
        try:
            from app.services.ai_role_normalization_service import AIRoleNormalizationService
            
            role_service = AIRoleNormalizationService()
            global_role, similarity, method = role_service.normalize_job_title(
                job_title=job.title,
                job_posting_id=job.id
            )
            
            if global_role:
                logger.info(
                    f"Job {job.id} '{job.title}' linked to role '{global_role.name}' "
                    f"(similarity: {similarity:.2%}, method: {method})"
                )
            else:
                logger.warning(f"Failed to normalize job {job.id} title '{job.title}'")
                
        except Exception as e:
            logger.error(f"Error normalizing job {job.id} title: {e}", exc_info=True)
            # Don't fail the entire job creation, just log the error
    
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

# AI Email Parser

## Overview

The AI Email Parser is "Layer 2" of the email processing pipeline. It uses Google Gemini to intelligently parse job requirement emails and extract structured job data that conforms to the existing `JobPosting` model.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AI EMAIL PARSER                                        │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         INPUT: Raw Email                                   │  │
│  │                                                                            │  │
│  │  Subject: Python Developer - Remote - 6 months contract                    │  │
│  │  From: vendor@staffing.com                                                 │  │
│  │  Body:                                                                     │  │
│  │    Hi Team,                                                                │  │
│  │    We have an urgent requirement for a Python Developer.                  │  │
│  │    Location: Remote (EST timezone)                                        │  │
│  │    Duration: 6 months                                                      │  │
│  │    Rate: $70-80/hr on C2C                                                 │  │
│  │    Client: Fortune 500 Financial Services company                        │  │
│  │    Requirements:                                                           │  │
│  │    - 5+ years Python experience                                           │  │
│  │    - FastAPI, Django                                                       │  │
│  │    - AWS experience                                                        │  │
│  │    ...                                                                     │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                          │
│                                       ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    GEMINI AI PROCESSING                                    │  │
│  │                                                                            │  │
│  │  Model: gemini-2.5-flash                                                   │  │
│  │  Prompt: Structured extraction with JSON schema                           │  │
│  │  Validation: Pydantic schema enforcement                                   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                          │
│                                       ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    OUTPUT: Structured Job Data                             │  │
│  │                                                                            │  │
│  │  {                                                                         │  │
│  │    "title": "Python Developer",                                           │  │
│  │    "company": "Fortune 500 Financial Services",                           │  │
│  │    "location": "Remote (EST timezone)",                                   │  │
│  │    "is_remote": true,                                                      │  │
│  │    "job_type": "Contract",                                                │  │
│  │    "salary_range": "$70-80/hr",                                           │  │
│  │    "salary_min": 145600,                                                  │  │
│  │    "salary_max": 166400,                                                  │  │
│  │    "description": "...",                                                   │  │
│  │    "skills": ["Python", "FastAPI", "Django", "AWS"],                     │  │
│  │    "experience_years": 5,                                                  │  │
│  │    "duration": "6 months",                                                │  │
│  │    "is_job_requirement": true,                                            │  │
│  │    "confidence_score": 0.95                                               │  │
│  │  }                                                                         │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## AI Email Parser Service

```python
# app/services/email_job_parser.py
import json
import google.generativeai as genai
from typing import Optional, List
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field, validator
from config.settings import settings
from app.services.email_sync_service import EmailMessage

# Configure Gemini
genai.configure(api_key=settings.google_api_key)


class ParsedJobData(BaseModel):
    """Structured job data extracted from email."""
    
    # Core fields
    title: str = Field(..., description="Job title")
    company: Optional[str] = Field(None, description="Company or client name")
    location: Optional[str] = Field(None, description="Job location")
    is_remote: bool = Field(False, description="Whether job is remote")
    
    # Job details
    job_type: Optional[str] = Field(None, description="Full-time, Contract, Part-time")
    duration: Optional[str] = Field(None, description="Contract duration if applicable")
    
    # Compensation
    salary_range: Optional[str] = Field(None, description="Salary/rate as mentioned")
    salary_min: Optional[int] = Field(None, description="Minimum salary (annualized)")
    salary_max: Optional[int] = Field(None, description="Maximum salary (annualized)")
    
    # Requirements
    description: str = Field(..., description="Full job description")
    skills: List[str] = Field(default_factory=list, description="Required skills")
    experience_years: Optional[int] = Field(None, description="Years of experience required")
    
    # Metadata
    is_job_requirement: bool = Field(True, description="Is this actually a job requirement email?")
    confidence_score: float = Field(0.0, description="AI confidence in parsing (0-1)")
    vendor_info: Optional[str] = Field(None, description="Vendor/recruiter company info")
    
    @validator('job_type')
    def normalize_job_type(cls, v):
        if not v:
            return None
        v_lower = v.lower()
        if 'contract' in v_lower or 'c2c' in v_lower or 'w2' in v_lower:
            return 'Contract'
        elif 'full' in v_lower or 'permanent' in v_lower or 'fte' in v_lower:
            return 'Full-time'
        elif 'part' in v_lower:
            return 'Part-time'
        return v
    
    @validator('skills', pre=True)
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(',')]
        return v or []


class EmailJobParserService:
    """
    AI-powered service to parse job requirement emails into structured data.
    """
    
    SYSTEM_PROMPT = """You are an expert at parsing job requirement emails from recruiters and vendors.
Your task is to extract structured job information from email content.

IMPORTANT RULES:
1. Only extract information that is explicitly stated in the email
2. If information is not present, use null/empty values
3. Normalize job types: "Contract", "Full-time", "Part-time"
4. Extract ALL mentioned skills/technologies
5. If this is NOT a job requirement email (e.g., marketing, newsletter), set is_job_requirement to false
6. Confidence score: 0.9+ for clear job emails, 0.5-0.9 for ambiguous, <0.5 for non-job emails

SALARY/RATE CONVERSION:
- Convert hourly rates to annual: hourly * 2080
- Convert daily rates to annual: daily * 260
- Keep the original format in salary_range field
- Put converted annual values in salary_min/salary_max

OUTPUT FORMAT:
Return ONLY a valid JSON object matching the specified schema. No markdown, no explanation."""

    EXTRACTION_PROMPT = """Parse the following job requirement email and extract structured job data.

EMAIL SUBJECT: {subject}
EMAIL FROM: {sender}
EMAIL BODY:
{body}

Extract the following information as a JSON object:
{{
    "title": "Job title (required)",
    "company": "Company/client name or null",
    "location": "Location or null",
    "is_remote": true/false,
    "job_type": "Contract/Full-time/Part-time or null",
    "duration": "Contract duration or null",
    "salary_range": "Original salary/rate text or null",
    "salary_min": annual_minimum_integer_or_null,
    "salary_max": annual_maximum_integer_or_null,
    "description": "Full job description (combine all relevant info)",
    "skills": ["skill1", "skill2", ...],
    "experience_years": integer_or_null,
    "is_job_requirement": true/false,
    "confidence_score": 0.0-1.0,
    "vendor_info": "Vendor/staffing company info or null"
}}

JSON Output:"""

    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name=settings.gemini_model,  # gemini-2.5-flash
            generation_config={
                "temperature": 0.1,  # Low temperature for consistent extraction
                "top_p": 0.95,
                "max_output_tokens": 2048,
            }
        )
    
    def parse_email(self, email: EmailMessage) -> Optional[ParsedJobData]:
        """
        Parse an email and extract job data using AI.
        
        Args:
            email: EmailMessage object with subject, sender, body
        
        Returns:
            ParsedJobData if successful, None if parsing fails
        """
        # Truncate body if too long (Gemini context limit)
        body = email.body_text[:15000] if email.body_text else ""
        
        if not body and not email.subject:
            return None
        
        prompt = self.EXTRACTION_PROMPT.format(
            subject=email.subject or "(No subject)",
            sender=email.sender or "(Unknown sender)",
            body=body or "(Empty body)"
        )
        
        try:
            response = self.model.generate_content(
                [self.SYSTEM_PROMPT, prompt],
                safety_settings={
                    'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                    'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                    'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
                }
            )
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Handle markdown code blocks
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            # Parse JSON
            data = json.loads(response_text.strip())
            
            # Validate with Pydantic
            parsed = ParsedJobData(**data)
            
            return parsed
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response was: {response.text[:500]}")
            return None
        except Exception as e:
            print(f"Email parsing error: {e}")
            return None
    
    def is_valid_job_email(self, parsed: ParsedJobData) -> bool:
        """
        Determine if parsed data represents a valid job requirement.
        
        Returns:
            True if this should be saved as a job
        """
        # Must be identified as a job requirement
        if not parsed.is_job_requirement:
            return False
        
        # Must have minimum confidence
        if parsed.confidence_score < 0.5:
            return False
        
        # Must have a title
        if not parsed.title or len(parsed.title) < 3:
            return False
        
        # Must have some description
        if not parsed.description or len(parsed.description) < 50:
            return False
        
        return True
    
    def create_job_from_parsed(
        self,
        parsed: ParsedJobData,
        email: EmailMessage,
        tenant_id: int,
        user_id: int
    ) -> 'JobPosting':
        """
        Create a JobPosting model instance from parsed email data.
        
        Args:
            parsed: ParsedJobData from AI parsing
            email: Original EmailMessage
            tenant_id: Tenant ID for job scoping
            user_id: User ID who sourced this job
        
        Returns:
            JobPosting instance (not yet committed)
        """
        from app.models import JobPosting
        from datetime import datetime
        
        job = JobPosting(
            # Standard job fields
            title=parsed.title,
            company=parsed.company,
            location=parsed.location,
            is_remote=parsed.is_remote,
            job_type=parsed.job_type,
            salary_range=parsed.salary_range,
            salary_min=parsed.salary_min,
            salary_max=parsed.salary_max,
            description=parsed.description,
            skills=parsed.skills,
            
            # Source tracking
            platform='email',  # Indicates email-sourced job
            status='ACTIVE',
            posted_date=email.received_at.date() if email.received_at else datetime.utcnow().date(),
            
            # Email-specific fields
            is_email_sourced=True,
            source_tenant_id=tenant_id,
            sourced_by_user_id=user_id,
            source_email_id=email.message_id,
            source_email_subject=email.subject[:500] if email.subject else None,
            source_email_sender=email.sender[:255] if email.sender else None,
            source_email_date=email.received_at,
        )
        
        return job


class EmailParsingResult:
    """Result of email parsing attempt."""
    
    def __init__(
        self,
        success: bool,
        parsed_data: Optional[ParsedJobData] = None,
        error: Optional[str] = None,
        skip_reason: Optional[str] = None
    ):
        self.success = success
        self.parsed_data = parsed_data
        self.error = error
        self.skip_reason = skip_reason
    
    @property
    def should_create_job(self) -> bool:
        return self.success and self.parsed_data is not None
    
    @classmethod
    def job_created(cls, parsed: ParsedJobData) -> 'EmailParsingResult':
        return cls(success=True, parsed_data=parsed)
    
    @classmethod
    def not_a_job(cls) -> 'EmailParsingResult':
        return cls(success=False, skip_reason="Not identified as a job requirement")
    
    @classmethod
    def low_confidence(cls, score: float) -> 'EmailParsingResult':
        return cls(success=False, skip_reason=f"Low confidence score: {score}")
    
    @classmethod
    def parsing_failed(cls, error: str) -> 'EmailParsingResult':
        return cls(success=False, error=error)
```

## Parsing Examples

### Example 1: Clear Job Requirement

**Input Email:**
```
Subject: Urgent - Senior Python Developer - NYC/Remote - $160K
From: john@staffingcompany.com

Hi Team,

Hope you're doing well. We have an urgent requirement with our direct client.

Position: Senior Python Developer
Location: New York, NY (Hybrid - 2 days onsite)
Salary: $150,000 - $170,000/year
Type: Full-time/Permanent

Requirements:
- 7+ years of Python development
- Experience with FastAPI or Django
- PostgreSQL, Redis
- AWS (EC2, S3, Lambda)
- Strong problem-solving skills

If you have matching candidates, please send their updated resumes.

Thanks,
John Smith
ABC Staffing Inc.
```

**Parsed Output:**
```json
{
    "title": "Senior Python Developer",
    "company": "Direct Client (via ABC Staffing Inc.)",
    "location": "New York, NY (Hybrid - 2 days onsite)",
    "is_remote": false,
    "job_type": "Full-time",
    "duration": null,
    "salary_range": "$150,000 - $170,000/year",
    "salary_min": 150000,
    "salary_max": 170000,
    "description": "Senior Python Developer position in NYC. Hybrid role with 2 days onsite. Requirements include 7+ years Python development, FastAPI/Django, PostgreSQL, Redis, AWS (EC2, S3, Lambda), strong problem-solving skills.",
    "skills": ["Python", "FastAPI", "Django", "PostgreSQL", "Redis", "AWS", "EC2", "S3", "Lambda"],
    "experience_years": 7,
    "is_job_requirement": true,
    "confidence_score": 0.95,
    "vendor_info": "ABC Staffing Inc."
}
```

### Example 2: Contract Position with Hourly Rate

**Input Email:**
```
Subject: React Developer - 6 month contract - Remote
From: recruiter@techstaffing.io

We need a React Developer for a 6-month contract.

Rate: $65-75/hr on W2
Location: 100% Remote
Start: ASAP

Must have:
- React, TypeScript
- Redux or MobX
- REST APIs
- 4+ years frontend experience

Send resumes to jobs@techstaffing.io
```

**Parsed Output:**
```json
{
    "title": "React Developer",
    "company": null,
    "location": "Remote",
    "is_remote": true,
    "job_type": "Contract",
    "duration": "6 months",
    "salary_range": "$65-75/hr on W2",
    "salary_min": 135200,
    "salary_max": 156000,
    "description": "React Developer needed for 6-month contract. 100% remote position. Must have React, TypeScript, Redux/MobX, REST APIs, 4+ years frontend experience. Start ASAP.",
    "skills": ["React", "TypeScript", "Redux", "MobX", "REST APIs", "Frontend"],
    "experience_years": 4,
    "is_job_requirement": true,
    "confidence_score": 0.92,
    "vendor_info": "techstaffing.io"
}
```

### Example 3: Not a Job Email (Newsletter)

**Input Email:**
```
Subject: Weekly Tech News - Python Updates
From: newsletter@technews.com

This week in Python:
- Python 3.13 beta released
- New typing features
- Performance improvements

Click here to read more...
Unsubscribe
```

**Parsed Output:**
```json
{
    "title": "Weekly Tech News",
    "company": null,
    "location": null,
    "is_remote": false,
    "job_type": null,
    "duration": null,
    "salary_range": null,
    "salary_min": null,
    "salary_max": null,
    "description": "Newsletter about Python updates",
    "skills": ["Python"],
    "experience_years": null,
    "is_job_requirement": false,
    "confidence_score": 0.15,
    "vendor_info": null
}
```

→ **Result**: Skipped (not a job requirement)

## Error Handling

```python
class ParsingError(Exception):
    """Base exception for parsing errors."""
    pass

class AIResponseError(ParsingError):
    """AI model returned invalid response."""
    pass

class ValidationError(ParsingError):
    """Parsed data failed validation."""
    pass
```

## Rate Limiting

- Gemini API: 60 requests/minute (free tier), 1000+ RPM (paid)
- Implementation uses sequential processing within each sync batch
- Consider adding Redis-based rate limiting for high-volume scenarios

## Quality Metrics

Track parsing quality over time:

```python
# In ProcessedEmail model, could add:
parsing_confidence = db.Column(db.Float)
parsing_model = db.Column(db.String(50))  # e.g., "gemini-2.5-flash"
was_job_created = db.Column(db.Boolean)
```

## Dependencies

```txt
# requirements.txt additions
google-generativeai>=0.3.0
pydantic>=2.0.0
```

"""
Simple Resume Parser Service
Direct text extraction without complex schemas
"""
import re
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from config.settings import settings

logger = logging.getLogger(__name__)

# Constants - configurable via environment
MAX_TEXT_LENGTH = 100000  # ~100KB max for AI processing
MAX_SKILLS = 50


class SimpleResumeParserService:
    """
    Simple resume parser using direct text extraction
    """
    
    def __init__(self):
        """Initialize parser with AI provider"""
        self.ai_provider = settings.ai_parsing_provider
        self._configure_ai()
    
    def _configure_ai(self):
        """Configure AI provider (Gemini via LangChain)"""
        if self.ai_provider == 'gemini':
            api_key = settings.google_api_key
            model_name = settings.gemini_model
            
            # Validate API key
            if not api_key or api_key.strip() == '':
                raise ValueError(
                    "GOOGLE_API_KEY not configured. "
                    "Set it in environment variables for resume parsing to work."
                )
            
            self.ai_model = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.1,
                max_output_tokens=16384,  # Increased for full work experience descriptions
                timeout=180,
                max_retries=2,
            )
            logger.info(f"Configured LangChain Gemini model: {model_name}")
        else:
            raise ValueError(f"Unsupported AI provider: {self.ai_provider}")
    
    def parse_resume(self, text: str, file_type: str = 'pdf') -> Dict[str, Any]:
        """
        Main parsing method - simple approach
        """
        start_time = time.time()
        original_length = len(text)
        
        # Truncate very large texts to prevent token limit issues
        if len(text) > MAX_TEXT_LENGTH:
            logger.warning(
                f"Resume text truncated from {len(text)} to {MAX_TEXT_LENGTH} chars"
            )
            text = text[:MAX_TEXT_LENGTH]
        
        logger.info(f"Parsing resume, text length: {len(text)} characters")
        
        # Extract using simple prompt
        result = self._extract_with_simple_prompt(text)
        
        # Post-process and validate extracted data
        result = self._validate_and_clean(result)
        
        # Add metadata
        elapsed = time.time() - start_time
        result['parsed_at'] = datetime.utcnow().isoformat()
        result['parser_version'] = '2.2.0'  # Full work experience descriptions
        result['ai_provider'] = self.ai_provider
        result['parsing_duration_seconds'] = round(elapsed, 2)
        result['original_text_length'] = original_length
        result['was_truncated'] = original_length > MAX_TEXT_LENGTH
        
        logger.info(
            f"Resume parsing completed in {elapsed:.2f}s, "
            f"name={result.get('full_name')}, email={result.get('email')}"
        )
        
        return result
    
    def _validate_and_clean(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean parsed data to ensure quality
        """
        # Validate and clean email
        email = parsed.get('email')
        if email:
            parsed['email'] = self._validate_email(email)
        
        # Validate and clean phone
        phone = parsed.get('phone')
        if phone:
            parsed['phone'] = self._validate_phone(phone)
        
        # Ensure total_experience_years is a number
        exp_years = parsed.get('total_experience_years')
        if exp_years is not None:
            try:
                parsed['total_experience_years'] = float(exp_years)
            except (ValueError, TypeError):
                logger.warning(f"Invalid total_experience_years: {exp_years}")
                parsed['total_experience_years'] = None
        
        # Clean work experience dates and duration
        work_exp = parsed.get('work_experience', [])
        if isinstance(work_exp, list):
            for exp in work_exp:
                if isinstance(exp, dict):
                    # Ensure duration_months is int or None
                    duration = exp.get('duration_months')
                    if duration is not None:
                        try:
                            exp['duration_months'] = int(duration)
                        except (ValueError, TypeError):
                            exp['duration_months'] = None
                    
                    # Ensure is_current is boolean
                    is_current = exp.get('is_current')
                    if isinstance(is_current, str):
                        exp['is_current'] = is_current.lower() in ('true', 'yes', '1')
                    elif not isinstance(is_current, bool):
                        exp['is_current'] = False
        
        # Clean education graduation years
        education = parsed.get('education', [])
        if isinstance(education, list):
            for edu in education:
                if isinstance(edu, dict):
                    grad_year = edu.get('graduation_year')
                    if grad_year is not None:
                        try:
                            year = int(grad_year)
                            # Sanity check - graduation year should be reasonable
                            if 1950 <= year <= 2030:
                                edu['graduation_year'] = year
                            else:
                                edu['graduation_year'] = None
                        except (ValueError, TypeError):
                            edu['graduation_year'] = None
        
        # Limit skills array
        skills = parsed.get('skills', [])
        if isinstance(skills, list) and len(skills) > MAX_SKILLS:
            parsed['skills'] = skills[:MAX_SKILLS]
        
        return parsed
    
    def _validate_email(self, email: Optional[str]) -> Optional[str]:
        """Validate and normalize email address"""
        if not email or not isinstance(email, str):
            return None
        
        email = email.strip().lower()
        
        # Basic email pattern check
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            logger.warning(f"Invalid email parsed and rejected: {email}")
            return None
        
        return email
    
    def _validate_phone(self, phone: Optional[str]) -> Optional[str]:
        """Validate and normalize phone number"""
        if not phone or not isinstance(phone, str):
            return None
        
        # Extract digits only
        digits = re.sub(r'\D', '', phone)
        
        # Phone should have 10-15 digits (international format)
        if len(digits) < 10 or len(digits) > 15:
            logger.warning(f"Invalid phone number parsed and rejected: {phone}")
            return None
        
        # Check it's not a year (common AI mistake)
        if len(digits) == 4 and digits.startswith(('19', '20')):
            logger.warning(f"Phone looks like a year, rejected: {phone}")
            return None
        
        return phone
    
    def _extract_with_simple_prompt(self, text: str) -> Dict[str, Any]:
        """
        Use simple prompt without structured output
        """
        try:
            prompt = f"""Extract information from this resume and return it as a JSON object.

CRITICAL RULES:
1. Read the resume text carefully - extract actual information, don't guess
2. Name should be from the top of the resume (usually in format "First Last" or "First Middle Last")
3. Phone should be an actual phone number with 10+ digits (not a year like "2023" or "2024")
4. Email must contain @ symbol and be a valid email format
5. Location should be a city/state or city/country (not a skill or tool name)
6. Current title is the job title right below the name or the most recent job
7. Professional summary: write a concise 3-4 sentence professional overview of the candidate
8. Extract ALL work experiences with company names, titles, dates, and locations
9. Extract ALL education entries
10. Extract ALL skills mentioned in the resume
11. certifications must be an array of simple strings like ["AWS Certified", "Scrum Master"] - NOT objects with name/year fields

IMPORTANT FOR WORK EXPERIENCE DESCRIPTIONS:
- Include ALL bullet points and responsibilities from the resume for each job
- Preserve the full detail of each responsibility - do NOT summarize or truncate
- Each description should be a comprehensive list of all duties mentioned
- Use "\\n" to separate bullet points within the description string
- This is critical for recruiter review - they need the full details

RESUME TEXT:
{text}

Return ONLY a valid JSON object in this exact format (no markdown, no explanation, no trailing commas):
{{
  "full_name": "",
  "email": "",
  "phone": "",
  "location": "",
  "linkedin_url": "",
  "current_title": "",
  "professional_summary": "",
  "total_experience_years": null,
  "skills": [],
  "education": [
    {{
      "degree": "",
      "field_of_study": "",
      "institution": "",
      "graduation_year": null,
      "gpa": null
    }}
  ],
  "work_experience": [
    {{
      "title": "",
      "company": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "is_current": false,
      "description": "Include ALL bullet points and responsibilities here, separated by newlines. Do NOT summarize.",
      "duration_months": null
    }}
  ],
  "certifications": [],
  "languages": [],
  "visa_type": null
}}"""
            
            response = self.ai_model.invoke([HumanMessage(content=prompt)])
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            logger.debug(f"AI response length: {len(response_text)} characters")
            
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if not json_match:
                logger.error("No JSON found in AI response")
                logger.debug(f"Response preview: {response_text[:500]}...")
                return self._empty_result()
            
            json_str = json_match.group(0)
            json_str = re.sub(r'```json\s*|\s*```', '', json_str)
            
            try:
                parsed = json.loads(json_str)
                logger.debug("Successfully parsed JSON from AI response")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed, attempting repair: {e}")
                
                # Attempt to repair common JSON issues
                parsed = self._repair_and_parse_json(json_str)
                
                if parsed is None:
                    logger.error("JSON repair failed, returning empty result")
                    return self._empty_result()
                
                logger.info("Successfully repaired and parsed JSON")
            
            logger.info(
                f"Parsed: name={parsed.get('full_name')}, "
                f"email={parsed.get('email')}, "
                f"work_exp={len(parsed.get('work_experience', []))}, "
                f"skills={len(parsed.get('skills', []))}"
            )
            
            # Ensure certifications are strings, not dicts
            certs = parsed.get('certifications', [])
            if isinstance(certs, list):
                cert_strings = []
                for cert in certs:
                    if isinstance(cert, dict):
                        cert_name = cert.get('name', '')
                        if cert_name:
                            cert_strings.append(cert_name)
                        else:
                            cert_strings.append(str(cert))
                    elif isinstance(cert, str):
                        cert_strings.append(cert)
                parsed['certifications'] = cert_strings
            
            return parsed
                
        except Exception as e:
            logger.error(f"Resume extraction failed: {e}", exc_info=True)
            return self._empty_result()
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'full_name': None,
            'email': None,
            'phone': None,
            'location': None,
            'linkedin_url': None,
            'current_title': None,
            'professional_summary': None,
            'total_experience_years': None,
            'skills': [],
            'education': [],
            'work_experience': [],
            'certifications': [],
            'languages': [],
            'visa_type': None,
            'preferred_locations': [],
        }
    
    def _repair_and_parse_json(self, json_str: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to repair malformed JSON from AI responses.
        Common issues: truncated responses, missing brackets, unescaped quotes
        """
        # Try multiple repair strategies in order of likelihood
        strategies = [
            ('trailing_commas', self._fix_trailing_commas),
            ('truncated', self._fix_truncated_json),
            ('unescaped_quotes', self._fix_unescaped_quotes),
            ('partial_extract', self._extract_partial_json),
        ]
        
        for name, strategy in strategies:
            try:
                repaired = strategy(json_str)
                if repaired:
                    result = json.loads(repaired)
                    logger.info(f"JSON repair successful with strategy: {name}")
                    return result
            except (json.JSONDecodeError, Exception) as e:
                logger.debug(f"Repair strategy '{name}' failed: {e}")
                continue
        
        return None
    
    def _fix_truncated_json(self, json_str: str) -> Optional[str]:
        """Fix JSON that was truncated mid-response"""
        # Count opening/closing brackets
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        # Add missing closing brackets
        repaired = json_str.rstrip()
        
        # Remove trailing incomplete elements
        # Common patterns: trailing comma, incomplete string, incomplete object
        patterns_to_remove = [
            r',\s*$',           # Trailing comma
            r',\s*"[^"]*$',     # Incomplete key
            r':\s*"[^"]*$',     # Incomplete string value
            r':\s*$',           # Incomplete value
        ]
        
        for pattern in patterns_to_remove:
            repaired = re.sub(pattern, '', repaired)
        
        # Close any unclosed strings
        quote_count = repaired.count('"') - repaired.count('\\"')
        if quote_count % 2 == 1:
            repaired += '"'
        
        # Add missing brackets in correct order (most recent first)
        while close_brackets < open_brackets:
            repaired += ']'
            close_brackets += 1
        
        while close_braces < open_braces:
            repaired += '}'
            close_braces += 1
        
        return repaired
    
    def _fix_unescaped_quotes(self, json_str: str) -> Optional[str]:
        """Fix unescaped quotes inside string values"""
        result = []
        in_string = False
        escape_next = False
        
        for i, char in enumerate(json_str):
            if escape_next:
                result.append(char)
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                result.append(char)
                continue
            
            if char == '"':
                if not in_string:
                    in_string = True
                    result.append(char)
                else:
                    # Look ahead to see if this closes the string
                    remaining = json_str[i+1:i+10].lstrip()
                    if remaining and remaining[0] in ':,}]\n':
                        in_string = False
                        result.append(char)
                    else:
                        # This might be an internal quote - escape it
                        result.append('\\"')
            else:
                result.append(char)
        
        return ''.join(result)
    
    def _fix_trailing_commas(self, json_str: str) -> Optional[str]:
        """Remove trailing commas before closing brackets"""
        # Remove trailing commas before ] or }
        repaired = re.sub(r',(\s*[}\]])', r'\1', json_str)
        return repaired
    
    def _extract_partial_json(self, json_str: str) -> Optional[str]:
        """
        Extract the main fields even if the full JSON is broken.
        Creates a valid JSON with at least the basic contact info.
        """
        result = self._empty_result()
        
        # Extract basic fields using regex
        patterns = {
            'full_name': r'"full_name"\s*:\s*"([^"]*)"',
            'email': r'"email"\s*:\s*"([^"]*)"',
            'phone': r'"phone"\s*:\s*"([^"]*)"',
            'location': r'"location"\s*:\s*"([^"]*)"',
            'linkedin_url': r'"linkedin_url"\s*:\s*"([^"]*)"',
            'current_title': r'"current_title"\s*:\s*"([^"]*)"',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, json_str)
            if match:
                value = match.group(1)
                if value:  # Only set non-empty values
                    result[field] = value
                    logger.debug(f"Partial extract - {field}: {value[:50]}...")
        
        # Extract professional summary (can be multiline)
        summary_match = re.search(
            r'"professional_summary"\s*:\s*"((?:[^"\\]|\\.)*)"',
            json_str,
            re.DOTALL
        )
        if summary_match:
            result['professional_summary'] = summary_match.group(1).replace('\\n', '\n')
        
        # Extract skills array
        skills_match = re.search(
            r'"skills"\s*:\s*\[((?:[^\[\]]|\[(?:[^\[\]]|\[[^\[\]]*\])*\])*)\]',
            json_str
        )
        if skills_match:
            skills_str = skills_match.group(1)
            skill_items = re.findall(r'"([^"]+)"', skills_str)
            result['skills'] = skill_items[:MAX_SKILLS]
        
        # Try to extract work experience array
        work_exp_match = re.search(
            r'"work_experience"\s*:\s*\[(.*?)\](?=\s*,\s*"|\s*})',
            json_str,
            re.DOTALL
        )
        if work_exp_match:
            try:
                # Try to parse individual work experiences
                work_str = '[' + work_exp_match.group(1) + ']'
                # Fix common issues in this substring
                work_str = re.sub(r',(\s*[}\]])', r'\1', work_str)
                work_exp = json.loads(work_str)
                if isinstance(work_exp, list):
                    result['work_experience'] = work_exp
            except json.JSONDecodeError:
                pass  # Keep empty work_experience
        
        # Try to extract education array
        edu_match = re.search(
            r'"education"\s*:\s*\[(.*?)\](?=\s*,\s*"|\s*})',
            json_str,
            re.DOTALL
        )
        if edu_match:
            try:
                edu_str = '[' + edu_match.group(1) + ']'
                edu_str = re.sub(r',(\s*[}\]])', r'\1', edu_str)
                education = json.loads(edu_str)
                if isinstance(education, list):
                    result['education'] = education
            except json.JSONDecodeError:
                pass  # Keep empty education
        
        # Only return if we got at least a name or email
        if result.get('full_name') or result.get('email'):
            logger.info(
                f"Partial extraction recovered: name={result.get('full_name')}, "
                f"email={result.get('email')}, "
                f"work_exp={len(result.get('work_experience', []))}"
            )
            return json.dumps(result)
        
        return None

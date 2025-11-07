"""
Resume Parser Service
Hybrid parsing using spaCy (fast extraction) + Gemini AI with LangChain (complex analysis)
"""
import os
import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import spacy
from spacy.matcher import Matcher
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage


# Pydantic schemas for structured output
class PersonalInfo(BaseModel):
    """Personal contact information"""
    full_name: Optional[str] = Field(None, description="Full name from top of resume (usually CAPS)")
    email: Optional[str] = Field(None, description="Email address with @ symbol")
    phone: Optional[str] = Field(None, description="Phone number in numeric format")
    location: Optional[str] = Field(None, description="City, State from contact section")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    portfolio_url: Optional[str] = Field(None, description="Portfolio or personal website URL")


class EducationEntry(BaseModel):
    """Education details"""
    degree: str = Field(description="Degree name (Bachelor of, Master of, etc.)")
    field_of_study: Optional[str] = Field(None, description="Major or field of study")
    institution: str = Field(description="University or institution name")
    graduation_year: Optional[int] = Field(None, description="Graduation year")
    gpa: Optional[float] = Field(None, description="GPA if mentioned")


class WorkExperience(BaseModel):
    """Work experience entry"""
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    location: Optional[str] = Field(None, description="Job location")
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM format or null if current")
    is_current: bool = Field(False, description="Whether this is current position")
    description: Optional[str] = Field(None, description="Job description and achievements")
    duration_months: Optional[int] = Field(None, description="Duration in months")


class ResumeData(BaseModel):
    """Complete resume data structure"""
    personal_info: PersonalInfo
    professional_summary: Optional[str] = Field(None, description="Professional summary or objective")
    current_title: Optional[str] = Field(None, description="Most recent job title")
    total_experience_years: Optional[int] = Field(None, description="Total years of experience")
    skills: List[str] = Field(default_factory=list, description="List of all skills")
    education: List[EducationEntry] = Field(default_factory=list, description="Education history")
    work_experience: List[WorkExperience] = Field(default_factory=list, description="Work experience history")
    certifications: List[str] = Field(default_factory=list, description="Certifications")
    languages: List[str] = Field(default_factory=list, description="Languages spoken")
    notice_period: Optional[str] = Field(None, description="Notice period")
    expected_salary: Optional[str] = Field(None, description="Expected salary")
    preferred_locations: List[str] = Field(default_factory=list, description="Preferred work locations")


class ResumeParserService:
    """
    Hybrid resume parser combining spaCy NER and Gemini AI
    """
    
    def __init__(self):
        """Initialize parser with spaCy model and AI provider"""
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' not found. "
                "Install with: python -m spacy download en_core_web_sm"
            )
        
        # Configure AI provider
        self.ai_provider = os.getenv('AI_PARSING_PROVIDER', 'gemini')
        self._configure_ai()
        
        # Initialize matcher for pattern matching
        self.matcher = Matcher(self.nlp.vocab)
        self._setup_patterns()
    
    def _configure_ai(self):
        """Configure AI provider (Gemini via LangChain or OpenAI)"""
        if self.ai_provider == 'gemini':
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY not found in environment. "
                    "Get one from https://ai.google.dev/"
                )
            if api_key == 'your_gemini_api_key_here' or api_key.startswith('your_'):
                raise ValueError(
                    "GEMINI_API_KEY is not configured properly. "
                    "Please set a valid API key in .env file. "
                    "Get one from https://makersuite.google.com/app/apikey"
                )
            
            # Get model from environment or use default
            model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            
            # Initialize LangChain ChatGoogleGenerativeAI with timeout and retry config
            self.ai_model = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.1,
                max_output_tokens=8192,
                timeout=60,  # 60 second timeout
                max_retries=2,  # Retry up to 2 times
            )
            print(f"[DEBUG] Configured LangChain Gemini model: {model_name}")
        elif self.ai_provider == 'openai':
            # OpenAI configuration (for future)
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            # Will implement OpenAI client when needed
            self.ai_model = None
        else:
            raise ValueError(f"Unsupported AI provider: {self.ai_provider}")
    
    def _setup_patterns(self):
        """Setup spaCy patterns for common resume sections"""
        # Email pattern
        email_pattern = [{"LIKE_EMAIL": True}]
        self.matcher.add("EMAIL", [email_pattern])
        
        # Phone pattern (various formats)
        phone_patterns = [
            [{"TEXT": {"REGEX": r"^\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}$"}}],
        ]
        self.matcher.add("PHONE", phone_patterns)
        
        # URL pattern
        url_pattern = [{"LIKE_URL": True}]
        self.matcher.add("URL", [url_pattern])
    
    def parse_resume(self, text: str, file_type: str = 'pdf') -> Dict[str, Any]:
        """
        Main parsing method - hybrid approach
        
        Args:
            text: Extracted text from resume
            file_type: 'pdf' or 'docx'
        
        Returns:
            Dictionary with parsed resume data
        """
        # Stage 1: Quick extraction with spaCy
        spacy_results = self._parse_with_spacy(text)
        
        # Stage 2: Enhanced extraction with AI
        ai_results = self._parse_with_ai(text, spacy_results)
        
        # Stage 3: Merge and validate results
        final_results = self._merge_results(spacy_results, ai_results)
        
        # Add metadata
        final_results['parsed_at'] = datetime.utcnow().isoformat()
        final_results['parser_version'] = '1.0.0'
        final_results['ai_provider'] = self.ai_provider
        
        return final_results
    
    def _parse_with_spacy(self, text: str) -> Dict[str, Any]:
        """
        Fast extraction using spaCy NER and pattern matching
        
        Returns:
            Dictionary with extracted data and confidence scores
        """
        doc = self.nlp(text)
        results = {
            'names': [],
            'locations': [],
            'organizations': [],
            'emails': [],
            'phones': [],
            'urls': [],
            'skills': [],
            'sections': {}
        }
        
        # Extract named entities
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                results['names'].append(ent.text)
            elif ent.label_ == "GPE" or ent.label_ == "LOC":
                results['locations'].append(ent.text)
            elif ent.label_ == "ORG":
                results['organizations'].append(ent.text)
        
        # Extract contact info using patterns
        matches = self.matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            rule_id = self.nlp.vocab.strings[match_id]
            
            if rule_id == "EMAIL":
                results['emails'].append(span.text)
            elif rule_id == "PHONE":
                results['phones'].append(span.text)
            elif rule_id == "URL":
                results['urls'].append(span.text)
        
        # Extract contact info with regex (backup)
        results['emails'].extend(self._extract_emails(text))
        results['phones'].extend(self._extract_phones(text))
        results['urls'].extend(self._extract_urls(text))
        
        # Identify sections
        results['sections'] = self._identify_sections(text)
        
        # Deduplicate
        results['emails'] = list(set(results['emails']))
        results['phones'] = list(set(results['phones']))
        results['urls'] = list(set(results['urls']))
        results['names'] = list(set(results['names']))
        results['locations'] = list(set(results['locations']))
        
        return results
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses using regex"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, text)
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers using regex"""
        phone_patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        ]
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))
        return phones
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs using regex"""
        url_pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
        urls = re.findall(url_pattern, text)
        
        # Also look for linkedin/github without http
        social_pattern = r'(?:linkedin\.com/in/|github\.com/)[\w-]+'
        social = re.findall(social_pattern, text, re.IGNORECASE)
        urls.extend([f"https://{s}" for s in social])
        
        return urls
    
    def _identify_sections(self, text: str) -> Dict[str, str]:
        """
        Identify major resume sections
        
        Returns:
            Dictionary mapping section names to their text content
        """
        sections = {}
        
        # Common section headers
        section_patterns = {
            'education': r'(?i)(education|academic|qualification)',
            'experience': r'(?i)(experience|employment|work history|professional)',
            'skills': r'(?i)(skills|technical|competencies|expertise)',
            'summary': r'(?i)(summary|objective|profile|about)',
            'certifications': r'(?i)(certifications|certificates|licenses)',
            'projects': r'(?i)(projects|portfolio)',
        }
        
        lines = text.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            # Check if line is a section header
            matched_section = None
            for section_name, pattern in section_patterns.items():
                if re.search(pattern, line) and len(line) < 50:
                    matched_section = section_name
                    break
            
            if matched_section:
                # Save previous section
                if current_section and section_content:
                    sections[current_section] = '\n'.join(section_content)
                
                # Start new section
                current_section = matched_section
                section_content = []
            elif current_section:
                section_content.append(line)
        
        # Save last section
        if current_section and section_content:
            sections[current_section] = '\n'.join(section_content)
        
        return sections
    
    def _parse_with_ai(self, text: str, spacy_data: Dict) -> Dict[str, Any]:
        """
        Enhanced parsing using Gemini AI
        
        Args:
            text: Full resume text
            spacy_data: Results from spaCy parsing
        
        Returns:
            Dictionary with AI-extracted structured data
        """
        if self.ai_provider == 'gemini':
            return self._parse_with_gemini(text, spacy_data)
        elif self.ai_provider == 'openai':
            return self._parse_with_openai(text, spacy_data)
        else:
            return {}
    
    def _parse_with_gemini(self, text: str, context: Dict) -> Dict[str, Any]:
        """
        Use LangChain + Gemini for structured extraction with timeout handling
        """
        try:
            print(f"[DEBUG] Calling Gemini API via LangChain...")
            print(f"[DEBUG] Resume text length: {len(text)} characters")
            
            # Limit text to prevent timeouts
            max_text_length = 6000  # 6000 chars for reliable processing
            truncated_text = text[:max_text_length]
            if len(text) > max_text_length:
                print(f"[DEBUG] Resume text truncated from {len(text)} to {max_text_length} characters")
            
            # Create structured output model
            structured_llm = self.ai_model.with_structured_output(ResumeData)
            
            # Build extraction prompt
            prompt = f"""Extract ALL information from this resume and return structured data.

CRITICAL INSTRUCTIONS:
1. Extract the candidate's ACTUAL name from the very top of the resume (usually in CAPS)
2. Extract REAL email address (must contain @) - use null if not found
3. Extract REAL phone number (10+ digits, NOT a year like 2024) - use null if not found
4. Extract ACTUAL city/location (e.g., "Houston, TX", "New York, NY") from contact section ONLY - use null if not found
5. Extract ALL work experiences with COMPLETE descriptions
6. Extract ALL education entries from EDUCATION section
7. Extract ALL technical and soft skills
8. Use null for missing values - do NOT make up data

STRICT VALIDATION RULES:
- full_name: Must be a person's name from TOP of resume (NOT a date, year, or tool name)
- email: Must contain @ symbol (e.g., name@domain.com)
- phone: Must be 10+ digits in phone format (NOT years like "2020", "2024")
- location: Must be City, State format (e.g., "Houston, TX") from CONTACT section at top
  * DO NOT extract technical acronyms like "ROC", "AUC", "SQL", "API"
  * DO NOT extract company names or organization names
  * DO NOT extract single words or abbreviations
  * If no city/state is found in contact section, use null

RESUME TEXT:
{truncated_text}

OUTPUT REQUIREMENTS:
- education: Array of ALL degrees with institutions and graduation years
- work_experience: Array of ALL jobs with title, company, dates, and full descriptions
- skills: Array of ALL skills mentioned (programming, tools, frameworks)
- certifications: Array of certifications if any
"""
            
            # Invoke with structured output
            result: ResumeData = structured_llm.invoke([HumanMessage(content=prompt)])
            
            print(f"[DEBUG] Structured data extracted successfully")
            print(f"[DEBUG] Extracted name: {result.personal_info.full_name}")
            print(f"[DEBUG] Extracted email: {result.personal_info.email}")
            print(f"[DEBUG] Extracted phone: {result.personal_info.phone}")
            print(f"[DEBUG] Extracted location: {result.personal_info.location}")
            print(f"[DEBUG] Extracted {len(result.skills)} skills")
            print(f"[DEBUG] Extracted {len(result.work_experience)} work experiences")
            print(f"[DEBUG] Extracted {len(result.education)} education entries")
            
            # Convert Pydantic model to dict
            return result.model_dump()
        
        except Exception as e:
            error_message = str(e)
            print(f"[ERROR] LangChain Gemini parsing error: {error_message}")
            
            # Check if it's a timeout error
            if 'timeout' in error_message.lower() or 'deadline' in error_message.lower() or '504' in error_message:
                print(f"[WARNING] Gemini API timed out. Falling back to spaCy-only parsing.")
            
            import traceback
            traceback.print_exc()
            return {}
    
    def _parse_with_openai(self, text: str, context: Dict) -> Dict[str, Any]:
        """
        Use OpenAI GPT-4 for structured extraction (future implementation)
        """
        # Placeholder for OpenAI implementation
        # Will add when switching to OpenAI
        return {}
    
    def _merge_results(self, spacy_data: Dict, ai_data: Dict) -> Dict[str, Any]:
        """
        Merge spaCy and AI results with confidence scoring
        
        Strategy:
        - Prefer AI results for complex fields (structured data)
        - Use spaCy for quick validation
        - Calculate confidence scores
        """
        merged = {
            'full_name': None,
            'email': None,
            'phone': None,
            'location': None,
            'linkedin_url': None,
            'portfolio_url': None,
            'current_title': None,
            'total_experience_years': None,
            'professional_summary': None,
            'skills': [],
            'education': [],
            'work_experience': [],
            'certifications': [],
            'languages': [],
            'notice_period': None,
            'expected_salary': None,
            'preferred_locations': [],
            'confidence_scores': {}
        }
        
        # Get personal info from AI (preferred)
        personal_info = ai_data.get('personal_info', {})
        
        # Validate full_name - should not be a date, number, or single word
        ai_name = personal_info.get('full_name')
        if ai_name:
            # Check if it looks like a valid name (not a date, not just numbers)
            import re
            # Reject if it matches date patterns like "Mar 2019", "2020", etc.
            if re.search(r'\d{4}', ai_name) or len(ai_name.split()) < 2:
                print(f"[WARNING] Invalid name from AI: '{ai_name}', using spaCy fallback")
                ai_name = None
        
        merged['full_name'] = ai_name or (spacy_data['names'][0] if spacy_data['names'] else None)
        
        # Validate email - must contain @ symbol
        ai_email = personal_info.get('email')
        if ai_email and '@' not in ai_email:
            print(f"[WARNING] Invalid email from AI: '{ai_email}', using spaCy fallback")
            ai_email = None
        merged['email'] = ai_email or (spacy_data['emails'][0] if spacy_data['emails'] else None)
        
        # Validate phone - must be mostly numeric and reasonable length
        ai_phone = personal_info.get('phone')
        if ai_phone:
            # Remove common phone formatting characters
            phone_digits = re.sub(r'[^\d]', '', str(ai_phone))
            # Check if it's a valid phone (7-15 digits, not a year like "2023")
            # Also reject if it's exactly 4 digits (likely a year)
            if (len(phone_digits) < 7 or len(phone_digits) > 15 or 
                len(phone_digits) == 4 or  # Reject 4-digit numbers (years)
                phone_digits in ['2019', '2020', '2021', '2022', '2023', '2024', '2025', '2026', '2027', '2028', '2029', '2030']):
                print(f"[WARNING] Invalid phone from AI: '{ai_phone}' (appears to be a year), using spaCy fallback")
                ai_phone = None
        merged['phone'] = ai_phone or (spacy_data['phones'][0] if spacy_data['phones'] else None)
        
        # Validate location - should not be a company name, acronym, or technical term
        ai_location = personal_info.get('location')
        if ai_location:
            location_lower = ai_location.lower().strip()
            
            # Reject if it's one of the companies from work experience
            companies = [exp.get('company', '').lower() for exp in ai_data.get('work_experience', [])]
            if location_lower in companies:
                print(f"[WARNING] Invalid location from AI (company name): '{ai_location}', using spaCy fallback")
                ai_location = None
            
            # Reject if it's too short (likely an acronym like "ROC", "AUC", "SQL")
            elif len(ai_location) <= 3 and ai_location.isupper():
                print(f"[WARNING] Invalid location from AI (acronym): '{ai_location}', using spaCy fallback")
                ai_location = None
            
            # Reject common technical terms that might be mistaken for locations
            elif location_lower in ['roc', 'auc', 'sql', 'aws', 'gcp', 'api', 'sdk', 'ide', 'npm', 'eda', 'etl', 'kpi']:
                print(f"[WARNING] Invalid location from AI (technical term): '{ai_location}', using spaCy fallback")
                ai_location = None
            
            # Reject if it contains common technical keywords
            elif any(keyword in location_lower for keyword in ['validation', 'testing', 'model', 'data', 'analysis']):
                print(f"[WARNING] Invalid location from AI (contains technical keyword): '{ai_location}', using spaCy fallback")
                ai_location = None
        
        merged['location'] = ai_location or (spacy_data['locations'][0] if spacy_data['locations'] else None)
        
        # URLs
        urls = spacy_data.get('urls', [])
        for url in urls:
            if 'linkedin' in url.lower():
                merged['linkedin_url'] = url
            elif any(domain in url.lower() for domain in ['github', 'portfolio', 'personal']):
                merged['portfolio_url'] = url
        
        # Override with AI data if available
        if personal_info.get('linkedin_url'):
            merged['linkedin_url'] = personal_info['linkedin_url']
        if personal_info.get('portfolio_url'):
            merged['portfolio_url'] = personal_info['portfolio_url']
        
        # Professional details (AI only)
        merged['current_title'] = ai_data.get('current_title')
        merged['total_experience_years'] = ai_data.get('total_experience_years')
        merged['professional_summary'] = ai_data.get('professional_summary')
        merged['notice_period'] = ai_data.get('notice_period')
        merged['expected_salary'] = ai_data.get('expected_salary')
        
        # Structured data (AI preferred)
        merged['skills'] = ai_data.get('skills', [])
        merged['education'] = ai_data.get('education', [])
        merged['work_experience'] = ai_data.get('work_experience', [])
        merged['certifications'] = ai_data.get('certifications', [])
        merged['languages'] = ai_data.get('languages', [])
        merged['preferred_locations'] = ai_data.get('preferred_locations', [])
        
        # Calculate confidence scores
        merged['confidence_scores'] = self._calculate_confidence(merged, spacy_data, ai_data)
        
        return merged
    
    def _calculate_confidence(
        self, 
        merged: Dict, 
        spacy_data: Dict, 
        ai_data: Dict
    ) -> Dict[str, float]:
        """
        Calculate confidence scores for each field
        
        Returns:
            Dictionary mapping field names to confidence scores (0.0-1.0)
        """
        scores = {}
        
        # High confidence if both sources agree
        if merged['email'] and merged['email'] in spacy_data.get('emails', []):
            scores['email'] = 0.95
        elif merged['email']:
            scores['email'] = 0.75
        
        if merged['phone'] and any(merged['phone'] in p for p in spacy_data.get('phones', [])):
            scores['phone'] = 0.95
        elif merged['phone']:
            scores['phone'] = 0.75
        
        # AI-extracted fields have medium-high confidence
        if merged.get('work_experience'):
            scores['work_experience'] = 0.85
        
        if merged.get('education'):
            scores['education'] = 0.85
        
        if merged.get('skills'):
            scores['skills'] = 0.80
        
        # Name confidence based on spaCy validation
        if merged['full_name'] and merged['full_name'] in spacy_data.get('names', []):
            scores['full_name'] = 0.90
        elif merged['full_name']:
            scores['full_name'] = 0.70
        
        return scores

"""
Simple Resume Parser Service
Direct text extraction without complex schemas
"""
import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from config.settings import settings


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
            
            self.ai_model = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.1,
                max_output_tokens=8192,
                timeout=180,
                max_retries=2,
            )
            print(f"[DEBUG] Configured LangChain Gemini model: {model_name}")
        else:
            raise ValueError(f"Unsupported AI provider: {self.ai_provider}")
    
    def parse_resume(self, text: str, file_type: str = 'pdf') -> Dict[str, Any]:
        """
        Main parsing method - simple approach
        """
        print(f"[DEBUG] Parsing resume, text length: {len(text)} characters")
        
        # Extract using simple prompt
        result = self._extract_with_simple_prompt(text)
        
        # Add metadata
        result['parsed_at'] = datetime.utcnow().isoformat()
        result['parser_version'] = '2.0.0'
        result['ai_provider'] = self.ai_provider
        
        return result
    
    def _extract_with_simple_prompt(self, text: str) -> Dict[str, Any]:
        """
        Use simple prompt without structured output
        """
        try:
            prompt = f"""Extract information from this resume and return it as a JSON object.

CRITICAL RULES:
1. Read the resume text carefully - extract actual information, don't guess
2. Name should be from the top of the resume (usually in format "First Last" or "First Middle Last")
3. Phone should be an actual phone number with 10 digits (not a year like "2023" or "2024")
4. Email must contain @ symbol
5. Location should be a city/state or city/country (not a skill or tool name)
6. Current title is the job title right below the name or the most recent job
7. Professional summary is the paragraph describing the candidate
8. Extract ALL work experiences with company names, titles, dates, and locations
9. Extract ALL education entries
10. Extract ALL skills mentioned in the resume
11. certifications must be an array of simple strings like ["AWS Certified", "Scrum Master"] - NOT objects with name/year fields

RESUME TEXT:
{text}

Return ONLY a JSON object in this exact format (no markdown, no explanation):
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
      "description": "",
      "duration_months": null
    }}
  ],
  "certifications": [],
  "languages": [],
  "visa_type": null
}}"""
            
            response = self.ai_model.invoke([HumanMessage(content=prompt)])
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            print(f"[DEBUG] AI response length: {len(response_text)} characters")
            
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if not json_match:
                print(f"[ERROR] No JSON found in response")
                return self._empty_result()
            
            json_str = json_match.group(0)
            json_str = re.sub(r'```json\s*|\s*```', '', json_str)
            
            try:
                parsed = json.loads(json_str)
                print(f"[DEBUG] Successfully parsed JSON")
            except json.JSONDecodeError as e:
                print(f"[WARNING] JSON parsing failed, attempting repair: {e}")
                print(f"[DEBUG] JSON string preview: {json_str[:500]}...")
                
                # Attempt to repair common JSON issues
                parsed = self._repair_and_parse_json(json_str)
                
                if parsed is None:
                    print(f"[ERROR] JSON repair failed, returning empty result")
                    return self._empty_result()
                
                print(f"[DEBUG] Successfully repaired and parsed JSON")
            
            print(f"[DEBUG] Name: {parsed.get('full_name')}")
            print(f"[DEBUG] Email: {parsed.get('email')}")
            print(f"[DEBUG] Phone: {parsed.get('phone')}")
            print(f"[DEBUG] Work experiences: {len(parsed.get('work_experience', []))}")
            print(f"[DEBUG] Education: {len(parsed.get('education', []))}")
            print(f"[DEBUG] Skills: {len(parsed.get('skills', []))}")
            
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
            print(f"[ERROR] Extraction failed: {e}")
            import traceback
            traceback.print_exc()
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
        # Try multiple repair strategies
        strategies = [
            self._fix_truncated_json,
            self._fix_unescaped_quotes,
            self._fix_trailing_commas,
            self._extract_partial_json,
        ]
        
        for strategy in strategies:
            try:
                repaired = strategy(json_str)
                if repaired:
                    result = json.loads(repaired)
                    print(f"[DEBUG] JSON repair successful with {strategy.__name__}")
                    return result
            except (json.JSONDecodeError, Exception) as e:
                print(f"[DEBUG] Repair strategy {strategy.__name__} failed: {e}")
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
        # Look for incomplete strings or objects
        if repaired.endswith(','):
            repaired = repaired[:-1]
        
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
        # This is a simple heuristic - look for patterns like ": "value with "quotes" inside"
        # Replace unescaped internal quotes
        
        # Pattern: find strings and escape internal quotes
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
                # Check if this quote is a string delimiter or internal
                if not in_string:
                    in_string = True
                    result.append(char)
                else:
                    # Look ahead to see if this closes the string
                    remaining = json_str[i+1:i+10].lstrip()
                    if remaining and remaining[0] in ':,}]':
                        in_string = False
                        result.append(char)
                    elif remaining.startswith('\n'):
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
        repaired = re.sub(r',\s*([}\]])', r'\1', json_str)
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
                result[field] = match.group(1)
                print(f"[DEBUG] Extracted {field}: {result[field][:50] if result[field] else None}...")
        
        # Extract professional summary (can be multiline)
        summary_match = re.search(
            r'"professional_summary"\s*:\s*"((?:[^"\\]|\\.)*)"',
            json_str,
            re.DOTALL
        )
        if summary_match:
            result['professional_summary'] = summary_match.group(1).replace('\\n', '\n')
        
        # Extract skills array
        skills_match = re.search(r'"skills"\s*:\s*\[((?:[^\[\]]|\[(?:[^\[\]]|\[[^\[\]]*\])*\])*)\]', json_str)
        if skills_match:
            skills_str = skills_match.group(1)
            # Extract individual skill strings
            skill_items = re.findall(r'"([^"]+)"', skills_str)
            result['skills'] = skill_items[:50]  # Limit to 50 skills
        
        # Only return if we got at least a name or email
        if result.get('full_name') or result.get('email'):
            return json.dumps(result)
        
        return None

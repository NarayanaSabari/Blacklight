"""
Base Resume Template

Abstract base class for all resume templates.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
from dataclasses import dataclass


class ResumeTemplateType(str, Enum):
    """Available resume template types."""
    MODERN = "modern"
    CLASSIC = "classic"


@dataclass
class TemplateMetadata:
    """Metadata about a resume template."""
    id: str
    name: str
    description: str
    preview_image: Optional[str] = None
    is_default: bool = False


class BaseResumeTemplate(ABC):
    """
    Abstract base class for resume templates.
    
    All templates must implement methods for:
    - Rendering HTML (for PDF generation and preview)
    - Rendering DOCX
    - Providing metadata for UI display
    """
    
    @property
    @abstractmethod
    def metadata(self) -> TemplateMetadata:
        """Return template metadata for UI display."""
        pass
    
    @abstractmethod
    def render_html(self, markdown_content: str) -> str:
        """
        Convert markdown content to styled HTML.
        
        Used for:
        - PDF generation via WeasyPrint
        - Frontend preview display
        
        Args:
            markdown_content: Resume content in markdown format
            
        Returns:
            Complete HTML document with styling
        """
        pass
    
    @abstractmethod
    def render_docx(self, markdown_content: str) -> bytes:
        """
        Convert markdown content to DOCX document.
        
        Args:
            markdown_content: Resume content in markdown format
            
        Returns:
            DOCX file as bytes
        """
        pass
    
    def get_preview_html(self, markdown_content: str) -> str:
        """
        Get HTML suitable for browser preview.
        
        By default, uses the same HTML as PDF rendering.
        Templates can override this for browser-specific adjustments.
        
        Args:
            markdown_content: Resume content in markdown format
            
        Returns:
            HTML for browser preview
        """
        return self.render_html(markdown_content)
    
    def _clean_markdown_content(self, content: str) -> str:
        """
        Clean and normalize markdown content.
        
        Common cleanup applied to all templates:
        - Remove duplicate sections
        - Fix inline bullet points
        - Ensure proper formatting
        
        Args:
            content: Raw markdown content
            
        Returns:
            Cleaned markdown content
        """
        import re
        
        if not content:
            return ""
        
        # Remove duplicate sections (AI sometimes outputs same section twice)
        section_pattern = r'^(#{1,3})\s+(.+?)$'
        lines = content.split('\n')
        seen_sections = {}
        section_ranges = []
        current_section_start = None
        current_section_header = None
        
        for i, line in enumerate(lines):
            match = re.match(section_pattern, line.strip())
            if match:
                if current_section_header is not None:
                    section_ranges.append((current_section_start, i - 1, current_section_header))
                current_section_start = i
                current_section_header = match.group(2).strip().lower()
        
        if current_section_header is not None:
            section_ranges.append((current_section_start, len(lines) - 1, current_section_header))
        
        # Keep only the last occurrence of each section
        section_last_occurrence = {}
        for start, end, header in section_ranges:
            normalized_header = header.replace('#', '').strip().lower()
            section_last_occurrence[normalized_header] = (start, end)
        
        if section_ranges and len(section_ranges) > len(section_last_occurrence):
            lines_to_keep = set()
            for header, (start, end) in section_last_occurrence.items():
                for i in range(start, end + 1):
                    lines_to_keep.add(i)
            
            if section_ranges:
                first_section_start = section_ranges[0][0]
                for i in range(first_section_start):
                    lines_to_keep.add(i)
            
            cleaned_lines = [lines[i] for i in sorted(lines_to_keep)]
            content = '\n'.join(cleaned_lines)
        
        # Fix formatting issues
        # 1. Ensure bullet points are on their own lines
        content = re.sub(r'([^\n])(\s*[-*]\s+)', r'\1\n\2', content)
        # 2. Ensure headers are on their own lines
        content = re.sub(r'([^\n])(#{1,3}\s+)', r'\1\n\n\2', content)
        # 3. Ensure there's a newline after headers before content
        content = re.sub(r'(#{1,3}\s+[^\n]+)(\n)([^#\n\-*])', r'\1\n\n\3', content)
        
        # 4. Fix inline bullet points
        lines = content.split('\n')
        processed_lines = []
        for line in lines:
            if line.strip().startswith('-') or line.strip().startswith('*') or line.strip().startswith('#'):
                processed_lines.append(line)
            elif line.count(' - ') >= 2 and not line.strip().startswith('*'):
                if ' | ' not in line:
                    parts = re.split(r'\s+-\s+', line)
                    if len(parts) > 1:
                        if parts[0].strip():
                            processed_lines.append(parts[0].strip())
                        for part in parts[1:]:
                            if part.strip():
                                processed_lines.append(f"- {part.strip()}")
                    else:
                        processed_lines.append(line)
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _markdown_to_html(self, content: str) -> str:
        """
        Convert markdown to HTML using the markdown library.
        
        Args:
            content: Markdown content
            
        Returns:
            HTML content (body only, no wrapper)
        """
        import markdown
        
        return markdown.markdown(
            content,
            extensions=['tables', 'fenced_code', 'nl2br']
        )

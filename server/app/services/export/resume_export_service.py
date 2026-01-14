"""
Resume Export Service

Main service for exporting resumes to PDF, DOCX, and other formats
with support for multiple templates.
"""

import logging
import re
import unicodedata
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from .base_template import BaseResumeTemplate, ResumeTemplateType, TemplateMetadata
from .templates import ModernTemplate, ClassicTemplate


logger = logging.getLogger(__name__)


class ResumeExportService:
    """
    Service for exporting resumes with template support.
    
    Provides:
    - PDF export via WeasyPrint
    - DOCX export via python-docx
    - Multiple template options
    - Template metadata for UI display
    - Preview HTML generation
    """
    
    def __init__(self):
        """Initialize with all available templates."""
        self._templates: Dict[str, BaseResumeTemplate] = {
            ResumeTemplateType.MODERN.value: ModernTemplate(),
            ResumeTemplateType.CLASSIC.value: ClassicTemplate(),
        }
        self._default_template = ResumeTemplateType.MODERN.value
    
    @property
    def available_templates(self) -> List[TemplateMetadata]:
        """Get metadata for all available templates."""
        return [t.metadata for t in self._templates.values()]
    
    def get_template(self, template_id: str) -> Optional[BaseResumeTemplate]:
        """
        Get a template by its ID.
        
        Args:
            template_id: Template identifier (e.g., "modern", "classic")
            
        Returns:
            Template instance or None if not found
        """
        return self._templates.get(template_id)
    
    def export_pdf(
        self,
        markdown_content: str,
        template: str = "modern",
    ) -> bytes:
        """
        Export resume to PDF.
        
        Args:
            markdown_content: Resume content in markdown format
            template: Template ID to use (default: "modern")
            
        Returns:
            PDF file as bytes
            
        Raises:
            ValueError: If template not found or content is empty
        """
        if not markdown_content:
            raise ValueError("No content provided for PDF export")
        
        template_obj = self._templates.get(template, self._templates[self._default_template])
        if not template_obj:
            raise ValueError(f"Template '{template}' not found")
        
        logger.info(f"Generating PDF with template: {template}")
        
        # Render HTML
        html_content = template_obj.render_html(markdown_content)
        
        # Lazy import WeasyPrint to avoid startup crashes when system libs are missing
        try:
            from weasyprint import HTML
        except OSError as e:
            logger.error(f"WeasyPrint system libraries not available: {e}")
            raise RuntimeError(
                "PDF export requires system libraries (pango, glib). "
                "On macOS: brew install pango glib gobject-introspection. "
                "On Ubuntu: apt-get install libpango-1.0-0 libpangocairo-1.0-0"
            ) from e
        
        # Generate PDF
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        logger.info(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")
        return pdf_bytes
    
    def export_docx(
        self,
        markdown_content: str,
        template: str = "modern",
    ) -> bytes:
        """
        Export resume to DOCX.
        
        Args:
            markdown_content: Resume content in markdown format
            template: Template ID to use (default: "modern")
            
        Returns:
            DOCX file as bytes
            
        Raises:
            ValueError: If template not found or content is empty
        """
        if not markdown_content:
            raise ValueError("No content provided for DOCX export")
        
        template_obj = self._templates.get(template, self._templates[self._default_template])
        if not template_obj:
            raise ValueError(f"Template '{template}' not found")
        
        logger.info(f"Generating DOCX with template: {template}")
        
        docx_bytes = template_obj.render_docx(markdown_content)
        
        logger.info(f"DOCX generated successfully, size: {len(docx_bytes)} bytes")
        return docx_bytes
    
    def get_preview_html(
        self,
        markdown_content: str,
        template: str = "modern",
    ) -> str:
        """
        Get HTML preview of resume.
        
        Returns HTML suitable for display in a browser preview.
        
        Args:
            markdown_content: Resume content in markdown format
            template: Template ID to use (default: "modern")
            
        Returns:
            HTML string for browser preview
            
        Raises:
            ValueError: If template not found
        """
        if not markdown_content:
            return "<html><body><p>No content available for preview</p></body></html>"
        
        template_obj = self._templates.get(template, self._templates[self._default_template])
        if not template_obj:
            raise ValueError(f"Template '{template}' not found")
        
        return template_obj.get_preview_html(markdown_content)
    
    def get_templates_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all templates for API response.
        
        Returns:
            List of template info dictionaries
        """
        return [
            {
                "id": meta.id,
                "name": meta.name,
                "description": meta.description,
                "is_default": meta.is_default,
            }
            for meta in self.available_templates
        ]
    
    @staticmethod
    def sanitize_filename(text: str) -> str:
        """
        Sanitize text for use in filename.
        
        Removes special characters that could cause issues in HTTP headers or file systems.
        
        Args:
            text: Original text
            
        Returns:
            Sanitized text safe for filenames
        """
        if not text:
            return "resume"
        
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Replace common problematic characters
        replacements = {
            '\u2013': '-',  # en-dash
            '\u2014': '-',  # em-dash
            '\u2018': "'",  # left single quote
            '\u2019': "'",  # right single quote
            '\u201c': '"',  # left double quote
            '\u201d': '"',  # right double quote
            '\u2026': '...',  # ellipsis
            '/': '-',
            '\\': '-',
            ':': '-',
            '|': '-',
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remove any remaining non-ASCII characters
        text = text.encode('ascii', 'ignore').decode('ascii')
        
        # Replace multiple spaces/dashes with single ones
        text = re.sub(r'[-\s]+', '_', text)
        
        # Remove any characters that aren't alphanumeric, underscore, or hyphen
        text = re.sub(r'[^\w\-]', '', text)
        
        # Trim and limit length
        text = text.strip('_-')[:50]
        
        return text if text else "resume"


# Singleton instance for use across the application
resume_export_service = ResumeExportService()

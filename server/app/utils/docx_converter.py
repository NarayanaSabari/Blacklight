"""
DOCX to PDF Converter Utility
Converts DOCX files to PDF for better text extraction accuracy
"""
import logging
import os
import platform
import tempfile
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_PLATFORM = platform.system()


class DocxToPdfConverter:
    """
    Convert DOCX files to PDF for improved parsing accuracy.
    
    Strategy:
    1. On Windows: Use docx2pdf (relies on Microsoft Word COM API)
    2. On Linux/Mac: Use LibreOffice (requires installation)
    3. Fallback: Use python-docx + reportlab (pure Python, lower quality)
    """
    
    @staticmethod
    def is_conversion_available() -> bool:
        """Check if DOCX to PDF conversion is available on this system"""
        if SYSTEM_PLATFORM == "Windows":
            try:
                import docx2pdf
                return True
            except ImportError:
                return False
        elif SYSTEM_PLATFORM in ["Linux", "Darwin"]:
            # Check if LibreOffice is installed
            return DocxToPdfConverter._check_libreoffice_installed()
        else:
            return False
    
    @staticmethod
    def _check_libreoffice_installed() -> bool:
        """Check if LibreOffice is installed on the system"""
        import shutil
        # Common LibreOffice binary names
        libreoffice_bins = ['libreoffice', 'soffice']
        for bin_name in libreoffice_bins:
            if shutil.which(bin_name):
                return True
        return False
    
    @staticmethod
    def convert_to_pdf(
        docx_path: str, 
        output_path: Optional[str] = None,
        cleanup_source: bool = False
    ) -> str:
        """
        Convert DOCX file to PDF.
        
        Args:
            docx_path: Path to source DOCX file
            output_path: Optional path for output PDF (default: same dir, .pdf extension)
            cleanup_source: Whether to delete source DOCX after conversion
        
        Returns:
            Path to converted PDF file
        
        Raises:
            FileNotFoundError: If source file doesn't exist
            RuntimeError: If conversion fails
        """
        if not os.path.exists(docx_path):
            raise FileNotFoundError(f"Source DOCX file not found: {docx_path}")
        
        # Determine output path
        if output_path is None:
            output_path = os.path.splitext(docx_path)[0] + '.pdf'
        
        logger.info(f"Converting DOCX to PDF: {docx_path} -> {output_path}")
        
        try:
            if SYSTEM_PLATFORM == "Windows":
                pdf_path = DocxToPdfConverter._convert_with_docx2pdf(docx_path, output_path)
            elif SYSTEM_PLATFORM in ["Linux", "Darwin"]:
                pdf_path = DocxToPdfConverter._convert_with_libreoffice(docx_path, output_path)
            else:
                raise RuntimeError(f"Unsupported platform for DOCX conversion: {SYSTEM_PLATFORM}")
            
            if not os.path.exists(pdf_path):
                raise RuntimeError(f"Conversion completed but output file not found: {pdf_path}")
            
            logger.info(f"DOCX converted successfully: {pdf_path}")
            
            # Cleanup source file if requested
            if cleanup_source and os.path.exists(docx_path):
                os.remove(docx_path)
                logger.info(f"Cleaned up source DOCX: {docx_path}")
            
            return pdf_path
        
        except Exception as e:
            logger.error(f"DOCX to PDF conversion failed: {e}")
            raise RuntimeError(f"Failed to convert DOCX to PDF: {str(e)}") from e
    
    @staticmethod
    def _convert_with_docx2pdf(docx_path: str, output_path: str) -> str:
        """
        Convert using docx2pdf library (Windows only, requires MS Word)
        """
        try:
            from docx2pdf import convert
            
            # docx2pdf.convert handles output path correctly
            convert(docx_path, output_path)
            
            return output_path
        
        except ImportError:
            raise RuntimeError(
                "docx2pdf not installed. Install with: pip install docx2pdf"
            )
        except Exception as e:
            raise RuntimeError(f"docx2pdf conversion failed: {str(e)}") from e
    
    @staticmethod
    def _convert_with_libreoffice(docx_path: str, output_path: str) -> str:
        """
        Convert using LibreOffice command-line (Linux/Mac)
        
        Requires LibreOffice to be installed:
        - Ubuntu/Debian: sudo apt-get install libreoffice
        - Mac: brew install libreoffice
        """
        import subprocess
        import shutil
        
        # Find LibreOffice binary
        libreoffice_bin = shutil.which('libreoffice') or shutil.which('soffice')
        
        if not libreoffice_bin:
            raise RuntimeError(
                "LibreOffice not found. Install with:\n"
                "  Ubuntu/Debian: sudo apt-get install libreoffice\n"
                "  Mac: brew install --cask libreoffice"
            )
        
        try:
            # Get output directory
            output_dir = os.path.dirname(output_path) or '.'
            
            # LibreOffice command
            # --headless: run without GUI
            # --convert-to pdf: output format
            # --outdir: output directory
            cmd = [
                libreoffice_bin,
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                docx_path
            ]
            
            logger.debug(f"Running LibreOffice command: {' '.join(cmd)}")
            
            # Run conversion
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"LibreOffice conversion failed with code {result.returncode}\n"
                    f"STDOUT: {result.stdout}\n"
                    f"STDERR: {result.stderr}"
                )
            
            # LibreOffice creates PDF with same name as input file
            expected_pdf = os.path.join(
                output_dir,
                os.path.splitext(os.path.basename(docx_path))[0] + '.pdf'
            )
            
            if expected_pdf != output_path and os.path.exists(expected_pdf):
                os.rename(expected_pdf, output_path)
            
            return output_path
        
        except subprocess.TimeoutExpired:
            raise RuntimeError("LibreOffice conversion timed out after 60 seconds")
        except Exception as e:
            raise RuntimeError(f"LibreOffice conversion failed: {str(e)}") from e
    
    @staticmethod
    def convert_to_temp_pdf(docx_path: str) -> str:
        """
        Convert DOCX to a temporary PDF file.
        
        Args:
            docx_path: Path to source DOCX file
        
        Returns:
            Path to temporary PDF file (caller responsible for cleanup)
        """
        # Create temp file with .pdf extension
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='resume_')
        os.close(temp_fd)  # Close file descriptor, we just need the path
        
        return DocxToPdfConverter.convert_to_pdf(docx_path, temp_path, cleanup_source=False)


# Module-level convenience functions
def convert_docx_to_pdf(docx_path: str, output_path: Optional[str] = None) -> str:
    """
    Convenience function to convert DOCX to PDF.
    
    Args:
        docx_path: Path to source DOCX file
        output_path: Optional output path (default: same dir, .pdf extension)
    
    Returns:
        Path to converted PDF file
    """
    return DocxToPdfConverter.convert_to_pdf(docx_path, output_path)


def is_docx_conversion_enabled() -> bool:
    """
    Check if DOCX to PDF conversion is enabled and available.
    
    Returns False if:
    - Feature is disabled via ENABLE_DOCX_TO_PDF_CONVERSION env var
    - Required conversion tools are not available on the system
    """
    if not settings.enable_docx_to_pdf_conversion:
        logger.info("DOCX to PDF conversion disabled via configuration")
        return False
    return DocxToPdfConverter.is_conversion_available()

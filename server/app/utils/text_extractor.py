"""
Text extraction utilities for resume files (PDF, DOCX)
"""
import os
from typing import Optional, Dict, Any
import fitz  # PyMuPDF
from docx import Document
import pdfplumber


class TextExtractor:
    """
    Extract text from PDF and DOCX files
    Supports multiple extraction methods for better accuracy
    """
    
    @staticmethod
    def extract_from_file(file_path: str) -> Dict[str, Any]:
        """
        Extract text from a file (auto-detect type)
        
        Args:
            file_path: Path to resume file
        
        Returns:
            Dictionary with extracted text and metadata
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            return TextExtractor.extract_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            return TextExtractor.extract_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    @staticmethod
    def extract_from_pdf(file_path: str) -> Dict[str, Any]:
        """
        Extract text from PDF using multiple methods for best results
        
        Strategy:
        1. Try PyMuPDF (fast, good for simple PDFs)
        2. Fallback to pdfplumber (better for tables/columns)
        
        Returns:
            {
                'text': str,
                'page_count': int,
                'method': str,
                'has_images': bool,
                'metadata': dict
            }
        """
        result = {
            'text': '',
            'page_count': 0,
            'method': '',
            'has_images': False,
            'metadata': {}
        }
        
        try:
            # Method 1: PyMuPDF (primary)
            text = TextExtractor._extract_with_pymupdf(file_path)
            
            if text and len(text.strip()) > 50:  # Valid extraction
                doc = fitz.open(file_path)
                result['text'] = text
                result['page_count'] = len(doc)
                result['method'] = 'pymupdf'
                result['metadata'] = doc.metadata
                
                # Check for images
                for page in doc:
                    if page.get_images():
                        result['has_images'] = True
                        break
                
                doc.close()
                return result
        
        except Exception as e:
            print(f"PyMuPDF extraction failed: {e}")
        
        try:
            # Method 2: pdfplumber (fallback)
            text = TextExtractor._extract_with_pdfplumber(file_path)
            
            if text:
                with pdfplumber.open(file_path) as pdf:
                    result['text'] = text
                    result['page_count'] = len(pdf.pages)
                    result['method'] = 'pdfplumber'
                    result['metadata'] = pdf.metadata
                
                return result
        
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
            raise RuntimeError(f"Failed to extract text from PDF: {file_path}")
    
    @staticmethod
    def _extract_with_pymupdf(file_path: str) -> str:
        """
        Extract text using PyMuPDF (fast method)
        """
        doc = fitz.open(file_path)
        text_parts = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            text_parts.append(text)
        
        doc.close()
        return '\n\n'.join(text_parts)
    
    @staticmethod
    def _extract_with_pdfplumber(file_path: str) -> str:
        """
        Extract text using pdfplumber (better for complex layouts)
        """
        text_parts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Extract text
                text = page.extract_text()
                if text:
                    text_parts.append(text)
                
                # Extract tables separately
                tables = page.extract_tables()
                for table in tables:
                    # Convert table to text
                    table_text = '\n'.join([
                        ' | '.join([cell or '' for cell in row])
                        for row in table
                    ])
                    text_parts.append(f"\n[TABLE]\n{table_text}\n[/TABLE]\n")
        
        return '\n\n'.join(text_parts)
    
    @staticmethod
    def extract_from_docx(file_path: str) -> Dict[str, Any]:
        """
        Extract text from DOCX file
        
        Returns:
            {
                'text': str,
                'page_count': int (estimated),
                'method': str,
                'has_images': bool,
                'metadata': dict
            }
        """
        result = {
            'text': '',
            'page_count': 0,
            'method': 'python-docx',
            'has_images': False,
            'metadata': {}
        }
        
        try:
            doc = Document(file_path)
            
            # Extract paragraphs
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            
            # Extract tables
            for table in doc.tables:
                table_text = []
                for row in table.rows:
                    row_text = ' | '.join([cell.text.strip() for cell in row.cells])
                    table_text.append(row_text)
                
                if table_text:
                    text_parts.append('\n[TABLE]\n' + '\n'.join(table_text) + '\n[/TABLE]\n')
            
            result['text'] = '\n\n'.join(text_parts)
            
            # Estimate page count (rough: 500 words per page)
            word_count = len(result['text'].split())
            result['page_count'] = max(1, word_count // 500)
            
            # Check for images
            for rel in doc.part.rels.values():
                if "image" in rel.target_ref:
                    result['has_images'] = True
                    break
            
            # Metadata
            core_props = doc.core_properties
            result['metadata'] = {
                'author': core_props.author,
                'created': str(core_props.created) if core_props.created else None,
                'modified': str(core_props.modified) if core_props.modified else None,
                'title': core_props.title,
            }
            
            return result
        
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from DOCX: {file_path}") from e
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean extracted text for better parsing
        
        - Remove excessive whitespace
        - Normalize line breaks
        - Remove special characters
        """
        # Remove multiple spaces
        text = ' '.join(text.split())
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        
        # Remove excessive newlines (more than 2)
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')
        
        return text.strip()
    
    @staticmethod
    def extract_metadata(file_path: str) -> Dict[str, Any]:
        """
        Extract only metadata from file (no text extraction)
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            try:
                doc = fitz.open(file_path)
                metadata = {
                    'page_count': len(doc),
                    'metadata': doc.metadata,
                    'file_size': os.path.getsize(file_path),
                }
                doc.close()
                return metadata
            except Exception as e:
                print(f"Failed to extract PDF metadata: {e}")
                return {'error': str(e)}
        
        elif file_ext in ['.docx', '.doc']:
            try:
                doc = Document(file_path)
                core_props = doc.core_properties
                
                return {
                    'metadata': {
                        'author': core_props.author,
                        'created': str(core_props.created) if core_props.created else None,
                        'modified': str(core_props.modified) if core_props.modified else None,
                        'title': core_props.title,
                    },
                    'file_size': os.path.getsize(file_path),
                }
            except Exception as e:
                print(f"Failed to extract DOCX metadata: {e}")
                return {'error': str(e)}
        
        return {'error': f'Unsupported file type: {file_ext}'}

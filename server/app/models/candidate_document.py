"""
Candidate Document Model
Manages documents uploaded by candidates (resume, ID proof, work authorization, etc.)
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app import db
from app.models import BaseModel


class CandidateDocument(BaseModel):
    """
    Document model for candidate files.
    Can be linked to either a candidate (post-approval) or an invitation (during onboarding).
    """
    __tablename__ = 'candidate_documents'
    
    # Tenant relationship
    tenant_id = db.Column(Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Link to candidate OR invitation (one must be set)
    candidate_id = db.Column(Integer, ForeignKey('candidates.id', ondelete='CASCADE'), index=True)
    invitation_id = db.Column(Integer, ForeignKey('candidate_invitations.id', ondelete='CASCADE'), index=True)
    
    # Document metadata
    document_type = db.Column(String(100), nullable=False, index=True)
    # Types: 'resume', 'id_proof', 'work_authorization', 'certificate', 'other'
    
    file_name = db.Column(String(500), nullable=False)
    file_key = db.Column(String(1000), nullable=False)  # Storage key/path (GCS or local)
    file_path = db.Column(String(1000))  # Legacy: kept for backward compatibility
    file_size = db.Column(Integer, nullable=False)  # Size in bytes
    mime_type = db.Column(String(100), nullable=False)  # 'application/pdf', 'image/jpeg', etc.
    storage_backend = db.Column(String(20), default='local')  # 'local' or 'gcs'
    
    # Upload info
    uploaded_by_id = db.Column(Integer, ForeignKey('portal_users.id'))  # NULL for candidate self-upload
    uploaded_at = db.Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Verification
    is_verified = db.Column(Boolean, nullable=False, default=False, index=True)
    verified_by_id = db.Column(Integer, ForeignKey('portal_users.id'))
    verified_at = db.Column(DateTime)
    verification_notes = db.Column(Text)
    
    # Relationships
    tenant = relationship('Tenant', back_populates='documents')
    candidate = relationship('Candidate', backref='documents', foreign_keys=[candidate_id])
    invitation = relationship('CandidateInvitation', backref='documents', foreign_keys=[invitation_id])
    uploaded_by = relationship('PortalUser', foreign_keys=[uploaded_by_id], backref='uploaded_documents')
    verified_by = relationship('PortalUser', foreign_keys=[verified_by_id], backref='verified_documents')
    
    # Allowed document types per category
    # These match the configurable document types in tenant settings
    DOCUMENT_TYPES = {
        'resume': {
            'label': 'Resume/CV',
            'allowed_mimes': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            'max_size_mb': 10
        },
        'id_proof': {
            'label': 'ID Proof',
            'allowed_mimes': ['application/pdf', 'image/jpeg', 'image/png'],
            'max_size_mb': 5
        },
        'work_authorization': {
            'label': 'Work Authorization',
            'allowed_mimes': ['application/pdf', 'image/jpeg', 'image/png'],
            'max_size_mb': 5
        },
        'educational_certificates': {
            'label': 'Educational Certificates',
            'allowed_mimes': ['application/pdf', 'image/jpeg', 'image/png'],
            'max_size_mb': 5
        },
        'employment_verification': {
            'label': 'Employment Verification',
            'allowed_mimes': ['application/pdf', 'image/jpeg', 'image/png'],
            'max_size_mb': 5
        },
        'professional_certifications': {
            'label': 'Professional Certifications',
            'allowed_mimes': ['application/pdf', 'image/jpeg', 'image/png'],
            'max_size_mb': 5
        },
        'background_check': {
            'label': 'Background Check Consent',
            'allowed_mimes': ['application/pdf', 'image/jpeg', 'image/png'],
            'max_size_mb': 5
        },
        'tax_documents': {
            'label': 'Tax Documents',
            'allowed_mimes': ['application/pdf', 'image/jpeg', 'image/png'],
            'max_size_mb': 5
        },
        'references': {
            'label': 'References',
            'allowed_mimes': ['application/pdf', 'image/jpeg', 'image/png', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            'max_size_mb': 5
        },
        'portfolio': {
            'label': 'Portfolio',
            'allowed_mimes': ['application/pdf', 'image/jpeg', 'image/png'],
            'max_size_mb': 10
        },
        'certificates': {
            'label': 'Certificate',
            'allowed_mimes': ['application/pdf', 'image/jpeg', 'image/png'],
            'max_size_mb': 5
        },
        'other': {
            'label': 'Other Document',
            'allowed_mimes': ['application/pdf', 'image/jpeg', 'image/png', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            'max_size_mb': 10
        }
    }
    
    @classmethod
    def validate_file(cls, document_type, file_size, mime_type):
        """
        Validate file against document type constraints.
        
        Args:
            document_type: Type of document
            file_size: File size in bytes
            mime_type: MIME type of file
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if document_type not in cls.DOCUMENT_TYPES:
            return False, f"Invalid document type: {document_type}"
        
        constraints = cls.DOCUMENT_TYPES[document_type]
        
        # Check MIME type
        if mime_type not in constraints['allowed_mimes']:
            return False, f"File type {mime_type} not allowed for {document_type}"
        
        # Check file size
        max_size_bytes = constraints['max_size_mb'] * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"File size exceeds maximum of {constraints['max_size_mb']}MB"
        
        return True, None
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def file_extension(self):
        """Extract file extension from filename"""
        if '.' in self.file_name:
            return self.file_name.rsplit('.', 1)[1].lower()
        return ''
    
    def __repr__(self):
        return f'<CandidateDocument {self.document_type} - {self.file_name}>'
    
    def to_dict(self):
        """Convert document to dictionary"""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'candidate_id': self.candidate_id,
            'invitation_id': self.invitation_id,
            'document_type': self.document_type,
            'document_type_label': self.DOCUMENT_TYPES.get(self.document_type, {}).get('label', self.document_type),
            'file_name': self.file_name,
            'file_key': self.file_key,
            'file_size': self.file_size,
            'file_size_mb': self.file_size_mb,
            'file_extension': self.file_extension,
            'mime_type': self.mime_type,
            'storage_backend': self.storage_backend,
            'uploaded_by_id': self.uploaded_by_id,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'is_verified': self.is_verified,
            'verified_by_id': self.verified_by_id,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'verification_notes': self.verification_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

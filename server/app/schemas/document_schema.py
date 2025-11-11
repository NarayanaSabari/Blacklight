"""
Document Schemas
Pydantic schemas for document validation and serialization with GCS/local storage support
"""
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class DocumentUploadRequest(BaseModel):
    """Request schema for document upload (sent as form data with file)"""
    document_type: str = Field(..., description="Type of document (resume, id_proof, etc.)")
    candidate_id: Optional[int] = Field(None, description="Candidate ID (for post-approval uploads)")
    invitation_id: Optional[int] = Field(None, description="Invitation ID (for onboarding uploads)")
    
    @field_validator('document_type')
    @classmethod
    def validate_document_type(cls, v):
        """Validate document type"""
        allowed_types = ['resume', 'id_proof', 'work_authorization', 'certificate', 'other']
        if v not in allowed_types:
            raise ValueError(f"Invalid document_type. Must be one of: {', '.join(allowed_types)}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_type": "resume",
                "invitation_id": 123
            }
        }


class DocumentResponse(BaseModel):
    """Response schema for document"""
    id: int
    tenant_id: int
    candidate_id: Optional[int] = None
    invitation_id: Optional[int] = None
    document_type: str
    document_type_label: str
    file_name: str
    file_key: str
    file_size: int
    file_size_mb: float
    file_extension: str
    mime_type: str
    storage_backend: str
    uploaded_by_id: Optional[int] = None
    uploaded_at: str
    is_verified: bool
    verified_by_id: Optional[int] = None
    verified_at: Optional[str] = None
    verification_notes: Optional[str] = None
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "tenant_id": 1,
                "candidate_id": None,
                "invitation_id": 123,
                "document_type": "resume",
                "document_type_label": "Resume/CV",
                "file_name": "john_doe_resume_20251108_123456_abc.pdf",
                "file_key": "tenants/1/resume/invitations/123/john_doe_resume_20251108_123456_abc.pdf",
                "file_size": 1048576,
                "file_size_mb": 1.0,
                "file_extension": "pdf",
                "mime_type": "application/pdf",
                "storage_backend": "gcs",
                "uploaded_by_id": None,
                "uploaded_at": "2025-11-08T12:34:56",
                "is_verified": False,
                "verified_by_id": None,
                "verified_at": None,
                "verification_notes": None,
                "created_at": "2025-11-08T12:34:56",
                "updated_at": "2025-11-08T12:34:56"
            }
        }


class DocumentListResponse(BaseModel):
    """Response schema for document list"""
    documents: List[DocumentResponse]
    total: int
    page: int
    per_page: int
    pages: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "documents": [],
                "total": 25,
                "page": 1,
                "per_page": 20,
                "pages": 2
            }
        }


class DocumentUrlResponse(BaseModel):
    """Response schema for signed URL"""
    url: str
    expires_in: int = Field(..., description="URL expiry time in seconds")
    document_id: int
    file_name: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://storage.googleapis.com/bucket/path?signature=...",
                "expires_in": 3600,
                "document_id": 1,
                "file_name": "john_doe_resume.pdf"
            }
        }


class DocumentVerifyRequest(BaseModel):
    """Request schema for document verification"""
    notes: Optional[str] = Field(None, max_length=1000, description="Verification notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "notes": "Document verified, all information matches"
            }
        }


class DocumentStatsResponse(BaseModel):
    """Response schema for document statistics"""
    total_documents: int
    by_type: Dict[str, int]
    verified_documents: int
    total_size_bytes: int
    total_size_mb: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_documents": 150,
                "by_type": {
                    "resume": 50,
                    "id_proof": 45,
                    "certificate": 30,
                    "other": 25
                },
                "verified_documents": 120,
                "total_size_bytes": 157286400,
                "total_size_mb": 150.0
            }
        }


class DocumentTypeConfig(BaseModel):
    """Document type configuration"""
    id: str
    name: str
    description: str
    mandatory: bool
    allowed_types: List[str]
    max_size_mb: int
    order: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "resume",
                "name": "Resume/CV",
                "description": "Upload your latest resume or CV",
                "mandatory": True,
                "allowed_types": ["pdf", "doc", "docx"],
                "max_size_mb": 10,
                "order": 0
            }
        }


class DocumentTypesConfigResponse(BaseModel):
    """Response schema for document types configuration"""
    document_types: List[DocumentTypeConfig]
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_types": [
                    {
                        "id": "resume",
                        "name": "Resume/CV",
                        "description": "Upload your latest resume or CV",
                        "mandatory": True,
                        "allowed_types": ["pdf", "doc", "docx"],
                        "max_size_mb": 10,
                        "order": 0
                    }
                ]
            }
        }


class PublicDocumentUploadRequest(BaseModel):
    """Request schema for public document upload (onboarding)"""
    invitation_token: str = Field(..., description="Invitation token for authentication")
    document_type: str = Field(..., description="Type of document")
    
    @field_validator('document_type')
    @classmethod
    def validate_document_type(cls, v):
        """Validate document type"""
        allowed_types = ['resume', 'id_proof', 'work_authorization', 'certificate', 'other']
        if v not in allowed_types:
            raise ValueError(f"Invalid document_type. Must be one of: {', '.join(allowed_types)}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "invitation_token": "abc123def456...",
                "document_type": "resume"
            }
        }


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    message: str
    status: int = 400
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Validation Error",
                "message": "File size exceeds maximum of 10MB",
                "status": 400
            }
        }




class DocumentUploadSchema(BaseModel):
    """Schema for document upload metadata (file sent separately as multipart/form-data)"""
    document_type: str = Field(..., description="Type of document (resume, id_proof, etc.)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes about the document")
    
    @field_validator('document_type')
    @classmethod
    def validate_document_type(cls, v):
        # Valid document types - will be checked against tenant config in service layer
        valid_types = [
            'resume', 'id_proof', 'work_authorization', 
            'background_check', 'certificates', 'other'
        ]
        if v not in valid_types:
            raise ValueError(f'Invalid document type. Must be one of: {", ".join(valid_types)}')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_type": "resume",
                "notes": "Updated resume with latest experience"
            }
        }


class DocumentVerifySchema(BaseModel):
    """Schema for HR verifying a document"""
    is_verified: bool = Field(..., description="Whether document is verified")
    verification_notes: Optional[str] = Field(None, max_length=500, description="Verification notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_verified": True,
                "verification_notes": "Valid ID document, expiry date 2025-12-31"
            }
        }


class DocumentResponseSchema(BaseModel):
    """Schema for document response"""
    id: int
    tenant_id: int
    candidate_id: Optional[int]
    invitation_id: Optional[int]
    document_type: str
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_by_id: Optional[int]
    uploaded_at: datetime
    is_verified: bool
    verified_by_id: Optional[int]
    verified_at: Optional[datetime]
    verification_notes: Optional[str]
    notes: Optional[str]
    
    # Computed properties
    file_size_mb: float
    file_extension: str
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "tenant_id": 1,
                "candidate_id": None,
                "invitation_id": 123,
                "document_type": "resume",
                "file_name": "john_doe_resume.pdf",
                "file_path": "/uploads/invitations/1/123/resume_abc123.pdf",
                "file_size": 524288,
                "mime_type": "application/pdf",
                "uploaded_by_id": None,
                "uploaded_at": "2024-01-15T10:30:00",
                "is_verified": False,
                "verified_by_id": None,
                "verified_at": None,
                "verification_notes": None,
                "notes": "Latest resume",
                "file_size_mb": 0.5,
                "file_extension": "pdf"
            }
        }


class DocumentListResponseSchema(BaseModel):
    """Schema for list of documents"""
    items: List[DocumentResponseSchema]
    total: int
    
    class Config:
        from_attributes = True


class DocumentTypeConfigSchema(BaseModel):
    """Schema for document type configuration"""
    required: bool = Field(..., description="Whether this document type is required")
    max_size_mb: int = Field(..., ge=1, le=100, description="Maximum file size in MB")
    allowed_types: List[str] = Field(..., description="Allowed MIME types")
    description: Optional[str] = Field(None, description="Description of what this document should contain")
    
    class Config:
        json_schema_extra = {
            "example": {
                "required": True,
                "max_size_mb": 10,
                "allowed_types": ["application/pdf", "application/msword"],
                "description": "Current resume or CV"
            }
        }


class DocumentTypesConfigResponseSchema(BaseModel):
    """Schema for all document types configuration"""
    document_types: Dict[str, DocumentTypeConfigSchema]
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_types": {
                    "resume": {
                        "required": True,
                        "max_size_mb": 10,
                        "allowed_types": ["application/pdf", "application/msword"],
                        "description": "Current resume or CV"
                    },
                    "id_proof": {
                        "required": True,
                        "max_size_mb": 5,
                        "allowed_types": ["application/pdf", "image/jpeg", "image/png"],
                        "description": "Government-issued ID (Driver's License, Passport)"
                    }
                }
            }
        }

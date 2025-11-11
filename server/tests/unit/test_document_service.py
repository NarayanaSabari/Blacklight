"""
Unit tests for DocumentService
"""
import pytest
import os
import tempfile
from werkzeug.datastructures import FileStorage
from io import BytesIO

from app.services.document_service import DocumentService
from app.models import CandidateDocument
from app import db


@pytest.fixture
def sample_tenant(db):
    """Create a sample tenant"""
    from app.models import Tenant
    tenant = Tenant(
        name="Test Company",
        subdomain="testcompany",
        status="ACTIVE",
        settings={}
    )
    db.session.add(tenant)
    db.session.commit()
    return tenant


@pytest.fixture
def sample_invitation(db, sample_tenant):
    """Create a sample invitation"""
    from app.models import CandidateInvitation
    from datetime import datetime, timedelta
    invitation = CandidateInvitation(
        tenant_id=sample_tenant.id,
        email="candidate@example.com",
        status="in_progress",
        token="test_token_12345",
        expires_at=datetime.utcnow() + timedelta(hours=72)
    )
    db.session.add(invitation)
    db.session.commit()
    return invitation


@pytest.fixture
def sample_candidate(db, sample_tenant):
    """Create a sample candidate"""
    from app.models import Candidate
    candidate = Candidate(
        tenant_id=sample_tenant.id,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com"
    )
    db.session.add(candidate)
    db.session.commit()
    return candidate


@pytest.fixture
def temp_upload_dir():
    """Create temporary upload directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_pdf_file():
    """Create a mock PDF file"""
    content = b"%PDF-1.4 fake pdf content"
    file = FileStorage(
        stream=BytesIO(content),
        filename="resume.pdf",
        content_type="application/pdf"
    )
    return file


@pytest.fixture
def mock_jpg_file():
    """Create a mock JPG file"""
    content = b"\xFF\xD8\xFF fake jpg content"
    file = FileStorage(
        stream=BytesIO(content),
        filename="id_proof.jpg",
        content_type="image/jpeg"
    )
    return file


@pytest.mark.unit
class TestDocumentServiceUpload:
    """Tests for document upload"""
    
    def test_upload_document_for_invitation(self, db, sample_tenant, sample_invitation, mock_pdf_file, temp_upload_dir):
        """Test uploading document for invitation"""
        document = DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="resume",
            notes="Latest resume",
            upload_dir=temp_upload_dir
        )
        
        assert document is not None
        assert document.tenant_id == sample_tenant.id
        assert document.invitation_id == sample_invitation.id
        assert document.candidate_id is None
        assert document.document_type == "resume"
        assert document.file_name == "resume.pdf"
        assert document.mime_type == "application/pdf"
        assert document.file_size > 0
        assert document.notes == "Latest resume"
        assert document.is_verified is False
        
        # Check file was saved
        assert os.path.exists(document.file_path)
    
    def test_upload_document_for_candidate(self, db, sample_tenant, sample_candidate, mock_pdf_file, temp_upload_dir):
        """Test uploading document for candidate"""
        document = DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            candidate_id=sample_candidate.id,
            file=mock_pdf_file,
            document_type="resume",
            upload_dir=temp_upload_dir
        )
        
        assert document.candidate_id == sample_candidate.id
        assert document.invitation_id is None
    
    def test_upload_document_validates_type(self, db, sample_tenant, sample_invitation, temp_upload_dir):
        """Test document type validation"""
        # Create oversized file
        large_content = b"X" * (15 * 1024 * 1024)  # 15MB
        large_file = FileStorage(
            stream=BytesIO(large_content),
            filename="huge.pdf",
            content_type="application/pdf"
        )
        
        with pytest.raises(ValueError, match="exceeds maximum"):
            DocumentService.upload_document(
                tenant_id=sample_tenant.id,
                invitation_id=sample_invitation.id,
                file=large_file,
                document_type="resume",
                upload_dir=temp_upload_dir
            )
    
    def test_upload_document_invalid_mime_type(self, db, sample_tenant, sample_invitation, temp_upload_dir):
        """Test rejecting invalid MIME types"""
        # Try to upload executable file as resume
        exe_file = FileStorage(
            stream=BytesIO(b"MZ fake exe"),
            filename="virus.exe",
            content_type="application/x-executable"
        )
        
        with pytest.raises(ValueError, match="not allowed"):
            DocumentService.upload_document(
                tenant_id=sample_tenant.id,
                invitation_id=sample_invitation.id,
                file=exe_file,
                document_type="resume",
                upload_dir=temp_upload_dir
            )
    
    def test_upload_requires_either_invitation_or_candidate(self, db, sample_tenant, mock_pdf_file, temp_upload_dir):
        """Test that either invitation_id or candidate_id is required"""
        with pytest.raises(ValueError, match="Either invitation_id or candidate_id"):
            DocumentService.upload_document(
                tenant_id=sample_tenant.id,
                file=mock_pdf_file,
                document_type="resume",
                upload_dir=temp_upload_dir
            )


@pytest.mark.unit
class TestDocumentServiceVerify:
    """Tests for document verification"""
    
    def test_verify_document_success(self, db, sample_tenant, sample_invitation, mock_pdf_file, temp_upload_dir):
        """Test verifying a document"""
        from app.models import PortalUser
        
        # Create HR user
        hr_user = PortalUser(
            tenant_id=sample_tenant.id,
            email="hr@test.com",
            first_name="HR",
            last_name="User",
            password_hash="hash",
            is_active=True
        )
        db.session.add(hr_user)
        db.session.commit()
        
        # Upload document
        document = DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="id_proof",
            upload_dir=temp_upload_dir
        )
        
        # Verify document
        verified_doc = DocumentService.verify_document(
            document_id=document.id,
            tenant_id=sample_tenant.id,
            is_verified=True,
            verification_notes="Valid ID, expires 2025",
            verified_by_id=hr_user.id
        )
        
        assert verified_doc.is_verified is True
        assert verified_doc.verification_notes == "Valid ID, expires 2025"
        assert verified_doc.verified_by_id == hr_user.id
        assert verified_doc.verified_at is not None
    
    def test_verify_document_tenant_isolation(self, db, sample_tenant, sample_invitation, mock_pdf_file, temp_upload_dir):
        """Test tenant isolation in verification"""
        from app.models import Tenant
        
        # Upload document
        document = DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="resume",
            upload_dir=temp_upload_dir
        )
        
        # Create different tenant
        other_tenant = Tenant(
            name="Other Company",
            subdomain="otherco",
            status="ACTIVE"
        )
        db.session.add(other_tenant)
        db.session.commit()
        
        # Try to verify from wrong tenant
        with pytest.raises(ValueError, match="Document not found"):
            DocumentService.verify_document(
                document_id=document.id,
                tenant_id=other_tenant.id,
                is_verified=True
            )


@pytest.mark.unit
class TestDocumentServiceList:
    """Tests for listing documents"""
    
    def test_list_documents_for_invitation(self, db, sample_tenant, sample_invitation, mock_pdf_file, mock_jpg_file, temp_upload_dir):
        """Test listing documents for invitation"""
        # Upload multiple documents
        DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="resume",
            upload_dir=temp_upload_dir
        )
        
        DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_jpg_file,
            document_type="id_proof",
            upload_dir=temp_upload_dir
        )
        
        # List documents
        documents = DocumentService.list_documents(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id
        )
        
        assert len(documents) == 2
        doc_types = [doc.document_type for doc in documents]
        assert "resume" in doc_types
        assert "id_proof" in doc_types
    
    def test_list_documents_by_type(self, db, sample_tenant, sample_invitation, mock_pdf_file, temp_upload_dir):
        """Test filtering documents by type"""
        # Upload documents
        DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="resume",
            upload_dir=temp_upload_dir
        )
        
        # Reset file stream for second upload
        mock_pdf_file.stream.seek(0)
        DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="certificates",
            upload_dir=temp_upload_dir
        )
        
        # Filter by resume type only
        documents = DocumentService.list_documents(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            document_type="resume"
        )
        
        assert len(documents) == 1
        assert documents[0].document_type == "resume"


@pytest.mark.unit
class TestDocumentServiceGet:
    """Tests for getting single document"""
    
    def test_get_document_success(self, db, sample_tenant, sample_invitation, mock_pdf_file, temp_upload_dir):
        """Test retrieving single document"""
        document = DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="resume",
            upload_dir=temp_upload_dir
        )
        
        retrieved = DocumentService.get_document(
            document_id=document.id,
            tenant_id=sample_tenant.id
        )
        
        assert retrieved is not None
        assert retrieved.id == document.id
    
    def test_get_document_wrong_tenant(self, db, sample_tenant, sample_invitation, mock_pdf_file, temp_upload_dir):
        """Test tenant isolation"""
        from app.models import Tenant
        
        document = DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="resume",
            upload_dir=temp_upload_dir
        )
        
        other_tenant = Tenant(
            name="Other",
            subdomain="other",
            status="ACTIVE"
        )
        db.session.add(other_tenant)
        db.session.commit()
        
        retrieved = DocumentService.get_document(
            document_id=document.id,
            tenant_id=other_tenant.id
        )
        
        assert retrieved is None


@pytest.mark.unit
class TestDocumentServiceDelete:
    """Tests for deleting documents"""
    
    def test_delete_document_success(self, db, sample_tenant, sample_invitation, mock_pdf_file, temp_upload_dir):
        """Test deleting document removes file and DB record"""
        document = DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="resume",
            upload_dir=temp_upload_dir
        )
        
        file_path = document.file_path
        assert os.path.exists(file_path)
        
        # Delete document
        success = DocumentService.delete_document(
            document_id=document.id,
            tenant_id=sample_tenant.id
        )
        
        assert success is True
        assert not os.path.exists(file_path)  # File removed
        
        # DB record removed
        deleted = db.session.query(CandidateDocument).get(document.id)
        assert deleted is None


@pytest.mark.unit
class TestDocumentServiceMove:
    """Tests for moving documents from invitation to candidate"""
    
    def test_move_documents_to_candidate(self, db, sample_tenant, sample_invitation, sample_candidate, mock_pdf_file, temp_upload_dir):
        """Test moving documents from invitation to candidate"""
        # Upload documents for invitation
        doc1 = DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="resume",
            upload_dir=temp_upload_dir
        )
        
        old_path = doc1.file_path
        
        # Move documents to candidate
        moved_count = DocumentService.move_documents_to_candidate(
            invitation_id=sample_invitation.id,
            candidate_id=sample_candidate.id,
            tenant_id=sample_tenant.id
        )
        
        assert moved_count == 1
        
        # Check document updated
        db.session.refresh(doc1)
        assert doc1.candidate_id == sample_candidate.id
        assert doc1.invitation_id is None
        
        # Check file was moved
        assert not os.path.exists(old_path)  # Old path should not exist
        assert os.path.exists(doc1.file_path)  # New path should exist
        assert "candidates" in doc1.file_path
        assert "invitations" not in doc1.file_path


@pytest.mark.unit
class TestDocumentServiceConfig:
    """Tests for document type configuration"""
    
    def test_get_document_types_config_default(self, db, sample_tenant):
        """Test getting default document types config"""
        config = DocumentService.get_document_types_config(sample_tenant.id)
        
        assert "resume" in config
        assert "id_proof" in config
        assert "work_authorization" in config
        assert "background_check" in config
        assert "certificates" in config
        
        # Check structure
        resume_config = config["resume"]
        assert "required" in resume_config
        assert "max_size_mb" in resume_config
        assert "allowed_types" in resume_config
    
    def test_get_document_types_config_custom(self, db, sample_tenant):
        """Test custom document types from tenant settings"""
        # Set custom config
        sample_tenant.settings = {
            "document_types": {
                "resume": {
                    "required": True,
                    "max_size_mb": 5,
                    "allowed_types": ["application/pdf"]
                },
                "custom_doc": {
                    "required": False,
                    "max_size_mb": 2,
                    "allowed_types": ["image/jpeg"]
                }
            }
        }
        db.session.commit()
        
        config = DocumentService.get_document_types_config(sample_tenant.id)
        
        assert "resume" in config
        assert config["resume"]["max_size_mb"] == 5
        assert "custom_doc" in config


@pytest.mark.unit
class TestDocumentModelProperties:
    """Tests for CandidateDocument computed properties"""
    
    def test_file_size_mb_property(self, db, sample_tenant, sample_invitation, mock_pdf_file, temp_upload_dir):
        """Test file_size_mb computed property"""
        document = DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="resume",
            upload_dir=temp_upload_dir
        )
        
        assert document.file_size_mb > 0
        assert isinstance(document.file_size_mb, float)
        assert document.file_size_mb == round(document.file_size / (1024 * 1024), 2)
    
    def test_file_extension_property(self, db, sample_tenant, sample_invitation, mock_pdf_file, temp_upload_dir):
        """Test file_extension computed property"""
        document = DocumentService.upload_document(
            tenant_id=sample_tenant.id,
            invitation_id=sample_invitation.id,
            file=mock_pdf_file,
            document_type="resume",
            upload_dir=temp_upload_dir
        )
        
        assert document.file_extension == "pdf"


@pytest.mark.unit
class TestDocumentValidation:
    """Tests for document validation logic"""
    
    def test_validate_file_success(self):
        """Test successful file validation"""
        # Should not raise exception
        CandidateDocument.validate_file(
            document_type="resume",
            file_size=5 * 1024 * 1024,  # 5MB
            mime_type="application/pdf"
        )
    
    def test_validate_file_size_exceeds(self):
        """Test file size validation"""
        with pytest.raises(ValueError, match="exceeds maximum"):
            CandidateDocument.validate_file(
                document_type="resume",
                file_size=15 * 1024 * 1024,  # 15MB - exceeds 10MB limit
                mime_type="application/pdf"
            )
    
    def test_validate_file_invalid_mime_type(self):
        """Test MIME type validation"""
        with pytest.raises(ValueError, match="not allowed"):
            CandidateDocument.validate_file(
                document_type="resume",
                file_size=1024,
                mime_type="application/x-executable"  # Not allowed
            )

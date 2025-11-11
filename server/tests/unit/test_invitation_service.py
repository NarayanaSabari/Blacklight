"""
Unit tests for InvitationService
"""
import pytest
from datetime import datetime, timedelta

from app.services.invitation_service import InvitationService
from app.models import CandidateInvitation, InvitationAuditLog, Candidate
from app import db


@pytest.fixture
def sample_tenant(db):
    """Create a sample tenant for testing"""
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
def sample_hr_user(db, sample_tenant):
    """Create a sample HR user"""
    from app.models import PortalUser
    user = PortalUser(
        tenant_id=sample_tenant.id,
        email="hr@testcompany.com",
        first_name="HR",
        last_name="User",
        password_hash="dummy_hash",
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_invitation(db, sample_tenant, sample_hr_user):
    """Create a sample invitation"""
    invitation = CandidateInvitation(
        tenant_id=sample_tenant.id,
        email="candidate@example.com",
        first_name="John",
        last_name="Doe",
        position="Software Engineer",
        status="pending",
        token=CandidateInvitation.generate_token(),
        expires_at=datetime.utcnow() + timedelta(hours=72),
        created_by_id=sample_hr_user.id
    )
    db.session.add(invitation)
    db.session.commit()
    return invitation


@pytest.mark.unit
class TestInvitationServiceCreate:
    """Tests for invitation creation"""
    
    def test_create_invitation_success(self, db, sample_tenant, sample_hr_user):
        """Test creating a new invitation"""
        invitation = InvitationService.create_invitation(
            tenant_id=sample_tenant.id,
            email="newcandidate@example.com",
            first_name="Jane",
            last_name="Smith",
            position="Senior Developer",
            recruiter_notes="Strong Python background",
            expiry_hours=48,
            created_by_id=sample_hr_user.id
        )
        
        assert invitation is not None
        assert invitation.email == "newcandidate@example.com"
        assert invitation.first_name == "Jane"
        assert invitation.last_name == "Smith"
        assert invitation.position == "Senior Developer"
        assert invitation.status == "pending"
        assert invitation.token is not None
        assert len(invitation.token) > 20  # Token should be long enough
        assert invitation.expires_at > datetime.utcnow()
        assert invitation.created_by_id == sample_hr_user.id
        
        # Check audit log was created
        logs = db.session.query(InvitationAuditLog).filter_by(
            invitation_id=invitation.id
        ).all()
        assert len(logs) == 1
        assert logs[0].action == "CREATED"
    
    def test_create_invitation_minimal_data(self, db, sample_tenant, sample_hr_user):
        """Test creating invitation with minimal required data"""
        invitation = InvitationService.create_invitation(
            tenant_id=sample_tenant.id,
            email="minimal@example.com",
            created_by_id=sample_hr_user.id
        )
        
        assert invitation is not None
        assert invitation.email == "minimal@example.com"
        assert invitation.first_name is None
        assert invitation.last_name is None
        assert invitation.status == "pending"


@pytest.mark.unit
class TestInvitationServiceDuplicate:
    """Tests for duplicate checking"""
    
    def test_check_duplicate_exists(self, db, sample_invitation):
        """Test detecting existing invitation"""
        duplicate = InvitationService.check_duplicate(
            tenant_id=sample_invitation.tenant_id,
            email=sample_invitation.email
        )
        
        assert duplicate is not None
        assert duplicate.id == sample_invitation.id
    
    def test_check_duplicate_not_exists(self, db, sample_tenant):
        """Test when no duplicate exists"""
        duplicate = InvitationService.check_duplicate(
            tenant_id=sample_tenant.id,
            email="nonexistent@example.com"
        )
        
        assert duplicate is None
    
    def test_check_duplicate_different_tenant(self, db, sample_invitation):
        """Test duplicate check is tenant-isolated"""
        from app.models import Tenant
        other_tenant = Tenant(
            name="Other Company",
            subdomain="othercompany",
            status="ACTIVE"
        )
        db.session.add(other_tenant)
        db.session.commit()
        
        # Same email but different tenant - should not find duplicate
        duplicate = InvitationService.check_duplicate(
            tenant_id=other_tenant.id,
            email=sample_invitation.email
        )
        
        assert duplicate is None


@pytest.mark.unit
class TestInvitationServiceResend:
    """Tests for resending invitations"""
    
    def test_resend_invitation_success(self, db, sample_invitation, sample_hr_user):
        """Test resending an invitation"""
        old_token = sample_invitation.token
        old_expiry = sample_invitation.expires_at
        
        invitation = InvitationService.resend_invitation(
            invitation_id=sample_invitation.id,
            tenant_id=sample_invitation.tenant_id,
            expiry_hours=24,
            resent_by_id=sample_hr_user.id
        )
        
        assert invitation.token != old_token  # New token generated
        assert invitation.expires_at > old_expiry  # New expiry time
        assert invitation.status == "pending"
        
        # Check audit log
        logs = db.session.query(InvitationAuditLog).filter_by(
            invitation_id=invitation.id,
            action="RESENT"
        ).all()
        assert len(logs) >= 1
    
    def test_resend_invalid_invitation(self, db, sample_tenant, sample_hr_user):
        """Test resending non-existent invitation raises error"""
        with pytest.raises(ValueError, match="Invitation not found"):
            InvitationService.resend_invitation(
                invitation_id=99999,
                tenant_id=sample_tenant.id,
                expiry_hours=24,
                resent_by_id=sample_hr_user.id
            )


@pytest.mark.unit
class TestInvitationServiceRetrieval:
    """Tests for retrieving invitations"""
    
    def test_get_by_token_success(self, db, sample_invitation):
        """Test retrieving invitation by token"""
        invitation = InvitationService.get_by_token(sample_invitation.token)
        
        assert invitation is not None
        assert invitation.id == sample_invitation.id
    
    def test_get_by_token_not_found(self, db):
        """Test retrieving with invalid token"""
        invitation = InvitationService.get_by_token("invalid_token_12345")
        
        assert invitation is None
    
    def test_get_by_id_success(self, db, sample_invitation):
        """Test retrieving invitation by ID"""
        invitation = InvitationService.get_by_id(
            sample_invitation.id,
            sample_invitation.tenant_id
        )
        
        assert invitation is not None
        assert invitation.id == sample_invitation.id
    
    def test_get_by_id_wrong_tenant(self, db, sample_invitation):
        """Test tenant isolation for get_by_id"""
        from app.models import Tenant
        other_tenant = Tenant(
            name="Other Company",
            subdomain="othercompany",
            status="ACTIVE"
        )
        db.session.add(other_tenant)
        db.session.commit()
        
        invitation = InvitationService.get_by_id(
            sample_invitation.id,
            other_tenant.id
        )
        
        assert invitation is None  # Should not find due to tenant mismatch


@pytest.mark.unit
class TestInvitationServiceList:
    """Tests for listing invitations"""
    
    def test_list_invitations_basic(self, db, sample_invitation):
        """Test listing invitations"""
        result = InvitationService.list_invitations(
            tenant_id=sample_invitation.tenant_id,
            page=1,
            per_page=10
        )
        
        assert result["total"] >= 1
        assert len(result["items"]) >= 1
        assert result["page"] == 1
        assert result["per_page"] == 10
    
    def test_list_invitations_status_filter(self, db, sample_tenant, sample_hr_user):
        """Test filtering by status"""
        # Create invitations with different statuses
        InvitationService.create_invitation(
            tenant_id=sample_tenant.id,
            email="pending1@example.com",
            created_by_id=sample_hr_user.id
        )
        
        # Create and submit another
        inv2 = InvitationService.create_invitation(
            tenant_id=sample_tenant.id,
            email="submitted@example.com",
            created_by_id=sample_hr_user.id
        )
        inv2.status = "submitted"
        db.session.commit()
        
        # Filter by pending
        result = InvitationService.list_invitations(
            tenant_id=sample_tenant.id,
            status="pending"
        )
        
        assert result["total"] >= 1
        for item in result["items"]:
            assert item.status == "pending"
    
    def test_list_invitations_pagination(self, db, sample_tenant, sample_hr_user):
        """Test pagination"""
        # Create multiple invitations
        for i in range(15):
            InvitationService.create_invitation(
                tenant_id=sample_tenant.id,
                email=f"candidate{i}@example.com",
                created_by_id=sample_hr_user.id
            )
        
        # Get first page
        result = InvitationService.list_invitations(
            tenant_id=sample_tenant.id,
            page=1,
            per_page=10
        )
        
        assert len(result["items"]) == 10
        assert result["total"] >= 15
        assert result["pages"] >= 2


@pytest.mark.unit
class TestInvitationServiceSubmit:
    """Tests for candidate submission"""
    
    def test_submit_invitation_success(self, db, sample_invitation):
        """Test submitting invitation data"""
        candidate_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "candidate@example.com",
            "phone": "+1-555-1234",
            "address_line1": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001",
            "skills": ["Python", "React"],
            "work_authorization_status": "US Citizen"
        }
        
        invitation = InvitationService.submit_invitation(
            token=sample_invitation.token,
            data=candidate_data,
            ip_address="127.0.0.1",
            user_agent="Test Browser"
        )
        
        assert invitation.status == "submitted"
        assert invitation.invitation_data is not None
        assert invitation.invitation_data["first_name"] == "John"
        assert invitation.submitted_at is not None
        
        # Check audit log
        logs = db.session.query(InvitationAuditLog).filter_by(
            invitation_id=invitation.id,
            action="SUBMITTED"
        ).all()
        assert len(logs) >= 1
    
    def test_submit_expired_invitation(self, db, sample_invitation):
        """Test submitting expired invitation raises error"""
        # Expire the invitation
        sample_invitation.expires_at = datetime.utcnow() - timedelta(hours=1)
        db.session.commit()
        
        with pytest.raises(ValueError, match="expired"):
            InvitationService.submit_invitation(
                token=sample_invitation.token,
                data={"first_name": "Test"},
                ip_address="127.0.0.1"
            )


@pytest.mark.unit
class TestInvitationServiceReview:
    """Tests for reviewing invitations"""
    
    def test_approve_invitation_creates_candidate(self, db, sample_invitation, sample_hr_user):
        """Test approving invitation creates candidate"""
        # First submit the invitation
        candidate_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1-555-1234",
            "address_line1": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001"
        }
        
        InvitationService.submit_invitation(
            token=sample_invitation.token,
            data=candidate_data
        )
        
        # Approve the invitation
        candidate = InvitationService.approve_invitation(
            invitation_id=sample_invitation.id,
            tenant_id=sample_invitation.tenant_id,
            reviewed_by_id=sample_hr_user.id,
            notes="Approved - good fit"
        )
        
        assert candidate is not None
        assert candidate.first_name == "John"
        assert candidate.last_name == "Doe"
        assert candidate.email == "john.doe@example.com"
        assert candidate.onboarding_type == "self_onboarding"
        assert candidate.invitation_id == sample_invitation.id
        
        # Check invitation status
        db.session.refresh(sample_invitation)
        assert sample_invitation.status == "approved"
        assert sample_invitation.reviewed_at is not None
        assert sample_invitation.reviewed_by_id == sample_hr_user.id
        assert sample_invitation.candidate_id == candidate.id
    
    def test_reject_invitation(self, db, sample_invitation, sample_hr_user):
        """Test rejecting invitation"""
        # Submit first
        InvitationService.submit_invitation(
            token=sample_invitation.token,
            data={"first_name": "Test"}
        )
        
        invitation = InvitationService.reject_invitation(
            invitation_id=sample_invitation.id,
            tenant_id=sample_invitation.tenant_id,
            reviewed_by_id=sample_hr_user.id,
            reason="Incomplete information"
        )
        
        assert invitation.status == "rejected"
        assert invitation.rejection_reason == "Incomplete information"
        assert invitation.reviewed_at is not None
        assert invitation.candidate_id is None  # No candidate created
    
    def test_approve_unsubmitted_invitation_fails(self, db, sample_invitation, sample_hr_user):
        """Test approving unsubmitted invitation raises error"""
        with pytest.raises(ValueError, match="Cannot approve"):
            InvitationService.approve_invitation(
                invitation_id=sample_invitation.id,
                tenant_id=sample_invitation.tenant_id,
                reviewed_by_id=sample_hr_user.id
            )


@pytest.mark.unit
class TestInvitationServiceCancel:
    """Tests for cancelling invitations"""
    
    def test_cancel_invitation_success(self, db, sample_invitation, sample_hr_user):
        """Test cancelling a pending invitation"""
        invitation = InvitationService.cancel_invitation(
            invitation_id=sample_invitation.id,
            tenant_id=sample_invitation.tenant_id,
            cancelled_by_id=sample_hr_user.id
        )
        
        assert invitation.status == "cancelled"
        
        # Check audit log
        logs = db.session.query(InvitationAuditLog).filter_by(
            invitation_id=invitation.id,
            action="CANCELLED"
        ).all()
        assert len(logs) >= 1


@pytest.mark.unit
class TestInvitationServiceStatusTracking:
    """Tests for status tracking methods"""
    
    def test_mark_as_opened(self, db, sample_invitation):
        """Test marking invitation as opened"""
        invitation = InvitationService.mark_as_opened(
            invitation_id=sample_invitation.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        assert invitation.opened_at is not None
        
        # Check audit log
        logs = db.session.query(InvitationAuditLog).filter_by(
            invitation_id=invitation.id,
            action="OPENED"
        ).all()
        assert len(logs) >= 1
        assert logs[0].ip_address == "192.168.1.1"
    
    def test_mark_as_in_progress(self, db, sample_invitation):
        """Test marking invitation as in progress"""
        invitation = InvitationService.mark_as_in_progress(sample_invitation.id)
        
        assert invitation.status == "in_progress"


@pytest.mark.unit
class TestInvitationServiceAuditTrail:
    """Tests for audit trail retrieval"""
    
    def test_get_audit_trail(self, db, sample_invitation, sample_hr_user):
        """Test retrieving audit trail"""
        # Perform multiple actions
        InvitationService.mark_as_opened(sample_invitation.id)
        InvitationService.mark_as_in_progress(sample_invitation.id)
        
        logs = InvitationService.get_invitation_audit_trail(
            invitation_id=sample_invitation.id,
            tenant_id=sample_invitation.tenant_id
        )
        
        assert len(logs) >= 3  # CREATED, OPENED, STATUS_CHANGED
        # Should be ordered by most recent first
        assert logs[0].performed_at >= logs[-1].performed_at

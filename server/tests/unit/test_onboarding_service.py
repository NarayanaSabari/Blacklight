"""
Unit tests for OnboardingService
Tests onboarding workflow, status transitions, and approval process
"""
import pytest
from datetime import datetime

from app.services.onboarding_service import OnboardingService
from app.models import Candidate, PortalUser, Tenant, CandidateAssignment


@pytest.fixture
def sample_tenant(db):
    """Create a sample tenant for testing"""
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
def sample_users(db, sample_tenant):
    """Create sample users"""
    recruiter = PortalUser(
        tenant_id=sample_tenant.id,
        email="recruiter@testcompany.com",
        first_name="Recruiter",
        last_name="User",
        password_hash="dummy_hash",
        is_active=True
    )
    approver = PortalUser(
        tenant_id=sample_tenant.id,
        email="approver@testcompany.com",
        first_name="Approver",
        last_name="User",
        password_hash="dummy_hash",
        is_active=True
    )
    db.session.add_all([recruiter, approver])
    db.session.commit()
    return {'recruiter': recruiter, 'approver': approver}


@pytest.fixture
def sample_candidates(db, sample_tenant):
    """Create candidates in various onboarding statuses"""
    candidates = {}
    
    # Pending assignment
    pending = Candidate(
        tenant_id=sample_tenant.id,
        first_name="Pending",
        last_name="Candidate",
        email="pending@example.com",
        onboarding_status="PENDING_ASSIGNMENT"
    )
    
    # Assigned
    assigned = Candidate(
        tenant_id=sample_tenant.id,
        first_name="Assigned",
        last_name="Candidate",
        email="assigned@example.com",
        onboarding_status="ASSIGNED"
    )
    
    # Pending onboarding
    pending_onboard = Candidate(
        tenant_id=sample_tenant.id,
        first_name="PendingOnboard",
        last_name="Candidate",
        email="pendonboard@example.com",
        onboarding_status="PENDING_ONBOARDING"
    )
    
    # Onboarded
    onboarded = Candidate(
        tenant_id=sample_tenant.id,
        first_name="Onboarded",
        last_name="Candidate",
        email="onboarded@example.com",
        onboarding_status="ONBOARDED"
    )
    
    db.session.add_all([pending, assigned, pending_onboard, onboarded])
    db.session.commit()
    
    return {
        'pending': pending,
        'assigned': assigned,
        'pending_onboard': pending_onboard,
        'onboarded': onboarded
    }


@pytest.mark.unit
class TestOnboardingServiceQueries:
    """Tests for querying candidates by status"""
    
    def test_get_pending_assignment_candidates(self, db, sample_tenant, sample_candidates):
        """Test getting candidates pending assignment"""
        result = OnboardingService.get_pending_candidates(
            tenant_id=sample_tenant.id,
            status='PENDING_ASSIGNMENT',
            page=1,
            per_page=10
        )
        
        assert result is not None
        assert result['total'] >= 1
        candidate_ids = [c['id'] for c in result['candidates']]
        assert sample_candidates['pending'].id in candidate_ids
        assert sample_candidates['assigned'].id not in candidate_ids
    
    def test_get_pending_onboarding_candidates(self, db, sample_tenant, sample_candidates):
        """Test getting candidates pending onboarding"""
        result = OnboardingService.get_pending_candidates(
            tenant_id=sample_tenant.id,
            status='PENDING_ONBOARDING',
            page=1,
            per_page=10
        )
        
        assert result is not None
        candidate_ids = [c['id'] for c in result['candidates']]
        assert sample_candidates['pending_onboard'].id in candidate_ids
    
    def test_get_all_candidates(self, db, sample_tenant, sample_candidates):
        """Test getting all onboarding candidates"""
        result = OnboardingService.get_pending_candidates(
            tenant_id=sample_tenant.id,
            page=1,
            per_page=10
        )
        
        assert result is not None
        assert result['total'] >= 4
    
    def test_get_candidates_pagination(self, db, sample_tenant):
        """Test pagination of candidate queries"""
        # Create 15 candidates
        for i in range(15):
            candidate = Candidate(
                tenant_id=sample_tenant.id,
                first_name=f"Candidate{i}",
                last_name="Test",
                email=f"candidate{i}@example.com",
                onboarding_status="PENDING_ASSIGNMENT"
            )
            db.session.add(candidate)
        db.session.commit()
        
        # Get page 1
        page1 = OnboardingService.get_pending_candidates(
            tenant_id=sample_tenant.id,
            status='PENDING_ASSIGNMENT',
            page=1,
            per_page=10
        )
        
        assert len(page1['candidates']) == 10
        assert page1['page'] == 1
        assert page1['total_pages'] >= 2
        
        # Get page 2
        page2 = OnboardingService.get_pending_candidates(
            tenant_id=sample_tenant.id,
            status='PENDING_ASSIGNMENT',
            page=2,
            per_page=10
        )
        
        assert len(page2['candidates']) >= 5
        assert page2['page'] == 2


@pytest.mark.unit
class TestOnboardingServiceWorkflow:
    """Tests for onboarding workflow transitions"""
    
    def test_assign_candidate_to_onboarding(self, db, sample_tenant, sample_candidates, sample_users):
        """Test assigning a candidate for onboarding"""
        result = OnboardingService.assign_candidate_to_onboarding(
            candidate_id=sample_candidates['pending'].id,
            assigned_to_user_id=sample_users['recruiter'].id,
            assigned_by_user_id=sample_users['approver'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert result['candidate_id'] == sample_candidates['pending'].id
        assert result['onboarding_status'] == 'ASSIGNED'
        
        # Verify candidate status updated
        db.session.refresh(sample_candidates['pending'])
        assert sample_candidates['pending'].onboarding_status == 'ASSIGNED'
        assert sample_candidates['pending'].assigned_to == sample_users['recruiter'].id
        
        # Verify assignment record created
        assignment = db.session.query(CandidateAssignment).filter_by(
            candidate_id=sample_candidates['pending'].id
        ).first()
        assert assignment is not None
        assert assignment.status == 'ACTIVE'
    
    def test_onboard_candidate_success(self, db, sample_tenant, sample_candidates, sample_users):
        """Test onboarding a candidate"""
        result = OnboardingService.onboard_candidate(
            candidate_id=sample_candidates['assigned'].id,
            onboarded_by_user_id=sample_users['recruiter'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert result['candidate_id'] == sample_candidates['assigned'].id
        assert result['onboarding_status'] == 'ONBOARDED'
        
        # Verify status updated
        db.session.refresh(sample_candidates['assigned'])
        assert sample_candidates['assigned'].onboarding_status == 'ONBOARDED'
        assert sample_candidates['assigned'].onboarded_by == sample_users['recruiter'].id
        assert sample_candidates['assigned'].onboarded_date is not None
    
    def test_onboard_candidate_wrong_status_fails(self, db, sample_tenant, sample_candidates, sample_users):
        """Test onboarding candidate in wrong status"""
        with pytest.raises(ValueError, match="must be in ASSIGNED or PENDING_ONBOARDING status"):
            OnboardingService.onboard_candidate(
                candidate_id=sample_candidates['pending'].id,  # PENDING_ASSIGNMENT status
                onboarded_by_user_id=sample_users['recruiter'].id,
                tenant_id=sample_tenant.id
            )
    
    def test_approve_candidate_success(self, db, sample_tenant, sample_candidates, sample_users):
        """Test approving an onboarded candidate"""
        result = OnboardingService.approve_candidate(
            candidate_id=sample_candidates['onboarded'].id,
            approved_by_user_id=sample_users['approver'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert result['candidate_id'] == sample_candidates['onboarded'].id
        assert result['onboarding_status'] == 'APPROVED'
        
        # Verify status updated
        db.session.refresh(sample_candidates['onboarded'])
        assert sample_candidates['onboarded'].onboarding_status == 'APPROVED'
        assert sample_candidates['onboarded'].approved_by == sample_users['approver'].id
        assert sample_candidates['onboarded'].approved_date is not None
    
    def test_approve_candidate_wrong_status_fails(self, db, sample_tenant, sample_candidates, sample_users):
        """Test approving candidate not in ONBOARDED status"""
        with pytest.raises(ValueError, match="must be in ONBOARDED status"):
            OnboardingService.approve_candidate(
                candidate_id=sample_candidates['assigned'].id,
                approved_by_user_id=sample_users['approver'].id,
                tenant_id=sample_tenant.id
            )
    
    def test_reject_candidate_success(self, db, sample_tenant, sample_candidates, sample_users):
        """Test rejecting an onboarded candidate with reason"""
        result = OnboardingService.reject_candidate(
            candidate_id=sample_candidates['onboarded'].id,
            rejected_by_user_id=sample_users['approver'].id,
            rejection_reason="Missing required documentation",
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert result['candidate_id'] == sample_candidates['onboarded'].id
        assert result['onboarding_status'] == 'REJECTED'
        assert result['rejection_reason'] == "Missing required documentation"
        
        # Verify status updated
        db.session.refresh(sample_candidates['onboarded'])
        assert sample_candidates['onboarded'].onboarding_status == 'REJECTED'
        assert sample_candidates['onboarded'].rejected_by == sample_users['approver'].id
        assert sample_candidates['onboarded'].rejected_date is not None
        assert sample_candidates['onboarded'].rejection_reason == "Missing required documentation"
    
    def test_reject_candidate_no_reason_fails(self, db, sample_tenant, sample_candidates, sample_users):
        """Test rejecting without reason fails"""
        with pytest.raises(ValueError, match="Rejection reason is required"):
            OnboardingService.reject_candidate(
                candidate_id=sample_candidates['onboarded'].id,
                rejected_by_user_id=sample_users['approver'].id,
                rejection_reason="",
                tenant_id=sample_tenant.id
            )
    
    def test_reject_candidate_wrong_status_fails(self, db, sample_tenant, sample_candidates, sample_users):
        """Test rejecting candidate not in ONBOARDED status"""
        with pytest.raises(ValueError, match="must be in ONBOARDED status"):
            OnboardingService.reject_candidate(
                candidate_id=sample_candidates['assigned'].id,
                rejected_by_user_id=sample_users['approver'].id,
                rejection_reason="Some reason",
                tenant_id=sample_tenant.id
            )


@pytest.mark.unit
class TestOnboardingServiceStats:
    """Tests for onboarding statistics"""
    
    def test_get_onboarding_stats(self, db, sample_tenant, sample_candidates):
        """Test getting onboarding statistics"""
        stats = OnboardingService.get_onboarding_stats(tenant_id=sample_tenant.id)
        
        assert stats is not None
        assert 'pending_assignment' in stats
        assert 'assigned' in stats
        assert 'pending_onboarding' in stats
        assert 'onboarded' in stats
        assert 'approved' in stats
        assert 'rejected' in stats
        assert 'total' in stats
        
        assert stats['pending_assignment'] >= 1
        assert stats['assigned'] >= 1
        assert stats['pending_onboarding'] >= 1
        assert stats['onboarded'] >= 1
        assert stats['total'] >= 4
    
    def test_get_onboarding_stats_empty_tenant(self, db):
        """Test stats for tenant with no candidates"""
        tenant = Tenant(
            name="Empty Company",
            subdomain="emptycompany",
            status="ACTIVE",
            settings={}
        )
        db.session.add(tenant)
        db.session.commit()
        
        stats = OnboardingService.get_onboarding_stats(tenant_id=tenant.id)
        
        assert stats['total'] == 0
        assert stats['pending_assignment'] == 0
        assert stats['assigned'] == 0
        assert stats['onboarded'] == 0
    
    def test_get_stats_for_specific_user(self, db, sample_tenant, sample_users):
        """Test getting stats filtered by assigned user"""
        # Create candidates assigned to specific user
        for i in range(3):
            candidate = Candidate(
                tenant_id=sample_tenant.id,
                first_name=f"UserCandidate{i}",
                last_name="Test",
                email=f"usercandidate{i}@example.com",
                onboarding_status="ASSIGNED",
                assigned_to=sample_users['recruiter'].id
            )
            db.session.add(candidate)
        db.session.commit()
        
        stats = OnboardingService.get_onboarding_stats(
            tenant_id=sample_tenant.id,
            assigned_to_user_id=sample_users['recruiter'].id
        )
        
        assert stats['assigned'] >= 3


@pytest.mark.unit
class TestOnboardingServiceWorkflowDetails:
    """Tests for candidate workflow details"""
    
    def test_get_candidate_workflow(self, db, sample_tenant, sample_candidates, sample_users):
        """Test getting workflow details for a candidate"""
        # Assign candidate
        OnboardingService.assign_candidate_to_onboarding(
            candidate_id=sample_candidates['pending'].id,
            assigned_to_user_id=sample_users['recruiter'].id,
            assigned_by_user_id=sample_users['approver'].id,
            tenant_id=sample_tenant.id
        )
        
        workflow = OnboardingService.get_candidate_workflow(
            candidate_id=sample_candidates['pending'].id,
            tenant_id=sample_tenant.id
        )
        
        assert workflow is not None
        assert workflow['candidate_id'] == sample_candidates['pending'].id
        assert workflow['onboarding_status'] == 'ASSIGNED'
        assert workflow['assigned_to_user_id'] == sample_users['recruiter'].id
    
    def test_get_workflow_not_found(self, db, sample_tenant):
        """Test getting workflow for non-existent candidate"""
        with pytest.raises(ValueError, match="Candidate not found"):
            OnboardingService.get_candidate_workflow(
                candidate_id=99999,
                tenant_id=sample_tenant.id
            )


@pytest.mark.unit
class TestOnboardingServiceStateValidation:
    """Tests for state transition validation"""
    
    def test_full_workflow_sequence(self, db, sample_tenant, sample_users):
        """Test complete onboarding workflow from start to finish"""
        # Create new candidate
        candidate = Candidate(
            tenant_id=sample_tenant.id,
            first_name="Workflow",
            last_name="Test",
            email="workflow@example.com",
            onboarding_status="PENDING_ASSIGNMENT"
        )
        db.session.add(candidate)
        db.session.commit()
        
        # Step 1: Assign
        result1 = OnboardingService.assign_candidate_to_onboarding(
            candidate_id=candidate.id,
            assigned_to_user_id=sample_users['recruiter'].id,
            assigned_by_user_id=sample_users['approver'].id,
            tenant_id=sample_tenant.id
        )
        assert result1['onboarding_status'] == 'ASSIGNED'
        
        # Step 2: Onboard
        result2 = OnboardingService.onboard_candidate(
            candidate_id=candidate.id,
            onboarded_by_user_id=sample_users['recruiter'].id,
            tenant_id=sample_tenant.id
        )
        assert result2['onboarding_status'] == 'ONBOARDED'
        
        # Step 3: Approve
        result3 = OnboardingService.approve_candidate(
            candidate_id=candidate.id,
            approved_by_user_id=sample_users['approver'].id,
            tenant_id=sample_tenant.id
        )
        assert result3['onboarding_status'] == 'APPROVED'
        
        # Verify final state
        db.session.refresh(candidate)
        assert candidate.onboarding_status == 'APPROVED'
        assert candidate.assigned_to is not None
        assert candidate.onboarded_by is not None
        assert candidate.approved_by is not None
    
    def test_cannot_approve_after_rejection(self, db, sample_tenant, sample_users):
        """Test that approved candidate cannot transition back"""
        # Create and fully onboard candidate
        candidate = Candidate(
            tenant_id=sample_tenant.id,
            first_name="Final",
            last_name="State",
            email="final@example.com",
            onboarding_status="ONBOARDED",
            onboarded_by=sample_users['recruiter'].id
        )
        db.session.add(candidate)
        db.session.commit()
        
        # Reject
        OnboardingService.reject_candidate(
            candidate_id=candidate.id,
            rejected_by_user_id=sample_users['approver'].id,
            rejection_reason="Test rejection",
            tenant_id=sample_tenant.id
        )
        
        # Try to approve (should fail)
        with pytest.raises(ValueError, match="must be in ONBOARDED status"):
            OnboardingService.approve_candidate(
                candidate_id=candidate.id,
                approved_by_user_id=sample_users['approver'].id,
                tenant_id=sample_tenant.id
            )


@pytest.mark.unit
class TestOnboardingServiceEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_candidate_not_found(self, db, sample_tenant, sample_users):
        """Test operations on non-existent candidate"""
        with pytest.raises(ValueError, match="Candidate not found"):
            OnboardingService.onboard_candidate(
                candidate_id=99999,
                onboarded_by_user_id=sample_users['recruiter'].id,
                tenant_id=sample_tenant.id
            )
    
    def test_user_not_found(self, db, sample_tenant, sample_candidates):
        """Test assigning to non-existent user"""
        with pytest.raises(ValueError, match="User not found"):
            OnboardingService.assign_candidate_to_onboarding(
                candidate_id=sample_candidates['pending'].id,
                assigned_to_user_id=99999,
                assigned_by_user_id=99998,
                tenant_id=sample_tenant.id
            )
    
    def test_assign_to_different_tenant_user(self, db, sample_candidates, sample_users):
        """Test assigning candidate to user from different tenant"""
        # Create another tenant and user
        other_tenant = Tenant(
            name="Other Company",
            subdomain="othercompany",
            status="ACTIVE",
            settings={}
        )
        db.session.add(other_tenant)
        db.session.flush()
        
        other_user = PortalUser(
            tenant_id=other_tenant.id,
            email="user@othercompany.com",
            first_name="Other",
            last_name="User",
            password_hash="dummy_hash",
            is_active=True
        )
        db.session.add(other_user)
        db.session.commit()
        
        # Try to assign
        with pytest.raises(ValueError, match="belong to different tenants"):
            OnboardingService.assign_candidate_to_onboarding(
                candidate_id=sample_candidates['pending'].id,
                assigned_to_user_id=other_user.id,
                assigned_by_user_id=sample_users['recruiter'].id,
                tenant_id=sample_candidates['pending'].tenant_id
            )
    
    def test_pending_onboarding_status_can_be_onboarded(self, db, sample_tenant, sample_candidates, sample_users):
        """Test that PENDING_ONBOARDING status can also be onboarded"""
        result = OnboardingService.onboard_candidate(
            candidate_id=sample_candidates['pending_onboard'].id,
            onboarded_by_user_id=sample_users['recruiter'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result['onboarding_status'] == 'ONBOARDED'

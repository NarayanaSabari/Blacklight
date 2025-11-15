"""
Unit tests for CandidateAssignmentService
Tests candidate assignment, reassignment, unassignment, and notifications
"""
import pytest
from datetime import datetime

from app.services.candidate_assignment_service import CandidateAssignmentService
from app.models import Candidate, PortalUser, Tenant, CandidateAssignment, AssignmentNotification


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
    recruiter1 = PortalUser(
        tenant_id=sample_tenant.id,
        email="recruiter1@testcompany.com",
        first_name="Recruiter",
        last_name="One",
        password_hash="dummy_hash",
        is_active=True
    )
    recruiter2 = PortalUser(
        tenant_id=sample_tenant.id,
        email="recruiter2@testcompany.com",
        first_name="Recruiter",
        last_name="Two",
        password_hash="dummy_hash",
        is_active=True
    )
    db.session.add_all([recruiter1, recruiter2])
    db.session.commit()
    return {'recruiter1': recruiter1, 'recruiter2': recruiter2}


@pytest.fixture
def sample_candidate(db, sample_tenant):
    """Create a sample candidate"""
    candidate = Candidate(
        tenant_id=sample_tenant.id,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="1234567890",
        onboarding_status="PENDING_ASSIGNMENT"
    )
    db.session.add(candidate)
    db.session.commit()
    return candidate


@pytest.mark.unit
class TestCandidateAssignmentServiceAssign:
    """Tests for candidate assignment"""
    
    def test_assign_candidate_success(self, db, sample_tenant, sample_candidate, sample_users):
        """Test assigning a candidate to a recruiter"""
        result = CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id,
            reason="Initial assignment"
        )
        
        assert result is not None
        assert result['candidate_id'] == sample_candidate.id
        assert result['assigned_to_user_id'] == sample_users['recruiter1'].id
        assert result['assignment_type'] == 'ASSIGNMENT'
        assert result['status'] == 'ACTIVE'
        
        # Verify candidate status updated
        db.session.refresh(sample_candidate)
        assert sample_candidate.onboarding_status == 'ASSIGNED'
        assert sample_candidate.assigned_to == sample_users['recruiter1'].id
        
        # Verify assignment record created
        assignment = db.session.query(CandidateAssignment).filter_by(
            candidate_id=sample_candidate.id
        ).first()
        assert assignment is not None
        assert assignment.status == 'ACTIVE'
        assert assignment.assignment_type == 'ASSIGNMENT'
        
        # Verify notification created
        notification = db.session.query(AssignmentNotification).filter_by(
            user_id=sample_users['recruiter1'].id,
            assignment_id=assignment.id
        ).first()
        assert notification is not None
        assert notification.notification_type == 'ASSIGNMENT'
        assert notification.is_read is False
    
    def test_assign_candidate_minimal_data(self, db, sample_tenant, sample_candidate, sample_users):
        """Test assigning candidate without optional reason"""
        result = CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert result['candidate_id'] == sample_candidate.id
    
    def test_assign_candidate_already_assigned_fails(self, db, sample_tenant, sample_candidate, sample_users):
        """Test assigning a candidate that is already assigned"""
        # First assignment
        CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        # Try second assignment (should fail)
        with pytest.raises(ValueError, match="already has an active assignment"):
            CandidateAssignmentService.assign_candidate(
                candidate_id=sample_candidate.id,
                assigned_to_user_id=sample_users['recruiter2'].id,
                assigned_by_user_id=sample_users['recruiter1'].id,
                tenant_id=sample_tenant.id
            )
    
    def test_assign_candidate_not_found(self, db, sample_tenant, sample_users):
        """Test assigning non-existent candidate"""
        with pytest.raises(ValueError, match="Candidate not found"):
            CandidateAssignmentService.assign_candidate(
                candidate_id=99999,
                assigned_to_user_id=sample_users['recruiter1'].id,
                assigned_by_user_id=sample_users['recruiter2'].id,
                tenant_id=sample_tenant.id
            )
    
    def test_assign_candidate_user_not_found(self, db, sample_tenant, sample_candidate, sample_users):
        """Test assigning to non-existent user"""
        with pytest.raises(ValueError, match="Assigned user not found"):
            CandidateAssignmentService.assign_candidate(
                candidate_id=sample_candidate.id,
                assigned_to_user_id=99999,
                assigned_by_user_id=sample_users['recruiter2'].id,
                tenant_id=sample_tenant.id
            )


@pytest.mark.unit
class TestCandidateAssignmentServiceReassign:
    """Tests for candidate reassignment"""
    
    def test_reassign_candidate_success(self, db, sample_tenant, sample_candidate, sample_users):
        """Test reassigning a candidate to a different recruiter"""
        # Initial assignment
        CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        # Reassign
        result = CandidateAssignmentService.reassign_candidate(
            candidate_id=sample_candidate.id,
            new_assigned_to_user_id=sample_users['recruiter2'].id,
            reassigned_by_user_id=sample_users['recruiter1'].id,
            tenant_id=sample_tenant.id,
            reason="Workload balancing"
        )
        
        assert result is not None
        assert result['candidate_id'] == sample_candidate.id
        assert result['assigned_to_user_id'] == sample_users['recruiter2'].id
        assert result['assignment_type'] == 'REASSIGNMENT'
        
        # Verify old assignment completed
        old_assignment = db.session.query(CandidateAssignment).filter_by(
            candidate_id=sample_candidate.id,
            assigned_to=sample_users['recruiter1'].id
        ).first()
        assert old_assignment.status == 'COMPLETED'
        assert old_assignment.completion_date is not None
        
        # Verify new assignment active
        new_assignment = db.session.query(CandidateAssignment).filter_by(
            candidate_id=sample_candidate.id,
            assigned_to=sample_users['recruiter2'].id,
            status='ACTIVE'
        ).first()
        assert new_assignment is not None
        assert new_assignment.assignment_type == 'REASSIGNMENT'
        
        # Verify notification sent to new assignee
        notification = db.session.query(AssignmentNotification).filter_by(
            user_id=sample_users['recruiter2'].id,
            notification_type='REASSIGNMENT'
        ).first()
        assert notification is not None
    
    def test_reassign_candidate_no_active_assignment(self, db, sample_tenant, sample_candidate, sample_users):
        """Test reassigning candidate with no active assignment"""
        with pytest.raises(ValueError, match="does not have an active assignment"):
            CandidateAssignmentService.reassign_candidate(
                candidate_id=sample_candidate.id,
                new_assigned_to_user_id=sample_users['recruiter2'].id,
                reassigned_by_user_id=sample_users['recruiter1'].id,
                tenant_id=sample_tenant.id
            )
    
    def test_reassign_to_same_user_fails(self, db, sample_tenant, sample_candidate, sample_users):
        """Test reassigning to the same user"""
        # Initial assignment
        CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        # Try to reassign to same user
        with pytest.raises(ValueError, match="already assigned to this user"):
            CandidateAssignmentService.reassign_candidate(
                candidate_id=sample_candidate.id,
                new_assigned_to_user_id=sample_users['recruiter1'].id,
                reassigned_by_user_id=sample_users['recruiter2'].id,
                tenant_id=sample_tenant.id
            )


@pytest.mark.unit
class TestCandidateAssignmentServiceUnassign:
    """Tests for candidate unassignment"""
    
    def test_unassign_candidate_success(self, db, sample_tenant, sample_candidate, sample_users):
        """Test unassigning a candidate"""
        # Initial assignment
        CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        # Unassign
        result = CandidateAssignmentService.unassign_candidate(
            candidate_id=sample_candidate.id,
            unassigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert result['candidate_id'] == sample_candidate.id
        
        # Verify candidate status reset
        db.session.refresh(sample_candidate)
        assert sample_candidate.onboarding_status == 'PENDING_ASSIGNMENT'
        assert sample_candidate.assigned_to is None
        
        # Verify assignment cancelled
        assignment = db.session.query(CandidateAssignment).filter_by(
            candidate_id=sample_candidate.id
        ).first()
        assert assignment.status == 'CANCELLED'
        
        # Verify notification sent
        notification = db.session.query(AssignmentNotification).filter_by(
            user_id=sample_users['recruiter1'].id,
            notification_type='UNASSIGNMENT'
        ).first()
        assert notification is not None
    
    def test_unassign_candidate_no_assignment(self, db, sample_tenant, sample_candidate, sample_users):
        """Test unassigning candidate with no assignment"""
        with pytest.raises(ValueError, match="does not have an active assignment"):
            CandidateAssignmentService.unassign_candidate(
                candidate_id=sample_candidate.id,
                unassigned_by_user_id=sample_users['recruiter1'].id,
                tenant_id=sample_tenant.id
            )


@pytest.mark.unit
class TestCandidateAssignmentServiceHistory:
    """Tests for assignment history and queries"""
    
    def test_get_candidate_assignments(self, db, sample_tenant, sample_candidate, sample_users):
        """Test getting assignment history for a candidate"""
        # Create assignment
        CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        result = CandidateAssignmentService.get_candidate_assignments(
            candidate_id=sample_candidate.id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert len(result['assignments']) == 1
        assert result['assignments'][0]['candidate_id'] == sample_candidate.id
        assert result['assignments'][0]['status'] == 'ACTIVE'
    
    def test_get_user_assignments(self, db, sample_tenant, sample_candidate, sample_users):
        """Test getting assignments for a user"""
        # Create assignment
        CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        result = CandidateAssignmentService.get_user_assignments(
            user_id=sample_users['recruiter1'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert len(result['candidates']) >= 1
        candidate_ids = [c['id'] for c in result['candidates']]
        assert sample_candidate.id in candidate_ids
    
    def test_get_assignment_history_multiple(self, db, sample_tenant, sample_candidate, sample_users):
        """Test assignment history with multiple assignments"""
        # Assign
        CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        # Reassign
        CandidateAssignmentService.reassign_candidate(
            candidate_id=sample_candidate.id,
            new_assigned_to_user_id=sample_users['recruiter2'].id,
            reassigned_by_user_id=sample_users['recruiter1'].id,
            tenant_id=sample_tenant.id
        )
        
        result = CandidateAssignmentService.get_assignment_history(
            tenant_id=sample_tenant.id,
            limit=10
        )
        
        assert result is not None
        assert len(result['assignments']) == 2
        
        # Verify order (most recent first)
        assert result['assignments'][0]['assignment_type'] == 'REASSIGNMENT'
        assert result['assignments'][1]['assignment_type'] == 'ASSIGNMENT'


@pytest.mark.unit
class TestCandidateAssignmentServiceNotifications:
    """Tests for notification management"""
    
    def test_get_user_notifications(self, db, sample_tenant, sample_candidate, sample_users):
        """Test getting notifications for a user"""
        # Create assignment (creates notification)
        CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        result = CandidateAssignmentService.get_user_notifications(
            user_id=sample_users['recruiter1'].id,
            tenant_id=sample_tenant.id,
            unread_only=False
        )
        
        assert result is not None
        assert len(result['notifications']) == 1
        assert result['notifications'][0]['notification_type'] == 'ASSIGNMENT'
        assert result['notifications'][0]['is_read'] is False
    
    def test_get_unread_notifications_only(self, db, sample_tenant, sample_candidate, sample_users):
        """Test filtering unread notifications"""
        # Create assignment
        assignment = CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        # Get notification and mark as read
        notification = db.session.query(AssignmentNotification).filter_by(
            user_id=sample_users['recruiter1'].id
        ).first()
        notification.is_read = True
        db.session.commit()
        
        # Query unread only
        result = CandidateAssignmentService.get_user_notifications(
            user_id=sample_users['recruiter1'].id,
            tenant_id=sample_tenant.id,
            unread_only=True
        )
        
        assert len(result['notifications']) == 0
        assert result['unread_count'] == 0
    
    def test_mark_notification_as_read(self, db, sample_tenant, sample_candidate, sample_users):
        """Test marking a notification as read"""
        # Create assignment
        CandidateAssignmentService.assign_candidate(
            candidate_id=sample_candidate.id,
            assigned_to_user_id=sample_users['recruiter1'].id,
            assigned_by_user_id=sample_users['recruiter2'].id,
            tenant_id=sample_tenant.id
        )
        
        # Get notification
        notification = db.session.query(AssignmentNotification).filter_by(
            user_id=sample_users['recruiter1'].id
        ).first()
        
        # Mark as read
        result = CandidateAssignmentService.mark_notification_as_read(
            notification_id=notification.id,
            user_id=sample_users['recruiter1'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert result['is_read'] is True
        
        # Verify in database
        db.session.refresh(notification)
        assert notification.is_read is True
        assert notification.read_date is not None
    
    def test_mark_all_notifications_as_read(self, db, sample_tenant, sample_users):
        """Test marking all notifications as read for a user"""
        # Create multiple candidates and assignments
        for i in range(3):
            candidate = Candidate(
                tenant_id=sample_tenant.id,
                first_name=f"Candidate{i}",
                last_name="Test",
                email=f"candidate{i}@example.com",
                onboarding_status="PENDING_ASSIGNMENT"
            )
            db.session.add(candidate)
            db.session.flush()
            
            CandidateAssignmentService.assign_candidate(
                candidate_id=candidate.id,
                assigned_to_user_id=sample_users['recruiter1'].id,
                assigned_by_user_id=sample_users['recruiter2'].id,
                tenant_id=sample_tenant.id
            )
        
        # Mark all as read
        result = CandidateAssignmentService.mark_all_notifications_as_read(
            user_id=sample_users['recruiter1'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert result['marked_count'] == 3
        
        # Verify all are read
        notifications = db.session.query(AssignmentNotification).filter_by(
            user_id=sample_users['recruiter1'].id
        ).all()
        assert all(n.is_read for n in notifications)


@pytest.mark.unit
class TestCandidateAssignmentServiceEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_assign_to_different_tenant_user(self, db, sample_candidate, sample_users):
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
            CandidateAssignmentService.assign_candidate(
                candidate_id=sample_candidate.id,
                assigned_to_user_id=other_user.id,
                assigned_by_user_id=sample_users['recruiter1'].id,
                tenant_id=sample_candidate.tenant_id
            )
    
    def test_notification_not_found(self, db, sample_tenant, sample_users):
        """Test marking non-existent notification"""
        with pytest.raises(ValueError, match="Notification not found"):
            CandidateAssignmentService.mark_notification_as_read(
                notification_id=99999,
                user_id=sample_users['recruiter1'].id,
                tenant_id=sample_tenant.id
            )

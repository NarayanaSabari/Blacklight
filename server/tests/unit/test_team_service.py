"""
Unit tests for TeamService
Tests team hierarchy management, manager assignments, and cycle detection
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.team_service import TeamService
from app.models import PortalUser, Tenant


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
    """Create sample users with manager relationships"""
    # CEO (no manager)
    ceo = PortalUser(
        tenant_id=sample_tenant.id,
        email="ceo@testcompany.com",
        first_name="CEO",
        last_name="Boss",
        password_hash="dummy_hash",
        is_active=True,
        manager_id=None
    )
    db.session.add(ceo)
    db.session.flush()
    
    # VP (reports to CEO)
    vp = PortalUser(
        tenant_id=sample_tenant.id,
        email="vp@testcompany.com",
        first_name="VP",
        last_name="Leader",
        password_hash="dummy_hash",
        is_active=True,
        manager_id=ceo.id
    )
    db.session.add(vp)
    db.session.flush()
    
    # Manager (reports to VP)
    manager = PortalUser(
        tenant_id=sample_tenant.id,
        email="manager@testcompany.com",
        first_name="Manager",
        last_name="Person",
        password_hash="dummy_hash",
        is_active=True,
        manager_id=vp.id
    )
    db.session.add(manager)
    db.session.flush()
    
    # Employee (reports to Manager)
    employee = PortalUser(
        tenant_id=sample_tenant.id,
        email="employee@testcompany.com",
        first_name="Employee",
        last_name="Worker",
        password_hash="dummy_hash",
        is_active=True,
        manager_id=manager.id
    )
    db.session.add(employee)
    db.session.commit()
    
    return {
        'ceo': ceo,
        'vp': vp,
        'manager': manager,
        'employee': employee
    }


@pytest.mark.unit
class TestTeamServiceHierarchy:
    """Tests for team hierarchy retrieval"""
    
    def test_get_team_hierarchy_full(self, db, sample_tenant, sample_users):
        """Test retrieving full team hierarchy"""
        hierarchy = TeamService.get_team_hierarchy(sample_tenant.id)
        
        assert hierarchy is not None
        assert len(hierarchy) == 4  # All 4 users
        
        # CEO should be at top (no manager)
        ceo_entry = next(u for u in hierarchy if u['id'] == sample_users['ceo'].id)
        assert ceo_entry['manager_id'] is None
        assert ceo_entry['level'] == 0
        
        # VP should report to CEO
        vp_entry = next(u for u in hierarchy if u['id'] == sample_users['vp'].id)
        assert vp_entry['manager_id'] == sample_users['ceo'].id
        assert vp_entry['level'] == 1
        
        # Manager should report to VP
        manager_entry = next(u for u in hierarchy if u['id'] == sample_users['manager'].id)
        assert manager_entry['manager_id'] == sample_users['vp'].id
        assert manager_entry['level'] == 2
        
        # Employee should report to Manager
        employee_entry = next(u for u in hierarchy if u['id'] == sample_users['employee'].id)
        assert employee_entry['manager_id'] == sample_users['manager'].id
        assert employee_entry['level'] == 3
    
    def test_get_team_tree_structure(self, db, sample_tenant, sample_users):
        """Test retrieving team tree structure"""
        tree = TeamService.get_team_tree(sample_tenant.id)
        
        assert tree is not None
        assert len(tree) == 1  # Only CEO at root
        
        # Check CEO node
        ceo_node = tree[0]
        assert ceo_node['id'] == sample_users['ceo'].id
        assert ceo_node['manager_id'] is None
        assert 'direct_reports' in ceo_node
        assert len(ceo_node['direct_reports']) == 1  # VP reports to CEO
        
        # Check VP node
        vp_node = ceo_node['direct_reports'][0]
        assert vp_node['id'] == sample_users['vp'].id
        assert len(vp_node['direct_reports']) == 1  # Manager reports to VP
        
        # Check Manager node
        manager_node = vp_node['direct_reports'][0]
        assert manager_node['id'] == sample_users['manager'].id
        assert len(manager_node['direct_reports']) == 1  # Employee reports to Manager
        
        # Check Employee node (leaf)
        employee_node = manager_node['direct_reports'][0]
        assert employee_node['id'] == sample_users['employee'].id
        assert len(employee_node['direct_reports']) == 0  # No reports
    
    def test_get_team_hierarchy_empty_tenant(self, db, sample_tenant):
        """Test hierarchy for tenant with no users"""
        hierarchy = TeamService.get_team_hierarchy(sample_tenant.id)
        assert hierarchy == []
    
    def test_get_team_tree_empty_tenant(self, db, sample_tenant):
        """Test tree for tenant with no users"""
        tree = TeamService.get_team_tree(sample_tenant.id)
        assert tree == []


@pytest.mark.unit
class TestTeamServiceManagers:
    """Tests for manager management"""
    
    def test_get_team_managers(self, db, sample_tenant, sample_users):
        """Test retrieving list of managers"""
        managers = TeamService.get_team_managers(sample_tenant.id)
        
        assert managers is not None
        assert len(managers) == 3  # CEO, VP, Manager (all have reports)
        
        # Check manager details
        manager_ids = [m['id'] for m in managers]
        assert sample_users['ceo'].id in manager_ids
        assert sample_users['vp'].id in manager_ids
        assert sample_users['manager'].id in manager_ids
        assert sample_users['employee'].id not in manager_ids  # Has no reports
        
        # Check report counts
        ceo_manager = next(m for m in managers if m['id'] == sample_users['ceo'].id)
        assert ceo_manager['report_count'] == 1  # VP
        
        vp_manager = next(m for m in managers if m['id'] == sample_users['vp'].id)
        assert vp_manager['report_count'] == 1  # Manager
        
        manager_manager = next(m for m in managers if m['id'] == sample_users['manager'].id)
        assert manager_manager['report_count'] == 1  # Employee
    
    def test_assign_manager_success(self, db, sample_tenant, sample_users):
        """Test assigning a manager to a user"""
        # Assign CEO as manager to employee (bypassing current hierarchy)
        result = TeamService.assign_manager(
            user_id=sample_users['employee'].id,
            manager_id=sample_users['ceo'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert result['user_id'] == sample_users['employee'].id
        assert result['manager_id'] == sample_users['ceo'].id
        
        # Verify in database
        db.session.refresh(sample_users['employee'])
        assert sample_users['employee'].manager_id == sample_users['ceo'].id
    
    def test_assign_manager_to_self_fails(self, db, sample_tenant, sample_users):
        """Test that user cannot be their own manager"""
        with pytest.raises(ValueError, match="cannot be their own manager"):
            TeamService.assign_manager(
                user_id=sample_users['ceo'].id,
                manager_id=sample_users['ceo'].id,
                tenant_id=sample_tenant.id
            )
    
    def test_assign_manager_creates_cycle_fails(self, db, sample_tenant, sample_users):
        """Test that creating a cycle is prevented"""
        # Try to make CEO report to Employee (would create cycle)
        with pytest.raises(ValueError, match="would create a circular reporting structure"):
            TeamService.assign_manager(
                user_id=sample_users['ceo'].id,
                manager_id=sample_users['employee'].id,
                tenant_id=sample_tenant.id
            )
    
    def test_assign_manager_different_tenant_fails(self, db, sample_users):
        """Test that users from different tenants cannot be linked"""
        # Create another tenant
        other_tenant = Tenant(
            name="Other Company",
            subdomain="othercompany",
            status="ACTIVE",
            settings={}
        )
        db.session.add(other_tenant)
        db.session.flush()
        
        # Create user in other tenant
        other_user = PortalUser(
            tenant_id=other_tenant.id,
            email="other@othercompany.com",
            first_name="Other",
            last_name="User",
            password_hash="dummy_hash",
            is_active=True
        )
        db.session.add(other_user)
        db.session.commit()
        
        # Try to assign manager from different tenant
        with pytest.raises(ValueError, match="belong to different tenants"):
            TeamService.assign_manager(
                user_id=sample_users['employee'].id,
                manager_id=other_user.id,
                tenant_id=sample_users['employee'].tenant_id
            )
    
    def test_remove_manager_success(self, db, sample_tenant, sample_users):
        """Test removing a manager from a user"""
        result = TeamService.remove_manager(
            user_id=sample_users['employee'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert result['user_id'] == sample_users['employee'].id
        assert result['manager_id'] is None
        
        # Verify in database
        db.session.refresh(sample_users['employee'])
        assert sample_users['employee'].manager_id is None
    
    def test_remove_manager_no_manager(self, db, sample_tenant, sample_users):
        """Test removing manager from user who has no manager"""
        # CEO has no manager
        result = TeamService.remove_manager(
            user_id=sample_users['ceo'].id,
            tenant_id=sample_tenant.id
        )
        
        assert result is not None
        assert result['manager_id'] is None
    
    def test_remove_manager_user_not_found(self, db, sample_tenant):
        """Test removing manager for non-existent user"""
        with pytest.raises(ValueError, match="User not found"):
            TeamService.remove_manager(
                user_id=99999,
                tenant_id=sample_tenant.id
            )


@pytest.mark.unit
class TestTeamServiceCycleDetection:
    """Tests for cycle detection algorithm"""
    
    def test_detect_simple_cycle(self, db, sample_tenant, sample_users):
        """Test detecting a simple 2-node cycle"""
        # Try VP -> CEO -> VP (cycle)
        detected = TeamService._detect_hierarchy_cycle(
            user_id=sample_users['ceo'].id,
            new_manager_id=sample_users['vp'].id,
            tenant_id=sample_tenant.id
        )
        assert detected is True
    
    def test_detect_complex_cycle(self, db, sample_tenant, sample_users):
        """Test detecting a longer cycle chain"""
        # Try CEO -> Employee (would create CEO -> Employee -> Manager -> VP -> CEO)
        detected = TeamService._detect_hierarchy_cycle(
            user_id=sample_users['ceo'].id,
            new_manager_id=sample_users['employee'].id,
            tenant_id=sample_tenant.id
        )
        assert detected is True
    
    def test_no_cycle_valid_assignment(self, db, sample_tenant, sample_users):
        """Test that valid assignments don't trigger false cycle detection"""
        # Employee -> CEO is valid (no cycle)
        detected = TeamService._detect_hierarchy_cycle(
            user_id=sample_users['employee'].id,
            new_manager_id=sample_users['ceo'].id,
            tenant_id=sample_tenant.id
        )
        assert detected is False
    
    def test_no_cycle_reassignment(self, db, sample_tenant, sample_users):
        """Test reassigning within same branch"""
        # Manager -> CEO is valid (skipping VP)
        detected = TeamService._detect_hierarchy_cycle(
            user_id=sample_users['manager'].id,
            new_manager_id=sample_users['ceo'].id,
            tenant_id=sample_tenant.id
        )
        assert detected is False


@pytest.mark.unit
class TestTeamServiceEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_assign_manager_user_not_found(self, db, sample_tenant):
        """Test assigning manager to non-existent user"""
        with pytest.raises(ValueError, match="User not found"):
            TeamService.assign_manager(
                user_id=99999,
                manager_id=1,
                tenant_id=sample_tenant.id
            )
    
    def test_assign_manager_manager_not_found(self, db, sample_tenant, sample_users):
        """Test assigning non-existent manager"""
        with pytest.raises(ValueError, match="Manager not found"):
            TeamService.assign_manager(
                user_id=sample_users['employee'].id,
                manager_id=99999,
                tenant_id=sample_tenant.id
            )
    
    def test_get_hierarchy_invalid_tenant(self, db):
        """Test getting hierarchy for non-existent tenant"""
        hierarchy = TeamService.get_team_hierarchy(99999)
        assert hierarchy == []
    
    def test_deep_hierarchy_levels(self, db, sample_tenant):
        """Test hierarchy with many levels"""
        users = []
        prev_user = None
        
        # Create 10 levels deep
        for i in range(10):
            user = PortalUser(
                tenant_id=sample_tenant.id,
                email=f"level{i}@testcompany.com",
                first_name=f"Level{i}",
                last_name="User",
                password_hash="dummy_hash",
                is_active=True,
                manager_id=prev_user.id if prev_user else None
            )
            db.session.add(user)
            db.session.flush()
            users.append(user)
            prev_user = user
        
        db.session.commit()
        
        # Get hierarchy
        hierarchy = TeamService.get_team_hierarchy(sample_tenant.id)
        assert len(hierarchy) == 10
        
        # Verify levels
        for i, user in enumerate(users):
            entry = next(u for u in hierarchy if u['id'] == user.id)
            assert entry['level'] == i
    
    def test_multiple_root_users(self, db, sample_tenant):
        """Test hierarchy with multiple users without managers"""
        # Create 3 independent users (no managers)
        for i in range(3):
            user = PortalUser(
                tenant_id=sample_tenant.id,
                email=f"root{i}@testcompany.com",
                first_name=f"Root{i}",
                last_name="User",
                password_hash="dummy_hash",
                is_active=True,
                manager_id=None
            )
            db.session.add(user)
        db.session.commit()
        
        # Get tree
        tree = TeamService.get_team_tree(sample_tenant.id)
        assert len(tree) == 3  # Three separate root nodes
        
        for node in tree:
            assert node['manager_id'] is None
            assert node['level'] == 0

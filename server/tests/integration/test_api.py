"""Tests for user API endpoints."""

import pytest
from app.models import User


@pytest.mark.unit
class TestListUsers:
    """Test list users endpoint."""
    
    def test_list_users_returns_200(self, client, sample_users):
        """Test list users returns 200."""
        response = client.get("/api/users")
        assert response.status_code == 200
    
    def test_list_users_contains_required_fields(self, client, sample_users):
        """Test list users response contains required fields."""
        response = client.get("/api/users")
        data = response.get_json()
        
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
    
    def test_list_users_pagination(self, client, sample_users):
        """Test list users pagination."""
        response = client.get("/api/users?page=1&per_page=2")
        data = response.get_json()
        
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 2
    
    def test_list_users_empty(self, client):
        """Test list users when no users exist."""
        response = client.get("/api/users")
        data = response.get_json()
        
        assert data["items"] == []
        assert data["total"] == 0


@pytest.mark.unit
class TestGetUser:
    """Test get user endpoint."""
    
    def test_get_user_returns_200(self, client, sample_user):
        """Test get user returns 200."""
        response = client.get(f"/api/users/{sample_user.id}")
        assert response.status_code == 200
    
    def test_get_user_contains_user_data(self, client, sample_user):
        """Test get user response contains user data."""
        response = client.get(f"/api/users/{sample_user.id}")
        data = response.get_json()
        
        assert data["id"] == sample_user.id
        assert data["username"] == sample_user.username
        assert data["email"] == sample_user.email
    
    def test_get_user_not_found(self, client):
        """Test get user returns 404 when not found."""
        response = client.get("/api/users/999")
        assert response.status_code == 404
        
        data = response.get_json()
        assert data["error"] == "Error"


@pytest.mark.unit
class TestCreateUser:
    """Test create user endpoint."""
    
    def test_create_user_returns_201(self, client):
        """Test create user returns 201."""
        response = client.post(
            "/api/users",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 201
    
    def test_create_user_contains_user_data(self, client):
        """Test create user response contains user data."""
        response = client.post(
            "/api/users",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123",
            },
        )
        data = response.get_json()
        
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert data["is_active"] is True
    
    def test_create_user_duplicate_username(self, client, sample_user):
        """Test create user with duplicate username."""
        response = client.post(
            "/api/users",
            json={
                "username": sample_user.username,
                "email": "different@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 409
    
    def test_create_user_invalid_email(self, client):
        """Test create user with invalid email."""
        response = client.post(
            "/api/users",
            json={
                "username": "newuser",
                "email": "invalid-email",
                "password": "password123",
            },
        )
        assert response.status_code == 400
    
    def test_create_user_short_password(self, client):
        """Test create user with short password."""
        response = client.post(
            "/api/users",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 400
    
    def test_create_user_missing_fields(self, client):
        """Test create user with missing fields."""
        response = client.post(
            "/api/users",
            json={
                "username": "newuser",
            },
        )
        assert response.status_code == 400


@pytest.mark.unit
class TestUpdateUser:
    """Test update user endpoint."""
    
    def test_update_user_returns_200(self, client, sample_user):
        """Test update user returns 200."""
        response = client.put(
            f"/api/users/{sample_user.id}",
            json={
                "username": "updateduser",
            },
        )
        assert response.status_code == 200
    
    def test_update_user_updates_data(self, client, sample_user, db):
        """Test update user updates data."""
        client.put(
            f"/api/users/{sample_user.id}",
            json={
                "username": "updateduser",
            },
        )
        
        # Refresh from database
        db.session.refresh(sample_user)
        assert sample_user.username == "updateduser"
    
    def test_update_user_not_found(self, client):
        """Test update user returns 404 when not found."""
        response = client.put(
            "/api/users/999",
            json={
                "username": "updateduser",
            },
        )
        assert response.status_code == 404
    
    def test_patch_user(self, client, sample_user):
        """Test PATCH also works for updating user."""
        response = client.patch(
            f"/api/users/{sample_user.id}",
            json={
                "is_active": False,
            },
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["is_active"] is False


@pytest.mark.unit
class TestDeleteUser:
    """Test delete user endpoint."""
    
    def test_delete_user_returns_200(self, client, sample_user):
        """Test delete user returns 200."""
        response = client.delete(f"/api/users/{sample_user.id}")
        assert response.status_code == 200
    
    def test_delete_user_removes_user(self, client, sample_user, db):
        """Test delete user removes user from database."""
        user_id = sample_user.id
        client.delete(f"/api/users/{user_id}")
        
        assert db.session.get(User, user_id) is None
    
    def test_delete_user_not_found(self, client):
        """Test delete user returns 404 when not found."""
        response = client.delete("/api/users/999")
        assert response.status_code == 404


@pytest.mark.integration
class TestUserAuditLogging:
    """Test user audit logging."""
    
    def test_create_user_creates_audit_log(self, client, db):
        """Test creating user creates audit log."""
        response = client.post(
            "/api/users",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123",
            },
        )
        
        # Check audit log was created
        from app.models import AuditLog
        logs = db.session.query(AuditLog).filter_by(action="CREATE").all()
        assert len(logs) > 0

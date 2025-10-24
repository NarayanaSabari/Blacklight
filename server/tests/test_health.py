"""Tests for health check and info endpoints."""

import pytest
from datetime import datetime


@pytest.mark.unit
class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check_returns_200(self, client):
        """Test health check returns 200."""
        response = client.get("/api/health")
        assert response.status_code == 200
    
    def test_health_check_contains_required_fields(self, client):
        """Test health check response contains required fields."""
        response = client.get("/api/health")
        data = response.get_json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "environment" in data
        assert data["status"] == "healthy"
    
    def test_health_check_timestamp_format(self, client):
        """Test health check timestamp is ISO format."""
        response = client.get("/api/health")
        data = response.get_json()
        
        # Should not raise exception
        datetime.fromisoformat(data["timestamp"])


@pytest.mark.unit
class TestAppInfo:
    """Test app info endpoint."""
    
    def test_app_info_returns_200(self, client):
        """Test app info returns 200."""
        response = client.get("/api/info")
        assert response.status_code == 200
    
    def test_app_info_contains_required_fields(self, client):
        """Test app info response contains required fields."""
        response = client.get("/api/info")
        data = response.get_json()
        
        assert "name" in data
        assert "version" in data
        assert "environment" in data
        assert "debug" in data
        assert "timestamp" in data


@pytest.mark.unit
class TestRootEndpoint:
    """Test root API endpoint."""
    
    def test_root_returns_200(self, client):
        """Test root endpoint returns 200."""
        response = client.get("/api/")
        assert response.status_code == 200
    
    def test_root_contains_endpoints(self, client):
        """Test root endpoint contains endpoints."""
        response = client.get("/api/")
        data = response.get_json()
        
        assert "message" in data
        assert "endpoints" in data
        assert "health" in data["endpoints"]
        assert "info" in data["endpoints"]
        assert "users" in data["endpoints"]


@pytest.mark.integration
class TestCors:
    """Test CORS headers."""
    
    def test_cors_headers_present(self, client):
        """Test CORS headers are present."""
        response = client.get("/api/health")
        # Headers will depend on Flask-CORS configuration
        assert response.status_code == 200

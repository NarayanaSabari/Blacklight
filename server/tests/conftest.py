"""Pytest configuration and fixtures."""

import pytest
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db as app_db
from config.testing import TestingConfig
from app.models import User, AuditLog


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    app = create_app(config=TestingConfig)
    return app


@pytest.fixture(scope="function")
def client(app):
    """Flask test client."""
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture(scope="function")
def db(app):
    """Database session for testing."""
    with app.app_context():
        # Create all tables
        app_db.create_all()
        yield app_db
        # Drop all tables
        app_db.session.remove()
        app_db.drop_all()


@pytest.fixture(scope="function")
def runner(app):
    """Flask CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def sample_user(db):
    """Create a sample user."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hash123",
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_users(db):
    """Create multiple sample users."""
    users = [
        User(
            username=f"user{i}",
            email=f"user{i}@example.com",
            password_hash="hash123",
            is_active=True,
        )
        for i in range(5)
    ]
    db.session.add_all(users)
    db.session.commit()
    return users


@pytest.fixture
def sample_audit_log(db, sample_user):
    """Create a sample audit log."""
    log = AuditLog(
        action="CREATE",
        entity_type="User",
        entity_id=sample_user.id,
        changes={"username": "testuser"},
        user_id=sample_user.id,
    )
    db.session.add(log)
    db.session.commit()
    return log

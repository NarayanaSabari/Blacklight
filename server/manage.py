"""Management CLI commands."""

import os
import sys
from datetime import datetime

from flask import Flask
from app import create_app, db


def init_db(app: Flask) -> None:
    """Initialize the database."""
    with app.app_context():
        db.create_all()
        app.logger.info("Database initialized successfully")


def drop_db(app: Flask, confirm: bool = False) -> None:
    """Drop all database tables."""
    if not confirm:
        response = input("Are you sure you want to drop all tables? [y/N]: ")
        if response.lower() != "y":
            print("Operation cancelled")
            return
    
    with app.app_context():
        db.drop_all()
        app.logger.info("Database dropped successfully")


def seed_db(app: Flask) -> None:
    """Seed the database with sample data."""
    from app.models import User, AuditLog
    import hashlib
    
    with app.app_context():
        # Check if data already exists
        if User.query.first():
            print("Database already has data. Skipping seed.")
            return
        
        # Create sample users
        users = [
            User(
                username="admin",
                email="admin@example.com",
                password_hash=hashlib.sha256(b"admin123").hexdigest(),
                is_active=True,
            ),
            User(
                username="user1",
                email="user1@example.com",
                password_hash=hashlib.sha256(b"user123").hexdigest(),
                is_active=True,
            ),
        ]
        
        db.session.add_all(users)
        db.session.commit()
        
        # Create sample audit logs
        audit_logs = [
            AuditLog(
                action="CREATE",
                entity_type="User",
                entity_id=users[0].id,
                changes={"username": "admin", "email": "admin@example.com"},
                user_id=None,
            ),
        ]
        
        db.session.add_all(audit_logs)
        db.session.commit()
        
        print(f"Database seeded with {len(users)} users and {len(audit_logs)} audit logs")


def migrate(app: Flask) -> None:
    """Run database migrations."""
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config("alembic.ini")
    
    with app.app_context():
        command.upgrade(alembic_cfg, "head")
        print("Migrations completed successfully")


def create_migration(app: Flask, message: str) -> None:
    """Create a new migration."""
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config("alembic.ini")
    
    with app.app_context():
        command.revision(alembic_cfg, autogenerate=True, message=message)
        print(f"Migration created with message: {message}")


if __name__ == "__main__":
    app = create_app()
    
    commands = {
        "init": lambda: init_db(app),
        "drop": lambda: drop_db(app),
        "seed": lambda: seed_db(app),
        "migrate": lambda: migrate(app),
        "create-migration": lambda: create_migration(app, sys.argv[2] if len(sys.argv) > 2 else "auto"),
    }
    
    if len(sys.argv) < 2:
        print("Usage: python manage.py <command>")
        print("Commands:")
        for cmd in commands.keys():
            print(f"  {cmd}")
        sys.exit(1)
    
    command = sys.argv[1]
    if command not in commands:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    commands[command]()

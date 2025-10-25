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
    """Seed the database with sample data (legacy - deprecated)."""
    print("⚠️  Legacy seed function - use 'seed-all' for tenant management system")
    print("This function is deprecated and does nothing.")


def seed_plans(app: Flask) -> None:
    """Seed subscription plans."""
    from app.seeds.subscription_plans import seed_subscription_plans
    
    with app.app_context():
        seed_subscription_plans()


def seed_pm_admin_user(app: Flask, email: str = None, password: str = None) -> None:
    """Seed PM admin user."""
    from app.seeds.pm_admin import seed_pm_admin
    
    with app.app_context():
        seed_pm_admin(email=email, password=password)


def seed_tenants(app: Flask, count: int = 3) -> None:
    """Seed sample tenants."""
    from app.seeds.sample_tenants import seed_sample_tenants
    
    with app.app_context():
        seed_sample_tenants(count=count)


def seed_all(app: Flask) -> None:
    """Seed all data: plans, PM admin, and sample tenants."""
    print("=" * 60)
    print("SEEDING ALL DATA")
    print("=" * 60)
    
    with app.app_context():
        # 1. Seed subscription plans
        print("\n1. Seeding subscription plans...")
        from app.seeds.subscription_plans import seed_subscription_plans
        seed_subscription_plans()
        
        # 2. Seed PM admin user
        print("\n2. Seeding PM admin user...")
        from app.seeds.pm_admin import seed_pm_admin
        seed_pm_admin()
        
        # 3. Seed sample tenants
        print("\n3. Seeding sample tenants...")
        from app.seeds.sample_tenants import seed_sample_tenants
        seed_sample_tenants(count=3)
        
        print("\n" + "=" * 60)
        print("✅ ALL DATA SEEDED SUCCESSFULLY!")
        print("=" * 60)


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
        "seed-plans": lambda: seed_plans(app),
        "seed-pm-admin": lambda: seed_pm_admin_user(
            app, 
            email=sys.argv[2] if len(sys.argv) > 2 else None,
            password=sys.argv[3] if len(sys.argv) > 3 else None
        ),
        "seed-tenants": lambda: seed_tenants(
            app, 
            count=int(sys.argv[2]) if len(sys.argv) > 2 else 3
        ),
        "seed-all": lambda: seed_all(app),
    }
    
    if len(sys.argv) < 2:
        print("Usage: python manage.py <command>")
        print("\nCommands:")
        print("  init                - Initialize database")
        print("  drop                - Drop all tables")
        print("  migrate             - Run migrations")
        print("  create-migration    - Create new migration")
        print("  seed                - Seed legacy sample data")
        print("\nTenant Management Commands:")
        print("  seed-plans          - Seed subscription plans")
        print("  seed-pm-admin       - Seed PM admin user")
        print("                        Usage: seed-pm-admin [email] [password]")
        print("  seed-tenants        - Seed sample tenants")
        print("                        Usage: seed-tenants [count]")
        print("  seed-all            - Seed all (plans + PM admin + tenants)")
        sys.exit(1)
    
    command = sys.argv[1]
    if command not in commands:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    commands[command]()

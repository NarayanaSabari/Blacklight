"""Management CLI commands."""

import os
import sys
from datetime import datetime

from flask import Flask
from app import create_app, db


def init_db(app: Flask) -> None:
    """Initialize the database."""
    with app.app_context():
        # db.create_all() # Removed as migrations handle table creation
        app.logger.info("Database initialized successfully (schema managed by migrations)")


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


def seed_roles_and_permissions_command(app: Flask) -> None:
    """Seed system roles and permissions."""
    from app.seeds.roles_and_permissions import seed_roles_and_permissions
    
    with app.app_context():
        seed_roles_and_permissions()


def seed_tenants(app: Flask, count: int = 3) -> None:
    """Seed sample tenants."""
    from app.seeds.sample_tenants import seed_sample_tenants
    
    with app.app_context():
        seed_sample_tenants(count=count)


def seed_all(app: Flask) -> None:
    """Seed all data: plans, PM admin, roles, permissions, and sample tenants."""
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

        # 3. Seed roles and permissions
        print("\n3. Seeding roles and permissions...")
        from app.seeds.roles_and_permissions import seed_roles_and_permissions
        seed_roles_and_permissions()
        
        # 4. Seed sample tenants
        print("\n4. Seeding sample tenants...")
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


def stamp_db(app: Flask, revision: str = "001") -> None:
    """Stamp database with a specific migration version without running it."""
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config("alembic.ini")
    
    with app.app_context():
        command.stamp(alembic_cfg, revision)
        print(f"Database stamped with revision: {revision}")


def setup_spacy(app: Flask) -> None:
    """Download and setup spaCy model."""
    import subprocess
    
    print("=" * 60)
    print("SETTING UP SPACY MODEL")
    print("=" * 60)
    
    try:
        # Downgrade to spaCy 3.7.2 if needed (more stable)
        print("\n1. Installing spaCy 3.7.2 (stable version)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "spacy==3.7.2"], check=True)
        
        # Install model from wheel directly
        print("\n2. Installing en_core_web_sm model...")
        model_url = "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl"
        subprocess.run([sys.executable, "-m", "pip", "install", model_url], check=True)
        
        # Verify installation
        print("\n3. Verifying installation...")
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("✅ spaCy model loaded successfully!")
        print(f"   Model: en_core_web_sm v{nlp.meta['version']}")
        print(f"   spaCy: v{spacy.__version__}")
        
        print("\n" + "=" * 60)
        print("✅ SPACY SETUP COMPLETE!")
        print("=" * 60)
        print("\n⚠️  Remember to restart Flask server for changes to take effect!")
    except Exception as e:
        print(f"\n❌ Error setting up spaCy: {e}")
        print("\nTry manually:")
        print("  pip install spacy==3.7.2")
        print("  pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl")
        print("\nThen verify:")
        print("  python -c \"import spacy; nlp = spacy.load('en_core_web_sm'); print('✅ Model loaded!')\"")
        sys.exit(1)


if __name__ == "__main__":
    app = create_app()
    
    commands = {
        "init": lambda: init_db(app),
        "drop": lambda: drop_db(app),
        "seed": lambda: seed_db(app),
        "migrate": lambda: migrate(app),
        "create-migration": lambda: create_migration(app, sys.argv[2] if len(sys.argv) > 2 else "auto"),
        "stamp": lambda: stamp_db(app, sys.argv[2] if len(sys.argv) > 2 else "001"),
        "seed-plans": lambda: seed_plans(app),
        "seed-pm-admin": lambda: seed_pm_admin_user(
            app, 
            email=sys.argv[2] if len(sys.argv) > 2 else None,
            password=sys.argv[3] if len(sys.argv) > 3 else None
        ),
        "seed-roles-and-permissions": lambda: seed_roles_and_permissions_command(app),
        "seed-tenants": lambda: seed_tenants(
            app, 
            count=int(sys.argv[2]) if len(sys.argv) > 2 else 3
        ),
        "seed-all": lambda: seed_all(app),
        "setup-spacy": lambda: setup_spacy(app),
    }
    
    if len(sys.argv) < 2:
        print("Usage: python manage.py <command>")
        print("\nCommands:")
        print("  init                - Initialize database")
        print("  drop                - Drop all tables")
        print("  migrate             - Run migrations")
        print("  create-migration    - Create new migration")
        print("  stamp               - Mark database as at specific revision")
        print("                        Usage: stamp [revision] (default: 001)")
        print("  seed                - Seed legacy sample data")
        print("\nTenant Management Commands:")
        print("  seed-plans          - Seed subscription plans")
        print("  seed-pm-admin       - Seed PM admin user")
        print("                        Usage: seed-pm-admin [email] [password]")
        print("  seed-tenants        - Seed sample tenants")
        print("                        Usage: seed-tenants [count]")
        print("  seed-all            - Seed all (plans + PM admin + tenants)")
        print("\nSetup Commands:")
        print("  setup-spacy         - Download and setup spaCy model for resume parsing")
        sys.exit(1)
    
    command = sys.argv[1]
    if command not in commands:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    commands[command]()

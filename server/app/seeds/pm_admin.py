"""Seed default PM admin user."""

import os
from werkzeug.security import generate_password_hash
from app import db
from app.models import PMAdminUser


def seed_pm_admin(email=None, password=None, first_name="Super", last_name="Admin"):
    """
    Seed default PM admin user.
    
    Args:
        email: Admin email (default: from env or admin@blacklight.com)
        password: Admin password (default: from env or auto-generated)
        first_name: First name (default: "Super")
        last_name: Last name (default: "Admin")
    
    Returns:
        Tuple of (PMAdminUser, was_created: bool)
    """
    # Get defaults from environment
    default_email = os.getenv("DEFAULT_PM_ADMIN_EMAIL", "admin@blacklight.com")
    default_password = os.getenv("DEFAULT_PM_ADMIN_PASSWORD", "Admin@123")  # Change in production!
    
    email = email or default_email
    password = password or default_password
    
    print(f"Seeding PM admin user: {email}...")
    
    # Check if admin already exists
    existing_admin = PMAdminUser.query.filter_by(email=email).first()
    
    if existing_admin:
        print(f"  ⏭️  Skipped: PM admin {email} already exists")
        return existing_admin, False
    
    # Create new PM admin
    admin = PMAdminUser(
        email=email,
        password_hash=generate_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        is_active=True
    )
    
    db.session.add(admin)
    db.session.commit()
    
    print(f"  ✅ Created PM admin: {email}")
    print(f"  📧 Email: {email}")
    print(f"  🔑 Password: {password}")
    print(f"  ⚠️  IMPORTANT: Change the password after first login!")
    
    return admin, True


if __name__ == "__main__":
    from app import create_app
    import sys
    
    app = create_app()
    with app.app_context():
        # Parse command line args
        email = sys.argv[1] if len(sys.argv) > 1 else None
        password = sys.argv[2] if len(sys.argv) > 2 else None
        
        admin, created = seed_pm_admin(email=email, password=password)
        
        if created:
            print(f"\n✅ PM admin user created successfully!")
        else:
            print(f"\n⏭️  PM admin user already exists")

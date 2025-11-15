from datetime import datetime
import bcrypt
from app import db
from app.models import Tenant, SubscriptionPlan, PortalUser, TenantSubscriptionHistory, Role, UserRole
from app.models.tenant import TenantStatus, BillingCycle
from app.services import PortalUserService # Import PortalUserService


def generate_slug(name):
    """Generate URL-safe slug from name."""
    return name.lower().replace(" ", "-").replace("&", "and")


def seed_sample_tenants(count=3):
    """
    Seed sample tenants with tenant admin users.
    
    Args:
        count: Number of sample tenants to create (default: 3)
    
    Returns:
        List of created tenants
    """
    print(f"Seeding {count} sample tenants...")
    
    # Get subscription plans
    free_plan = SubscriptionPlan.query.filter_by(name="FREE").first()
    starter_plan = SubscriptionPlan.query.filter_by(name="STARTER").first()
    pro_plan = SubscriptionPlan.query.filter_by(name="PROFESSIONAL").first()
    
    if not free_plan or not starter_plan or not pro_plan:
        print("  ❌ Error: Subscription plans not found. Run seed_subscription_plans first.")
        return []
    
    # Sample tenant data
    sample_tenants = [
        {
            "name": "Acme Corporation",
            "company_email": "contact@acme-corp.com",
            "company_phone": "+1-555-0101",
            "subscription_plan": starter_plan,
            "billing_cycle": BillingCycle.MONTHLY,
            "admin": {
                "email": "admin@acme-corp.com",
                "password": "Acme@12345",
                "first_name": "John",
                "last_name": "Doe"
            }
        },
        {
            "name": "TechStart Inc",
            "company_email": "hello@techstart.io",
            "company_phone": "+1-555-0102",
            "subscription_plan": free_plan,
            "billing_cycle": BillingCycle.MONTHLY,
            "admin": {
                "email": "demo@demo.com",
                "password": "demodemo",
                "first_name": "Jane",
                "last_name": "Smith"
            }
        },
        {
            "name": "Global Recruiters LLC",
            "company_email": "info@globalrecruiters.com",
            "company_phone": "+1-555-0103",
            "subscription_plan": pro_plan,
            "billing_cycle": BillingCycle.YEARLY,
            "admin": {
                "email": "admin@globalrecruiters.com",
                "password": "Global@12345",
                "first_name": "Robert",
                "last_name": "Johnson"
            }
        }
    ]
    
    created_tenants = []
    created_count = 0
    skipped_count = 0
    
    for tenant_data in sample_tenants[:count]:
        slug = generate_slug(tenant_data["name"])
        
        # Check if tenant already exists
        existing_tenant = Tenant.query.filter_by(slug=slug).first()
        if existing_tenant:
            print(f"  ⏭️  Skipped: {tenant_data['name']} (already exists)")
            skipped_count += 1
            continue
        
        # Check if admin email already exists
        admin_email = tenant_data["admin"]["email"]
        existing_user = PortalUser.query.filter_by(email=admin_email).first()
        if existing_user:
            print(f"  ⏭️  Skipped: {tenant_data['name']} (admin email {admin_email} already exists)")
            skipped_count += 1
            continue
        
        # Create tenant
        tenant = Tenant(
            name=tenant_data["name"],
            slug=slug,
            company_email=tenant_data["company_email"],
            company_phone=tenant_data["company_phone"],
            status=TenantStatus.ACTIVE,
            subscription_plan_id=tenant_data["subscription_plan"].id,
            subscription_start_date=datetime.utcnow(),
            billing_cycle=tenant_data["billing_cycle"],
            settings={}
        )
        db.session.add(tenant)
        db.session.flush()  # Get tenant ID
        
        # Get TENANT_ADMIN role
        tenant_admin_role = db.session.query(Role).filter_by(
            name="TENANT_ADMIN", is_system_role=True
        ).first()
        
        if not tenant_admin_role:
            raise ValueError("TENANT_ADMIN system role not found. Run migrations to seed roles.")
        
        # Create tenant admin user
        admin_user = PortalUser(
            tenant_id=tenant.id,
            email=tenant_data["admin"]["email"],
            password_hash=bcrypt.hashpw(
                tenant_data["admin"]["password"].encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8"),
            first_name=tenant_data["admin"]["first_name"],
            last_name=tenant_data["admin"]["last_name"],
            is_active=True,
        )
        db.session.add(admin_user)
        db.session.flush() # Get admin_user ID
        
        # Assign TENANT_ADMIN role to the user
        user_role = UserRole(
            user_id=admin_user.id,
            role_id=tenant_admin_role.id
        )
        db.session.add(user_role)
        
        # Create subscription history entry
        history = TenantSubscriptionHistory(
            tenant_id=tenant.id,
            subscription_plan_id=tenant_data["subscription_plan"].id,
            billing_cycle=tenant_data["billing_cycle"],
            started_at=datetime.utcnow(),
            changed_by=None,  # Initial creation, no PM admin
            notes="Initial subscription on tenant creation"
        )
        db.session.add(history)
        
        created_tenants.append(tenant)
        created_count += 1
        
        print(f"  ✅ Created: {tenant_data['name']}")
        print(f"     - Slug: {slug}")
        print(f"     - Plan: {tenant_data['subscription_plan'].display_name}")
        print(f"     - Admin: {admin_email} / {tenant_data['admin']['password']}")
    
    db.session.commit()
    
    print(f"\n✅ Sample tenants seeded: {created_count} created, {skipped_count} skipped")
    
    if created_count > 0:
        print("\n⚠️  IMPORTANT: Change all passwords after first login!")
    
    return created_tenants


if __name__ == "__main__":
    from app import create_app
    import sys
    
    app = create_app()
    with app.app_context():
        # Parse command line args
        count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
        
        tenants = seed_sample_tenants(count=count)
        
        if tenants:
            print(f"\n✅ {len(tenants)} sample tenant(s) created successfully!")
        else:
            print(f"\n⏭️  No tenants created")

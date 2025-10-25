"""Seed default subscription plans."""

from app import db
from app.models import SubscriptionPlan


DEFAULT_PLANS = [
    {
        "name": "FREE",
        "display_name": "Free Plan",
        "description": "Perfect for trying out the platform",
        "price_monthly": 0.00,
        "price_yearly": 0.00,
        "max_users": 5,
        "max_candidates": 50,
        "max_jobs": 5,
        "max_storage_gb": 1,
        "features": {
            "advanced_analytics": False,
            "custom_branding": False,
            "api_access": False,
            "priority_support": False
        },
        "is_active": True,
        "sort_order": 1
    },
    {
        "name": "STARTER",
        "display_name": "Starter Plan",
        "description": "For small teams getting started",
        "price_monthly": 49.00,
        "price_yearly": 490.00,
        "max_users": 25,
        "max_candidates": 500,
        "max_jobs": 50,
        "max_storage_gb": 10,
        "features": {
            "advanced_analytics": True,
            "custom_branding": False,
            "api_access": False,
            "priority_support": False
        },
        "is_active": True,
        "sort_order": 2
    },
    {
        "name": "PROFESSIONAL",
        "display_name": "Professional Plan",
        "description": "For growing recruitment teams",
        "price_monthly": 149.00,
        "price_yearly": 1490.00,
        "max_users": 100,
        "max_candidates": 5000,
        "max_jobs": 500,
        "max_storage_gb": 100,
        "features": {
            "advanced_analytics": True,
            "custom_branding": True,
            "api_access": True,
            "priority_support": True
        },
        "is_active": True,
        "sort_order": 3
    },
    {
        "name": "ENTERPRISE",
        "display_name": "Enterprise Plan",
        "description": "For large organizations with custom needs",
        "price_monthly": 499.00,
        "price_yearly": 4990.00,
        "max_users": 999,
        "max_candidates": 99999,
        "max_jobs": 9999,
        "max_storage_gb": 1000,
        "features": {
            "advanced_analytics": True,
            "custom_branding": True,
            "api_access": True,
            "priority_support": True,
            "dedicated_support": True,
            "sla_guarantee": True
        },
        "is_active": True,
        "sort_order": 4
    }
]


def seed_subscription_plans():
    """
    Seed default subscription plans.
    
    Creates 4 default plans: FREE, STARTER, PROFESSIONAL, ENTERPRISE
    Skips if plan already exists (idempotent).
    """
    print("Seeding subscription plans...")
    
    created_count = 0
    skipped_count = 0
    
    for plan_data in DEFAULT_PLANS:
        # Check if plan already exists
        existing_plan = SubscriptionPlan.query.filter_by(name=plan_data["name"]).first()
        
        if existing_plan:
            print(f"  ⏭️  Skipped: {plan_data['name']} (already exists)")
            skipped_count += 1
            continue
        
        # Create new plan
        plan = SubscriptionPlan(**plan_data)
        db.session.add(plan)
        created_count += 1
        print(f"  ✅ Created: {plan_data['name']} - {plan_data['display_name']}")
    
    db.session.commit()
    
    print(f"\n✅ Subscription plans seeded: {created_count} created, {skipped_count} skipped")
    return created_count, skipped_count


if __name__ == "__main__":
    from app import create_app
    
    app = create_app()
    with app.app_context():
        seed_subscription_plans()

"""Seed default system roles and permissions."""

from app import db
from app.models import Role, Permission
from app.models.role import Role as RoleModel # Alias to avoid conflict with SQLAlchemy Role
from app.models.permission import Permission as PermissionModel # Alias

def seed_roles_and_permissions():
    """
    Seed initial system roles and permissions.
    """
    print("Seeding system roles and permissions...")

    # Define system roles
    system_roles_data = [
        {
            "name": "TENANT_ADMIN",
            "display_name": "Tenant Administrator",
            "description": "Full access to tenant settings, users, and all recruitment features. Can manage other users and customize tenant settings.",
            "is_system_role": True,
            "is_active": True,
            "tenant_id": None
        },
        {
            "name": "RECRUITER",
            "display_name": "Recruiter",
            "description": "Manage candidates, jobs, interviews, and client communications. Cannot manage users or tenant settings.",
            "is_system_role": True,
            "is_active": True,
            "tenant_id": None
        },
        {
            "name": "HIRING_MANAGER",
            "display_name": "Hiring Manager",
            "description": "View candidates and jobs, participate in interviews. Limited editing capabilities, cannot delete records.",
            "is_system_role": True,
            "is_active": True,
            "tenant_id": None
        },
        {
            "name": "MANAGER",
            "display_name": "Manager",
            "description": "Oversee team activities, manage jobs, and view reports. Can view and edit users, but not manage roles or tenant settings.",
            "is_system_role": True,
            "is_active": True,
            "tenant_id": None
        }
    ]

    # Define permissions
    permissions_data = [
        # Candidates
        {"name": "candidates.view", "display_name": "View Candidates", "category": "candidates", "description": "View candidate list and details"},
        {"name": "candidates.create", "display_name": "Create Candidates", "category": "candidates", "description": "Add new candidates to the system"},
        {"name": "candidates.edit", "display_name": "Edit Candidates", "category": "candidates", "description": "Update candidate information"},
        {"name": "candidates.delete", "display_name": "Delete Candidates", "category": "candidates", "description": "Remove candidates from the system"},
        {"name": "candidates.upload_resume", "display_name": "Upload Resume", "category": "candidates", "description": "Upload and manage candidate resumes"},
        {"name": "candidates.export", "display_name": "Export Candidates", "category": "candidates", "description": "Export candidate data"},
        
        # Jobs
        {"name": "jobs.view", "display_name": "View Jobs", "category": "jobs", "description": "View job postings and applications"},
        {"name": "jobs.create", "display_name": "Create Jobs", "category": "jobs", "description": "Create new job postings"},
        {"name": "jobs.edit", "display_name": "Edit Jobs", "category": "jobs", "description": "Update job posting information"},
        {"name": "jobs.delete", "display_name": "Delete Jobs", "category": "jobs", "description": "Remove job postings"},
        {"name": "jobs.publish", "display_name": "Publish Jobs", "category": "jobs", "description": "Publish jobs to external platforms"},
        {"name": "jobs.manage_applications", "display_name": "Manage Applications", "category": "jobs", "description": "Manage job applications and candidates"},
        
        # Interviews
        {"name": "interviews.view", "display_name": "View Interviews", "category": "interviews", "description": "View scheduled interviews"},
        {"name": "interviews.create", "display_name": "Schedule Interviews", "category": "interviews", "description": "Schedule new interviews"},
        {"name": "interviews.edit", "display_name": "Edit Interviews", "category": "interviews", "description": "Update interview details"},
        {"name": "interviews.delete", "display_name": "Delete Interviews", "category": "interviews", "description": "Cancel/delete interviews"},
        {"name": "interviews.feedback", "display_name": "Submit Feedback", "category": "interviews", "description": "Submit interview feedback and ratings"},
        
        # Clients
        {"name": "clients.view", "display_name": "View Clients", "category": "clients", "description": "View client list and details"},
        {"name": "clients.create", "display_name": "Create Clients", "category": "clients", "description": "Add new clients"},
        {"name": "clients.edit", "display_name": "Edit Clients", "category": "clients", "description": "Update client information"},
        {"name": "clients.delete", "display_name": "Delete Clients", "category": "clients", "description": "Remove clients"},
        {"name": "clients.communicate", "display_name": "Communicate with Clients", "category": "clients", "description": "Send emails and messages to clients"},
        
        # Users (Portal Users)
        {"name": "users.view", "display_name": "View Users", "category": "users", "description": "View portal users list"},
        {"name": "users.create", "display_name": "Create Users", "category": "users", "description": "Add new portal users"},
        {"name": "users.edit", "display_name": "Edit Users", "category": "users", "description": "Update user information"},
        {"name": "users.delete", "display_name": "Delete Users", "category": "users", "description": "Remove users from the system"},
        {"name": "users.manage_roles", "display_name": "Manage User Roles", "category": "users", "description": "Assign and change user roles"},
        {"name": "users.reset_password", "display_name": "Reset User Password", "category": "users", "description": "Reset user passwords"},
        
        # Roles (Custom Role Management)
        {"name": "roles.view", "display_name": "View Roles", "category": "roles", "description": "View available roles"},
        {"name": "roles.create", "display_name": "Create Roles", "category": "roles", "description": "Create custom roles"},
        {"name": "roles.edit", "display_name": "Edit Roles", "category": "roles", "description": "Update role permissions"},
        {"name": "roles.delete", "display_name": "Delete Roles", "category": "roles", "description": "Remove custom roles"},
        
        # Settings
        {"name": "settings.view", "display_name": "View Settings", "category": "settings", "description": "View tenant settings"},
        {"name": "settings.edit", "display_name": "Edit Settings", "category": "settings", "description": "Update tenant settings and preferences"},
        {"name": "settings.billing", "display_name": "Manage Billing", "category": "settings", "description": "View and manage subscription and billing"},
        
        # Reports
        {"name": "reports.view", "display_name": "View Reports", "category": "reports", "description": "Access reports and analytics dashboards"},
        {"name": "reports.export", "display_name": "Export Reports", "category": "reports", "description": "Export report data and analytics"},
        {"name": "reports.advanced", "display_name": "Advanced Reports", "category": "reports", "description": "Access advanced analytics and custom reports"}
    ]

    created_roles = {}
    created_permissions = {}

    # Insert roles
    for role_data in system_roles_data:
        existing_role = Role.query.filter_by(name=role_data["name"]).first()
        if not existing_role:
            role = Role(**role_data)
            db.session.add(role)
            created_roles[role.name] = role
            print(f"  ✅ Created role: {role.name}")
        else:
            created_roles[existing_role.name] = existing_role
            print(f"  ⏭️  Skipped role: {existing_role.name} (already exists)")
    db.session.flush() # Ensure roles get IDs

    # Insert permissions
    for perm_data in permissions_data:
        existing_perm = Permission.query.filter_by(name=perm_data["name"]).first()
        if not existing_perm:
            perm = Permission(**perm_data)
            db.session.add(perm)
            created_permissions[perm.name] = perm
            print(f"  ✅ Created permission: {perm.name}")
        else:
            created_permissions[existing_perm.name] = existing_perm
            print(f"  ⏭️  Skipped permission: {existing_perm.name} (already exists)")
    db.session.flush() # Ensure permissions get IDs

    # Assign permissions to roles
    print("Assigning permissions to roles...")

    # TENANT_ADMIN gets all permissions
    tenant_admin_role = created_roles.get("TENANT_ADMIN")
    if tenant_admin_role:
        for perm_name, perm_obj in created_permissions.items():
            if perm_obj not in tenant_admin_role.permissions:
                tenant_admin_role.permissions.append(perm_obj)
                print(f"    ✅ Assigned {perm_name} to TENANT_ADMIN")
            else:
                print(f"    ⏭️  TENANT_ADMIN already has {perm_name}")

    # RECRUITER (all except user/role/settings management)
    recruiter_role = created_roles.get("RECRUITER")
    if recruiter_role:
        recruiter_perms = [
            p for p_name, p in created_permissions.items()
            if p.category in ('candidates', 'jobs', 'interviews', 'clients', 'reports')
        ]
        for perm_obj in recruiter_perms:
            if perm_obj not in recruiter_role.permissions:
                recruiter_role.permissions.append(perm_obj)
                print(f"    ✅ Assigned {perm_obj.name} to RECRUITER")
            else:
                print(f"    ⏭️  RECRUITER already has {perm_obj.name}")

    # HIRING_MANAGER (view only + interview feedback)
    hiring_manager_role = created_roles.get("HIRING_MANAGER")
    if hiring_manager_role:
        hiring_manager_perms_names = [
            'candidates.view', 'jobs.view', 'interviews.view', 'interviews.feedback',
            'clients.view', 'reports.view'
        ]
        for perm_name in hiring_manager_perms_names:
            perm_obj = created_permissions.get(perm_name)
            if perm_obj and perm_obj not in hiring_manager_role.permissions:
                hiring_manager_role.permissions.append(perm_obj)
                print(f"    ✅ Assigned {perm_name} to HIRING_MANAGER")
            else:
                print(f"    ⏭️  HIRING_MANAGER already has {perm_name}")

    # MANAGER
    manager_role = created_roles.get("MANAGER")
    if manager_role:
        manager_perms_names = [
            'candidates.view', 'jobs.view', 'jobs.edit', 'jobs.manage_applications',
            'interviews.view', 'interviews.create', 'interviews.edit', 'interviews.feedback',
            'clients.view', 'users.view', 'users.edit', 'users.reset_password',
            'reports.view', 'reports.export'
        ]
        for perm_name in manager_perms_names:
            perm_obj = created_permissions.get(perm_name)
            if perm_obj and perm_obj not in manager_role.permissions:
                manager_role.permissions.append(perm_obj)
                print(f"    ✅ Assigned {perm_name} to MANAGER")
            else:
                print(f"    ⏭️  MANAGER already has {perm_name}")

    db.session.commit()
    print("\n✅ System roles and permissions seeded successfully!")

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        seed_roles_and_permissions()

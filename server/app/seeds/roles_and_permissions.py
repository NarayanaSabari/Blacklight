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
            "display_name": "Hiring Manager / HR",
            "description": "Manages candidate onboarding, approvals, and team structure. Can assign candidates to managers, assign recruiters to managers, and participate in hiring decisions.",
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
        {"name": "candidates.update", "display_name": "Update Candidates", "category": "candidates", "description": "Update candidate information (alias for edit)"},
        {"name": "candidates.delete", "display_name": "Delete Candidates", "category": "candidates", "description": "Remove candidates from the system"},
        {"name": "candidates.upload_resume", "display_name": "Upload Resume", "category": "candidates", "description": "Upload and manage candidate resumes"},
        {"name": "candidates.export", "display_name": "Export Candidates", "category": "candidates", "description": "Export candidate data"},
        {"name": "candidates.assign", "display_name": "Assign Candidates", "category": "candidates", "description": "Assign candidates to managers or recruiters"},
        {"name": "candidates.view_all", "display_name": "View All Candidates", "category": "candidates", "description": "View all candidates in the tenant"},
        {"name": "candidates.view_assigned", "display_name": "View Assigned Candidates", "category": "candidates", "description": "View candidates assigned to you"},
        {"name": "candidates.unassign", "display_name": "Unassign Candidates", "category": "candidates", "description": "Remove candidate assignments"},
        {"name": "candidates.view_history", "display_name": "View Assignment History", "category": "candidates", "description": "View candidate assignment history"},
        {"name": "candidates.reassign", "display_name": "Reassign Candidates", "category": "candidates", "description": "Reassign candidates to different users"},
        {"name": "candidates.approve", "display_name": "Approve Candidates", "category": "candidates", "description": "Approve manually onboarded candidates"},
        {"name": "candidates.review", "display_name": "Review Candidates", "category": "candidates", "description": "Review and edit AI-parsed candidate data"},
        {"name": "candidates.reject", "display_name": "Reject Candidates", "category": "candidates", "description": "Reject candidates from onboarding"},
        
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
        {"name": "users.view_team", "display_name": "View Team Members", "category": "users", "description": "View team members (recruiters under manager)"},
        {"name": "users.assign_manager", "display_name": "Assign Manager", "category": "users", "description": "Assign manager to users during creation"},
        
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

    # RECRUITER (work with assigned candidates only)
    recruiter_role = created_roles.get("RECRUITER")
    if recruiter_role:
        recruiter_perms_names = [
            # Assigned candidate permissions only
            'candidates.view_assigned', 'candidates.edit', 'candidates.upload_resume',
            # Full job and interview access
            'jobs.view', 'jobs.create', 'jobs.edit', 'jobs.delete', 'jobs.publish', 'jobs.manage_applications',
            'interviews.view', 'interviews.create', 'interviews.edit', 'interviews.delete', 'interviews.feedback',
            # Client communication
            'clients.view', 'clients.create', 'clients.edit', 'clients.delete', 'clients.communicate',
            # Reporting
            'reports.view', 'reports.export'
        ]
        for perm_name in recruiter_perms_names:
            perm_obj = created_permissions.get(perm_name)
            if perm_obj and perm_obj not in recruiter_role.permissions:
                recruiter_role.permissions.append(perm_obj)
                print(f"    ✅ Assigned {perm_name} to RECRUITER")
            else:
                print(f"    ⏭️  RECRUITER already has {perm_name}")

    # HIRING_MANAGER (HR role - candidate onboarding and team management)
    hiring_manager_role = created_roles.get("HIRING_MANAGER")
    if hiring_manager_role:
        hiring_manager_perms_names = [
            # Candidate management
            'candidates.view', 'candidates.create', 'candidates.edit', 'candidates.delete',
            'candidates.view_all', 'candidates.view_assigned', 'candidates.assign', 'candidates.reassign', 'candidates.approve',
            'candidates.view_history', 'candidates.upload_resume',
            # User/team management
            'users.view', 'users.create', 'users.assign_manager', 'users.view_team',
            # Other permissions
            'jobs.view', 'interviews.view', 'interviews.feedback',
            'clients.view', 'reports.view'
        ]
        for perm_name in hiring_manager_perms_names:
            perm_obj = created_permissions.get(perm_name)
            if perm_obj and perm_obj not in hiring_manager_role.permissions:
                hiring_manager_role.permissions.append(perm_obj)
                print(f"    ✅ Assigned {perm_name} to HIRING_MANAGER")
            else:
                print(f"    ⏭️  HIRING_MANAGER already has {perm_name}")

    # MANAGER (team manager - assigns candidates to recruiters)
    manager_role = created_roles.get("MANAGER")
    if manager_role:
        manager_perms_names = [
            # Candidate assignment permissions
            'candidates.view', 'candidates.view_all', 'candidates.view_assigned',
            'candidates.assign', 'candidates.reassign', 'candidates.view_history',
            # Job and interview management
            'jobs.view', 'jobs.edit', 'jobs.manage_applications',
            'interviews.view', 'interviews.create', 'interviews.edit', 'interviews.feedback',
            # User and team management
            'clients.view', 'users.view', 'users.edit', 'users.reset_password', 'users.view_team',
            # Reporting
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

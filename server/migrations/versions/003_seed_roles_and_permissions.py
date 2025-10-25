"""seed roles and permissions

Revision ID: 003
Revises: 002
Create Date: 2025-10-25 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """
    Seed initial system roles and permissions.
    """
    
    # Insert system roles
    op.execute("""
        INSERT INTO roles (name, display_name, description, is_system_role, is_active, tenant_id) VALUES
        ('TENANT_ADMIN', 'Tenant Administrator', 'Full access to tenant settings, users, and all recruitment features. Can manage other users and customize tenant settings.', TRUE, TRUE, NULL),
        ('RECRUITER', 'Recruiter', 'Manage candidates, jobs, interviews, and client communications. Cannot manage users or tenant settings.', TRUE, TRUE, NULL),
        ('HIRING_MANAGER', 'Hiring Manager', 'View candidates and jobs, participate in interviews. Limited editing capabilities, cannot delete records.', TRUE, TRUE, NULL)
    """)
    
    # Insert permissions
    # Candidate permissions
    op.execute("""
        INSERT INTO permissions (name, display_name, category, description) VALUES
        -- Candidates
        ('candidates.view', 'View Candidates', 'candidates', 'View candidate list and details'),
        ('candidates.create', 'Create Candidates', 'candidates', 'Add new candidates to the system'),
        ('candidates.edit', 'Edit Candidates', 'candidates', 'Update candidate information'),
        ('candidates.delete', 'Delete Candidates', 'candidates', 'Remove candidates from the system'),
        ('candidates.upload_resume', 'Upload Resume', 'candidates', 'Upload and manage candidate resumes'),
        ('candidates.export', 'Export Candidates', 'candidates', 'Export candidate data'),
        
        -- Jobs
        ('jobs.view', 'View Jobs', 'jobs', 'View job postings and applications'),
        ('jobs.create', 'Create Jobs', 'jobs', 'Create new job postings'),
        ('jobs.edit', 'Edit Jobs', 'jobs', 'Update job posting information'),
        ('jobs.delete', 'Delete Jobs', 'jobs', 'Remove job postings'),
        ('jobs.publish', 'Publish Jobs', 'jobs', 'Publish jobs to external platforms'),
        ('jobs.manage_applications', 'Manage Applications', 'jobs', 'Manage job applications and candidates'),
        
        -- Interviews
        ('interviews.view', 'View Interviews', 'interviews', 'View scheduled interviews'),
        ('interviews.create', 'Schedule Interviews', 'interviews', 'Schedule new interviews'),
        ('interviews.edit', 'Edit Interviews', 'interviews', 'Update interview details'),
        ('interviews.delete', 'Delete Interviews', 'interviews', 'Cancel/delete interviews'),
        ('interviews.feedback', 'Submit Feedback', 'interviews', 'Submit interview feedback and ratings'),
        
        -- Clients
        ('clients.view', 'View Clients', 'clients', 'View client list and details'),
        ('clients.create', 'Create Clients', 'clients', 'Add new clients'),
        ('clients.edit', 'Edit Clients', 'clients', 'Update client information'),
        ('clients.delete', 'Delete Clients', 'clients', 'Remove clients'),
        ('clients.communicate', 'Communicate with Clients', 'clients', 'Send emails and messages to clients'),
        
        -- Users (Portal Users)
        ('users.view', 'View Users', 'users', 'View portal users list'),
        ('users.create', 'Create Users', 'users', 'Add new portal users'),
        ('users.edit', 'Edit Users', 'users', 'Update user information'),
        ('users.delete', 'Delete Users', 'users', 'Remove users from the system'),
        ('users.manage_roles', 'Manage User Roles', 'users', 'Assign and change user roles'),
        ('users.reset_password', 'Reset User Password', 'users', 'Reset user passwords'),
        
        -- Roles (Custom Role Management)
        ('roles.view', 'View Roles', 'roles', 'View available roles'),
        ('roles.create', 'Create Roles', 'roles', 'Create custom roles'),
        ('roles.edit', 'Edit Roles', 'roles', 'Update role permissions'),
        ('roles.delete', 'Delete Roles', 'roles', 'Remove custom roles'),
        
        -- Settings
        ('settings.view', 'View Settings', 'settings', 'View tenant settings'),
        ('settings.edit', 'Edit Settings', 'settings', 'Update tenant settings and preferences'),
        ('settings.billing', 'Manage Billing', 'settings', 'View and manage subscription and billing'),
        
        -- Reports
        ('reports.view', 'View Reports', 'reports', 'Access reports and analytics dashboards'),
        ('reports.export', 'Export Reports', 'reports', 'Export report data and analytics'),
        ('reports.advanced', 'Advanced Reports', 'reports', 'Access advanced analytics and custom reports')
    """)
    
    # Assign permissions to TENANT_ADMIN (all permissions)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'TENANT_ADMIN'
    """)
    
    # Assign permissions to RECRUITER (all except user/role/settings management)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'RECRUITER'
        AND p.category IN ('candidates', 'jobs', 'interviews', 'clients', 'reports')
    """)
    
    # Assign permissions to HIRING_MANAGER (view only + interview feedback)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'HIRING_MANAGER'
        AND p.name IN (
            'candidates.view',
            'jobs.view',
            'interviews.view',
            'interviews.feedback',
            'clients.view',
            'reports.view'
        )
    """)


def downgrade():
    """
    Remove seeded data.
    """
    
    # Delete role-permission mappings
    op.execute("DELETE FROM role_permissions")
    
    # Delete permissions
    op.execute("DELETE FROM permissions")
    
    # Delete roles
    op.execute("DELETE FROM roles")

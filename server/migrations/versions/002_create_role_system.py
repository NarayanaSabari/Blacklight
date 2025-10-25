"""create role system

Revision ID: 002
Revises: 001
Create Date: 2025-10-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create dynamic role-based access control (RBAC) system.
    
    Order:
    1. roles table (with tenant_id for custom roles)
    2. permissions table
    3. role_permissions junction table
    4. Add role_id to portal_users
    5. Migrate data from role enum to role_id
    6. Drop old role enum column
    """
    
    # 1. Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),  # NULL for system roles, tenant_id for custom roles
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # Unique constraint: role name must be unique per tenant (or globally for system roles)
        sa.UniqueConstraint('tenant_id', 'name', name='uq_roles_tenant_name'),
        # Check constraint: system roles must have tenant_id = NULL
        sa.CheckConstraint(
            '(is_system_role = true AND tenant_id IS NULL) OR (is_system_role = false)',
            name='ck_roles_system_role_tenant'
        )
    )
    op.create_index('idx_roles_tenant_id', 'roles', ['tenant_id'])
    op.create_index('idx_roles_name', 'roles', ['name'])
    op.create_index('idx_roles_is_active', 'roles', ['is_active'])
    op.create_index('idx_roles_is_system', 'roles', ['is_system_role'])
    
    # 2. Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_permissions_name')
    )
    op.create_index('idx_permissions_name', 'permissions', ['name'])
    op.create_index('idx_permissions_category', 'permissions', ['category'])
    
    # 3. Create role_permissions junction table
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permissions_role_permission')
    )
    op.create_index('idx_role_permissions_role_id', 'role_permissions', ['role_id'])
    op.create_index('idx_role_permissions_permission_id', 'role_permissions', ['permission_id'])
    
    # 4. Add role_id column to portal_users (nullable initially for migration)
    op.add_column('portal_users', sa.Column('role_id', sa.Integer(), nullable=True))
    op.create_index('idx_portal_users_role_id', 'portal_users', ['role_id'])


def downgrade():
    """
    Rollback role system changes.
    """
    
    # Drop role_id column from portal_users
    op.drop_index('idx_portal_users_role_id', table_name='portal_users')
    op.drop_column('portal_users', 'role_id')
    
    # Drop role_permissions table
    op.drop_index('idx_role_permissions_permission_id', table_name='role_permissions')
    op.drop_index('idx_role_permissions_role_id', table_name='role_permissions')
    op.drop_table('role_permissions')
    
    # Drop permissions table
    op.drop_index('idx_permissions_category', table_name='permissions')
    op.drop_index('idx_permissions_name', table_name='permissions')
    op.drop_table('permissions')
    
    # Drop roles table
    op.drop_index('idx_roles_is_system', table_name='roles')
    op.drop_index('idx_roles_is_active', table_name='roles')
    op.drop_index('idx_roles_name', table_name='roles')
    op.drop_index('idx_roles_tenant_id', table_name='roles')
    op.drop_table('roles')

"""add tenant management system

Revision ID: 001
Revises: 
Create Date: 2025-10-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Create tables for tenant management system.
    
    Order is critical:
    1. subscription_plans (no dependencies)
    2. tenants (depends on subscription_plans)
    3. pm_admin_users (no dependencies)
    4. portal_users (depends on tenants)
    5. tenant_subscription_history (depends on tenants, subscription_plans, pm_admin_users)
    
    Also drops legacy 'users' table if it exists.
    """
    
    # Drop legacy users table if it exists (cleanup)
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    
    # 1. Create subscription_plans table
    op.create_table(
        'subscription_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price_monthly', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('price_yearly', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=False),
        sa.Column('max_candidates', sa.Integer(), nullable=False),
        sa.Column('max_jobs', sa.Integer(), nullable=False),
        sa.Column('max_storage_gb', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_subscription_plans_name', 'subscription_plans', ['name'])
    
    # 2. Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('company_email', sa.String(length=120), nullable=False),
        sa.Column('company_phone', sa.String(length=20), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'SUSPENDED', 'INACTIVE', name='tenantstatus'), nullable=False, server_default='ACTIVE'),
        sa.Column('subscription_plan_id', sa.Integer(), nullable=False),
        sa.Column('subscription_start_date', sa.DateTime(), nullable=False),
        sa.Column('subscription_end_date', sa.DateTime(), nullable=True),
        sa.Column('billing_cycle', sa.Enum('MONTHLY', 'YEARLY', name='billingcycle'), nullable=True),
        sa.Column('next_billing_date', sa.DateTime(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['subscription_plan_id'], ['subscription_plans.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('company_email')
    )
    op.create_index('ix_tenants_name', 'tenants', ['name'])
    op.create_index('ix_tenants_slug', 'tenants', ['slug'])
    op.create_index('ix_tenants_status', 'tenants', ['status'])
    op.create_index('ix_tenants_subscription_plan_id', 'tenants', ['subscription_plan_id'])
    
    # 3. Create pm_admin_users table
    op.create_table(
        'pm_admin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_pm_admin_users_email', 'pm_admin_users', ['email'])
    
    # 4. Create portal_users table
    op.create_table(
        'portal_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('role', sa.Enum('TENANT_ADMIN', 'RECRUITER', 'HIRING_MANAGER', name='portaluserrole'), nullable=False, server_default='RECRUITER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_portal_users_tenant_id', 'portal_users', ['tenant_id'])
    op.create_index('ix_portal_users_email', 'portal_users', ['email'])
    op.create_index('ix_portal_users_role', 'portal_users', ['role'])
    op.create_index('idx_portal_user_tenant_id', 'portal_users', ['tenant_id'])
    op.create_index('idx_portal_user_email', 'portal_users', ['email'])
    
    # 5. Create tenant_subscription_history table
    op.create_table(
        'tenant_subscription_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('subscription_plan_id', sa.Integer(), nullable=False),
        sa.Column('billing_cycle', sa.Enum('MONTHLY', 'YEARLY', name='billingcycle'), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_plan_id'], ['subscription_plans.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['changed_by'], ['pm_admin_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tenant_subscription_history_tenant_id', 'tenant_subscription_history', ['tenant_id'])
    op.create_index('ix_tenant_subscription_history_subscription_plan_id', 'tenant_subscription_history', ['subscription_plan_id'])


def downgrade():
    """Drop all tenant management tables in reverse order."""
    
    # Drop tables in reverse order of creation
    op.drop_index('ix_tenant_subscription_history_subscription_plan_id', table_name='tenant_subscription_history')
    op.drop_index('ix_tenant_subscription_history_tenant_id', table_name='tenant_subscription_history')
    op.drop_table('tenant_subscription_history')
    
    op.drop_index('idx_portal_user_email', table_name='portal_users')
    op.drop_index('idx_portal_user_tenant_id', table_name='portal_users')
    op.drop_index('ix_portal_users_role', table_name='portal_users')
    op.drop_index('ix_portal_users_email', table_name='portal_users')
    op.drop_index('ix_portal_users_tenant_id', table_name='portal_users')
    op.drop_table('portal_users')
    
    op.drop_index('ix_pm_admin_users_email', table_name='pm_admin_users')
    op.drop_table('pm_admin_users')
    
    op.drop_index('ix_tenants_subscription_plan_id', table_name='tenants')
    op.drop_index('ix_tenants_status', table_name='tenants')
    op.drop_index('ix_tenants_slug', table_name='tenants')
    op.drop_index('ix_tenants_name', table_name='tenants')
    op.drop_table('tenants')
    
    op.drop_index('ix_subscription_plans_name', table_name='subscription_plans')
    op.drop_table('subscription_plans')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS portaluserrole')
    op.execute('DROP TYPE IF EXISTS billingcycle')
    op.execute('DROP TYPE IF EXISTS tenantstatus')

"""migrate portal_users to role_id

Revision ID: 004
Revises: 003
Create Date: 2025-10-25 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """
    Migrate portal_users from role enum to role_id foreign key.
    """
    
    # Migrate existing data: map old role enum values to role_id
    op.execute("""
        UPDATE portal_users pu
        SET role_id = r.id
        FROM roles r
        WHERE r.name = pu.role
        AND r.is_system_role = TRUE
    """)
    
    # Make role_id NOT NULL (all users should now have a role_id)
    op.alter_column('portal_users', 'role_id', nullable=False)
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_portal_users_role_id',
        'portal_users',
        'roles',
        ['role_id'],
        ['id'],
        ondelete='RESTRICT'
    )
    
    # Drop the old role enum column
    op.drop_index('ix_portal_users_role', table_name='portal_users')
    op.drop_column('portal_users', 'role')
    
    # Drop the portaluserrole enum type (no longer needed)
    op.execute('DROP TYPE IF EXISTS portaluserrole')


def downgrade():
    """
    Rollback to role enum column.
    """
    
    # Recreate the enum type
    op.execute("""
        CREATE TYPE portaluserrole AS ENUM ('TENANT_ADMIN', 'RECRUITER', 'HIRING_MANAGER')
    """)
    
    # Add back the role column
    op.add_column(
        'portal_users',
        sa.Column('role', sa.Enum('TENANT_ADMIN', 'RECRUITER', 'HIRING_MANAGER', name='portaluserrole'), 
                  nullable=True, 
                  server_default='RECRUITER')
    )
    
    # Migrate data back from role_id to role
    op.execute("""
        UPDATE portal_users pu
        SET role = r.name::portaluserrole
        FROM roles r
        WHERE r.id = pu.role_id
    """)
    
    # Make role NOT NULL
    op.alter_column('portal_users', 'role', nullable=False)
    
    # Recreate index
    op.create_index('ix_portal_users_role', 'portal_users', ['role'])
    
    # Drop foreign key constraint
    op.drop_constraint('fk_portal_users_role_id', 'portal_users', type_='foreignkey')
    
    # Drop role_id column
    op.drop_column('portal_users', 'role_id')

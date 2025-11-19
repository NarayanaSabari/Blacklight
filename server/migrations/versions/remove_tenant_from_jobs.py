"""remove tenant_id from job_postings to make jobs global

Revision ID: remove_tenant_from_jobs
Revises: 8556f8b85cae
Create Date: 2025-11-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_tenant_from_jobs'
down_revision = '8556f8b85cae'
branch_labels = None
depends_on = None


def upgrade():
    """
    Remove tenant_id from job_postings table to make jobs global.
    Jobs from public platforms (Indeed, Dice, etc.) are shared across all tenants.
    Only candidate_job_matches and job_applications remain tenant-specific.
    """
    
    # Drop the unique constraint that includes tenant_id
    op.drop_index('idx_job_posting_tenant_platform_external', table_name='job_postings')
    
    # Drop the tenant_id index
    op.drop_index('ix_job_postings_tenant_id', table_name='job_postings')
    
    # Drop the foreign key constraint
    op.drop_constraint('job_postings_tenant_id_fkey', 'job_postings', type_='foreignkey')
    
    # Drop the tenant_id column
    op.drop_column('job_postings', 'tenant_id')
    
    # Create new unique constraint without tenant_id (global uniqueness)
    op.create_index(
        'idx_job_posting_platform_external',
        'job_postings',
        ['platform', 'external_job_id'],
        unique=True
    )


def downgrade():
    """
    Restore tenant_id to job_postings table (not recommended after data migration).
    """
    
    # Drop the global unique constraint
    op.drop_index('idx_job_posting_platform_external', table_name='job_postings')
    
    # Add tenant_id column back (nullable first for existing data)
    op.add_column('job_postings', sa.Column('tenant_id', sa.Integer(), nullable=True))
    
    # Note: You would need to manually populate tenant_id values for existing jobs
    # before making it NOT NULL and adding constraints
    
    # Create index on tenant_id
    op.create_index('ix_job_postings_tenant_id', 'job_postings', ['tenant_id'])
    
    # Add foreign key constraint
    op.create_foreign_key(
        'job_postings_tenant_id_fkey',
        'job_postings',
        'tenants',
        ['tenant_id'],
        ['id']
    )
    
    # Create unique constraint with tenant_id
    op.create_index(
        'idx_job_posting_tenant_platform_external',
        'job_postings',
        ['tenant_id', 'platform', 'external_job_id'],
        unique=True
    )
    
    # Make tenant_id NOT NULL (would fail if not populated)
    # op.alter_column('job_postings', 'tenant_id', nullable=False)

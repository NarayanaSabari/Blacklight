"""remove tenant from import batches

Revision ID: remove_tenant_batches
Revises: remove_tenant_from_jobs
Create Date: 2025-11-16 00:00:00.000000

Since job imports are managed by PM_ADMIN (product owner) who manages
the entire platform, there is no need for tenant-based audit tracking.
Removes tenant_id from job_import_batches table.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_tenant_batches'
down_revision = 'remove_tenant_from_jobs'
branch_labels = None
depends_on = None


def upgrade():
    # Drop foreign key constraint first
    op.drop_constraint('job_import_batches_tenant_id_fkey', 'job_import_batches', type_='foreignkey')
    
    # Drop indexes that reference tenant_id
    op.drop_index('idx_job_import_batch_tenant_status', table_name='job_import_batches')
    op.drop_index('ix_job_import_batches_tenant_id', table_name='job_import_batches')
    
    # Drop tenant_id column
    op.drop_column('job_import_batches', 'tenant_id')
    
    # Create new index for import status only
    op.create_index('idx_job_import_batch_status', 'job_import_batches', ['import_status'])


def downgrade():
    # Add tenant_id column back
    op.add_column('job_import_batches', sa.Column('tenant_id', sa.INTEGER(), autoincrement=False, nullable=True))
    
    # Populate with default value (1) for existing records
    op.execute("UPDATE job_import_batches SET tenant_id = 1 WHERE tenant_id IS NULL")
    
    # Make column NOT NULL after populating
    op.alter_column('job_import_batches', 'tenant_id', nullable=False)
    
    # Recreate indexes
    op.create_index('ix_job_import_batches_tenant_id', 'job_import_batches', ['tenant_id'])
    op.create_index('idx_job_import_batch_tenant_status', 'job_import_batches', ['tenant_id', 'import_status'])
    
    # Drop new index
    op.drop_index('idx_job_import_batch_status', table_name='job_import_batches')
    
    # Recreate foreign key constraint
    op.create_foreign_key('job_import_batches_tenant_id_fkey', 'job_import_batches', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

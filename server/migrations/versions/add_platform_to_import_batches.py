"""add platform to import batches

Revision ID: add_platform_batches
Revises: remove_tenant_batches
Create Date: 2025-11-16 00:00:00.000000

Add platform field to job_import_batches for tracking which
platform (indeed, dice, techfetch, etc.) the batch imported from.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_platform_batches'
down_revision = 'remove_tenant_batches'
branch_labels = None
depends_on = None


def upgrade():
    # Add platform column (nullable first to allow existing data)
    op.add_column('job_import_batches', sa.Column('platform', sa.String(length=50), nullable=True))
    
    # Update existing records with a default value (if any exist)
    op.execute("UPDATE job_import_batches SET platform = 'unknown' WHERE platform IS NULL")
    
    # Make column NOT NULL after populating
    op.alter_column('job_import_batches', 'platform', nullable=False)
    
    # Create index on platform
    op.create_index('idx_job_import_batch_platform', 'job_import_batches', ['platform'])


def downgrade():
    # Drop index
    op.drop_index('idx_job_import_batch_platform', table_name='job_import_batches')
    
    # Drop column
    op.drop_column('job_import_batches', 'platform')

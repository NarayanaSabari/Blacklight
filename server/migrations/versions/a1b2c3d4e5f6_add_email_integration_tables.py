"""Add email integration tables

Revision ID: a1b2c3d4e5f6
Revises: e6adbe9f8003
Create Date: 2025-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e6adbe9f8003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tables for email integration feature."""
    
    # Create user_email_integrations table
    op.create_table(
        'user_email_integrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(), nullable=True),
        sa.Column('email_address', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('sync_frequency_minutes', sa.Integer(), nullable=True, server_default='15'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('emails_processed_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('jobs_created_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['portal_users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'provider', name='uq_user_email_integration_user_provider'),
    )
    
    # Create indexes for user_email_integrations
    op.create_index('ix_user_email_integrations_user_id', 'user_email_integrations', ['user_id'])
    op.create_index('ix_user_email_integrations_tenant_id', 'user_email_integrations', ['tenant_id'])
    op.create_index('ix_user_email_integrations_provider', 'user_email_integrations', ['provider'])
    op.create_index('ix_user_email_integrations_is_active', 'user_email_integrations', ['is_active'])
    
    # Create processed_emails table
    op.create_table(
        'processed_emails',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('integration_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('email_message_id', sa.String(length=255), nullable=False),
        sa.Column('email_thread_id', sa.String(length=255), nullable=True),
        sa.Column('processing_result', sa.String(length=50), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('email_subject', sa.String(length=500), nullable=True),
        sa.Column('email_sender', sa.String(length=255), nullable=True),
        sa.Column('skip_reason', sa.String(length=255), nullable=True),
        sa.Column('parsing_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['integration_id'], ['user_email_integrations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['job_postings.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('integration_id', 'email_message_id', name='uq_processed_email_integration_message'),
    )
    
    # Create indexes for processed_emails
    op.create_index('ix_processed_emails_integration_id', 'processed_emails', ['integration_id'])
    op.create_index('ix_processed_emails_tenant_id', 'processed_emails', ['tenant_id'])
    op.create_index('ix_processed_emails_processing_result', 'processed_emails', ['processing_result'])
    op.create_index('ix_processed_emails_job_id', 'processed_emails', ['job_id'])
    
    # Add email source columns to job_postings
    op.add_column('job_postings', sa.Column('is_email_sourced', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('job_postings', sa.Column('source_tenant_id', sa.Integer(), nullable=True))
    op.add_column('job_postings', sa.Column('sourced_by_user_id', sa.Integer(), nullable=True))
    op.add_column('job_postings', sa.Column('source_email_id', sa.String(length=255), nullable=True))
    op.add_column('job_postings', sa.Column('source_email_subject', sa.String(length=500), nullable=True))
    op.add_column('job_postings', sa.Column('source_email_sender', sa.String(length=255), nullable=True))
    op.add_column('job_postings', sa.Column('source_email_date', sa.DateTime(), nullable=True))
    
    # Create foreign keys for job_postings email source columns
    op.create_foreign_key(
        'fk_job_postings_source_tenant',
        'job_postings',
        'tenants',
        ['source_tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_job_postings_sourced_by_user',
        'job_postings',
        'portal_users',
        ['sourced_by_user_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes for job_postings email source columns
    op.create_index('ix_job_postings_is_email_sourced', 'job_postings', ['is_email_sourced'])
    op.create_index('ix_job_postings_source_tenant_id', 'job_postings', ['source_tenant_id'])
    op.create_index('ix_job_postings_sourced_by_user_id', 'job_postings', ['sourced_by_user_id'])


def downgrade() -> None:
    """Remove email integration tables and columns."""
    
    # Drop indexes from job_postings
    op.drop_index('ix_job_postings_sourced_by_user_id', table_name='job_postings')
    op.drop_index('ix_job_postings_source_tenant_id', table_name='job_postings')
    op.drop_index('ix_job_postings_is_email_sourced', table_name='job_postings')
    
    # Drop foreign keys from job_postings
    op.drop_constraint('fk_job_postings_sourced_by_user', 'job_postings', type_='foreignkey')
    op.drop_constraint('fk_job_postings_source_tenant', 'job_postings', type_='foreignkey')
    
    # Drop columns from job_postings
    op.drop_column('job_postings', 'source_email_date')
    op.drop_column('job_postings', 'source_email_sender')
    op.drop_column('job_postings', 'source_email_subject')
    op.drop_column('job_postings', 'source_email_id')
    op.drop_column('job_postings', 'sourced_by_user_id')
    op.drop_column('job_postings', 'source_tenant_id')
    op.drop_column('job_postings', 'is_email_sourced')
    
    # Drop processed_emails indexes
    op.drop_index('ix_processed_emails_job_id', table_name='processed_emails')
    op.drop_index('ix_processed_emails_processing_result', table_name='processed_emails')
    op.drop_index('ix_processed_emails_tenant_id', table_name='processed_emails')
    op.drop_index('ix_processed_emails_integration_id', table_name='processed_emails')
    
    # Drop processed_emails table
    op.drop_table('processed_emails')
    
    # Drop user_email_integrations indexes
    op.drop_index('ix_user_email_integrations_is_active', table_name='user_email_integrations')
    op.drop_index('ix_user_email_integrations_provider', table_name='user_email_integrations')
    op.drop_index('ix_user_email_integrations_tenant_id', table_name='user_email_integrations')
    op.drop_index('ix_user_email_integrations_user_id', table_name='user_email_integrations')
    
    # Drop user_email_integrations table
    op.drop_table('user_email_integrations')

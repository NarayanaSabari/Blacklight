"""Create invitation_audit_logs table for audit trail

Revision ID: 008_create_invitation_audit_logs
Revises: 007_create_candidate_invitations
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '008_create_invitation_audit_logs'
down_revision = '007_create_candidate_invitations'  # Points to 007
branch_labels = None
depends_on = None


def upgrade():
    """Create invitation_audit_logs table"""
    
    # Create invitation_audit_logs table
    op.create_table(
        'invitation_audit_logs',
        # Primary key
        sa.Column('id', sa.Integer(), primary_key=True),
        
        # Foreign key to invitation
        sa.Column('invitation_id', sa.Integer(), sa.ForeignKey('candidate_invitations.id', ondelete='CASCADE'), nullable=False),
        
        # Action details
        sa.Column('action', sa.String(50), nullable=False),
        # Action values: 'invitation_sent', 'invitation_opened', 'invitation_submitted', 
        #                'invitation_approved', 'invitation_rejected', 'invitation_resent', 'invitation_cancelled'
        
        # Who performed the action
        sa.Column('performed_by', sa.String(100), nullable=True),  # 'portal_user_id:123' or 'candidate' or 'system'
        
        # Request metadata
        sa.Column('ip_address', sa.String(45), nullable=True),  # IPv4 or IPv6
        sa.Column('user_agent', sa.String(500), nullable=True),
        
        # Additional context
        sa.Column('extra_data', JSONB(), nullable=True),  # Flexible JSON for additional context
        
        # Timestamp
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for audit log queries
    op.create_index('idx_audit_logs_invitation_id', 'invitation_audit_logs', ['invitation_id'])
    op.create_index('idx_audit_logs_action', 'invitation_audit_logs', ['action'])
    op.create_index('idx_audit_logs_timestamp', 'invitation_audit_logs', ['timestamp'])
    
    # Composite index for common query: get all actions for an invitation ordered by time
    op.create_index(
        'idx_audit_logs_invitation_timestamp',
        'invitation_audit_logs',
        ['invitation_id', 'timestamp']
    )
    
    # GIN index for extra_data search
    op.create_index(
        'idx_audit_logs_extra_data_gin',
        'invitation_audit_logs',
        ['extra_data'],
        postgresql_using='gin'
    )


def downgrade():
    """Drop invitation_audit_logs table and all indexes"""
    op.drop_index('idx_audit_logs_extra_data_gin', table_name='invitation_audit_logs')
    op.drop_index('idx_audit_logs_invitation_timestamp', table_name='invitation_audit_logs')
    op.drop_index('idx_audit_logs_timestamp', table_name='invitation_audit_logs')
    op.drop_index('idx_audit_logs_action', table_name='invitation_audit_logs')
    op.drop_index('idx_audit_logs_invitation_id', table_name='invitation_audit_logs')
    op.drop_table('invitation_audit_logs')

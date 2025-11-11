"""Create candidate_invitations table for self-onboarding

Revision ID: 007_create_candidate_invitations
Revises: 006
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '007_create_candidate_invitations'
down_revision = '006'  # Points to 006_make_last_name_nullable
branch_labels = None
depends_on = None


def upgrade():
    """Create candidate_invitations table"""
    
    # Create candidate_invitations table
    op.create_table(
        'candidate_invitations',
        # Primary key and timestamps
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Tenant relationship
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        
        # Candidate information
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        
        # Token and security
        sa.Column('token', sa.String(100), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        
        # Status tracking
        sa.Column('status', sa.String(50), nullable=False, server_default='sent'),
        # Status values: 'sent', 'opened', 'in_progress', 'submitted', 'approved', 'rejected', 'expired', 'cancelled'
        
        # Invitation metadata
        sa.Column('invited_by_id', sa.Integer(), sa.ForeignKey('portal_users.id'), nullable=False),
        sa.Column('invited_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        
        # Submission data
        sa.Column('invitation_data', JSONB(), nullable=True),  # Candidate's submitted form data
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        
        # Review information
        sa.Column('reviewed_by_id', sa.Integer(), sa.ForeignKey('portal_users.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        
        # Link to created candidate (after approval)
        sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('candidates.id'), nullable=True),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_invitations_token', 'candidate_invitations', ['token'], unique=True)
    op.create_index('idx_invitations_tenant_id', 'candidate_invitations', ['tenant_id'])
    op.create_index('idx_invitations_email', 'candidate_invitations', ['email'])
    op.create_index('idx_invitations_status', 'candidate_invitations', ['status'])
    op.create_index('idx_invitations_invited_by', 'candidate_invitations', ['invited_by_id'])
    op.create_index('idx_invitations_expires_at', 'candidate_invitations', ['expires_at'])
    
    # Composite indexes for common queries
    op.create_index(
        'idx_invitations_tenant_email',
        'candidate_invitations',
        ['tenant_id', 'email']
    )
    op.create_index(
        'idx_invitations_tenant_status',
        'candidate_invitations',
        ['tenant_id', 'status']
    )
    
    # GIN index for JSONB search
    op.create_index(
        'idx_invitations_data_gin',
        'candidate_invitations',
        ['invitation_data'],
        postgresql_using='gin'
    )


def downgrade():
    """Drop candidate_invitations table and all indexes"""
    op.drop_index('idx_invitations_data_gin', table_name='candidate_invitations')
    op.drop_index('idx_invitations_tenant_status', table_name='candidate_invitations')
    op.drop_index('idx_invitations_tenant_email', table_name='candidate_invitations')
    op.drop_index('idx_invitations_expires_at', table_name='candidate_invitations')
    op.drop_index('idx_invitations_invited_by', table_name='candidate_invitations')
    op.drop_index('idx_invitations_status', table_name='candidate_invitations')
    op.drop_index('idx_invitations_email', table_name='candidate_invitations')
    op.drop_index('idx_invitations_tenant_id', table_name='candidate_invitations')
    op.drop_index('idx_invitations_token', table_name='candidate_invitations')
    op.drop_table('candidate_invitations')

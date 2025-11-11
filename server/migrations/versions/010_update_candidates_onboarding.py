"""Update candidates table for onboarding tracking

Revision ID: 010_update_candidates_onboarding
Revises: 009_create_candidate_documents
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010_update_candidates_onboarding'
down_revision = '009_create_candidate_documents'  # Points to 009
branch_labels = None
depends_on = None


def upgrade():
    """Add onboarding tracking columns to candidates table"""
    
    # Add onboarding_type column (tracks how candidate was added)
    op.add_column(
        'candidates',
        sa.Column('onboarding_type', sa.String(50), nullable=False, server_default='manual')
    )
    # Values: 'manual' (HR entered directly), 'self_onboarding' (via invitation)
    
    # Add invitation_id to link candidate to originating invitation
    op.add_column(
        'candidates',
        sa.Column('invitation_id', sa.Integer(), sa.ForeignKey('candidate_invitations.id'), nullable=True)
    )
    
    # Create index on invitation_id for queries
    op.create_index('idx_candidates_invitation_id', 'candidates', ['invitation_id'])
    
    # Create index on onboarding_type for filtering
    op.create_index('idx_candidates_onboarding_type', 'candidates', ['onboarding_type'])


def downgrade():
    """Remove onboarding tracking columns from candidates table"""
    op.drop_index('idx_candidates_onboarding_type', table_name='candidates')
    op.drop_index('idx_candidates_invitation_id', table_name='candidates')
    op.drop_column('candidates', 'invitation_id')
    op.drop_column('candidates', 'onboarding_type')

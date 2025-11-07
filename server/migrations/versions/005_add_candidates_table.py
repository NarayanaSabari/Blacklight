"""Add candidates table with resume parsing support

Revision ID: 005_add_candidates_table
Revises: 004
Create Date: 2025-10-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


# revision identifiers, used by Alembic.
revision = '005_add_candidates_table'
down_revision = '004'  # Points to 004_migrate_portal_users_to_role_id
branch_labels = None
depends_on = None


def upgrade():
    """Create candidates table with all resume parsing fields"""
    
    # Create candidates table
    op.create_table(
        'candidates',
        # Primary key and timestamps
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Tenant relationship
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        
        # Basic information
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        
        # Status and source
        sa.Column('status', sa.String(50), nullable=False, server_default='NEW'),
        sa.Column('source', sa.String(100), nullable=True),
        
        # Resume file storage
        sa.Column('resume_file_path', sa.String(500), nullable=True),
        sa.Column('resume_file_url', sa.String(500), nullable=True),
        sa.Column('resume_uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('resume_parsed_at', sa.DateTime(), nullable=True),
        
        # Enhanced personal information
        sa.Column('full_name', sa.String(200), nullable=True),
        sa.Column('location', sa.String(200), nullable=True),
        sa.Column('linkedin_url', sa.String(500), nullable=True),
        sa.Column('portfolio_url', sa.String(500), nullable=True),
        
        # Professional details
        sa.Column('current_title', sa.String(200), nullable=True),
        sa.Column('total_experience_years', sa.Integer(), nullable=True),
        sa.Column('notice_period', sa.String(100), nullable=True),
        sa.Column('expected_salary', sa.String(100), nullable=True),
        sa.Column('professional_summary', sa.Text(), nullable=True),
        
        # Array columns
        sa.Column('preferred_locations', ARRAY(sa.String), nullable=True),
        sa.Column('skills', ARRAY(sa.String), nullable=True),
        sa.Column('certifications', ARRAY(sa.String), nullable=True),
        sa.Column('languages', ARRAY(sa.String), nullable=True),
        
        # JSONB columns for structured data
        sa.Column('education', JSONB(), nullable=True),
        sa.Column('work_experience', JSONB(), nullable=True),
        sa.Column('parsed_resume_data', JSONB(), nullable=True),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_candidates_tenant_id', 'candidates', ['tenant_id'])
    op.create_index('idx_candidates_email', 'candidates', ['email'])
    op.create_index('idx_candidates_status', 'candidates', ['status'])
    op.create_index('idx_candidates_created_at', 'candidates', ['created_at'])
    
    # GIN indexes for JSONB and ARRAY columns (fast searches)
    op.create_index(
        'idx_candidates_skills_gin',
        'candidates',
        ['skills'],
        postgresql_using='gin'
    )
    op.create_index(
        'idx_candidates_education_gin',
        'candidates',
        ['education'],
        postgresql_using='gin'
    )
    op.create_index(
        'idx_candidates_work_experience_gin',
        'candidates',
        ['work_experience'],
        postgresql_using='gin'
    )
    
    # Composite indexes for common queries
    op.create_index(
        'idx_candidates_tenant_status',
        'candidates',
        ['tenant_id', 'status']
    )


def downgrade():
    """Drop candidates table and all indexes"""
    op.drop_index('idx_candidates_tenant_status', table_name='candidates')
    op.drop_index('idx_candidates_work_experience_gin', table_name='candidates')
    op.drop_index('idx_candidates_education_gin', table_name='candidates')
    op.drop_index('idx_candidates_skills_gin', table_name='candidates')
    op.drop_index('idx_candidates_created_at', table_name='candidates')
    op.drop_index('idx_candidates_status', table_name='candidates')
    op.drop_index('idx_candidates_email', table_name='candidates')
    op.drop_index('idx_candidates_tenant_id', table_name='candidates')
    op.drop_table('candidates')

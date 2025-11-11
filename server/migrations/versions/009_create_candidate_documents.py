"""Create candidate_documents table for file management

Revision ID: 009_create_candidate_documents
Revises: 008_create_invitation_audit_logs
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '009_create_candidate_documents'
down_revision = '008_create_invitation_audit_logs'  # Points to 008
branch_labels = None
depends_on = None


def upgrade():
    """Create candidate_documents table"""
    
    # Create candidate_documents table
    op.create_table(
        'candidate_documents',
        # Primary key and timestamps
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Tenant relationship
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        
        # Link to candidate OR invitation (one must be set)
        sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=True),
        sa.Column('invitation_id', sa.Integer(), sa.ForeignKey('candidate_invitations.id', ondelete='CASCADE'), nullable=True),
        
        # Document metadata
        sa.Column('document_type', sa.String(100), nullable=False),  # 'resume', 'id_proof', 'work_authorization', etc.
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),  # Size in bytes
        sa.Column('mime_type', sa.String(100), nullable=False),  # 'application/pdf', 'image/jpeg', etc.
        
        # Verification
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verified_by_id', sa.Integer(), sa.ForeignKey('portal_users.id'), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        
        # Upload timestamp
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_documents_tenant_id', 'candidate_documents', ['tenant_id'])
    op.create_index('idx_documents_candidate_id', 'candidate_documents', ['candidate_id'])
    op.create_index('idx_documents_invitation_id', 'candidate_documents', ['invitation_id'])
    op.create_index('idx_documents_document_type', 'candidate_documents', ['document_type'])
    op.create_index('idx_documents_is_verified', 'candidate_documents', ['is_verified'])
    op.create_index('idx_documents_uploaded_at', 'candidate_documents', ['uploaded_at'])
    
    # Composite indexes for common queries
    op.create_index(
        'idx_documents_candidate_type',
        'candidate_documents',
        ['candidate_id', 'document_type']
    )
    op.create_index(
        'idx_documents_invitation_type',
        'candidate_documents',
        ['invitation_id', 'document_type']
    )
    op.create_index(
        'idx_documents_tenant_type',
        'candidate_documents',
        ['tenant_id', 'document_type']
    )


def downgrade():
    """Drop candidate_documents table and all indexes"""
    op.drop_index('idx_documents_tenant_type', table_name='candidate_documents')
    op.drop_index('idx_documents_invitation_type', table_name='candidate_documents')
    op.drop_index('idx_documents_candidate_type', table_name='candidate_documents')
    op.drop_index('idx_documents_uploaded_at', table_name='candidate_documents')
    op.drop_index('idx_documents_is_verified', table_name='candidate_documents')
    op.drop_index('idx_documents_document_type', table_name='candidate_documents')
    op.drop_index('idx_documents_invitation_id', table_name='candidate_documents')
    op.drop_index('idx_documents_candidate_id', table_name='candidate_documents')
    op.drop_index('idx_documents_tenant_id', table_name='candidate_documents')
    op.drop_table('candidate_documents')

"""Add storage fields to candidate_documents for GCS support

Revision ID: 011_add_document_storage
Revises: 010_update_candidates_onboarding
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011_add_document_storage'
down_revision = '010_update_candidates_onboarding'
branch_labels = None
depends_on = None


def upgrade():
    """Add file_key, storage_backend, and uploaded_by_id fields"""
    
    # Add new columns
    op.add_column('candidate_documents', 
        sa.Column('file_key', sa.String(1000), nullable=True)
    )
    op.add_column('candidate_documents', 
        sa.Column('storage_backend', sa.String(20), nullable=True, server_default='local')
    )
    op.add_column('candidate_documents', 
        sa.Column('uploaded_by_id', sa.Integer(), sa.ForeignKey('portal_users.id'), nullable=True)
    )
    
    # Migrate existing data: copy file_path to file_key for existing records
    op.execute("""
        UPDATE candidate_documents 
        SET file_key = file_path,
            storage_backend = 'local'
        WHERE file_key IS NULL
    """)
    
    # Now make file_key NOT NULL and make file_path nullable (for backward compatibility)
    op.alter_column('candidate_documents', 'file_key', nullable=False)
    op.alter_column('candidate_documents', 'file_path', nullable=True)
    
    # Create index for file_key (used for lookups)
    op.create_index('idx_documents_file_key', 'candidate_documents', ['file_key'])
    
    # Create index for uploaded_by_id
    op.create_index('idx_documents_uploaded_by_id', 'candidate_documents', ['uploaded_by_id'])


def downgrade():
    """Remove storage fields"""
    
    # Drop indexes
    op.drop_index('idx_documents_uploaded_by_id', table_name='candidate_documents')
    op.drop_index('idx_documents_file_key', table_name='candidate_documents')
    
    # Restore file_path as NOT NULL before dropping file_key
    op.execute("""
        UPDATE candidate_documents 
        SET file_path = file_key
        WHERE file_path IS NULL
    """)
    op.alter_column('candidate_documents', 'file_path', nullable=False)
    
    # Drop new columns
    op.drop_column('candidate_documents', 'uploaded_by_id')
    op.drop_column('candidate_documents', 'storage_backend')
    op.drop_column('candidate_documents', 'file_key')

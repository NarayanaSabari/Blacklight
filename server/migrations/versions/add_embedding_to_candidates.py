"""add_embedding_to_candidates

Revision ID: add_embedding_candidates
Revises: add_platform_batches
Create Date: 2025-11-16 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = 'add_embedding_candidates'
down_revision: Union[str, Sequence[str], None] = 'add_platform_batches'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add embedding column to candidates table for semantic matching."""
    # Ensure pgvector extension is enabled (idempotent)
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Add embedding column to candidates table
    op.add_column('candidates', 
        sa.Column('embedding', pgvector.sqlalchemy.Vector(768), nullable=True)
    )
    
    # Create index for vector similarity search using cosine distance
    op.execute(
        'CREATE INDEX idx_candidates_embedding_cosine ON candidates '
        'USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)'
    )


def downgrade() -> None:
    """Remove embedding column from candidates table."""
    # Drop the index first
    op.drop_index('idx_candidates_embedding_cosine', table_name='candidates')
    
    # Drop the embedding column
    op.drop_column('candidates', 'embedding')

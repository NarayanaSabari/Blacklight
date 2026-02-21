"""add_candidate_indexes_and_remove_duplicate_link_table_indexes

Revision ID: 9b5d6da3a341
Revises: e9b4594d7067
Create Date: 2026-02-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b5d6da3a341'
down_revision: Union[str, Sequence[str], None] = 'e9b4594d7067'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing indexes on candidates table and remove duplicate indexes on link tables.

    1. candidates table: add B-tree indexes on tenant_id, (tenant_id, status),
       (tenant_id, created_at DESC), and IVFFlat ANN index on embedding.
    2. role_job_mappings: drop duplicate single-column indexes (already covered by
       inline index=True on the FK columns).
    3. candidate_global_roles: drop duplicate single-column indexes (same reason).
    """
    # =========================================================================
    # 1. Candidates table indexes (currently ZERO indexes)
    # =========================================================================

    # Single-column tenant_id index for simple tenant scoping
    op.create_index(
        'idx_candidates_tenant',
        'candidates',
        ['tenant_id']
    )

    # Composite: tenant_id + status (used by most candidate list queries)
    op.create_index(
        'idx_candidates_tenant_status',
        'candidates',
        ['tenant_id', 'status']
    )

    # Composite: tenant_id + created_at DESC (used for sorted listing)
    op.create_index(
        'idx_candidates_tenant_created',
        'candidates',
        ['tenant_id', sa.text('created_at DESC')]
    )

    # IVFFlat ANN index on embedding for nearest-neighbour searches.
    # pgvector requires ivfflat_probes to be set before querying.
    # lists=10 is appropriate for < 10k rows; increase later if needed.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidates_embedding_ivfflat "
        "ON candidates USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)"
    )

    # =========================================================================
    # 2. Remove duplicate indexes on role_job_mappings
    #    The inline index=True on global_role_id and job_posting_id already
    #    created ix_role_job_mappings_global_role_id and ix_role_job_mappings_job_posting_id.
    #    The __table_args__ Index('idx_role_job_mapping_role', ...) and
    #    Index('idx_role_job_mapping_job', ...) are exact duplicates.
    # =========================================================================
    op.drop_index('idx_role_job_mapping_role', table_name='role_job_mappings')
    op.drop_index('idx_role_job_mapping_job', table_name='role_job_mappings')

    # =========================================================================
    # 3. Remove duplicate indexes on candidate_global_roles
    #    Same situation: inline index=True + __table_args__ Index() are duplicates.
    # =========================================================================
    op.drop_index('idx_candidate_global_roles_role', table_name='candidate_global_roles')
    op.drop_index('idx_candidate_global_roles_candidate', table_name='candidate_global_roles')


def downgrade() -> None:
    """Reverse: drop candidate indexes, recreate duplicate link table indexes."""
    # Re-create duplicate indexes on link tables
    op.create_index('idx_candidate_global_roles_candidate', 'candidate_global_roles', ['candidate_id'])
    op.create_index('idx_candidate_global_roles_role', 'candidate_global_roles', ['global_role_id'])
    op.create_index('idx_role_job_mapping_job', 'role_job_mappings', ['job_posting_id'])
    op.create_index('idx_role_job_mapping_role', 'role_job_mappings', ['global_role_id'])

    # Drop candidate indexes
    op.execute("DROP INDEX IF EXISTS idx_candidates_embedding_ivfflat")
    op.drop_index('idx_candidates_tenant_created', table_name='candidates')
    op.drop_index('idx_candidates_tenant_status', table_name='candidates')
    op.drop_index('idx_candidates_tenant', table_name='candidates')

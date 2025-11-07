"""make_last_name_nullable

Revision ID: 006
Revises: 005_add_candidates_table
Create Date: 2025-11-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005_add_candidates_table'
branch_labels = None
depends_on = None

def upgrade():
    # Make last_name nullable for candidates
    op.alter_column('candidates', 'last_name',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
    
    # Make email nullable too (not everyone has email on resume)
    op.alter_column('candidates', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)


def downgrade():
    # Revert: make last_name NOT NULL again
    op.alter_column('candidates', 'last_name',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
    
    op.alter_column('candidates', 'email',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)

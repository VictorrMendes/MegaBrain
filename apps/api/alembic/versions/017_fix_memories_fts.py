"""fix_memories_fts

Revision ID: 017
Revises: 15960f0bc3e4
Create Date: 2026-06-27
"""
from typing import Sequence, Union
from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "15960f0bc3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='memories' AND column_name='fts') THEN
                ALTER TABLE memories ADD COLUMN fts tsvector GENERATED ALWAYS AS (to_tsvector('portuguese', content)) STORED;
                CREATE INDEX ix_memories_fts ON memories USING GIN (fts);
            END IF;
        END $$;
        """
    )

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_memories_fts")
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS fts")

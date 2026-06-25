"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

memory_type_enum = sa.Enum(
    "long", "working", "episodic", "semantic", name="memory_type"
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "workspaces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workspaces"),
    )

    op.create_table(
        "memories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("type", memory_type_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("superseded_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_memories_workspace_id_workspaces",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by"],
            ["memories.id"],
            name="fk_memories_superseded_by_memories",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_memories"),
    )

    op.execute("ALTER TABLE memories ADD COLUMN embedding vector(768)")
    op.execute(
        "ALTER TABLE memories ADD COLUMN fts tsvector "
        "GENERATED ALWAYS AS (to_tsvector('portuguese', content)) STORED"
    )
    op.execute(
        "CREATE INDEX ix_memories_embedding ON memories "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute("CREATE INDEX ix_memories_fts ON memories USING GIN (fts)")


def downgrade() -> None:
    op.drop_table("memories")
    op.drop_table("workspaces")
    op.execute("DROP TYPE IF EXISTS memory_type")
    op.execute("DROP EXTENSION IF EXISTS vector")

"""memory evolution — confidence, importance, source, expires_at (Phase 2C)

Revision ID: 010
Revises: 009
Create Date: 2026-06-25
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memories",
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
    )
    op.add_column(
        "memories",
        sa.Column(
            "importance",
            sa.Float(),
            nullable=False,
            server_default="0.5",
        ),
    )
    op.add_column(
        "memories",
        sa.Column("source", sa.Text(), nullable=True),
    )
    op.add_column(
        "memories",
        sa.Column("source_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "memories",
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.create_foreign_key(
        "fk_memories_source_id",
        "memories",
        "memories",
        ["source_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_memories_workspace_id", "memories", ["workspace_id"]
    )
    op.create_index(
        "ix_memories_expires_at", "memories", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_memories_expires_at", "memories")
    op.drop_index("ix_memories_workspace_id", "memories")
    op.drop_constraint(
        "fk_memories_source_id", "memories", type_="foreignkey"
    )
    op.drop_column("memories", "expires_at")
    op.drop_column("memories", "source_id")
    op.drop_column("memories", "source")
    op.drop_column("memories", "importance")
    op.drop_column("memories", "confidence")

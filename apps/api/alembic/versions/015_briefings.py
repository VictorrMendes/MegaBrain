"""briefings — Cognitive Briefing artifacts (Phase 8B)

Revision ID: 015
Revises: 014
Create Date: 2026-06-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "briefings",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "type",
            sa.String(32),
            nullable=False,
            server_default="daily",
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "metadata",
            JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_briefings_workspace_id",
        "briefings",
        ["workspace_id"],
    )
    op.create_index(
        "ix_briefings_created_at",
        "briefings",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_briefings_created_at", table_name="briefings")
    op.drop_index("ix_briefings_workspace_id", table_name="briefings")
    op.drop_table("briefings")

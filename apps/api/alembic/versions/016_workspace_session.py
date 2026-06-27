"""workspace_sessions — persist UI state per workspace (RC-06)

Revision ID: 016
Revises: 015
Create Date: 2026-06-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_sessions",
        sa.Column(
            "workspace_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey(
                "workspaces.id", ondelete="CASCADE"
            ),
            primary_key=True,
        ),
        sa.Column(
            "active_conversation_id",
            sa.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "current_page",
            sa.String(64),
            nullable=True,
        ),
        sa.Column(
            "ui_state",
            JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("workspace_sessions")

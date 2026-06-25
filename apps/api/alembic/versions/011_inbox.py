"""cognitive inbox — InboxItem pipeline universal de entrada

Revision ID: 011
Revises: 010
Create Date: 2026-06-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE inbox_item_type AS ENUM (
            'text', 'file', 'url', 'email', 'note', 'event'
        )
    """)
    op.execute("""
        CREATE TYPE inbox_item_status AS ENUM (
            'pending', 'processing',
            'routed_knowledge', 'routed_task', 'routed_both',
            'dismissed'
        )
    """)

    op.create_table(
        "inbox_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "text", "file", "url", "email", "note", "event",
                name="inbox_item_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "processing",
                "routed_knowledge", "routed_task", "routed_both",
                "dismissed",
                name="inbox_item_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column(
            "source", sa.Text(), nullable=False, server_default="api"
        ),
        sa.Column(
            "metadata", JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column("mission_id", sa.UUID(), nullable=True),
        sa.Column(
            "knowledge_extracted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("routing_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "processed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_inbox_items_workspace_id",
        ),
        sa.ForeignKeyConstraint(
            ["mission_id"], ["missions.id"],
            ondelete="SET NULL",
            name="fk_inbox_items_mission_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inbox_items"),
    )
    op.create_index(
        "ix_inbox_items_workspace_id", "inbox_items", ["workspace_id"]
    )
    op.create_index(
        "ix_inbox_items_status", "inbox_items", ["status"]
    )
    op.create_index(
        "ix_inbox_items_type", "inbox_items", ["type"]
    )
    op.create_index(
        "ix_inbox_items_created_at", "inbox_items", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_inbox_items_created_at", "inbox_items")
    op.drop_index("ix_inbox_items_type", "inbox_items")
    op.drop_index("ix_inbox_items_status", "inbox_items")
    op.drop_index("ix_inbox_items_workspace_id", "inbox_items")
    op.drop_table("inbox_items")
    op.execute("DROP TYPE IF EXISTS inbox_item_status")
    op.execute("DROP TYPE IF EXISTS inbox_item_type")

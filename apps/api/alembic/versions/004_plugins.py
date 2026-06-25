"""workspace plugins

Revision ID: 004
Revises: 003
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_plugins",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("plugin_name", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "config",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
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
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_workspace_plugins_workspace_id_workspaces",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workspace_plugins"),
        sa.UniqueConstraint(
            "workspace_id", "plugin_name", name="uq_workspace_plugins_workspace_plugin"
        ),
    )
    op.create_index(
        "ix_workspace_plugins_workspace_id", "workspace_plugins", ["workspace_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_plugins_workspace_id", "workspace_plugins")
    op.drop_table("workspace_plugins")

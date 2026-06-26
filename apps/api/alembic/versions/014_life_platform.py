"""life_platform — Integration, ConnectedAccount, SyncRecord (Phase 8A)

Revision ID: 014
Revises: 013
Create Date: 2026-06-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from alembic import op

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── integrations ──────────────────────────────────────────────────────
    # Creates: integration_category, integration_status, integration_health,
    #          sync_mode  (reused by sync_records with create_type=False)
    op.create_table(
        "integrations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "productivity", "development", "infrastructure",
                "communication", "information", "home", "storage",
                name="integration_category",
            ),
            nullable=False,
        ),
        sa.Column("icon", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "description", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active", "paused", "error", "disconnected", "pending_auth",
                name="integration_status",
            ),
            nullable=False,
            server_default="disconnected",
        ),
        sa.Column(
            "health",
            sa.Enum(
                "healthy", "degraded", "unhealthy", "unknown",
                name="integration_health",
            ),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column(
            "sync_strategy",
            sa.Enum(
                "manual", "scheduled", "incremental",
                "full", "webhook", "event_driven",
                name="sync_mode",
            ),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "config", JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "life_context_lines",
            ARRAY(sa.Text()),
            server_default="{}",
        ),
        sa.Column(
            "last_sync_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "next_sync_at", sa.DateTime(timezone=True), nullable=True
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
            ["workspace_id"], ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_integrations_workspace_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_integrations"),
        sa.UniqueConstraint(
            "workspace_id", "slug",
            name="uq_integrations_workspace_slug",
        ),
    )
    op.create_index(
        "ix_integrations_workspace_id", "integrations", ["workspace_id"]
    )
    op.create_index(
        "ix_integrations_slug", "integrations", ["slug"]
    )
    op.create_index(
        "ix_integrations_status", "integrations", ["status"]
    )

    # ── connected_accounts ────────────────────────────────────────────────
    # Creates: account_status
    op.create_table(
        "connected_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("integration_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("account_name", sa.Text(), nullable=False),
        sa.Column("account_email", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active", "expired", "revoked", "error",
                name="account_status",
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("scopes", ARRAY(sa.Text()), server_default="{}"),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column(
            "token_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "config", JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "quota_used",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "quota_limit",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "last_sync_at", sa.DateTime(timezone=True), nullable=True
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
            ["integration_id"], ["integrations.id"],
            ondelete="CASCADE",
            name="fk_connected_accounts_integration_id",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_connected_accounts_workspace_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_connected_accounts"),
    )
    op.create_index(
        "ix_connected_accounts_integration_id",
        "connected_accounts",
        ["integration_id"],
    )
    op.create_index(
        "ix_connected_accounts_workspace_id",
        "connected_accounts",
        ["workspace_id"],
    )

    # ── sync_records ──────────────────────────────────────────────────────
    # Creates: sync_record_status
    # Reuses: sync_mode (create_type=False)
    op.create_table(
        "sync_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("integration_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column(
            "sync_type",
            sa.Enum(
                "manual", "scheduled", "incremental",
                "full", "webhook", "event_driven",
                name="sync_mode",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "running", "success", "partial", "failed", "skipped",
                name="sync_record_status",
            ),
            nullable=False,
            server_default="running",
        ),
        sa.Column(
            "items_synced",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "items_failed",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "conflicts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "finished_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["integration_id"], ["integrations.id"],
            ondelete="CASCADE",
            name="fk_sync_records_integration_id",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["connected_accounts.id"],
            ondelete="SET NULL",
            name="fk_sync_records_account_id",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_sync_records_workspace_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sync_records"),
    )
    op.create_index(
        "ix_sync_records_integration_id",
        "sync_records",
        ["integration_id"],
    )
    op.create_index(
        "ix_sync_records_workspace_id",
        "sync_records",
        ["workspace_id"],
    )
    op.create_index(
        "ix_sync_records_started_at",
        "sync_records",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_sync_records_started_at", "sync_records")
    op.drop_index("ix_sync_records_workspace_id", "sync_records")
    op.drop_index("ix_sync_records_integration_id", "sync_records")
    op.drop_table("sync_records")

    op.drop_index(
        "ix_connected_accounts_workspace_id", "connected_accounts"
    )
    op.drop_index(
        "ix_connected_accounts_integration_id", "connected_accounts"
    )
    op.drop_table("connected_accounts")

    op.drop_index("ix_integrations_status", "integrations")
    op.drop_index("ix_integrations_slug", "integrations")
    op.drop_index("ix_integrations_workspace_id", "integrations")
    op.drop_table("integrations")

    op.execute("DROP TYPE IF EXISTS sync_record_status")
    op.execute("DROP TYPE IF EXISTS account_status")
    op.execute("DROP TYPE IF EXISTS sync_mode")
    op.execute("DROP TYPE IF EXISTS integration_health")
    op.execute("DROP TYPE IF EXISTS integration_status")
    op.execute("DROP TYPE IF EXISTS integration_category")

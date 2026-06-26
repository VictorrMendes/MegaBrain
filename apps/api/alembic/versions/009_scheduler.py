"""scheduler triggers — TemporalTrigger, EventTrigger, RuleTrigger

Revision ID: 009
Revises: 008
Create Date: 2026-06-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduler_triggers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "type",
            sa.Enum(
                "temporal", "event", "rule",
                name="trigger_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active", "paused", "disabled",
                name="trigger_status",
            ),
            nullable=False,
            server_default="active",
        ),
        # TemporalTrigger
        sa.Column("cron_expression", sa.Text(), nullable=True),
        sa.Column(
            "timezone",
            sa.Text(),
            nullable=False,
            server_default="America/Sao_Paulo",
        ),
        # EventTrigger
        sa.Column("event_type", sa.Text(), nullable=True),
        sa.Column("event_filter", JSONB(), nullable=True),
        # RuleTrigger
        sa.Column("rule_expression", sa.Text(), nullable=True),
        sa.Column("poll_interval_seconds", sa.Integer(), nullable=True),
        # Mission template
        sa.Column("mission_intent_template", sa.Text(), nullable=False),
        sa.Column(
            "mission_context",
            JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "requires_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        # Scheduling metadata
        sa.Column(
            "last_fired_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "next_fire_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "fire_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
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
            name="fk_scheduler_triggers_workspace_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scheduler_triggers"),
    )
    op.create_index(
        "ix_scheduler_triggers_workspace_id",
        "scheduler_triggers",
        ["workspace_id"],
    )
    op.create_index(
        "ix_scheduler_triggers_type",
        "scheduler_triggers",
        ["type"],
    )
    op.create_index(
        "ix_scheduler_triggers_status",
        "scheduler_triggers",
        ["status"],
    )
    op.create_index(
        "ix_scheduler_triggers_next_fire_at",
        "scheduler_triggers",
        ["next_fire_at"],
    )
    op.create_index(
        "ix_scheduler_triggers_event_type",
        "scheduler_triggers",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scheduler_triggers_event_type", "scheduler_triggers"
    )
    op.drop_index(
        "ix_scheduler_triggers_next_fire_at", "scheduler_triggers"
    )
    op.drop_index(
        "ix_scheduler_triggers_status", "scheduler_triggers"
    )
    op.drop_index(
        "ix_scheduler_triggers_type", "scheduler_triggers"
    )
    op.drop_index(
        "ix_scheduler_triggers_workspace_id", "scheduler_triggers"
    )
    op.drop_table("scheduler_triggers")

    op.execute("DROP TYPE IF EXISTS trigger_status")
    op.execute("DROP TYPE IF EXISTS trigger_type")

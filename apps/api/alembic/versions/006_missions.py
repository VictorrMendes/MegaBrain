"""missions — Phase 2A: Mission Engine data model

Revision ID: 006
Revises: 005
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums
    op.execute("""
        CREATE TYPE mission_status AS ENUM (
            'pending', 'planning', 'waiting_approval', 'ready',
            'running', 'paused', 'retrying', 'succeeded', 'failed', 'cancelled'
        )
    """)
    op.execute("""
        CREATE TYPE mission_trigger AS ENUM (
            'manual', 'scheduled', 'event', 'rule'
        )
    """)
    op.execute("""
        CREATE TYPE step_type AS ENUM (
            'tool', 'workflow', 'agent', 'human'
        )
    """)
    op.execute("""
        CREATE TYPE step_status AS ENUM (
            'pending', 'running', 'succeeded', 'failed', 'skipped'
        )
    """)

    # missions
    op.create_table(
        "missions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "planning", "waiting_approval", "ready",
                "running", "paused", "retrying", "succeeded",
                "failed", "cancelled",
                name="mission_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("planner", sa.Text(), nullable=True),
        sa.Column("executor", sa.Text(), nullable=True),
        sa.Column(
            "trigger",
            sa.Enum(
                "manual", "scheduled", "event", "rule",
                name="mission_trigger",
                create_type=False,
            ),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "requires_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_missions_workspace_id_workspaces",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_missions"),
    )
    op.create_index("ix_missions_workspace_id", "missions", ["workspace_id"])
    op.create_index("ix_missions_status", "missions", ["status"])

    # mission_steps
    op.create_table(
        "mission_steps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("mission_id", sa.UUID(), nullable=False),
        sa.Column("parent_step_id", sa.UUID(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "tool", "workflow", "agent", "human",
                name="step_type",
                create_type=False,
            ),
            nullable=False,
            server_default="tool",
        ),
        sa.Column("tool", sa.Text(), nullable=False),
        sa.Column("input", JSONB(), nullable=False, server_default="{}"),
        sa.Column("output", JSONB(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "running", "succeeded", "failed", "skipped",
                name="step_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["mission_id"], ["missions.id"],
            ondelete="CASCADE",
            name="fk_mission_steps_mission_id_missions",
        ),
        sa.ForeignKeyConstraint(
            ["parent_step_id"], ["mission_steps.id"],
            ondelete="SET NULL",
            name="fk_mission_steps_parent_step_id_mission_steps",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mission_steps"),
    )
    op.create_index("ix_mission_steps_mission_id", "mission_steps", ["mission_id"])
    op.create_index("ix_mission_steps_status", "mission_steps", ["status"])

    # mission_contexts
    op.create_table(
        "mission_contexts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("mission_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=True),
        sa.Column("event_id", sa.UUID(), nullable=True),
        sa.Column(
            "available_capabilities",
            ARRAY(sa.Text()),
            server_default="{}",
        ),
        sa.Column(
            "workspace_config",
            JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "metadata",
            JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.ForeignKeyConstraint(
            ["mission_id"], ["missions.id"],
            ondelete="CASCADE",
            name="fk_mission_contexts_mission_id_missions",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"],
            ondelete="SET NULL",
            name="fk_mission_contexts_conversation_id_conversations",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mission_contexts"),
        sa.UniqueConstraint(
            "mission_id", name="uq_mission_contexts_mission_id"
        ),
    )

    # mission_artifacts
    op.create_table(
        "mission_artifacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("mission_id", sa.UUID(), nullable=False),
        sa.Column("step_id", sa.UUID(), nullable=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column(
            "mime",
            sa.Text(),
            nullable=False,
            server_default="application/octet-stream",
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mission_id"], ["missions.id"],
            ondelete="CASCADE",
            name="fk_mission_artifacts_mission_id_missions",
        ),
        sa.ForeignKeyConstraint(
            ["step_id"], ["mission_steps.id"],
            ondelete="SET NULL",
            name="fk_mission_artifacts_step_id_mission_steps",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mission_artifacts"),
    )
    op.create_index(
        "ix_mission_artifacts_mission_id",
        "mission_artifacts",
        ["mission_id"],
    )

    # mission_logs
    op.create_table(
        "mission_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("mission_id", sa.UUID(), nullable=False),
        sa.Column("step_id", sa.UUID(), nullable=True),
        sa.Column(
            "level", sa.Text(), nullable=False, server_default="info"
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mission_id"], ["missions.id"],
            ondelete="CASCADE",
            name="fk_mission_logs_mission_id_missions",
        ),
        sa.ForeignKeyConstraint(
            ["step_id"], ["mission_steps.id"],
            ondelete="SET NULL",
            name="fk_mission_logs_step_id_mission_steps",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mission_logs"),
    )
    op.create_index(
        "ix_mission_logs_mission_id", "mission_logs", ["mission_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_mission_logs_mission_id", "mission_logs")
    op.drop_table("mission_logs")

    op.drop_index("ix_mission_artifacts_mission_id", "mission_artifacts")
    op.drop_table("mission_artifacts")

    op.drop_table("mission_contexts")

    op.drop_index("ix_mission_steps_status", "mission_steps")
    op.drop_index("ix_mission_steps_mission_id", "mission_steps")
    op.drop_table("mission_steps")

    op.drop_index("ix_missions_status", "missions")
    op.drop_index("ix_missions_workspace_id", "missions")
    op.drop_table("missions")

    op.execute("DROP TYPE IF EXISTS step_status")
    op.execute("DROP TYPE IF EXISTS step_type")
    op.execute("DROP TYPE IF EXISTS mission_trigger")
    op.execute("DROP TYPE IF EXISTS mission_status")

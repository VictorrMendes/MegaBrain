"""execution_plans — ExecutionPlan entity (ADR-001)

Adds the execution_plans table between missions and mission_steps.
Backfills one ExecutionPlan per existing Mission so FK can be set.

Revision ID: 007
Revises: 006
Create Date: 2026-06-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("mission_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("planner", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "validated", "approved", "running",
                "completed", "failed", "superseded",
                name="execution_plan_status",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("validation_errors", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["mission_id"], ["missions.id"],
            ondelete="CASCADE",
            name="fk_execution_plans_mission_id_missions",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_execution_plans"),
    )
    op.create_index(
        "ix_execution_plans_mission_id", "execution_plans", ["mission_id"]
    )
    op.create_index(
        "ix_execution_plans_status", "execution_plans", ["status"]
    )

    # Add execution_plan_id to mission_steps (nullable — backfilled below)
    op.add_column(
        "mission_steps",
        sa.Column("execution_plan_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_mission_steps_execution_plan_id",
        "mission_steps",
        ["execution_plan_id"],
    )

    # Backfill: create one validated ExecutionPlan per existing Mission,
    # then assign all of that mission's steps to it.
    op.execute("""
        INSERT INTO execution_plans (id, mission_id, version, status, created_at)
        SELECT
            gen_random_uuid(),
            id,
            1,
            CASE
                WHEN status IN ('running', 'succeeded', 'failed', 'cancelled')
                THEN 'validated'::execution_plan_status
                ELSE 'draft'::execution_plan_status
            END,
            created_at
        FROM missions
    """)

    op.execute("""
        UPDATE mission_steps ms
        SET execution_plan_id = ep.id
        FROM execution_plans ep
        WHERE ep.mission_id = ms.mission_id
    """)

    op.create_foreign_key(
        "fk_mission_steps_execution_plan_id_execution_plans",
        "mission_steps",
        "execution_plans",
        ["execution_plan_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_mission_steps_execution_plan_id_execution_plans",
        "mission_steps",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_mission_steps_execution_plan_id", "mission_steps"
    )
    op.drop_column("mission_steps", "execution_plan_id")

    op.drop_index("ix_execution_plans_status", "execution_plans")
    op.drop_index("ix_execution_plans_mission_id", "execution_plans")
    op.drop_table("execution_plans")

    op.execute("DROP TYPE IF EXISTS execution_plan_status")

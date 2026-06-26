"""scheduler trigger priority field

Revision ID: 013
Revises: 012
Create Date: 2026-06-26
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scheduler_triggers",
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_index(
        "ix_scheduler_triggers_priority",
        "scheduler_triggers",
        ["priority"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scheduler_triggers_priority",
        table_name="scheduler_triggers",
    )
    op.drop_column("scheduler_triggers", "priority")

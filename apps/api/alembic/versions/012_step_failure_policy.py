"""mission step failure policy — FailurePolicy enum + campo em mission_steps

Revision ID: 012
Revises: 011
Create Date: 2026-06-26
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE failure_policy AS ENUM "
        "('retry', 'abort', 'skip', 'ignore')"
    )
    op.add_column(
        "mission_steps",
        sa.Column(
            "failure_policy",
            sa.Enum(
                "retry", "abort", "skip", "ignore",
                name="failure_policy",
                create_type=False,
            ),
            nullable=False,
            server_default="retry",
        ),
    )


def downgrade() -> None:
    op.drop_column("mission_steps", "failure_policy")
    op.execute("DROP TYPE IF EXISTS failure_policy")

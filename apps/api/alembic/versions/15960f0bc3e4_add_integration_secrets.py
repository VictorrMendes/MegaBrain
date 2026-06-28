"""add_integration_secrets

Revision ID: 15960f0bc3e4
Revises: 016
Create Date: 2026-06-27
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "15960f0bc3e4"
down_revision: str | None = "016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table(
        "integration_secrets",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
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
    )
    op.create_index(
        "ix_integration_secrets_provider",
        "integration_secrets",
        ["provider"],
        unique=True,
    )

def downgrade() -> None:
    op.drop_index("ix_integration_secrets_provider", table_name="integration_secrets")
    op.drop_table("integration_secrets")

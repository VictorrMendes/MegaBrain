"""obsidian knowledge graph

Revision ID: 005
Revises: 004
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "obsidian_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", sa.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("frontmatter", JSONB(), server_default=sa.text("'{}'")),
        sa.Column("last_modified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            ondelete="CASCADE", name="fk_obsidian_notes_workspace_id",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"],
            ondelete="SET NULL", name="fk_obsidian_notes_document_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_obsidian_notes"),
        sa.UniqueConstraint("workspace_id", "path", name="uq_obsidian_notes_workspace_path"),
    )
    op.create_index("ix_obsidian_notes_workspace_id", "obsidian_notes", ["workspace_id"])

    op.create_table(
        "obsidian_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("link_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            ondelete="CASCADE", name="fk_obsidian_links_workspace_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_obsidian_links"),
        sa.UniqueConstraint("workspace_id", "source_path", "target_path", name="uq_obsidian_links"),
    )
    op.create_index("ix_obsidian_links_workspace_id", "obsidian_links", ["workspace_id"])
    op.create_index("ix_obsidian_links_source_path", "obsidian_links", ["source_path"])


def downgrade() -> None:
    op.drop_index("ix_obsidian_links_source_path", "obsidian_links")
    op.drop_index("ix_obsidian_links_workspace_id", "obsidian_links")
    op.drop_table("obsidian_links")
    op.drop_index("ix_obsidian_notes_workspace_id", "obsidian_notes")
    op.drop_table("obsidian_notes")

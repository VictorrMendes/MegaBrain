"""documents and document chunks

Revision ID: 003
Revises: 002
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

document_status_enum = sa.Enum(
    "pending", "processing", "ready", "failed", name="document_status"
)


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column(
            "content_type",
            sa.String(100),
            nullable=False,
            server_default="text/plain",
        ),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            document_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "metadata",
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
            name="fk_documents_workspace_id_workspaces",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
    )

    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
            name="fk_document_chunks_document_id_documents",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_document_chunks_workspace_id_workspaces",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_chunks"),
    )

    op.create_index(
        "ix_document_chunks_workspace_id", "document_chunks", ["workspace_id"]
    )
    op.create_index(
        "ix_document_chunks_document_id", "document_chunks", ["document_id", "chunk_index"]
    )

    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN embedding vector(768)"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding ON document_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)"
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding", "document_chunks")
    op.drop_index("ix_document_chunks_document_id", "document_chunks")
    op.drop_index("ix_document_chunks_workspace_id", "document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_workspace_id", "documents")
    op.drop_table("documents")
    op.execute("DROP TYPE IF EXISTS document_status")

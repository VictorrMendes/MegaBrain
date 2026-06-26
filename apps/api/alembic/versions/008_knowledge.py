"""knowledge engine — Entity, Relation, Fact, Observation (ADR-005)

Revision ID: 008
Revises: 007
Create Date: 2026-06-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE entity_type AS ENUM (
                'person', 'service', 'device', 'concept',
                'place', 'organization', 'document', 'other'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # knowledge_entities
    op.create_table(
        "knowledge_entities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "person", "service", "device", "concept",
                "place", "organization", "document", "other",
                name="entity_type",
                create_type=False,
            ),
            nullable=False,
            server_default="other",
        ),
        sa.Column("aliases", ARRAY(sa.Text()), server_default="{}"),
        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
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
            name="fk_knowledge_entities_workspace_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_entities"),
    )
    op.create_index(
        "ix_knowledge_entities_workspace_id",
        "knowledge_entities",
        ["workspace_id"],
    )
    op.create_index(
        "ix_knowledge_entities_type",
        "knowledge_entities",
        ["type"],
    )
    # Full-text search on entity name
    op.execute("""
        CREATE INDEX ix_knowledge_entities_name_fts
        ON knowledge_entities
        USING gin(to_tsvector('portuguese', name))
    """)

    # knowledge_relations
    op.create_table(
        "knowledge_relations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("source_entity_id", sa.UUID(), nullable=False),
        sa.Column("relation", sa.Text(), nullable=False),
        sa.Column("target_entity_id", sa.UUID(), nullable=False),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column("source_type", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_knowledge_relations_workspace_id",
        ),
        sa.ForeignKeyConstraint(
            ["source_entity_id"], ["knowledge_entities.id"],
            ondelete="CASCADE",
            name="fk_knowledge_relations_source_entity_id",
        ),
        sa.ForeignKeyConstraint(
            ["target_entity_id"], ["knowledge_entities.id"],
            ondelete="CASCADE",
            name="fk_knowledge_relations_target_entity_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_relations"),
    )
    op.create_index(
        "ix_knowledge_relations_workspace_id",
        "knowledge_relations",
        ["workspace_id"],
    )
    op.create_index(
        "ix_knowledge_relations_source",
        "knowledge_relations",
        ["source_entity_id"],
    )
    op.create_index(
        "ix_knowledge_relations_target",
        "knowledge_relations",
        ["target_entity_id"],
    )

    # knowledge_facts
    op.create_table(
        "knowledge_facts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column(
            "source_type",
            sa.Text(),
            nullable=False,
            server_default="conversation",
        ),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column("superseded_by_id", sa.UUID(), nullable=True),
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
            name="fk_knowledge_facts_workspace_id",
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["knowledge_entities.id"],
            ondelete="SET NULL",
            name="fk_knowledge_facts_entity_id",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"], ["knowledge_facts.id"],
            ondelete="SET NULL",
            name="fk_knowledge_facts_superseded_by_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_facts"),
    )
    op.create_index(
        "ix_knowledge_facts_workspace_id",
        "knowledge_facts",
        ["workspace_id"],
    )
    op.create_index(
        "ix_knowledge_facts_entity_id",
        "knowledge_facts",
        ["entity_id"],
    )
    # Full-text search on fact statement
    op.execute("""
        CREATE INDEX ix_knowledge_facts_statement_fts
        ON knowledge_facts
        USING gin(to_tsvector('portuguese', statement))
        WHERE superseded_by_id IS NULL
    """)

    # knowledge_observations
    op.create_table(
        "knowledge_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column(
            "derived_from",
            sa.Text(),
            nullable=False,
            server_default="agent",
        ),
        sa.Column("derivation_agent", sa.Text(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="0.7",
        ),
        sa.Column(
            "reinforcement_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_reinforced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "expired",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_knowledge_observations_workspace_id",
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["knowledge_entities.id"],
            ondelete="SET NULL",
            name="fk_knowledge_observations_entity_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_observations"),
    )
    op.create_index(
        "ix_knowledge_observations_workspace_id",
        "knowledge_observations",
        ["workspace_id"],
    )
    op.create_index(
        "ix_knowledge_observations_entity_id",
        "knowledge_observations",
        ["entity_id"],
    )
    op.create_index(
        "ix_knowledge_observations_expired",
        "knowledge_observations",
        ["expired"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_observations_expired", "knowledge_observations"
    )
    op.drop_index(
        "ix_knowledge_observations_entity_id", "knowledge_observations"
    )
    op.drop_index(
        "ix_knowledge_observations_workspace_id", "knowledge_observations"
    )
    op.drop_table("knowledge_observations")

    op.execute("DROP INDEX IF EXISTS ix_knowledge_facts_statement_fts")
    op.drop_index("ix_knowledge_facts_entity_id", "knowledge_facts")
    op.drop_index("ix_knowledge_facts_workspace_id", "knowledge_facts")
    op.drop_table("knowledge_facts")

    op.drop_index("ix_knowledge_relations_target", "knowledge_relations")
    op.drop_index("ix_knowledge_relations_source", "knowledge_relations")
    op.drop_index(
        "ix_knowledge_relations_workspace_id", "knowledge_relations"
    )
    op.drop_table("knowledge_relations")

    op.execute(
        "DROP INDEX IF EXISTS ix_knowledge_entities_name_fts"
    )
    op.drop_index("ix_knowledge_entities_type", "knowledge_entities")
    op.drop_index(
        "ix_knowledge_entities_workspace_id", "knowledge_entities"
    )
    op.drop_table("knowledge_entities")

    op.execute("DROP TYPE IF EXISTS entity_type")

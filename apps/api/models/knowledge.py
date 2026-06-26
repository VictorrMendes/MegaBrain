from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class EntityType(enum.StrEnum):
    person = "person"
    service = "service"
    device = "device"
    concept = "concept"
    place = "place"
    organization = "organization"
    document = "document"
    other = "other"


class Entity(Base):
    """A named thing the system knows about.

    Entities are the anchors of the knowledge graph. Facts and
    Observations are attached to entities.
    """

    __tablename__ = "knowledge_entities"

    id: Mapped[UUID] = mapped_column(
        sa.UUID(), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    type: Mapped[EntityType] = mapped_column(
        sa.Enum(EntityType, name="entity_type"),
        nullable=False,
        default=EntityType.other,
        index=True,
    )
    aliases: Mapped[list] = mapped_column(
        sa.ARRAY(sa.Text()), server_default="{}"
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB(), nullable=False, server_default=sa.text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )

    facts: Mapped[list[Fact]] = relationship(
        "Fact",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    observations: Mapped[list[Observation]] = relationship(
        "Observation",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    relations_from: Mapped[list[Relation]] = relationship(
        "Relation",
        back_populates="source_entity",
        foreign_keys="Relation.source_entity_id",
        cascade="all, delete-orphan",
    )
    relations_to: Mapped[list[Relation]] = relationship(
        "Relation",
        back_populates="target_entity",
        foreign_keys="Relation.target_entity_id",
    )


class Relation(Base):
    """A directed relationship between two entities.

    Example: entity("PostgreSQL") --[runs_on]--> entity("Samsung NP550XCJ")
    """

    __tablename__ = "knowledge_relations"

    id: Mapped[UUID] = mapped_column(
        sa.UUID(), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_entity_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation: Mapped[str] = mapped_column(
        sa.Text(), nullable=False
    )  # e.g. "runs_on", "owns", "depends_on"
    target_entity_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(
        sa.Float(), nullable=False, server_default="1.0"
    )
    source_type: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )  # "conversation" | "document" | "user_explicit" | "inferred"
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )

    source_entity: Mapped[Entity] = relationship(
        "Entity",
        back_populates="relations_from",
        foreign_keys=[source_entity_id],
    )
    target_entity: Mapped[Entity] = relationship(
        "Entity",
        back_populates="relations_to",
        foreign_keys=[target_entity_id],
    )


class Fact(Base):
    """A verified statement about the world.

    Facts are near-certain (confidence ≥ 0.9), have a traceable source,
    and do not expire. They are corrected by creating a new Fact and
    marking this one superseded. See ADR-005.
    """

    __tablename__ = "knowledge_facts"

    id: Mapped[UUID] = mapped_column(
        sa.UUID(), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("knowledge_entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    statement: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    # "conversation" | "document" | "user_explicit" | "mission_output"
    source_type: Mapped[str] = mapped_column(
        sa.Text(), nullable=False, server_default="conversation"
    )
    source_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(), nullable=True
    )  # conversation_id or document_id
    confidence: Mapped[float] = mapped_column(
        sa.Float(), nullable=False, server_default="1.0"
    )
    superseded_by_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("knowledge_facts.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )

    entity: Mapped[Entity | None] = relationship(
        "Entity", back_populates="facts"
    )


class Observation(Base):
    """An inferred pattern derived from behavior, statistics, or rules.

    Observations have lower confidence than Facts, can expire, and decay
    over time if not reinforced. They are presented in the prompt as
    hedged knowledge ("parece que…", "tende a…"). See ADR-005.
    """

    __tablename__ = "knowledge_observations"

    id: Mapped[UUID] = mapped_column(
        sa.UUID(), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("knowledge_entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    statement: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    # "conversation_pattern" | "mission_statistics" | "rule_engine" | "agent"
    derived_from: Mapped[str] = mapped_column(
        sa.Text(), nullable=False, server_default="agent"
    )
    derivation_agent: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )
    sample_size: Mapped[int | None] = mapped_column(
        sa.Integer(), nullable=True
    )
    confidence: Mapped[float] = mapped_column(
        sa.Float(), nullable=False, server_default="0.7"
    )
    reinforcement_count: Mapped[int] = mapped_column(
        sa.Integer(), nullable=False, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
    last_reinforced_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    expired: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.false(), index=True
    )

    entity: Mapped[Entity | None] = relationship(
        "Entity", back_populates="observations"
    )

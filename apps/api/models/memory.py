import enum
from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MemoryType(str, enum.Enum):
    long = "long"
    working = "working"
    episodic = "episodic"
    semantic = "semantic"


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[MemoryType] = mapped_column(
        SAEnum(MemoryType, name="memory_type"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    superseded_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("memories.id"), nullable=True
    )
    # Campos de qualidade (Phase 2C)
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="1.0"
    )
    importance: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.5"
    )
    source: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # "conversation" | "mission" | "user_explicit" | "agent"
    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "memories.id",
            use_alter=True,
            name="fk_memories_source_id",
        ),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

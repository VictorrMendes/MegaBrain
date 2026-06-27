from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class WorkspaceSession(Base):
    __tablename__ = "workspace_sessions"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    active_conversation_id: Mapped[UUID | None] = mapped_column(
        nullable=True,
        default=None,
    )
    current_page: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None
    )
    ui_state: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        default=dict,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(UTC),
    )

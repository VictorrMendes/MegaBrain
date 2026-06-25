from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class InboxItemType(str, enum.Enum):
    text = "text"
    file = "file"
    url = "url"
    email = "email"
    note = "note"
    event = "event"


class InboxItemStatus(str, enum.Enum):
    pending = "pending"      # recebido, aguardando processamento
    processing = "processing"
    routed_knowledge = "routed_knowledge"  # enviado ao KnowledgeEngine
    routed_task = "routed_task"            # virou uma Mission
    routed_both = "routed_both"            # knowledge + mission
    dismissed = "dismissed"  # descartado sem ação


class InboxItem(Base):
    """Item da fila universal de entrada do PAIOS (Cognitive Inbox).

    Qualquer conteúdo externo — texto, arquivo, URL, email, nota —
    entra aqui primeiro. O InboxEngine decide se vai para:
    - KnowledgeEngine (extração de fatos/observações)
    - MissionEngine (criação de tarefa/mission)
    - Ambos

    Ver ARCHITECTURE.md §Cognitive Inbox.
    """

    __tablename__ = "inbox_items"

    id: Mapped[UUID] = mapped_column(
        sa.UUID(), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[InboxItemType] = mapped_column(
        sa.Enum(InboxItemType, name="inbox_item_type"),
        nullable=False,
        index=True,
    )
    status: Mapped[InboxItemStatus] = mapped_column(
        sa.Enum(InboxItemStatus, name="inbox_item_status"),
        nullable=False,
        default=InboxItemStatus.pending,
        index=True,
    )
    # Conteúdo bruto — texto, URL, caminho de arquivo, corpo do email
    raw_content: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    # Título opcional (subject do email, nome do arquivo, etc.)
    title: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    # Origem — "api" | "email" | "telegram" | "obsidian" | "webhook"
    source: Mapped[str] = mapped_column(
        sa.Text(), nullable=False, server_default="api"
    )
    # Metadata livre: remetente, tags, prioridade sugerida, etc.
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB(), nullable=False, server_default=sa.text("'{}'")
    )
    # Resultado do roteamento
    mission_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("missions.id", ondelete="SET NULL"),
        nullable=True,
    )
    knowledge_extracted: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.false()
    )
    routing_notes: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

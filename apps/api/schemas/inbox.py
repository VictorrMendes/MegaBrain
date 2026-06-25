from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from models.inbox import InboxItemStatus, InboxItemType


class SubmitInboxRequest(BaseModel):
    raw_content: str = Field(..., min_length=1)
    type: InboxItemType = InboxItemType.text
    title: str | None = None
    source: str = "api"
    metadata: dict = Field(default_factory=dict)
    # Se True, processa imediatamente ao invés de encfileirar
    process_now: bool = False


class InboxItemResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    type: InboxItemType
    status: InboxItemStatus
    raw_content: str
    title: str | None
    source: str
    metadata: dict
    mission_id: UUID | None
    knowledge_extracted: bool
    routing_notes: str | None
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class ProcessResultResponse(BaseModel):
    item_id: UUID
    status: InboxItemStatus
    mission_id: UUID | None
    knowledge_extracted: bool
    routing_notes: str | None

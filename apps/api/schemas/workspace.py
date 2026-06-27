from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str
    description: str | None = None


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceSessionResponse(BaseModel):
    workspace_id: UUID
    active_conversation_id: UUID | None
    current_page: str | None
    ui_state: dict
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceSessionUpdate(BaseModel):
    active_conversation_id: UUID | None = None
    current_page: str | None = None
    ui_state: dict = Field(default_factory=dict)

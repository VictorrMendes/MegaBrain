from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AvailablePlugin(BaseModel):
    name: str
    description: str


class WorkspacePluginCreate(BaseModel):
    plugin_name: str
    config: dict = {}
    is_enabled: bool = True


class WorkspacePluginUpdate(BaseModel):
    is_enabled: bool | None = None
    config: dict | None = None


class WorkspacePluginResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    plugin_name: str
    is_enabled: bool
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

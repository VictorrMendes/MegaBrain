from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from models.memory import MemoryType


class MemoryCreate(BaseModel):
    content: str
    type: MemoryType = MemoryType.long
    metadata: dict = {}


class MemorySupersede(BaseModel):
    content: str
    metadata: dict | None = None


class MemoryResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    type: MemoryType
    content: str
    metadata_: dict
    superseded_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}

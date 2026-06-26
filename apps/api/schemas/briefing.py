from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BriefingRequest(BaseModel):
    type: str = "daily"
    additional_context: str = ""


class BriefingResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    type: str
    title: str
    content: str
    metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            workspace_id=obj.workspace_id,
            type=obj.type,
            title=obj.title,
            content=obj.content,
            metadata=obj.metadata_,
            created_at=obj.created_at,
        )

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from models.document import DocumentStatus


class DocumentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    filename: str
    content_type: str
    file_size: int
    status: DocumentStatus
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    workspace_id: UUID
    chunk_index: int
    content: str
    token_count: int
    created_at: datetime

    model_config = {"from_attributes": True}

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ObsidianNoteInput(BaseModel):
    path: str
    content: str
    last_modified: datetime | None = None


class ObsidianSyncRequest(BaseModel):
    notes: list[ObsidianNoteInput]


class ObsidianSyncResponse(BaseModel):
    added: int
    updated: int
    unchanged: int
    errors: list[str]


class ObsidianNoteResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    path: str
    title: str
    tags: list[str]
    frontmatter: dict
    last_modified: datetime | None
    document_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GraphNode(BaseModel):
    id: str          # note path
    title: str
    tags: list[str]
    path: str


class GraphEdge(BaseModel):
    source: str      # source note path
    target: str      # target note path
    link_text: str | None


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]

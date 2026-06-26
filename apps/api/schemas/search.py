from __future__ import annotations

from pydantic import BaseModel


class SearchResult(BaseModel):
    type: str
    id: str
    title: str
    excerpt: str
    workspace_id: str
    href: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int

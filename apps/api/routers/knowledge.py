from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.dependencies import get_knowledge_engine
from engines.knowledge import KnowledgeEngine
from models.knowledge import EntityType

router = APIRouter(
    prefix="/workspaces/{workspace_id}/knowledge",
    tags=["knowledge"],
)


class FactResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    statement: str
    source_type: str
    source_id: UUID | None
    entity_id: UUID | None
    confidence: float
    created_at: datetime

    model_config = {"from_attributes": True}


class ObservationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    statement: str
    derived_from: str
    confidence: float
    reinforcement_count: int
    expired: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EntityResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    type: EntityType
    aliases: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class RelationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    source_entity_id: UUID
    relation: str
    target_entity_id: UUID
    confidence: float
    source_type: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/facts", response_model=list[FactResponse])
async def list_facts(
    workspace_id: UUID,
    entity_id: UUID | None = None,
    include_superseded: bool = False,
    limit: int = 50,
    engine: KnowledgeEngine = Depends(get_knowledge_engine),
):
    return await engine.list_facts(
        workspace_id=workspace_id,
        entity_id=entity_id,
        include_superseded=include_superseded,
        limit=limit,
    )


@router.get("/observations", response_model=list[ObservationResponse])
async def list_observations(
    workspace_id: UUID,
    entity_id: UUID | None = None,
    min_confidence: float = 0.0,
    include_expired: bool = False,
    limit: int = 50,
    engine: KnowledgeEngine = Depends(get_knowledge_engine),
):
    return await engine.list_observations(
        workspace_id=workspace_id,
        entity_id=entity_id,
        min_confidence=min_confidence,
        include_expired=include_expired,
        limit=limit,
    )


@router.get("/entities", response_model=list[EntityResponse])
async def list_entities(
    workspace_id: UUID,
    entity_type: EntityType | None = None,
    limit: int = 50,
    engine: KnowledgeEngine = Depends(get_knowledge_engine),
):
    return await engine.list_entities(
        workspace_id=workspace_id,
        entity_type=entity_type,
        limit=limit,
    )


@router.get("/relations", response_model=list[RelationResponse])
async def list_relations(
    workspace_id: UUID,
    entity_id: UUID | None = None,
    limit: int = 100,
    engine: KnowledgeEngine = Depends(get_knowledge_engine),
):
    return await engine.list_relations(
        workspace_id=workspace_id,
        entity_id=entity_id,
        limit=limit,
    )


@router.post("/decay")
async def run_decay(
    workspace_id: UUID,
    engine: KnowledgeEngine = Depends(get_knowledge_engine),
):
    """Manually trigger confidence decay on observations."""
    expired = await engine.run_decay(workspace_id=workspace_id)
    return {"expired_count": expired}

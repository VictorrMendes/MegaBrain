from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from models.memory import MemoryType

from core.dependencies import get_memory_engine
from engines.memory import MemoryEngine
from schemas.memory import MemoryCreate, MemoryResponse, MemorySupersede

router = APIRouter(
    prefix="/workspaces/{workspace_id}/memories",
    tags=["memories"],
)


@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(
    workspace_id: UUID,
    data: MemoryCreate,
    engine: MemoryEngine = Depends(get_memory_engine),
):
    return await engine.remember(
        workspace_id=workspace_id,
        content=data.content,
        type=data.type,
        metadata=data.metadata,
    )


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    workspace_id: UUID,
    type: MemoryType | None = None,
    limit: int = 50,
    engine: MemoryEngine = Depends(get_memory_engine),
):
    return await engine.list_active(
        workspace_id=workspace_id,
        type_filter=type,
        limit=limit,
    )


@router.get("/recall", response_model=list[MemoryResponse])
async def recall_memories(
    workspace_id: UUID,
    q: str,
    limit: int = 10,
    type: MemoryType | None = None,
    engine: MemoryEngine = Depends(get_memory_engine),
):
    return await engine.recall(
        workspace_id=workspace_id,
        query=q,
        limit=limit,
        type_filter=type,
    )


@router.post("/{memory_id}/supersede", response_model=MemoryResponse)
async def supersede_memory(
    workspace_id: UUID,
    memory_id: UUID,
    data: MemorySupersede,
    engine: MemoryEngine = Depends(get_memory_engine),
):
    try:
        return await engine.supersede(
            memory_id=memory_id,
            new_content=data.content,
            new_metadata=data.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

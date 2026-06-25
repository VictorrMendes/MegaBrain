from uuid import UUID

from fastapi import APIRouter, Depends

from core.dependencies import get_obsidian_engine
from engines.obsidian import ObsidianEngine
from schemas.obsidian import (
    GraphResponse,
    ObsidianNoteResponse,
    ObsidianSyncRequest,
    ObsidianSyncResponse,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/obsidian",
    tags=["obsidian"],
)


@router.post("/sync", response_model=ObsidianSyncResponse)
async def sync_vault(
    workspace_id: UUID,
    data: ObsidianSyncRequest,
    engine: ObsidianEngine = Depends(get_obsidian_engine),
):
    stats = await engine.sync(workspace_id=workspace_id, notes=data.notes)
    return ObsidianSyncResponse(
        added=stats.added,
        updated=stats.updated,
        unchanged=stats.unchanged,
        errors=stats.errors,
    )


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    workspace_id: UUID,
    engine: ObsidianEngine = Depends(get_obsidian_engine),
):
    return await engine.get_graph(workspace_id)


@router.get("/notes", response_model=list[ObsidianNoteResponse])
async def list_notes(
    workspace_id: UUID,
    engine: ObsidianEngine = Depends(get_obsidian_engine),
):
    return await engine.list_notes(workspace_id)

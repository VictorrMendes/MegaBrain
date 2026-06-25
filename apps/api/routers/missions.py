from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_mission_engine
from engines.mission import InvalidTransitionError, MissionEngine, MissionError
from models.mission import MissionStatus
from schemas.mission import (
    CreateMissionRequest,
    MissionDetailResponse,
    MissionResponse,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/missions",
    tags=["missions"],
)


@router.post("", response_model=MissionResponse, status_code=201)
async def create_mission(
    workspace_id: UUID,
    body: CreateMissionRequest,
    engine: MissionEngine = Depends(get_mission_engine),
):
    return await engine.create(
        workspace_id=workspace_id,
        intent=body.intent,
        trigger=body.trigger,
        requires_approval=body.requires_approval,
        conversation_id=body.conversation_id,
        context_metadata=body.context_metadata,
    )


@router.get("", response_model=list[MissionResponse])
async def list_missions(
    workspace_id: UUID,
    status: MissionStatus | None = None,
    limit: int = 50,
    engine: MissionEngine = Depends(get_mission_engine),
):
    return await engine.list(
        workspace_id=workspace_id,
        status=status,
        limit=limit,
    )


@router.get("/{mission_id}", response_model=MissionDetailResponse)
async def get_mission(
    workspace_id: UUID,
    mission_id: UUID,
    engine: MissionEngine = Depends(get_mission_engine),
):
    try:
        return await engine.get(mission_id)
    except MissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{mission_id}/plan", response_model=MissionResponse)
async def plan_mission(
    workspace_id: UUID,
    mission_id: UUID,
    provider: str | None = None,
    engine: MissionEngine = Depends(get_mission_engine),
):
    try:
        return await engine.plan(mission_id, provider_name=provider)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except MissionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/{mission_id}/approve", response_model=MissionResponse)
async def approve_mission(
    workspace_id: UUID,
    mission_id: UUID,
    engine: MissionEngine = Depends(get_mission_engine),
):
    try:
        return await engine.approve(mission_id)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{mission_id}/reject", response_model=MissionResponse)
async def reject_mission(
    workspace_id: UUID,
    mission_id: UUID,
    engine: MissionEngine = Depends(get_mission_engine),
):
    try:
        return await engine.reject(mission_id)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{mission_id}/run", response_model=MissionResponse)
async def run_mission(
    workspace_id: UUID,
    mission_id: UUID,
    engine: MissionEngine = Depends(get_mission_engine),
):
    try:
        return await engine.run(mission_id)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except MissionError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{mission_id}/pause", response_model=MissionResponse)
async def pause_mission(
    workspace_id: UUID,
    mission_id: UUID,
    engine: MissionEngine = Depends(get_mission_engine),
):
    try:
        return await engine.pause(mission_id)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{mission_id}/resume", response_model=MissionResponse)
async def resume_mission(
    workspace_id: UUID,
    mission_id: UUID,
    engine: MissionEngine = Depends(get_mission_engine),
):
    try:
        return await engine.resume(mission_id)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{mission_id}/cancel", response_model=MissionResponse)
async def cancel_mission(
    workspace_id: UUID,
    mission_id: UUID,
    engine: MissionEngine = Depends(get_mission_engine),
):
    try:
        return await engine.cancel(mission_id)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

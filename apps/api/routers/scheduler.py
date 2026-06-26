from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_scheduler_engine
from engines.scheduler import SchedulerEngine
from models.scheduler import TriggerStatus, TriggerType
from schemas.scheduler import CreateTriggerRequest, TriggerResponse

router = APIRouter(
    prefix="/workspaces/{workspace_id}/triggers",
    tags=["scheduler"],
)


@router.post("", response_model=TriggerResponse, status_code=201)
async def create_trigger(
    workspace_id: UUID,
    body: CreateTriggerRequest,
    engine: SchedulerEngine = Depends(get_scheduler_engine),
):
    try:
        return await engine.create_trigger(
            workspace_id=workspace_id,
            name=body.name,
            description=body.description,
            trigger_type=body.type,
            mission_intent_template=body.mission_intent_template,
            cron_expression=body.cron_expression,
            timezone=body.timezone,
            event_type=body.event_type,
            event_filter=body.event_filter,
            rule_expression=body.rule_expression,
            poll_interval_seconds=body.poll_interval_seconds,
            mission_context=body.mission_context,
            requires_approval=body.requires_approval,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("", response_model=list[TriggerResponse])
async def list_triggers(
    workspace_id: UUID,
    type: TriggerType | None = None,
    status: TriggerStatus | None = None,
    engine: SchedulerEngine = Depends(get_scheduler_engine),
):
    return await engine.list_triggers(
        workspace_id=workspace_id,
        trigger_type=type,
        status=status,
    )


@router.get("/{trigger_id}", response_model=TriggerResponse)
async def get_trigger(
    workspace_id: UUID,
    trigger_id: UUID,
    engine: SchedulerEngine = Depends(get_scheduler_engine),
):
    try:
        return await engine.get_trigger(trigger_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{trigger_id}/pause", response_model=TriggerResponse)
async def pause_trigger(
    workspace_id: UUID,
    trigger_id: UUID,
    engine: SchedulerEngine = Depends(get_scheduler_engine),
):
    try:
        return await engine.pause_trigger(trigger_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{trigger_id}/resume", response_model=TriggerResponse)
async def resume_trigger(
    workspace_id: UUID,
    trigger_id: UUID,
    engine: SchedulerEngine = Depends(get_scheduler_engine),
):
    try:
        return await engine.resume_trigger(trigger_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{trigger_id}", status_code=204)
async def delete_trigger(
    workspace_id: UUID,
    trigger_id: UUID,
    engine: SchedulerEngine = Depends(get_scheduler_engine),
):
    await engine.delete_trigger(trigger_id)

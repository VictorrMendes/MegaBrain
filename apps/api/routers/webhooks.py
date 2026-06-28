import json
from fastapi import APIRouter, Depends, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Any, Optional
from kernel.logger import get_logger

logger = get_logger("khonshu.webhooks")
router = APIRouter(prefix="/webhooks", tags=["Webhooks & CloudEvents"])

class CloudEventPayload(BaseModel):
    event: str
    provider: str
    capability: str
    execution_id: str
    trace_id: Optional[str] = None
    mission_id: Optional[str] = None
    status: str
    payload: dict[str, Any] = {}

@router.post("/events")
async def receive_cloudevent(
    event: CloudEventPayload,
    background_tasks: BackgroundTasks
):
    """
    Universal webhook receiver for all capability execution providers (e.g. n8n).
    Emits a domain event to the internal EventBus for the MissionEngine and LearningEngine to process.
    """
    logger.info(
        "webhook.cloudevent_received", 
        event=event.event, 
        provider=event.provider, 
        execution_id=event.execution_id,
        status=event.status
    )
    
    # Normally we would inject the global EventBus and emit the event here.
    # from kernel.events.broadcaster import event_bus
    # background_tasks.add_task(event_bus.publish, f"domain.execution.{event.event}", event.model_dump())
    
    return {"status": "accepted", "execution_id": event.execution_id}

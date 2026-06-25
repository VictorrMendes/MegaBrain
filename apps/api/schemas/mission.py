from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from models.mission import MissionStatus, MissionTrigger, StepStatus, StepType


class CreateMissionRequest(BaseModel):
    intent: str
    trigger: MissionTrigger = MissionTrigger.MANUAL
    requires_approval: bool = False
    conversation_id: UUID | None = None
    context_metadata: dict = {}


class MissionStepResponse(BaseModel):
    id: UUID
    mission_id: UUID
    order: int
    type: StepType
    tool: str
    input: dict
    output: dict | None
    status: StepStatus
    started_at: datetime | None
    finished_at: datetime | None
    retry_count: int

    model_config = {"from_attributes": True}


class MissionArtifactResponse(BaseModel):
    id: UUID
    mission_id: UUID
    step_id: UUID | None
    type: str
    mime: str
    name: str
    uri: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MissionLogResponse(BaseModel):
    id: UUID
    mission_id: UUID
    step_id: UUID | None
    level: str
    message: str
    occurred_at: datetime

    model_config = {"from_attributes": True}


class MissionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    intent: str
    status: MissionStatus
    planner: str | None
    executor: str | None
    trigger: MissionTrigger
    requires_approval: bool
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class MissionDetailResponse(MissionResponse):
    steps: list[MissionStepResponse] = []
    artifacts: list[MissionArtifactResponse] = []
    logs: list[MissionLogResponse] = []

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from models.scheduler import TriggerStatus, TriggerType


class CreateTriggerRequest(BaseModel):
    name: str
    description: str | None = None
    type: TriggerType
    mission_intent_template: str

    # TemporalTrigger
    cron_expression: str | None = None
    timezone: str = "America/Sao_Paulo"

    # EventTrigger
    event_type: str | None = None
    event_filter: dict | None = None

    # RuleTrigger
    rule_expression: str | None = None
    poll_interval_seconds: int | None = None

    mission_context: dict = Field(default_factory=dict)
    requires_approval: bool = False


class TriggerResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    type: TriggerType
    status: TriggerStatus
    cron_expression: str | None
    timezone: str
    event_type: str | None
    rule_expression: str | None
    poll_interval_seconds: int | None
    mission_intent_template: str
    requires_approval: bool
    last_fired_at: datetime | None
    next_fire_at: datetime | None
    fire_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

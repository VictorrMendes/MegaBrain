from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProviderInfo(BaseModel):
    name: str
    model: str
    embed_model: str | None = None
    base_url: str


class CapabilityInfo(BaseModel):
    name: str
    description: str
    plugin: str
    risk_level: str
    tags: list[str]
    tool_count: int
    requires_network: bool
    requires_confirmation: bool
    confidence_score: float


class SchedulerInfo(BaseModel):
    active_triggers: int
    paused_triggers: int
    total_triggers: int


class MissionSummary(BaseModel):
    id: UUID
    intent: str
    status: str
    created_at: datetime
    updated_at: datetime


class ComponentHealthInfo(BaseModel):
    name: str
    status: str
    latency_ms: float | None = None
    detail: str | None = None
    checked_at: datetime


class RuntimeStatus(BaseModel):
    status: str
    checked_at: datetime
    provider: ProviderInfo
    health: list[ComponentHealthInfo]
    capabilities: list[CapabilityInfo]
    scheduler: SchedulerInfo
    active_missions: list[MissionSummary]

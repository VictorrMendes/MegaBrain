from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from schemas.runtime import ComponentHealthInfo, SchedulerInfo


class MissionCounts(BaseModel):
    pending: int = 0
    planning: int = 0
    waiting_approval: int = 0
    ready: int = 0
    running: int = 0
    succeeded: int = 0
    failed: int = 0
    cancelled: int = 0
    total: int = 0


class RecentMission(BaseModel):
    id: UUID
    intent: str
    status: str
    trigger: str
    created_at: datetime
    updated_at: datetime


class RecentMemory(BaseModel):
    id: UUID
    type: str
    content: str
    importance: float
    created_at: datetime


class RecentFact(BaseModel):
    id: UUID
    statement: str
    confidence: float
    created_at: datetime


class RecentArtifact(BaseModel):
    id: UUID
    name: str
    type: str
    mime: str
    mission_id: UUID
    created_at: datetime


class DashboardSummary(BaseModel):
    workspace_id: UUID
    workspace_name: str
    generated_at: datetime
    missions: MissionCounts
    inbox_pending: int
    recent_missions: list[RecentMission]
    recent_memories: list[RecentMemory]
    recent_facts: list[RecentFact]
    recent_artifacts: list[RecentArtifact]
    health: list[ComponentHealthInfo]
    scheduler: SchedulerInfo

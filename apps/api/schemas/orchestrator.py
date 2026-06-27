"""Pydantic schemas for the /orchestrator/execute endpoint.

All fields mirror the internal dataclasses in kernel/orchestrator/models.py
but use Pydantic for serialisation and FastAPI request validation.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# ── Request ──────────────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    message: str
    conversation_id: str | None = None


# ── Sub-schemas ───────────────────────────────────────────────────────────────

class DecisionSchema(BaseModel):
    need_memory: bool
    need_knowledge: bool
    need_search: bool
    need_integrations: bool
    need_planner: bool
    need_mission: bool
    need_execution: bool
    need_confirmation: bool
    need_learning: bool
    risk_level: str
    confidence: float
    reason: str


class TraceNodeSchema(BaseModel):
    id: str
    step: str
    engine: str
    reason: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: float | None
    status: str
    output_summary: str | None


class LearningActionSchema(BaseModel):
    type: str
    content: str
    confidence: float
    reason: str


# ── Response ──────────────────────────────────────────────────────────────────

class ExecuteResponse(BaseModel):
    response: str
    decision: DecisionSchema
    trace: list[TraceNodeSchema]
    confidence: float
    risk: str
    sources: list[dict]
    capabilities_used: list[str]
    missions_created: list[str]
    learning_actions: list[LearningActionSchema]
    thinking_steps: list[str]
    memory_used: int
    knowledge_used: int
    internet_sources: int
    integrations_used: list[str]
    planner_used: bool
    mission_created: bool
    estimated_cost: float
    estimated_time: float
    approval_required: bool

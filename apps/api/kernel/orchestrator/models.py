"""Typed models for the Cognitive Orchestrator.

All data flowing through the orchestrator pipeline is strongly typed.
No raw dicts — every boundary is a dataclass or Enum.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TraceStatus(str, Enum):
    running = "running"
    completed = "completed"
    skipped = "skipped"
    failed = "failed"


class LearningActionType(str, Enum):
    create_memory = "create_memory"
    create_fact = "create_fact"
    create_observation = "create_observation"
    update_preference = "update_preference"
    record_pattern = "record_pattern"
    ignore = "ignore"


@dataclass
class Decision:
    """Routing decision produced by DecisionEngine."""

    need_memory: bool = True
    need_knowledge: bool = True
    need_search: bool = False
    need_integrations: bool = False
    need_planner: bool = False
    need_mission: bool = False
    need_execution: bool = False
    need_learning: bool = True
    need_confirmation: bool = False
    risk_level: RiskLevel = RiskLevel.low
    confidence: float = 0.8
    estimated_cost: float = 0.0
    estimated_latency: float = 0.0
    reason: str = ""
    target_capability: str | None = None
    target_provider: str | None = None
    capability_params: dict = field(default_factory=dict)



@dataclass
class TraceNode:
    """Single step in the reasoning trace."""

    step: str
    engine: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reason: str = ""
    finished_at: datetime | None = None
    duration_ms: float | None = None
    status: TraceStatus = TraceStatus.running
    output_summary: str | None = None
    children: list[TraceNode] = field(default_factory=list)


@dataclass
class LearningAction:
    """A single learning action proposed by LearningEngine."""

    type: LearningActionType
    content: str
    confidence: float
    reason: str
    metadata: dict = field(default_factory=dict)


@dataclass
class LearningDecision:
    """Full learning decision with list of actions."""

    should_learn: bool
    actions: list[LearningAction]
    reason: str


@dataclass
class OrchestratorRequest:
    """Input to the cognitive pipeline."""

    workspace_id: str
    message: str
    conversation_id: str | None = None


@dataclass
class ConversationResult:
    """Snapshot of a completed exchange, fed into LearningEngine."""

    request: OrchestratorRequest
    decision: Decision
    response: str
    memories_retrieved: int = 0
    knowledge_count: int = 0
    search_results: list[dict] = field(default_factory=list)
    integrations_used: list[str] = field(default_factory=list)
    missions_created: list[str] = field(default_factory=list)


@dataclass
class OrchestratorResponse:
    """Full cognitive response exposed to the API."""

    response: str
    decision: Decision
    trace: list[TraceNode]
    confidence: float
    risk: RiskLevel
    sources: list[dict]
    capabilities_used: list[str]
    missions_created: list[str]
    learning_actions: list[LearningAction]
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

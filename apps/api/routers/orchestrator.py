"""POST /orchestrator/{workspace_id}/execute

Runs the full cognitive pipeline and returns a rich response that
exposes how Khonshu thought: decision, reasoning trace, learning
actions, missions created, and confidence metrics.

Designed for frontend flows where transparency matters — the chat
streaming endpoint (/messages/stream) remains the primary interactive
interface; this endpoint is the "thinking aloud" interface.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_orchestrator
from kernel.orchestrator import CognitiveOrchestrator, OrchestratorRequest
from schemas.orchestrator import (
    DecisionSchema,
    ExecuteRequest,
    ExecuteResponse,
    LearningActionSchema,
    TraceNodeSchema,
)

router = APIRouter(
    prefix="/orchestrator",
    tags=["orchestrator"],
)


def _to_response(orch_resp) -> ExecuteResponse:
    """Convert internal OrchestratorResponse to Pydantic schema."""
    return ExecuteResponse(
        response=orch_resp.response,
        decision=DecisionSchema(
            need_memory=orch_resp.decision.need_memory,
            need_knowledge=orch_resp.decision.need_knowledge,
            need_search=orch_resp.decision.need_search,
            need_integrations=orch_resp.decision.need_integrations,
            need_planner=orch_resp.decision.need_planner,
            need_mission=orch_resp.decision.need_mission,
            need_execution=orch_resp.decision.need_execution,
            need_confirmation=orch_resp.decision.need_confirmation,
            need_learning=orch_resp.decision.need_learning,
            risk_level=orch_resp.decision.risk_level.value,
            confidence=orch_resp.decision.confidence,
            reason=orch_resp.decision.reason,
        ),
        trace=[
            TraceNodeSchema(
                id=n.id,
                step=n.step,
                engine=n.engine,
                reason=n.reason,
                started_at=n.started_at,
                finished_at=n.finished_at,
                duration_ms=n.duration_ms,
                status=n.status.value,
                output_summary=n.output_summary,
            )
            for n in orch_resp.trace
        ],
        confidence=orch_resp.confidence,
        risk=orch_resp.risk.value,
        sources=orch_resp.sources,
        capabilities_used=orch_resp.capabilities_used,
        missions_created=orch_resp.missions_created,
        learning_actions=[
            LearningActionSchema(
                type=a.type.value,
                content=a.content,
                confidence=a.confidence,
                reason=a.reason,
            )
            for a in orch_resp.learning_actions
        ],
        thinking_steps=orch_resp.thinking_steps,
        memory_used=orch_resp.memory_used,
        knowledge_used=orch_resp.knowledge_used,
        internet_sources=orch_resp.internet_sources,
        integrations_used=orch_resp.integrations_used,
        planner_used=orch_resp.planner_used,
        mission_created=orch_resp.mission_created,
        estimated_cost=orch_resp.estimated_cost,
        estimated_time=orch_resp.estimated_time,
        approval_required=orch_resp.approval_required,
    )


@router.post(
    "/{workspace_id}/execute",
    response_model=ExecuteResponse,
)
async def execute(
    workspace_id: UUID,
    body: ExecuteRequest,
    orchestrator: CognitiveOrchestrator = Depends(get_orchestrator),
):
    """Run the full cognitive pipeline for a user message.

    Returns the LLM response plus a complete reasoning trace: which
    engines activated, what was learned, any missions created, and the
    decision that drove routing.
    """
    request = OrchestratorRequest(
        workspace_id=str(workspace_id),
        message=body.message,
        conversation_id=body.conversation_id,
    )
    try:
        result = await orchestrator.execute(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _to_response(result)

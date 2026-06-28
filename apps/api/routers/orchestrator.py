"""POST /orchestrator/{workspace_id}/execute  (full response)
POST /orchestrator/{workspace_id}/stream    (SSE — trace steps in real time)

The streaming endpoint emits one SSE event per pipeline step as it
completes, then a final "done" event carrying the full response JSON.
This lets the frontend show cognitive steps as they happen, not all
at once after the full round-trip.
"""
from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

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


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


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


@router.post("/{workspace_id}/stream")
async def stream(
    workspace_id: UUID,
    body: ExecuteRequest,
    orchestrator: CognitiveOrchestrator = Depends(get_orchestrator),
):
    """Stream cognitive pipeline steps as SSE events, then final response.

    Event shapes:
      {"event": "trace_step", "step": str, "engine": str,
       "status": "completed"|"skipped"|"failed",
       "output": str|null, "duration_ms": float|null}
      {"event": "done", "response": <ExecuteResponse JSON>}
      {"event": "error", "message": str}
    """
    orch_request = OrchestratorRequest(
        workspace_id=str(workspace_id),
        message=body.message,
        conversation_id=body.conversation_id,
    )

    async def event_generator():
        step_queue: asyncio.Queue = asyncio.Queue()
        token_queue: asyncio.Queue = asyncio.Queue()

        async def on_step(node) -> None:
            await step_queue.put(("step", node))

        async def on_token(chunk: str) -> None:
            await token_queue.put(chunk)

        task = asyncio.create_task(
            orchestrator.execute(
                orch_request, on_step=on_step, on_token=on_token
            )
        )

        last_ping = asyncio.get_event_loop().time()
        try:
            while not task.done():
                # Drain tokens with priority (tokens come fast)
                while not token_queue.empty():
                    chunk = token_queue.get_nowait()
                    yield _sse({"event": "llm_token", "token": chunk})

                # Check for trace steps
                try:
                    kind, node = await asyncio.wait_for(
                        step_queue.get(), timeout=0.02
                    )
                    yield _sse({
                        "event": "trace_step",
                        "step": node.step,
                        "engine": node.engine,
                        "status": node.status.value,
                        "output": node.output_summary,
                        "duration_ms": node.duration_ms,
                    })
                except asyncio.TimeoutError:
                    pass
                
                # Keep-alive ping every 10 seconds to prevent Next.js / browser network drops
                now = asyncio.get_event_loop().time()
                if now - last_ping > 10.0:
                    yield _sse({"event": "ping", "timestamp": str(now)})
                    last_ping = now

            # Drain remaining tokens
            while not token_queue.empty():
                chunk = token_queue.get_nowait()
                yield _sse({"event": "llm_token", "token": chunk})

            # Drain remaining trace steps
            while not step_queue.empty():
                _, node = step_queue.get_nowait()
                yield _sse({
                    "event": "trace_step",
                    "step": node.step,
                    "engine": node.engine,
                    "status": node.status.value,
                    "output": node.output_summary,
                    "duration_ms": node.duration_ms,
                })

            result = task.result()
            resp = _to_response(result)
            yield _sse({
                "event": "done",
                "response": resp.model_dump(mode="json"),
            })

        except Exception as exc:
            yield _sse({"event": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

"""ReasoningTrace — builds a structured audit trail of cognitive steps.

Each step is opened with begin(), closed with complete()/fail(), or
recorded as skipped(). The trace becomes part of OrchestratorResponse
so the frontend can show exactly how Khonshu reasoned.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

from .models import TraceNode, TraceStatus
from schemas.events import TraceEvent
from .events.broadcaster import TraceBroadcaster


class ReasoningTrace:
    """Mutable trace built incrementally during orchestrator execution."""

    def __init__(
        self, 
        workspace_id: str, 
        trace_id: str | None = None,
        broadcaster: TraceBroadcaster | None = None
    ) -> None:
        self._nodes: list[TraceNode] = []
        self._workspace_id = workspace_id
        self._trace_id = trace_id or str(uuid.uuid4())
        self._broadcaster = broadcaster

        self._broadcast("trace.started", "Orchestrator", "running")

    def _broadcast(self, stage: str, engine: str, status: str, duration_ms: float = 0.0, metadata: dict | None = None) -> None:
        if not self._broadcaster:
            return
            
        event = TraceEvent(
            trace_id=self._trace_id,
            workspace_id=self._workspace_id,
            timestamp=datetime.now(timezone.utc),
            engine=engine,
            stage=stage,
            status=status,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        self._broadcaster.broadcast(event)

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def begin(
        self, step: str, engine: str, reason: str = ""
    ) -> TraceNode:
        """Open a new trace node (status=running)."""
        node = TraceNode(step=step, engine=engine, reason=reason)
        self._nodes.append(node)
        self._broadcast("step.started", engine, "running", metadata={"step": step, "reason": reason})
        return node

    def complete(
        self,
        node: TraceNode,
        output_summary: str | None = None,
        status: TraceStatus = TraceStatus.completed,
    ) -> None:
        """Close a node as completed (or override status)."""
        node.finished_at = datetime.utcnow()
        node.duration_ms = (
            (node.finished_at - node.started_at).total_seconds() * 1000
        )
        node.status = status
        node.output_summary = output_summary
        self._broadcast("step.completed", node.engine, status.value, node.duration_ms, metadata={"step": node.step, "output": output_summary})

    def fail(self, node: TraceNode, error: str) -> None:
        """Close a node as failed with an error description."""
        node.finished_at = datetime.utcnow()
        node.duration_ms = (
            (node.finished_at - node.started_at).total_seconds() * 1000
        )
        node.status = TraceStatus.failed
        node.output_summary = f"error: {error}"
        self._broadcast("step.failed", node.engine, "failed", node.duration_ms, metadata={"step": node.step, "error": error})

    def skip(
        self, step: str, engine: str, reason: str = ""
    ) -> TraceNode:
        """Record a step that was intentionally skipped."""
        node = TraceNode(
            step=step,
            engine=engine,
            reason=reason,
            finished_at=datetime.utcnow(),
            duration_ms=0.0,
            status=TraceStatus.skipped,
        )
        self._nodes.append(node)
        self._broadcast("step.skipped", engine, "skipped", 0.0, metadata={"step": step, "reason": reason})
        return node
        
    def finish(self, success: bool = True, error: str | None = None) -> None:
        """Mark the entire trace as completed or failed."""
        status = "completed" if success else "failed"
        stage = "trace.completed" if success else "trace.failed"
        metadata = {"error": error} if error else {}
        self._broadcast(stage, "Orchestrator", status, metadata=metadata)

    # ------------------------------------------------------------------ #
    # Accessors                                                            #
    # ------------------------------------------------------------------ #

    @property
    def nodes(self) -> list[TraceNode]:
        return list(self._nodes)

    def thinking_steps(self) -> list[str]:
        """Human-readable summary of each non-skipped step."""
        result = []
        for n in self._nodes:
            if n.status == TraceStatus.skipped:
                continue
            detail = n.output_summary or n.reason or n.step
            result.append(f"[{n.engine}] {n.step}: {detail}")
        return result

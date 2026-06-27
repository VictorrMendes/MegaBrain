"""ReasoningTrace — builds a structured audit trail of cognitive steps.

Each step is opened with begin(), closed with complete()/fail(), or
recorded as skipped(). The trace becomes part of OrchestratorResponse
so the frontend can show exactly how Khonshu reasoned.
"""
from __future__ import annotations

from datetime import datetime

from .models import TraceNode, TraceStatus


class ReasoningTrace:
    """Mutable trace built incrementally during orchestrator execution."""

    def __init__(self) -> None:
        self._nodes: list[TraceNode] = []

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def begin(
        self, step: str, engine: str, reason: str = ""
    ) -> TraceNode:
        """Open a new trace node (status=running)."""
        node = TraceNode(step=step, engine=engine, reason=reason)
        self._nodes.append(node)
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

    def fail(self, node: TraceNode, error: str) -> None:
        """Close a node as failed with an error description."""
        node.finished_at = datetime.utcnow()
        node.duration_ms = (
            (node.finished_at - node.started_at).total_seconds() * 1000
        )
        node.status = TraceStatus.failed
        node.output_summary = f"error: {error}"

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
        return node

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

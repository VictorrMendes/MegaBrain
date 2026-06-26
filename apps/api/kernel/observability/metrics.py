"""CognitiveMetrics — in-memory telemetry for the AI layer.

Tracks planning latency, execution latency, capability usage, search calls,
context builds, memory hits, knowledge hits and token estimates.

Exposed via GET /runtime as a 'cognitive_metrics' field.
Singleton owned by KhonshuRuntime.
"""
from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class _Counter:
    count: int = 0
    total_ms: float = 0.0

    def record(self, ms: float) -> None:
        self.count += 1
        self.total_ms += ms

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count else 0.0

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "avg_ms": round(self.avg_ms, 1),
            "total_ms": round(self.total_ms, 1),
        }


class CognitiveMetrics:
    """Lightweight in-memory metrics collector for the cognitive layer.

    All methods are synchronous and non-blocking — safe to call from
    any async context without await.
    """

    def __init__(self) -> None:
        self._planning = _Counter()
        self._execution = _Counter()
        self._context_builds = _Counter()
        self._web_searches: int = 0
        self._memory_hits: int = 0
        self._knowledge_hits: int = 0
        self._capability_calls: dict[str, int] = defaultdict(int)
        self._integration_syncs: dict[str, int] = defaultdict(int)
        self._cognitive_loop_ticks: int = 0
        self._briefings_generated: int = 0
        self._missions_auto_created: int = 0
        self._tokens_estimate: int = 0

    # ------------------------------------------------------------------ #
    # Recording                                                            #
    # ------------------------------------------------------------------ #

    def record_planning(self, ms: float) -> None:
        self._planning.record(ms)

    def record_execution(self, ms: float) -> None:
        self._execution.record(ms)

    def record_context_build(self, ms: float) -> None:
        self._context_builds.record(ms)

    def record_web_search(self) -> None:
        self._web_searches += 1

    def record_memory_hit(self, count: int = 1) -> None:
        self._memory_hits += count

    def record_knowledge_hit(self, count: int = 1) -> None:
        self._knowledge_hits += count

    def record_capability(self, name: str) -> None:
        self._capability_calls[name] += 1

    def record_integration_sync(self, slug: str) -> None:
        self._integration_syncs[slug] += 1

    def record_cognitive_loop_tick(self) -> None:
        self._cognitive_loop_ticks += 1

    def record_briefing(self) -> None:
        self._briefings_generated += 1

    def record_auto_mission(self) -> None:
        self._missions_auto_created += 1

    def record_tokens(self, count: int) -> None:
        self._tokens_estimate += count

    # ------------------------------------------------------------------ #
    # Timer helpers                                                        #
    # ------------------------------------------------------------------ #

    @contextmanager
    def time_planning(self) -> Iterator[None]:
        t0 = time.monotonic()
        try:
            yield
        finally:
            self.record_planning((time.monotonic() - t0) * 1000)

    @contextmanager
    def time_execution(self) -> Iterator[None]:
        t0 = time.monotonic()
        try:
            yield
        finally:
            self.record_execution((time.monotonic() - t0) * 1000)

    @contextmanager
    def time_context_build(self) -> Iterator[None]:
        t0 = time.monotonic()
        try:
            yield
        finally:
            self.record_context_build((time.monotonic() - t0) * 1000)

    # ------------------------------------------------------------------ #
    # Serialisation                                                        #
    # ------------------------------------------------------------------ #

    def top_capabilities(self, n: int = 5) -> list[dict]:
        sorted_caps = sorted(
            self._capability_calls.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [{"name": k, "calls": v} for k, v in sorted_caps[:n]]

    def top_integrations(self, n: int = 5) -> list[dict]:
        sorted_ints = sorted(
            self._integration_syncs.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [{"slug": k, "syncs": v} for k, v in sorted_ints[:n]]

    def to_dict(self) -> dict:
        return {
            "planning": self._planning.to_dict(),
            "execution": self._execution.to_dict(),
            "context_builds": self._context_builds.to_dict(),
            "web_searches": self._web_searches,
            "memory_hits": self._memory_hits,
            "knowledge_hits": self._knowledge_hits,
            "cognitive_loop_ticks": self._cognitive_loop_ticks,
            "briefings_generated": self._briefings_generated,
            "missions_auto_created": self._missions_auto_created,
            "tokens_estimate": self._tokens_estimate,
            "top_capabilities": self.top_capabilities(),
            "top_integrations": self.top_integrations(),
        }

"""CapabilityReasoner — scores and ranks capabilities before planning.

The Planner never picks tools directly.
It receives a pre-filtered, pre-ranked capability list from this module.

Scoring factors:
- availability       (provider-reported uptime, 0–1)
- confidence_score   (provider-reported reliability, 0–1)
- recent_failure     (in-memory exponential decay)
- risk_level         (low → bonus, critical → penalty)
- cooldown           (still in cooldown → excluded)
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from kernel.capabilities.registry import Capability, CapabilityRegistry, RiskLevel
from kernel.logger import get_logger

logger = get_logger(__name__)

_RISK_FACTOR = {
    RiskLevel.low: 1.0,
    RiskLevel.medium: 0.85,
    RiskLevel.high: 0.65,
    RiskLevel.critical: 0.40,
}

_FAILURE_WINDOW = timedelta(hours=1)
_FAILURE_HISTORY = 10  # max recent events tracked per capability


class CapabilityReasoner:
    """Evaluates available capabilities and ranks them for the Planner.

    Singleton owned by KhonshuRuntime; injected into LLMPlanProvider and
    StepExecutor.
    """

    def __init__(self) -> None:
        # Deque of (timestamp, success: bool) tuples per capability
        self._history: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=_FAILURE_HISTORY)
        )
        # Timestamp of last call per capability (for cooldown enforcement)
        self._last_call: dict[str, datetime] = {}

    # ------------------------------------------------------------------ #
    # Event recording                                                      #
    # ------------------------------------------------------------------ #

    def record_success(self, capability_name: str) -> None:
        self._history[capability_name].append((datetime.now(UTC), True))
        self._last_call[capability_name] = datetime.now(UTC)

    def record_failure(self, capability_name: str) -> None:
        self._history[capability_name].append((datetime.now(UTC), False))
        self._last_call[capability_name] = datetime.now(UTC)
        logger.warning(
            "capability_reasoner.failure_recorded",
            capability=capability_name,
        )

    # ------------------------------------------------------------------ #
    # Scoring                                                              #
    # ------------------------------------------------------------------ #

    def score(self, cap: Capability) -> float:
        """Return a composite score in [0, 1] for planning priority."""
        # Base: availability × confidence
        base = cap.availability * cap.confidence_score

        # Risk penalty
        base *= _RISK_FACTOR.get(cap.risk_level, 1.0)

        # Recent failure penalty (exponential decay over window)
        recent_failure_rate = self._recent_failure_rate(cap.name)
        base *= max(0.0, 1.0 - recent_failure_rate)

        return round(max(0.0, min(1.0, base)), 4)

    def _recent_failure_rate(self, capability_name: str) -> float:
        history = self._history[capability_name]
        if not history:
            return 0.0
        cutoff = datetime.now(UTC) - _FAILURE_WINDOW
        recent = [(ts, ok) for ts, ok in history if ts >= cutoff]
        if not recent:
            return 0.0
        failures = sum(1 for _, ok in recent if not ok)
        # Exponential weighting: most recent failures weigh more
        weighted_failure = sum(
            math.exp(-(i / max(len(recent), 1)))
            for i, (_, ok) in enumerate(reversed(recent))
            if not ok
        )
        weighted_total = sum(
            math.exp(-(i / max(len(recent), 1)))
            for i in range(len(recent))
        )
        return weighted_failure / weighted_total if weighted_total > 0 else 0.0

    # ------------------------------------------------------------------ #
    # Filtering + ranking                                                  #
    # ------------------------------------------------------------------ #

    def is_on_cooldown(self, cap: Capability) -> bool:
        if cap.cooldown_seconds is None:
            return False
        last = self._last_call.get(cap.name)
        if last is None:
            return False
        elapsed = (datetime.now(UTC) - last).total_seconds()
        return elapsed < cap.cooldown_seconds

    def filter_viable(
        self,
        capabilities: list[Capability],
        *,
        exclude_cooldown: bool = True,
        min_availability: float = 0.0,
    ) -> list[Capability]:
        result = []
        for cap in capabilities:
            if cap.availability < min_availability:
                logger.debug(
                    "capability_reasoner.filtered_unavailable",
                    capability=cap.name,
                    availability=cap.availability,
                )
                continue
            if exclude_cooldown and self.is_on_cooldown(cap):
                logger.debug(
                    "capability_reasoner.filtered_cooldown",
                    capability=cap.name,
                )
                continue
            result.append(cap)
        return result

    def rank(self, capabilities: list[Capability]) -> list[Capability]:
        return sorted(capabilities, key=lambda c: self.score(c), reverse=True)

    # ------------------------------------------------------------------ #
    # Planner context                                                      #
    # ------------------------------------------------------------------ #

    def to_planner_context(
        self,
        registry: CapabilityRegistry,
        *,
        include_score: bool = True,
    ) -> list[dict]:
        """Return a ranked, filtered capability list for LLM injection.

        Adds 'reasoner_score' and 'recently_failed' fields so the LLM
        can prefer reliable, low-risk capabilities.
        """
        viable = self.filter_viable(registry.list())
        ranked = self.rank(viable)

        result = []
        for cap in ranked:
            descriptor = cap.to_planner_descriptor()
            if include_score:
                descriptor["reasoner_score"] = self.score(cap)
                descriptor["recently_failed"] = (
                    self._recent_failure_rate(cap.name) > 0.3
                )
            result.append(descriptor)
        return result

    # ------------------------------------------------------------------ #
    # Diagnostics                                                          #
    # ------------------------------------------------------------------ #

    def status_report(self, registry: CapabilityRegistry) -> list[dict]:
        """Full status report for all registered capabilities."""
        return [
            {
                "name": cap.name,
                "score": self.score(cap),
                "on_cooldown": self.is_on_cooldown(cap),
                "recent_failure_rate": round(
                    self._recent_failure_rate(cap.name), 3
                ),
                "availability": cap.availability,
                "confidence_score": cap.confidence_score,
                "risk_level": cap.risk_level.value,
            }
            for cap in registry.list()
        ]

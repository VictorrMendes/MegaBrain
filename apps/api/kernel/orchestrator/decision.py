"""DecisionEngine — routes every user request to the right engines.

Asks the LLM: "which engines should activate for this message?"
Returns a typed Decision so the orchestrator knows exactly what to do.

Uses ExecutionProfile with low latency and deterministic output so
routing decisions are fast and predictable.
"""
from __future__ import annotations

import json
import re

from kernel.logger import get_logger
from kernel.providers.base import (
    ChatMessage,
    ExecutionProfile,
    LLMProvider,
)

from .models import Decision, RiskLevel

logger = get_logger("khonshu.orchestrator.decision")

_SYSTEM = """\
You are the routing intelligence of a personal cognitive operating system.
Analyze the user's message and return a JSON routing decision.

Return ONLY valid JSON (no markdown fences, no explanation):
{
  "need_memory": bool,
  "need_knowledge": bool,
  "need_search": bool,
  "need_integrations": bool,
  "need_planner": bool,
  "need_mission": bool,
  "need_execution": bool,
  "need_confirmation": bool,
  "need_learning": bool,
  "risk_level": "low" | "medium" | "high" | "critical",
  "confidence": 0.0-1.0,
  "reason": "one sentence in Portuguese"
}

Rules:
- Simple question/conversation → need_memory=true, others=false
- Research/current events → need_search=true, need_knowledge=true
- Automation task → need_planner=true, need_mission=true
- risk_level > low OR destructive action → need_confirmation=true
- Calendar/email/GitHub access → need_integrations=true
- Always set need_learning=true unless trivial greeting
- need_memory and need_knowledge default to true
"""

_PROFILE = ExecutionProfile(
    name="routing",
    max_latency_ms=5_000,
    deterministic=True,
    max_context_tokens=2048,
)


def _strip_think(text: str) -> str:
    if "</think>" in text:
        return text[text.rfind("</think>") + len("</think>"):].strip()
    return text.strip()


class DecisionEngine:
    """Produces a Decision from a user message using a fast LLM call."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    async def decide(
        self, message: str, context_hint: str = ""
    ) -> Decision:
        """Analyze message and return routing Decision.

        context_hint: optional short summary of current system state
        to help the LLM make a better routing decision.
        """
        user_content = f"Message: {message}"
        if context_hint:
            user_content += f"\n\nContext: {context_hint[:300]}"

        try:
            result = await self._llm.chat(
                messages=[
                    ChatMessage(role="system", content=_SYSTEM),
                    ChatMessage(role="user", content=user_content),
                ],
                profile=_PROFILE,
            )
            raw = _strip_think(result.content)
            if raw.startswith("```"):
                raw = re.sub(r"^```\w*\n?", "", raw)
                raw = raw.rstrip("`").strip()
            data: dict = json.loads(raw)
        except Exception as exc:
            logger.warning(
                "decision_engine.parse_failed",
                error=str(exc),
                message=message[:100],
            )
            return Decision()

        try:
            risk = RiskLevel(data.get("risk_level", "low"))
        except ValueError:
            risk = RiskLevel.low

        return Decision(
            need_memory=bool(data.get("need_memory", True)),
            need_knowledge=bool(data.get("need_knowledge", True)),
            need_search=bool(data.get("need_search", False)),
            need_integrations=bool(data.get("need_integrations", False)),
            need_planner=bool(data.get("need_planner", False)),
            need_mission=bool(data.get("need_mission", False)),
            need_execution=bool(data.get("need_execution", False)),
            need_confirmation=bool(data.get("need_confirmation", False)),
            need_learning=bool(data.get("need_learning", True)),
            risk_level=risk,
            confidence=float(data.get("confidence", 0.8)),
            reason=str(data.get("reason", "")),
        )

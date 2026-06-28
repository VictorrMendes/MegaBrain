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
  "reason": "one sentence in Portuguese",
  "target_capability": "string or null (e.g., 'calendar.create_event', 'docker.ps')",
  "target_provider": "string or null (e.g., 'google', 'docker')",
  "capability_params": {}
}

Rules:
- Simple question/conversation → need_memory=true, others=false
- Research/current events → need_search=true, need_knowledge=true
- Automation task → need_planner=true, need_mission=true
- risk_level > low OR destructive action → need_confirmation=true
- Calendar/email/GitHub access → need_integrations=true
- Always set need_learning=true unless trivial greeting
- need_memory and need_knowledge default to true
- IF the user asks to execute a specific action on an integration (e.g. create a meeting, list containers, search emails), populate target_capability, target_provider and capability_params with the specific data.
- NEVER calculate exact ISO dates. If a semantic temporal range is requested (e.g., "today", "tomorrow", "next_week"), set the capability parameter "temporal" to an object: {"range": "<semantic>"}
- VALID CAPABILITIES FOR GOOGLE (target_provider="google"):
  - "calendar.list_events" (params: temporal)
  - "calendar.get_event" (params: event_id)
  - "calendar.create_event" (params: summary, start, end, etc)
  - "calendar.update_event" (params: event_id, event_data)
  - "calendar.delete_event" (params: event_id)
- VALID CAPABILITIES FOR DOCKER (target_provider="docker"):
  - "docker.list_containers"
"""

_PROFILE = ExecutionProfile(
    name="routing",
    max_latency_ms=5_000,
    deterministic=True,
    max_context_tokens=2048,
)


def _strip_think(text: str) -> str:
    """Remove <think>…</think> blocks emitted by reasoning models."""
    if "</think>" in text:
        return text[text.rfind("</think>") + len("</think>"):].strip()
    return text.strip()


def _extract_json(text: str) -> dict:
    """Robustly extract a JSON object from LLM output.

    Handles: plain JSON, markdown fences (```json…```), inline text
    before/after the object, and nested braces.  Raises ValueError if
    nothing parseable is found.
    """
    text = _strip_think(text)

    # 1. Try direct parse first (fastest path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences
    stripped = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    stripped = re.sub(r"\n?```$", "", stripped.strip())
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 3. Find the outermost { … } block
    start = text.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"No JSON object found in LLM output: {text[:200]!r}")


class DecisionEngine:
    """Produces a Decision from a user message using a fast LLM call."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    async def decide(
        self, message: str, context_hint: str = ""
    ) -> Decision:
        """Analyze message and return routing Decision."""
        user_content = f"Message: {message}"
        if context_hint:
            user_content += f"\n\nContext: {context_hint[:300]}"

        raw_content = ""
        try:
            result = await self._llm.chat(
                messages=[
                    ChatMessage(role="system", content=_SYSTEM),
                    ChatMessage(role="user", content=user_content),
                ],
                profile=_PROFILE,
            )
            raw_content = result.content
            data: dict = _extract_json(raw_content)
        except Exception as exc:
            logger.warning(
                "decision_engine.parse_failed",
                error=str(exc),
                raw=raw_content[:300],
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
            target_capability=data.get("target_capability"),
            target_provider=data.get("target_provider"),
            capability_params=data.get("capability_params") or {},
        )

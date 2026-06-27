"""LearningEngine — decides what to extract and persist after each exchange.

Analyzes the conversation and produces a LearningDecision with typed
LearningAction items. Actual persistence is handled by MemoryEngine and
KnowledgeEngine — LearningEngine only decides what is worth keeping.
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

from .models import (
    ConversationResult,
    LearningAction,
    LearningActionType,
    LearningDecision,
)

logger = get_logger("khonshu.orchestrator.learning")

_SYSTEM = """\
You are the learning intelligence of a personal cognitive operating system.
Analyze a conversation and decide what is worth persisting long-term.

Return ONLY valid JSON (no markdown fences, no explanation):
{
  "should_learn": bool,
  "reason": "one sentence",
  "actions": [
    {
      "type": "create_memory|create_fact|create_observation|update_preference|record_pattern|ignore",
      "content": "what to persist (concise, self-contained)",
      "confidence": 0.0-1.0,
      "reason": "why this is worth keeping"
    }
  ]
}

Action type guide:
- update_preference: user stated a personal preference, style, or habit
- create_fact: objective factual information stated in the exchange
- record_pattern: behavioral pattern detected across exchanges
- create_observation: short-lived context (expires in days, not months)
- create_memory: significant event, decision, or experience
- ignore: trivial exchange, no learning value

Rules:
- Max 3 actions per conversation
- If trivial greeting or no new information → should_learn=false
- Prefer create_observation over create_memory for temporary context
- confidence reflects how certain the information is (0.9+ = confirmed fact)
"""

_PROFILE = ExecutionProfile(
    name="extraction",
    max_latency_ms=10_000,
    deterministic=True,
    max_context_tokens=4096,
)


def _strip_think(text: str) -> str:
    if "</think>" in text:
        return text[text.rfind("</think>") + len("</think>"):].strip()
    return text.strip()


class LearningEngine:
    """Extracts learning opportunities from completed conversations."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    async def decide(
        self, result: ConversationResult
    ) -> LearningDecision:
        """Analyze a ConversationResult and decide what to learn."""
        user_part = result.request.message[:400]
        resp_part = result.response[:600]
        summary = (
            f"User said: {user_part}\n\n"
            f"Assistant replied: {resp_part}"
        )

        try:
            llm_result = await self._llm.chat(
                messages=[
                    ChatMessage(role="system", content=_SYSTEM),
                    ChatMessage(role="user", content=summary),
                ],
                profile=_PROFILE,
            )
            raw = _strip_think(llm_result.content)
            if raw.startswith("```"):
                raw = re.sub(r"^```\w*\n?", "", raw)
                raw = raw.rstrip("`").strip()
            data: dict = json.loads(raw)
        except Exception as exc:
            logger.warning(
                "learning_engine.parse_failed",
                error=str(exc),
            )
            return LearningDecision(
                should_learn=False,
                actions=[],
                reason="parse error — skipping learning",
            )

        actions: list[LearningAction] = []
        for item in data.get("actions", [])[:3]:
            try:
                action_type = LearningActionType(item["type"])
            except (ValueError, KeyError):
                continue
            actions.append(LearningAction(
                type=action_type,
                content=str(item.get("content", "")).strip(),
                confidence=float(item.get("confidence", 0.7)),
                reason=str(item.get("reason", "")),
            ))

        return LearningDecision(
            should_learn=bool(data.get("should_learn", False)),
            actions=actions,
            reason=str(data.get("reason", "")),
        )

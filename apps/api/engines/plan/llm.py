from __future__ import annotations

import json
from typing import TYPE_CHECKING

from kernel.capabilities import capability_registry
from kernel.logger import get_logger
from kernel.providers.base import ChatMessage, LLMProvider
from models.mission import MissionStep, StepStatus, StepType

from .provider import PlanProviderError

if TYPE_CHECKING:
    from kernel.capabilities.reasoner import CapabilityReasoner
    from models.mission import Mission

logger = get_logger(__name__)

_SYSTEM = """\
You are a planning engine for a cognitive operating system.
Given a mission intent and available capabilities (pre-scored by the
CapabilityReasoner), generate a step-by-step execution plan.

Capabilities with higher "reasoner_score" are more reliable.
Capabilities marked "recently_failed" should be avoided when alternatives
exist. Prefer idempotent, low-risk capabilities when possible.

Respond ONLY with a valid JSON object:
{
  "confidence": <float 0.0-1.0>,
  "estimated_seconds": <int>,
  "impact": "<one sentence describing what will change>",
  "risks": ["<risk 1>", "<risk 2>"],
  "steps": [
    {"tool": "<tool>", "description": "<what>", "input": {}}
  ]
}

No explanation, no markdown fences.
"""


def _strip_think(text: str) -> str:
    if "</think>" in text:
        return text[text.rfind("</think>") + len("</think>"):].strip()
    return text.strip()


class LLMPlanProvider:
    """Generates an execution plan using the LLM with CapabilityReasoner.

    The Planner receives a pre-filtered, pre-ranked capability list from
    the CapabilityReasoner so it can make informed choices about which
    tools to use.
    """

    name = "llm"

    def __init__(
        self,
        llm_provider: LLMProvider,
        reasoner: CapabilityReasoner | None = None,
    ) -> None:
        self._llm = llm_provider
        self._reasoner = reasoner

    async def create_execution_plan(
        self, mission: Mission
    ) -> list[MissionStep]:
        if self._reasoner is not None:
            capabilities = self._reasoner.to_planner_context(
                capability_registry
            )
        else:
            capabilities = capability_registry.to_planner_context()

        cap_text = json.dumps(capabilities, ensure_ascii=False, indent=2)
        user_prompt = (
            "Available capabilities (ranked by reliability):\n"
            f"{cap_text}\n\n"
            f"Mission intent: {mission.intent}\n\n"
            "Generate the execution plan."
        )

        response = await self._llm.chat([
            ChatMessage(role="system", content=_SYSTEM),
            ChatMessage(role="user", content=user_prompt),
        ])

        raw = _strip_think(response.content)

        try:
            plan_data: dict = json.loads(raw)
        except Exception:
            # Fallback: try parsing as plain list (older model format)
            try:
                steps_data: list[dict] = json.loads(raw)
                plain_steps = (
                    steps_data if isinstance(steps_data, list) else []
                )
                plan_data = {
                    "confidence": 0.7,
                    "estimated_seconds": 60,
                    "impact": "Mission execution",
                    "risks": [],
                    "steps": plain_steps,
                }
            except Exception as exc:
                logger.warning(
                    "llm_plan_provider.parse_failed",
                    mission_id=str(mission.id),
                    raw=raw[:500],
                )
                raise PlanProviderError(
                    f"LLM returned invalid plan JSON: {exc}"
                ) from exc

        if not isinstance(plan_data, dict):
            raise PlanProviderError(
                "LLM returned unexpected plan format"
            )

        steps_list = plan_data.get("steps", [])

        steps = []
        for i, item in enumerate(steps_list):
            tool = item.get("tool", "")
            if not tool:
                continue
            steps.append(
                MissionStep(
                    mission_id=mission.id,
                    order=i,
                    type=StepType.TOOL,
                    tool=tool,
                    input=item.get("input", {}),
                    status=StepStatus.PENDING,
                )
            )

        if not steps:
            raise PlanProviderError("LLM generated an empty plan")

        # Approval context stored on mission for Human Approval 2.0
        approval_ctx = {
            "planner": "llm",
            "confidence": plan_data.get("confidence", 0.7),
            "estimated_seconds": plan_data.get("estimated_seconds", 0),
            "impact": plan_data.get("impact", ""),
            "risks": plan_data.get("risks", []),
            "capabilities_used": list(
                {s.tool.split(".")[0] for s in steps}
            ),
        }
        mission._plan_approval_ctx = approval_ctx  # type: ignore[attr-defined]

        logger.info(
            "llm_plan_provider.plan_created",
            mission_id=str(mission.id),
            steps=len(steps),
            confidence=approval_ctx["confidence"],
        )
        return steps

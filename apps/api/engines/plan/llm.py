from __future__ import annotations

import json
from typing import TYPE_CHECKING

from kernel.capabilities import capability_registry
from kernel.logger import get_logger
from kernel.providers.base import ChatMessage, LLMProvider
from models.mission import MissionStep, StepStatus, StepType

from .provider import PlanProviderError

if TYPE_CHECKING:
    from models.mission import Mission

logger = get_logger(__name__)

_SYSTEM = """\
You are a planning engine for a cognitive operating system.
Given a mission intent and available capabilities, generate a step-by-step
execution plan as a JSON array.

Each step must have:
- tool: the capability tool name (string)
- description: what this step does (string)
- input: a dict of arguments (object)

Respond ONLY with a JSON array. No explanation, no markdown fences.
Example:
[
  {"tool": "docker.ps", "description": "List running containers", "input": {}},
  {"tool": "docker.stats", "description": "Get metrics for each container", "input": {"all": true}}
]
"""


def _strip_think(text: str) -> str:
    if "</think>" in text:
        return text[text.rfind("</think>") + len("</think>"):].strip()
    return text.strip()


class LLMPlanProvider:
    """Generates an execution plan using the LLM.

    The Planner injects the available capabilities as context so the LLM
    can reason about what tools exist, without knowing tool signatures.
    """

    name = "llm"

    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    async def create_execution_plan(
        self, mission: Mission
    ) -> list[MissionStep]:
        capabilities = capability_registry.to_planner_context()

        cap_text = json.dumps(capabilities, ensure_ascii=False, indent=2)
        user_prompt = (
            f"Available capabilities:\n{cap_text}\n\n"
            f"Mission intent: {mission.intent}\n\n"
            "Generate the execution plan."
        )

        response = await self._llm.chat([
            ChatMessage(role="system", content=_SYSTEM),
            ChatMessage(role="user", content=user_prompt),
        ])

        raw = _strip_think(response.content)

        try:
            plan_data: list[dict] = json.loads(raw)
            if not isinstance(plan_data, list):
                raise ValueError("Expected a JSON array")
        except Exception as exc:
            logger.warning(
                "llm_plan_provider.parse_failed",
                mission_id=str(mission.id),
                raw=raw[:500],
            )
            raise PlanProviderError(
                f"LLM returned invalid plan JSON: {exc}"
            ) from exc

        steps = []
        for i, item in enumerate(plan_data):
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

        logger.info(
            "llm_plan_provider.plan_created",
            mission_id=str(mission.id),
            steps=len(steps),
        )
        return steps

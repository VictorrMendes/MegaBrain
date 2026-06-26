"""CognitiveLoop — proactive AI agent cycle.

Every N minutes the loop:
1. Reads current Life Context snapshot.
2. Fetches recent knowledge and memories.
3. Asks the LLM: "Given the current state, is there an important action
   to take that the user hasn't explicitly requested?"
4. If the LLM identifies a necessary action → creates a Mission
   (requires_approval=True for medium/high risk, False for low risk).

The user never needs to start the conversation.
The system acts on its own initiative.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from kernel.logger import get_logger
from kernel.providers.base import ChatMessage
from models.mission import MissionTrigger

if TYPE_CHECKING:
    from engines.knowledge import KnowledgeEngine
    from engines.mission import MissionEngine
    from kernel.life_context import LifeContextProvider
    from kernel.providers.base import LLMProvider

logger = get_logger(__name__)

_COGNITIVE_SYSTEM = """\
You are the proactive reasoning engine of KHONSHU, a personal AI OS.

Analyse the provided context (life integrations, knowledge, missions) and
decide whether the system should take a proactive action RIGHT NOW.

Rules:
- Only suggest ONE action per cycle.
- Only suggest if the action is genuinely important and time-sensitive.
- Do NOT suggest actions that are already covered by an active mission.
- Low-risk actions (web search, send notification, check status): auto-approve.
- Medium/high-risk actions (restart service, delete data): require approval.

Respond with a JSON object:
{
  "should_act": true | false,
  "reason": "<one sentence explaining why>",
  "intent": "<mission intent if should_act is true, else null>",
  "risk_level": "low" | "medium" | "high",
  "auto_approve": true | false
}

If should_act is false, respond with:
{"should_act": false, "reason": "<why no action needed>"}
"""


class CognitiveLoop:
    """Runs a periodic proactive reasoning cycle."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        mission_engine: MissionEngine,
        life_context_provider: LifeContextProvider,
        knowledge_engine: KnowledgeEngine,
        workspace_ids: list[UUID] | None = None,
        interval_seconds: int = 1800,  # 30 minutes
    ) -> None:
        self._llm = llm_provider
        self._missions = mission_engine
        self._life_context = life_context_provider
        self._knowledge = knowledge_engine
        self._workspace_ids = workspace_ids or []
        self._interval = interval_seconds
        self._task: asyncio.Task | None = None

    def set_workspace_ids(self, ids: list[UUID]) -> None:
        self._workspace_ids = ids

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "cognitive_loop.started",
            interval_seconds=self._interval,
        )

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("cognitive_loop.stopped")

    # ------------------------------------------------------------------ #
    # Internal loop                                                        #
    # ------------------------------------------------------------------ #

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            for ws_id in self._workspace_ids:
                try:
                    await self._tick(ws_id)
                except Exception as exc:
                    logger.warning(
                        "cognitive_loop.tick_error",
                        workspace_id=str(ws_id),
                        error=str(exc),
                    )

    async def _tick(self, workspace_id: UUID) -> None:
        logger.debug(
            "cognitive_loop.tick", workspace_id=str(workspace_id)
        )

        context_parts: list[str] = []

        # Life context
        try:
            lc = await self._life_context.to_prompt_section(workspace_id)
            if lc:
                context_parts.append(lc)
        except Exception:
            pass

        # Knowledge
        try:
            know = await self._knowledge.build_prompt_context(
                workspace_id=workspace_id,
                min_observation_confidence=0.5,
                limit=10,
            )
            if know.strip():
                context_parts.append(know)
        except Exception:
            pass

        # Active missions (avoid duplicates)
        try:
            from models.mission import MissionStatus
            active = await self._missions.list(
                workspace_id=workspace_id,
                status=MissionStatus.RUNNING,
                limit=5,
            )
            if active:
                lines = "\n".join(
                    f"- {m.intent}" for m in active
                )
                context_parts.append(
                    f"## Missões em Execução\n{lines}"
                )
        except Exception:
            pass

        if not context_parts:
            return

        context = "\n\n".join(context_parts)
        now = datetime.now(UTC).strftime("%d/%m/%Y %H:%M")

        user_prompt = (
            f"Data/hora atual: {now}\n\n"
            f"{context}\n\n"
            "Existe alguma ação proativa importante a executar?"
        )

        import json
        try:
            response = await self._llm.chat([
                ChatMessage(role="system", content=_COGNITIVE_SYSTEM),
                ChatMessage(role="user", content=user_prompt),
            ])
            raw = response.content.strip()
            # Strip think tags if present
            if "</think>" in raw:
                raw = raw[raw.rfind("</think>") + 8:].strip()
            decision = json.loads(raw)
        except Exception as exc:
            logger.warning(
                "cognitive_loop.llm_failed", error=str(exc)
            )
            return

        if not decision.get("should_act"):
            logger.debug(
                "cognitive_loop.no_action",
                reason=decision.get("reason", ""),
            )
            return

        intent = decision.get("intent")
        if not intent:
            return

        auto_approve = decision.get("auto_approve", False)
        risk = decision.get("risk_level", "medium")
        requires_approval = not auto_approve or risk in ("medium", "high")

        mission = await self._missions.create(
            workspace_id=workspace_id,
            intent=intent,
            trigger=MissionTrigger.SCHEDULED,
            requires_approval=requires_approval,
            context_metadata={
                "cognitive_loop": True,
                "risk_level": risk,
                "auto_approve": auto_approve,
                "loop_reason": decision.get("reason", ""),
                "triggered_at": now,
            },
        )

        logger.info(
            "cognitive_loop.mission_created",
            workspace_id=str(workspace_id),
            mission_id=str(mission.id),
            intent=intent,
            risk=risk,
            requires_approval=requires_approval,
        )

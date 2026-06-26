"""BriefingEngine — generates cognitive briefings from all context sources.

A briefing synthesises Life Context, Knowledge, Memory, active Missions,
Scheduler triggers, and optionally search results into a concise digest
formatted by the LLM.

Types:
- daily: morning summary of everything relevant for today
- weekly: retrospective + ahead-of-the-week outlook
- monthly: strategic overview
- on_demand: user-requested, any time
- contextual: triggered by a specific event (e.g., calendar meeting in 15m)

Briefings are persisted in the briefings table and returned as Briefing
model instances. They are NOT tied to a Mission.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kernel.logger import get_logger
from kernel.providers.base import ChatMessage, LLMProvider
from models.briefing import Briefing

logger = get_logger(__name__)

_BRIEFING_SYSTEM = """\
You are the cognitive briefing engine of KHONSHU, a personal AI operating
system. Generate a concise, actionable briefing in Brazilian Portuguese
based on the context provided.

Structure:
## Briefing — <type> (<date>)

<greeting + 1-line summary>

### Hoje
<bullet points about today: meetings, tasks, alerts>

### Infraestrutura
<container status, service health>

### Código & Projetos
<PRs, issues, commits>

### Mensagens
<important emails, Telegram>

### Recomendações
<1-3 specific, prioritised actions>

Be concise. Use bullet points. Highlight urgent items with ⚠️.
"""


class BriefingEngine:
    """Generates and persists cognitive briefings."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        llm_provider: LLMProvider,
        life_context_provider=None,
        knowledge_engine=None,
        memory_engine=None,
        mission_engine=None,
        scheduler_engine=None,
    ) -> None:
        self._sessions = session_factory
        self._llm = llm_provider
        self._life_context = life_context_provider
        self._knowledge = knowledge_engine
        self._memory = memory_engine
        self._missions = mission_engine
        self._scheduler = scheduler_engine

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def generate(
        self,
        workspace_id: UUID,
        type: str = "daily",
        additional_context: str = "",
    ) -> Briefing:
        """Generate and persist a new briefing."""
        context_sections: list[str] = []

        # Life context (integration snapshot)
        if self._life_context:
            try:
                section = await self._life_context.to_prompt_section(
                    workspace_id
                )
                if section:
                    context_sections.append(section)
            except Exception as exc:
                logger.warning(
                    "briefing.life_context_failed", error=str(exc)
                )

        # Knowledge (facts + observations)
        if self._knowledge:
            try:
                know_ctx = await self._knowledge.build_prompt_context(
                    workspace_id=workspace_id,
                    min_observation_confidence=0.5,
                    limit=20,
                )
                if know_ctx.strip():
                    context_sections.append(know_ctx)
            except Exception as exc:
                logger.warning(
                    "briefing.knowledge_failed", error=str(exc)
                )

        # Active missions
        if self._missions:
            try:
                from models.mission import MissionStatus
                running = await self._missions.list(
                    workspace_id=workspace_id,
                    status=MissionStatus.RUNNING,
                    limit=5,
                )
                pending = await self._missions.list(
                    workspace_id=workspace_id,
                    status=MissionStatus.PENDING,
                    limit=3,
                )
                missions = running + pending
                if missions:
                    lines = "\n".join(
                        f"- [{m.status.value}] {m.intent}"
                        for m in missions
                    )
                    context_sections.append(
                        f"## Missões Ativas\n{lines}"
                    )
            except Exception as exc:
                logger.warning(
                    "briefing.missions_failed", error=str(exc)
                )

        # Upcoming scheduler triggers
        if self._scheduler:
            try:
                triggers = await self._scheduler.list_triggers(
                    workspace_id=workspace_id
                )
                upcoming = [
                    t for t in triggers
                    if t.next_fire_at is not None
                ][:5]
                if upcoming:
                    lines = "\n".join(
                        f"- {t.name} ({t.next_fire_at})"
                        for t in upcoming
                    )
                    context_sections.append(
                        f"## Agendamentos\n{lines}"
                    )
            except Exception as exc:
                logger.warning(
                    "briefing.scheduler_failed", error=str(exc)
                )

        if additional_context:
            context_sections.append(
                f"## Contexto Adicional\n{additional_context}"
            )

        context_body = (
            "\n\n".join(context_sections) or "Sem contexto disponível."
        )
        now_str = datetime.now(UTC).strftime("%d/%m/%Y %H:%M")

        user_prompt = (
            f"Tipo de briefing: {type}\n"
            f"Data/hora: {now_str}\n\n"
            f"{context_body}\n\n"
            "Gere o briefing."
        )

        response = await self._llm.chat([
            ChatMessage(role="system", content=_BRIEFING_SYSTEM),
            ChatMessage(role="user", content=user_prompt),
        ])

        content = response.content.strip()
        title = self._extract_title(content, type, now_str)

        briefing = await self._persist(
            workspace_id=workspace_id,
            type=type,
            title=title,
            content=content,
            metadata={"sections": len(context_sections)},
        )

        logger.info(
            "briefing.generated",
            workspace_id=str(workspace_id),
            type=type,
            briefing_id=str(briefing.id),
        )
        return briefing

    async def list(
        self, workspace_id: UUID, limit: int = 10
    ) -> list[Briefing]:
        async with self._sessions() as db:
            result = await db.execute(
                select(Briefing)
                .where(Briefing.workspace_id == workspace_id)
                .order_by(Briefing.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars())

    async def get(
        self, briefing_id: UUID
    ) -> Briefing | None:
        async with self._sessions() as db:
            return await db.get(Briefing, briefing_id)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _extract_title(
        self, content: str, type: str, date_str: str
    ) -> str:
        for line in content.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped and "Briefing" in stripped:
                return stripped[:120]
        labels = {
            "daily": "Briefing Diário",
            "weekly": "Briefing Semanal",
            "monthly": "Briefing Mensal",
            "on_demand": "Briefing Sob Demanda",
            "contextual": "Briefing Contextual",
        }
        return f"{labels.get(type, 'Briefing')} — {date_str}"

    async def _persist(
        self,
        workspace_id: UUID,
        type: str,
        title: str,
        content: str,
        metadata: dict,
    ) -> Briefing:
        async with self._sessions() as db:
            briefing = Briefing(
                workspace_id=workspace_id,
                type=type,
                title=title,
                content=content,
                metadata_=metadata,
            )
            db.add(briefing)
            await db.commit()
            await db.refresh(briefing)
        return briefing

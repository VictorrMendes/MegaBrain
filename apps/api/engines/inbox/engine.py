from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kernel.events import DomainEventType, KhonshuEvent, event_bus
from kernel.health import ComponentHealth, db_health
from kernel.logger import get_logger
from kernel.providers.base import LLMProvider
from models.inbox import InboxItem, InboxItemStatus, InboxItemType

logger = get_logger(__name__)

_ROUTER_SYSTEM = """Você é o roteador do Cognitive Inbox do PAIOS.

Dado o conteúdo recebido, decida para onde ele deve ir:
- "knowledge": contém fatos, informações, aprendizados, referências, URLs
  com conteúdo informativo. Deve ser armazenado no Knowledge Engine.
- "task": contém uma ação a realizar, pedido, tarefa, objetivo ou missão.
  Deve virar uma Mission.
- "both": contém tanto conhecimento útil quanto uma tarefa a executar.
- "dismiss": spam, ruído, conteúdo sem valor, duplicado óbvio.

Responda SOMENTE com JSON válido neste formato exato:
{
  "route": "knowledge|task|both|dismiss",
  "title": "título curto opcional (até 80 chars)",
  "reasoning": "explicação de 1-2 frases",
  "mission_intent": "intenção da missão em linguagem natural (se task|both)",
  "key_facts": ["fato 1", "fato 2"]
}"""


class InboxEngine:
    """Pipeline universal de entrada do PAIOS.

    Classifica o conteúdo via LLM e publica eventos de roteamento:
    - DomainEventType.INBOX_ROUTED_AS_KNOWLEDGE  → KnowledgeEngine processa
    - DomainEventType.INBOX_ROUTED_AS_TASK       → MissionEngine processa

    Nenhuma Engine é importada diretamente. Toda comunicação passa pelo
    EventBus (ADR-008).
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        llm_provider: LLMProvider,
    ) -> None:
        self._sessions = session_factory
        self._llm = llm_provider

    async def health(self) -> ComponentHealth:
        return await db_health("inbox_engine", self._sessions)

    def subscribe_to_events(self) -> None:
        """Registra handlers de eventos no EventBus.

        Chamado por KhonshuRuntime.start() após todas as engines serem
        criadas. InboxEngine escuta mission.created para atualizar
        InboxItem.mission_id de forma assíncrona.
        """
        event_bus.subscribe_event(
            DomainEventType.MISSION_CREATED,
            self._on_mission_created,
        )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def submit(
        self,
        workspace_id: UUID,
        raw_content: str,
        item_type: InboxItemType = InboxItemType.text,
        title: str | None = None,
        source: str = "api",
        metadata: dict | None = None,
        process_now: bool = False,
    ) -> InboxItem:
        async with self._sessions() as session:
            item = InboxItem(
                workspace_id=workspace_id,
                type=item_type,
                raw_content=raw_content,
                title=title,
                source=source,
                metadata_=metadata or {},
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)

        logger.info(
            "inbox.submitted",
            item_id=str(item.id),
            type=item_type.value,
            source=source,
        )

        if process_now:
            item = await self.process(item.id)

        return item

    async def process(self, item_id: UUID) -> InboxItem:
        """Classifica o item via LLM e publica eventos de roteamento."""
        async with self._sessions() as session:
            item = await session.get(InboxItem, item_id)
            if item is None:
                raise ValueError(f"InboxItem {item_id} not found")
            if item.status not in (
                InboxItemStatus.pending,
                InboxItemStatus.processing,
            ):
                return item

            item.status = InboxItemStatus.processing
            await session.commit()
            workspace_id = item.workspace_id
            raw_content = item.raw_content
            item_type = item.type

        try:
            decision = await self._classify(raw_content, item_type)
        except Exception as exc:
            logger.warning(
                "inbox.classify_failed",
                item_id=str(item_id),
                error=str(exc),
            )
            await self._update_status(
                item_id,
                InboxItemStatus.pending,
                routing_notes=f"Classificação falhou: {exc}",
            )
            return await self._load(item_id)

        route = decision.get("route", "dismiss")
        notes = decision.get("reasoning", "")

        if route in ("knowledge", "both"):
            key_facts: list[str] = decision.get("key_facts", [])
            if key_facts:
                await event_bus.publish_event(
                    KhonshuEvent(
                        type=DomainEventType.INBOX_ROUTED_AS_KNOWLEDGE,
                        workspace_id=workspace_id,
                        source="inbox",
                        payload={
                            "item_id": str(item_id),
                            "key_facts": key_facts,
                        },
                    )
                )
                logger.info(
                    "inbox.knowledge_event_published",
                    item_id=str(item_id),
                    facts=len(key_facts),
                )

        if route in ("task", "both"):
            intent = (
                decision.get("mission_intent")
                or decision.get("title", raw_content[:200])
            )
            await event_bus.publish_event(
                KhonshuEvent(
                    type=DomainEventType.INBOX_ROUTED_AS_TASK,
                    workspace_id=workspace_id,
                    source="inbox",
                    payload={
                        "item_id": str(item_id),
                        "intent": intent,
                    },
                )
            )
            logger.info(
                "inbox.task_event_published",
                item_id=str(item_id),
                intent=str(intent)[:80],
            )

        status_map = {
            "knowledge": InboxItemStatus.routed_knowledge,
            "task": InboxItemStatus.routed_task,
            "both": InboxItemStatus.routed_both,
            "dismiss": InboxItemStatus.dismissed,
        }
        final_status = status_map.get(route, InboxItemStatus.dismissed)

        await self._update_status(
            item_id, final_status, routing_notes=notes
        )

        logger.info(
            "inbox.processed",
            item_id=str(item_id),
            route=route,
            status=final_status.value,
        )
        return await self._load(item_id)

    async def list_items(
        self,
        workspace_id: UUID,
        status: InboxItemStatus | None = None,
        item_type: InboxItemType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InboxItem]:
        async with self._sessions() as session:
            q = (
                select(InboxItem)
                .where(InboxItem.workspace_id == workspace_id)
                .order_by(InboxItem.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            if status:
                q = q.where(InboxItem.status == status)
            if item_type:
                q = q.where(InboxItem.type == item_type)
            result = await session.execute(q)
            return list(result.scalars())

    async def get_item(self, item_id: UUID) -> InboxItem:
        async with self._sessions() as session:
            item = await session.get(InboxItem, item_id)
            if item is None:
                raise ValueError(f"InboxItem {item_id} not found")
            return item

    async def dismiss(self, item_id: UUID) -> InboxItem:
        await self._update_status(item_id, InboxItemStatus.dismissed)
        return await self._load(item_id)

    # ------------------------------------------------------------------ #
    # Event handlers                                                       #
    # ------------------------------------------------------------------ #

    async def _on_mission_created(self, event: KhonshuEvent) -> None:
        """Atualiza InboxItem.mission_id quando MissionEngine cria a missão."""
        inbox_item_id = (
            event.payload
            .get("context_metadata", {})
            .get("inbox_item_id")
        )
        if not inbox_item_id:
            return

        mission_id = event.payload.get("mission_id")
        if not mission_id:
            return

        try:
            async with self._sessions() as session:
                item = await session.get(InboxItem, UUID(inbox_item_id))
                if item:
                    item.mission_id = UUID(mission_id)
                    await session.commit()
                    logger.info(
                        "inbox.mission_linked",
                        item_id=inbox_item_id,
                        mission_id=mission_id,
                    )
        except Exception as exc:
            logger.warning(
                "inbox.mission_link_failed",
                item_id=inbox_item_id,
                error=str(exc),
            )

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    async def _classify(
        self, content: str, item_type: InboxItemType
    ) -> dict:
        prompt = (
            f"Tipo do conteúdo: {item_type.value}\n\n"
            f"Conteúdo:\n{content[:4000]}"
        )
        result = await self._llm.generate(
            prompt=prompt, system=_ROUTER_SYSTEM
        )
        raw = result.content.strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]
        return json.loads(raw)

    async def _update_status(
        self,
        item_id: UUID,
        status: InboxItemStatus,
        mission_id: UUID | None = None,
        knowledge_extracted: bool | None = None,
        routing_notes: str | None = None,
    ) -> None:
        async with self._sessions() as session:
            item = await session.get(InboxItem, item_id)
            if item is None:
                return
            item.status = status
            item.processed_at = datetime.now(UTC)
            if mission_id is not None:
                item.mission_id = mission_id
            if knowledge_extracted is not None:
                item.knowledge_extracted = knowledge_extracted
            if routing_notes is not None:
                item.routing_notes = routing_notes
            await session.commit()

    async def _load(self, item_id: UUID) -> InboxItem:
        async with self._sessions() as session:
            item = await session.get(InboxItem, item_id)
            if item is None:
                raise ValueError(f"InboxItem {item_id} not found")
            return item

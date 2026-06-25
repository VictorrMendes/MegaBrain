from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
  "mission_intent": "intenção da missão em linguagem natural (se route=task|both)",
  "key_facts": ["fato 1", "fato 2"]  // se route=knowledge|both, extraia fatos
}"""


class InboxEngine:
    """Pipeline universal de entrada do PAIOS.

    Classifica o conteúdo via LLM e roteia para:
    - KnowledgeEngine (fatos extraídos)
    - MissionEngine (intent → nova Mission)
    - Ambos
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        llm_provider: LLMProvider,
        knowledge_engine: object,
        mission_engine: object,
    ) -> None:
        self._sessions = session_factory
        self._llm = llm_provider
        # typed as object to avoid circular imports
        self._knowledge = knowledge_engine
        self._mission = mission_engine

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
        """Recebe um item e o persiste com status pending.

        Se process_now=True, executa o roteamento imediatamente.
        """
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
        """Classifica e roteia um item da inbox via LLM."""
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

        mission_id: UUID | None = None
        knowledge_extracted = False
        route = decision.get("route", "dismiss")
        notes = decision.get("reasoning", "")

        if route in ("knowledge", "both"):
            key_facts: list[str] = decision.get("key_facts", [])
            if key_facts:
                for fact_text in key_facts:
                    try:
                        await self._knowledge.store_fact(  # type: ignore[attr-defined]
                            workspace_id=workspace_id,
                            statement=fact_text,
                            source_type="inbox",
                            source_id=item_id,
                        )
                    except Exception as exc:
                        logger.warning(
                            "inbox.fact_store_failed",
                            item_id=str(item_id),
                            error=str(exc),
                        )
                knowledge_extracted = bool(key_facts)

        if route in ("task", "both"):
            intent = decision.get("mission_intent") or decision.get(
                "title", raw_content[:200]
            )
            try:
                mission = await self._mission.create(  # type: ignore[attr-defined]
                    workspace_id=workspace_id,
                    intent=intent,
                    metadata={"inbox_item_id": str(item_id)},
                    trigger=None,
                )
                mission_id = mission.id
            except Exception as exc:
                logger.warning(
                    "inbox.mission_create_failed",
                    item_id=str(item_id),
                    error=str(exc),
                )

        status_map = {
            ("knowledge", False): InboxItemStatus.routed_knowledge,
            ("knowledge", True): InboxItemStatus.routed_knowledge,
            ("task", False): InboxItemStatus.routed_task,
            ("task", True): InboxItemStatus.routed_task,
            ("both", False): InboxItemStatus.routed_both,
            ("both", True): InboxItemStatus.routed_both,
            ("dismiss", False): InboxItemStatus.dismissed,
            ("dismiss", True): InboxItemStatus.dismissed,
        }
        # fallback for unknown route values
        final_status = status_map.get(
            (route, bool(mission_id)),
            InboxItemStatus.dismissed,
        )
        if route == "knowledge":
            final_status = InboxItemStatus.routed_knowledge
        elif route == "task":
            final_status = InboxItemStatus.routed_task
        elif route == "both":
            final_status = InboxItemStatus.routed_both
        else:
            final_status = InboxItemStatus.dismissed

        await self._update_status(
            item_id,
            final_status,
            mission_id=mission_id,
            knowledge_extracted=knowledge_extracted,
            routing_notes=notes,
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

        # Extrai JSON mesmo se houver texto ao redor
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

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kernel.events import DomainEventType, KhonshuEvent, event_bus
from kernel.health import ComponentHealth, db_health
from kernel.logger import get_logger
from models.knowledge import (
    Entity,
    EntityType,
    Fact,
    Observation,
    Relation,
)

logger = get_logger(__name__)

# Decaimento de confiança: confiança * 0.5 ^ (dias / 30)
# Abaixo desse limiar a observação é marcada como expirada
_DECAY_HALF_LIFE_DAYS = 30
_DECAY_EXPIRY_THRESHOLD = 0.15


class KnowledgeEngine:
    """Gerencia o grafo de conhecimento do workspace.

    Separa Fatos (verificados, alta confiança, sem expiração) de
    Observações (inferidas, confiança variável, podem expirar).
    Ver ADR-005.
    """

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._sessions = session_factory

    async def health(self) -> ComponentHealth:
        return await db_health("knowledge_engine", self._sessions)

    def subscribe_to_events(self) -> None:
        """Registra handlers de eventos no EventBus."""
        event_bus.subscribe_event(
            DomainEventType.INBOX_ROUTED_AS_KNOWLEDGE,
            self._on_inbox_knowledge,
        )

    async def _on_inbox_knowledge(self, event: KhonshuEvent) -> None:
        """Armazena fatos extraídos pelo InboxEngine."""
        key_facts: list[str] = event.payload.get("key_facts", [])
        item_id_str: str | None = event.payload.get("item_id")

        for fact_text in key_facts:
            try:
                await self.store_fact(
                    workspace_id=event.workspace_id,
                    statement=fact_text,
                    source_type="inbox",
                    source_id=(
                        UUID(item_id_str) if item_id_str else None
                    ),
                )
            except Exception as exc:
                logger.warning(
                    "knowledge.inbox_fact_failed",
                    item_id=item_id_str,
                    error=str(exc),
                )

    # ------------------------------------------------------------------ #
    # Entities                                                             #
    # ------------------------------------------------------------------ #

    async def get_or_create_entity(
        self,
        workspace_id: UUID,
        name: str,
        entity_type: EntityType = EntityType.other,
        aliases: list[str] | None = None,
    ) -> Entity:
        async with self._sessions() as session:
            result = await session.execute(
                select(Entity).where(
                    Entity.workspace_id == workspace_id,
                    Entity.name == name,
                )
            )
            entity = result.scalar_one_or_none()
            if entity:
                return entity

            entity = Entity(
                workspace_id=workspace_id,
                name=name,
                type=entity_type,
                aliases=aliases or [],
            )
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            logger.info(
                "knowledge.entity_created",
                name=name,
                type=entity_type.value,
                workspace_id=str(workspace_id),
            )
            return entity

    async def list_entities(
        self,
        workspace_id: UUID,
        entity_type: EntityType | None = None,
        limit: int = 50,
    ) -> list[Entity]:
        async with self._sessions() as session:
            q = (
                select(Entity)
                .where(Entity.workspace_id == workspace_id)
                .order_by(Entity.name)
                .limit(limit)
            )
            if entity_type:
                q = q.where(Entity.type == entity_type)
            result = await session.execute(q)
            return list(result.scalars())

    # ------------------------------------------------------------------ #
    # Relations                                                            #
    # ------------------------------------------------------------------ #

    async def list_relations(
        self,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        limit: int = 100,
    ) -> list[Relation]:
        async with self._sessions() as session:
            q = (
                select(Relation)
                .where(Relation.workspace_id == workspace_id)
                .order_by(Relation.created_at.desc())
                .limit(limit)
            )
            if entity_id:
                q = q.where(
                    or_(
                        Relation.source_entity_id == entity_id,
                        Relation.target_entity_id == entity_id,
                    )
                )
            result = await session.execute(q)
            return list(result.scalars())

    async def add_relation(
        self,
        workspace_id: UUID,
        source_entity_id: UUID,
        relation: str,
        target_entity_id: UUID,
        confidence: float = 1.0,
        source_type: str = "user_explicit",
    ) -> Relation:
        async with self._sessions() as session:
            rel = Relation(
                workspace_id=workspace_id,
                source_entity_id=source_entity_id,
                relation=relation,
                target_entity_id=target_entity_id,
                confidence=confidence,
                source_type=source_type,
            )
            session.add(rel)
            await session.commit()
            await session.refresh(rel)
            logger.info(
                "knowledge.relation_added",
                source=str(source_entity_id),
                relation=relation,
                target=str(target_entity_id),
            )
            return rel

    # ------------------------------------------------------------------ #
    # Facts                                                                #
    # ------------------------------------------------------------------ #

    async def store_fact(
        self,
        workspace_id: UUID,
        statement: str,
        source_type: str = "conversation",
        source_id: UUID | None = None,
        entity_id: UUID | None = None,
        confidence: float = 1.0,
        supersede_fact_id: UUID | None = None,
    ) -> Fact:
        async with self._sessions() as session:
            fact = Fact(
                workspace_id=workspace_id,
                statement=statement,
                source_type=source_type,
                source_id=source_id,
                entity_id=entity_id,
                confidence=confidence,
            )
            session.add(fact)
            await session.flush()

            if supersede_fact_id:
                await session.execute(
                    update(Fact)
                    .where(Fact.id == supersede_fact_id)
                    .values(superseded_by_id=fact.id)
                )

            await session.commit()
            await session.refresh(fact)

        logger.info(
            "knowledge.fact_stored",
            workspace_id=str(workspace_id),
            entity_id=str(entity_id) if entity_id else None,
            source_type=source_type,
        )
        return fact

    async def list_facts(
        self,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        include_superseded: bool = False,
        limit: int = 50,
    ) -> list[Fact]:
        async with self._sessions() as session:
            q = (
                select(Fact)
                .where(Fact.workspace_id == workspace_id)
                .order_by(Fact.created_at.desc())
                .limit(limit)
            )
            if entity_id:
                q = q.where(Fact.entity_id == entity_id)
            if not include_superseded:
                q = q.where(Fact.superseded_by_id.is_(None))
            result = await session.execute(q)
            return list(result.scalars())

    # ------------------------------------------------------------------ #
    # Observations                                                         #
    # ------------------------------------------------------------------ #

    async def store_observation(
        self,
        workspace_id: UUID,
        statement: str,
        derived_from: str = "agent",
        derivation_agent: str | None = None,
        entity_id: UUID | None = None,
        confidence: float = 0.7,
        sample_size: int | None = None,
        expires_in_days: int | None = 90,
    ) -> Observation:
        expires_at = (
            datetime.now(UTC) + timedelta(days=expires_in_days)
            if expires_in_days
            else None
        )
        async with self._sessions() as session:
            obs = Observation(
                workspace_id=workspace_id,
                statement=statement,
                derived_from=derived_from,
                derivation_agent=derivation_agent,
                entity_id=entity_id,
                confidence=confidence,
                sample_size=sample_size,
                expires_at=expires_at,
            )
            session.add(obs)
            await session.commit()
            await session.refresh(obs)

        logger.info(
            "knowledge.observation_stored",
            workspace_id=str(workspace_id),
            derived_from=derived_from,
            confidence=confidence,
        )
        return obs

    async def reinforce_observation(
        self,
        observation_id: UUID,
        confidence_delta: float = 0.05,
        new_sample_size: int | None = None,
    ) -> Observation:
        """Aumenta a confiança de uma observação já existente."""
        async with self._sessions() as session:
            obs = await session.get(Observation, observation_id)
            if obs is None:
                raise ValueError(
                    f"Observation {observation_id} not found"
                )
            obs.confidence = min(1.0, obs.confidence + confidence_delta)
            obs.reinforcement_count += 1
            obs.last_reinforced_at = datetime.now(UTC)
            if new_sample_size is not None:
                obs.sample_size = new_sample_size
            await session.commit()
            await session.refresh(obs)
        return obs

    async def list_observations(
        self,
        workspace_id: UUID,
        entity_id: UUID | None = None,
        min_confidence: float = 0.0,
        include_expired: bool = False,
        limit: int = 50,
    ) -> list[Observation]:
        async with self._sessions() as session:
            q = (
                select(Observation)
                .where(Observation.workspace_id == workspace_id)
                .where(Observation.confidence >= min_confidence)
                .order_by(Observation.confidence.desc())
                .limit(limit)
            )
            if entity_id:
                q = q.where(Observation.entity_id == entity_id)
            if not include_expired:
                q = q.where(Observation.expired.is_(False))
            result = await session.execute(q)
            return list(result.scalars())

    # ------------------------------------------------------------------ #
    # Decay job — chamado periodicamente pelo Scheduler                   #
    # ------------------------------------------------------------------ #

    async def run_decay(self, workspace_id: UUID) -> int:
        """Aplica decaimento de confiança em observações não reforçadas.

        Retorna o número de observações expiradas nessa execução.
        """
        now = datetime.now(UTC)
        expired_count = 0

        async with self._sessions() as session:
            result = await session.execute(
                select(Observation).where(
                    Observation.workspace_id == workspace_id,
                    Observation.expired.is_(False),
                )
            )
            observations = list(result.scalars())

        for obs in observations:
            days_since = (now - obs.last_reinforced_at).days
            if days_since == 0:
                continue

            decay = 0.5 ** (days_since / _DECAY_HALF_LIFE_DAYS)
            new_confidence = obs.confidence * decay

            async with self._sessions() as session:
                o = await session.get(Observation, obs.id)
                o.confidence = new_confidence
                if new_confidence < _DECAY_EXPIRY_THRESHOLD:
                    o.expired = True
                    expired_count += 1
                    logger.info(
                        "knowledge.observation_expired",
                        observation_id=str(obs.id),
                        final_confidence=new_confidence,
                    )
                await session.commit()

        logger.info(
            "knowledge.decay_run",
            workspace_id=str(workspace_id),
            checked=len(observations),
            expired=expired_count,
        )
        return expired_count

    # ------------------------------------------------------------------ #
    # Prompt context                                                       #
    # ------------------------------------------------------------------ #

    async def build_prompt_context(
        self,
        workspace_id: UUID,
        min_observation_confidence: float = 0.4,
        limit: int = 20,
    ) -> str:
        """Retorna um bloco de texto formatado para injeção no prompt.

        Fatos são apresentados como certezas.
        Observações são apresentadas com nível de confiança explícito.
        """
        facts = await self.list_facts(
            workspace_id, include_superseded=False, limit=limit
        )
        observations = await self.list_observations(
            workspace_id,
            min_confidence=min_observation_confidence,
            include_expired=False,
            limit=limit,
        )

        parts: list[str] = []

        if facts:
            fact_lines = "\n".join(f"- {f.statement}" for f in facts)
            parts.append(f"## Fatos conhecidos\n{fact_lines}")

        if observations:
            obs_lines = "\n".join(
                f"- [{o.confidence:.0%} confiança] {o.statement}"
                for o in observations
            )
            parts.append(
                f"## Observações (padrões inferidos)\n{obs_lines}"
            )

        return "\n\n".join(parts)

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kernel.events import event_bus
from kernel.events.schema import DomainEventType, KhonshuEvent
from kernel.logger import get_logger
from kernel.providers.base import EmbeddingProvider
from models.memory import Memory, MemoryType

logger = get_logger(__name__)


class MemoryEngine:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._sessions = session_factory
        self._embedding = embedding_provider

    async def remember(
        self,
        workspace_id: UUID,
        content: str,
        type: MemoryType = MemoryType.long,
        metadata: dict | None = None,
        confidence: float = 1.0,
        importance: float = 0.5,
        source: str | None = None,
        source_id: UUID | None = None,
        expires_in_days: int | None = None,
    ) -> Memory:
        embed = await self._embedding.embed(content)
        expires_at = (
            datetime.now(UTC) + timedelta(days=expires_in_days)
            if expires_in_days
            else None
        )

        async with self._sessions() as session:
            memory = Memory(
                workspace_id=workspace_id,
                type=type,
                content=content,
                embedding=embed.embedding,
                metadata_=metadata or {},
                confidence=confidence,
                importance=importance,
                source=source,
                source_id=source_id,
                expires_at=expires_at,
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)

        logger.info("memory.created", id=str(memory.id), type=type.value)

        try:
            await event_bus.publish_event(
                KhonshuEvent(
                    type=DomainEventType.MEMORY_CREATED,
                    workspace_id=workspace_id,
                    source="memory_engine",
                    payload={"memory_id": str(memory.id)},
                )
            )
        except RuntimeError:
            pass

        return memory

    async def recall(
        self,
        workspace_id: UUID,
        query: str,
        limit: int = 10,
        type_filter: MemoryType | None = None,
    ) -> list[Memory]:
        embed = await self._embedding.embed(query)
        vector_str = "[" + ",".join(f"{x:.8f}" for x in embed.embedding) + "]"

        type_clause = (
            "AND m.type::text = :type_filter" if type_filter else ""
        )

        # RRF com boost de importância:
        #   score_final = rrf_score * (0.5 + 0.5 * importance)
        # Memórias expiradas são excluídas pelo filtro expires_at.
        sql = text(f"""
            WITH bm25 AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           ORDER BY ts_rank(fts, q) DESC
                       ) AS rank
                FROM memories,
                     plainto_tsquery('portuguese', :query) AS q
                WHERE workspace_id = :workspace_id
                  AND superseded_by IS NULL
                  AND (expires_at IS NULL OR expires_at > now())
                  AND fts @@ q
                LIMIT 40
            ),
            vec AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           ORDER BY embedding <=> CAST(:vector AS vector)
                       ) AS rank
                FROM memories
                WHERE workspace_id = :workspace_id
                  AND superseded_by IS NULL
                  AND (expires_at IS NULL OR expires_at > now())
                  AND embedding IS NOT NULL
                LIMIT 40
            ),
            rrf AS (
                SELECT COALESCE(b.id, v.id) AS id,
                       COALESCE(1.0 / (60 + b.rank), 0) +
                       COALESCE(1.0 / (60 + v.rank), 0) AS rrf_score
                FROM bm25 b FULL OUTER JOIN vec v ON b.id = v.id
            )
            SELECT m.id
            FROM rrf
            JOIN memories m ON m.id = rrf.id
            {type_clause}
            ORDER BY rrf.rrf_score * (0.5 + 0.5 * m.importance) DESC
            LIMIT :limit
        """)

        async with self._sessions() as session:
            rows = await session.execute(
                sql,
                {
                    "query": query,
                    "workspace_id": workspace_id,
                    "vector": vector_str,
                    "type_filter": type_filter.value if type_filter else None,
                    "limit": limit,
                },
            )
            ids = [row[0] for row in rows.fetchall()]

            if not ids:
                return []

            result = await session.execute(
                select(Memory).where(Memory.id.in_(ids))
            )
            mem_map = {m.id: m for m in result.scalars()}

        return [mem_map[id_] for id_ in ids if id_ in mem_map]

    async def supersede(
        self,
        memory_id: UUID,
        new_content: str,
        new_metadata: dict | None = None,
    ) -> Memory:
        async with self._sessions() as session:
            old = await session.get(Memory, memory_id)
            if old is None:
                raise ValueError(f"Memory {memory_id} not found")
            workspace_id = old.workspace_id
            memory_type = old.type
            inherited_meta = old.metadata_

        new_memory = await self.remember(
            workspace_id=workspace_id,
            content=new_content,
            type=memory_type,
            metadata=new_metadata
            if new_metadata is not None
            else inherited_meta,
        )

        async with self._sessions() as session:
            await session.execute(
                update(Memory)
                .where(Memory.id == memory_id)
                .values(superseded_by=new_memory.id)
            )
            await session.commit()

        logger.info(
            "memory.superseded",
            old_id=str(memory_id),
            new_id=str(new_memory.id),
        )
        return new_memory

    async def list_active(
        self,
        workspace_id: UUID,
        type_filter: MemoryType | None = None,
        limit: int = 50,
    ) -> list[Memory]:
        async with self._sessions() as session:
            q = (
                select(Memory)
                .where(
                    Memory.workspace_id == workspace_id,
                    Memory.superseded_by.is_(None),
                )
                .order_by(Memory.created_at.desc())
                .limit(limit)
            )
            if type_filter:
                q = q.where(Memory.type == type_filter)
            result = await session.execute(q)
            return list(result.scalars())

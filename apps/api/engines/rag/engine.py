from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kernel.logger import get_logger
from kernel.providers.base import EmbeddingProvider
from models.document import Document, DocumentChunk, DocumentStatus

logger = get_logger(__name__)

_CHUNK_SIZE = 1500
_CHUNK_OVERLAP = 200
_EMBED_BATCH_SIZE = 20


def _chunk_text(
    text: str,
    chunk_size: int = _CHUNK_SIZE,
    overlap: int = _CHUNK_OVERLAP,
) -> list[str]:
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            for sep in ["\n\n", "\n", ". ", "! ", "? ", " "]:
                pos = text.rfind(sep, start + overlap, end)
                if pos != -1:
                    end = pos + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = max(start + 1, end - overlap)

    return chunks


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    document_filename: str
    chunk_index: int
    content: str


class RAGEngine:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._sessions = session_factory
        self._embedding = embedding_provider

    async def ingest(
        self,
        workspace_id: UUID,
        filename: str,
        content: str,
        content_type: str = "text/plain",
    ) -> Document:
        file_size = len(content.encode("utf-8"))

        async with self._sessions() as session:
            doc = Document(
                workspace_id=workspace_id,
                filename=filename,
                content_type=content_type,
                file_size=file_size,
                status=DocumentStatus.processing,
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_id = doc.id

        logger.info(
            "rag.ingest.started",
            document_id=str(doc_id),
            filename=filename,
        )

        try:
            chunks = _chunk_text(content)

            # Embed all chunks in batches (single API call per batch)
            all_embeddings: list[list[float]] = []
            for i in range(0, len(chunks), _EMBED_BATCH_SIZE):
                batch = chunks[i : i + _EMBED_BATCH_SIZE]
                results = await self._embedding.embed_batch(batch)
                all_embeddings.extend(r.embedding for r in results)

            embedded_chunks = [
                DocumentChunk(
                    id=uuid4(),
                    document_id=doc_id,
                    workspace_id=workspace_id,
                    chunk_index=idx,
                    content=chunk_content,
                    embedding=emb,
                    token_count=len(chunk_content) // 4,
                )
                for idx, (chunk_content, emb) in enumerate(
                    zip(chunks, all_embeddings)
                )
            ]

            async with self._sessions() as session:
                session.add_all(embedded_chunks)
                await session.execute(
                    update(Document)
                    .where(Document.id == doc_id)
                    .values(
                        status=DocumentStatus.ready,
                        chunk_count=len(chunks),
                    )
                )
                await session.commit()

            logger.info(
                "rag.ingest.done",
                document_id=str(doc_id),
                chunk_count=len(chunks),
            )

        except Exception as exc:
            async with self._sessions() as session:
                await session.execute(
                    update(Document)
                    .where(Document.id == doc_id)
                    .values(status=DocumentStatus.failed)
                )
                await session.commit()
            logger.error(
                "rag.ingest.failed",
                document_id=str(doc_id),
                error=str(exc),
            )
            raise

        async with self._sessions() as session:
            refreshed = await session.get(Document, doc_id)
            return refreshed

    async def retrieve(
        self,
        workspace_id: UUID,
        query: str,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        embed = await self._embedding.embed(query)
        vector_str = "[" + ",".join(f"{x:.8f}" for x in embed.embedding) + "]"

        sql = text("""
            SELECT
                dc.id,
                dc.document_id,
                d.filename,
                dc.chunk_index,
                dc.content
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.workspace_id = :workspace_id
              AND d.status = 'ready'
              AND dc.embedding IS NOT NULL
            ORDER BY dc.embedding <=> CAST(:vector AS vector)
            LIMIT :limit
        """)

        async with self._sessions() as session:
            rows = await session.execute(
                sql,
                {
                    "workspace_id": workspace_id,
                    "vector": vector_str,
                    "limit": limit,
                },
            )
            return [
                RetrievedChunk(
                    chunk_id=row[0],
                    document_id=row[1],
                    document_filename=row[2],
                    chunk_index=row[3],
                    content=row[4],
                )
                for row in rows.fetchall()
            ]

    async def list_documents(self, workspace_id: UUID) -> list[Document]:
        async with self._sessions() as session:
            result = await session.execute(
                select(Document)
                .where(Document.workspace_id == workspace_id)
                .where(Document.status == DocumentStatus.ready)
                .order_by(Document.created_at.desc())
            )
            return list(result.scalars())

    async def retrieve_all_chunks(
        self,
        workspace_id: UUID,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        """Return the first chunks of each ready document, ordered by chunk_index."""
        sql = text("""
            SELECT DISTINCT ON (dc.document_id)
                dc.id,
                dc.document_id,
                d.filename,
                dc.chunk_index,
                dc.content
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.workspace_id = :workspace_id
              AND d.status = 'ready'
              AND dc.chunk_index = 0
            ORDER BY dc.document_id, d.created_at DESC
            LIMIT :limit
        """)

        async with self._sessions() as session:
            rows = await session.execute(
                sql, {"workspace_id": workspace_id, "limit": limit}
            )
            return [
                RetrievedChunk(
                    chunk_id=row[0],
                    document_id=row[1],
                    document_filename=row[2],
                    chunk_index=row[3],
                    content=row[4],
                )
                for row in rows.fetchall()
            ]

    async def delete_document(self, document_id: UUID) -> None:
        async with self._sessions() as session:
            doc = await session.get(Document, document_id)
            if doc:
                await session.delete(doc)
                await session.commit()
        logger.info("rag.document.deleted", document_id=str(document_id))

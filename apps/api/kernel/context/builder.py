"""ContextBuilder — assembles the full system context for every LLM call.

Single authoritative source for:
  - User preferences (semantic memories)
  - Relevant memories (episodic recall)
  - Knowledge facts and observations (KnowledgeEngine)
  - RAG document chunks
  - Recent mission artifacts
  - Available capabilities

No engine should build prompts manually; this component owns that
responsibility (Fase 5 principle).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from kernel.logger import get_logger

if TYPE_CHECKING:
    from engines.knowledge import KnowledgeEngine
    from engines.memory import MemoryEngine
    from engines.rag import RAGEngine
    from kernel.life_context import LifeContextProvider

logger = get_logger(__name__)

_BASE_SYSTEM = """\
Você é KHONSHU, um Sistema Operacional Cognitivo rodando localmente no \
servidor do seu dono.

## Identidade
Você não é um chatbot genérico da internet. Você pertence exclusivamente \
ao seu dono, roda em hardware local (Samsung NP550XCJ, i5-10210U, 16 GB RAM) \
com total privacidade e sem dependência de nuvem.

## Arquitetura
- **Modelo de linguagem**: Ollama local (sem nuvem)
- **Memória persistente**: fatos e observações extraídos de cada conversa
- **Documentos (RAG)**: você pode referenciar arquivos ingeridos pelo dono
- **Missões**: ações complexas são executadas via planos estruturados e \
aprovadas pelo dono antes de rodar
- **Plugins**: ntfy, clima, busca web, Home Assistant, Notion, Google Calendar

## Comportamento
- Responda sempre em português do Brasil
- Seja direto e objetivo — sem rodeios
- Quando documentos relevantes estiverem no contexto, use-os diretamente
- Nunca diga que não tem acesso a documentos — eles estão no contexto abaixo\
"""


@dataclass
class BuiltContext:
    """Result of a ContextBuilder.build() call."""

    system_prompt: str
    memory_count: int = 0
    knowledge_count: int = 0
    chunk_count: int = 0
    sections: list[str] = field(default_factory=list)


class ContextBuilder:
    """Assembles the complete system prompt for a conversation turn.

    Owned by KhonshuRuntime; obtained via Depends(get_context_builder).
    """

    def __init__(
        self,
        memory_engine: MemoryEngine,
        rag_engine: RAGEngine,
        knowledge_engine: KnowledgeEngine,
        life_context: LifeContextProvider | None = None,
    ) -> None:
        self._memory = memory_engine
        self._rag = rag_engine
        self._knowledge = knowledge_engine
        self._life_context = life_context

    async def build(
        self,
        workspace_id: UUID,
        user_message: str,
        base_prompt: str | None = None,
    ) -> BuiltContext:
        """Build system prompt from all context sources.

        Returns BuiltContext with the assembled prompt and counts for
        streaming status events (reading_memory, reading_knowledge, etc.).
        """
        base = base_prompt or _BASE_SYSTEM
        sections: list[str] = [base]
        memory_count = 0
        knowledge_count = 0
        chunk_count = 0

        # ── 1. User preferences (semantic memories) ─────────────────────
        try:
            from models.memory import MemoryType
            preferences = await self._memory.list_active(
                workspace_id=workspace_id,
                type_filter=MemoryType.semantic,
                limit=10,
            )
            if preferences:
                lines = "\n".join(f"- {m.content}" for m in preferences)
                sections.append(f"## Preferências do usuário\n{lines}")
                memory_count += len(preferences)
        except Exception as exc:
            logger.warning("context.preferences_failed", error=str(exc))

        # ── 2. Relevant episodic memories ───────────────────────────────
        try:
            from models.memory import MemoryType
            relevant = await self._memory.recall(
                workspace_id=workspace_id,
                query=user_message,
                limit=5,
                type_filter=MemoryType.long,
            )
            if relevant:
                lines = "\n".join(f"- {m.content}" for m in relevant)
                sections.append(f"## Contexto relevante\n{lines}")
                memory_count += len(relevant)
        except Exception as exc:
            logger.warning("context.recall_failed", error=str(exc))

        # ── 3. Knowledge facts and observations ─────────────────────────
        try:
            knowledge_ctx = await self._knowledge.build_prompt_context(
                workspace_id=workspace_id,
                min_observation_confidence=0.4,
                limit=15,
            )
            if knowledge_ctx.strip():
                sections.append(knowledge_ctx)
                # Approximate count from lines starting with "- "
                knowledge_count = knowledge_ctx.count("\n- ")
        except Exception as exc:
            logger.warning("context.knowledge_failed", error=str(exc))

        # ── 4. RAG document chunks ───────────────────────────────────────
        try:
            docs = await self._rag.list_documents(workspace_id=workspace_id)
            if docs:
                names = ", ".join(f'"{d.filename}"' for d in docs)
                sections.append(f"## Documentos disponíveis\n{names}")

            chunks = await self._rag.retrieve(
                workspace_id=workspace_id,
                query=user_message,
                limit=5,
            )
            if not chunks and docs:
                chunks = await self._rag.retrieve_all_chunks(
                    workspace_id=workspace_id,
                    limit=len(docs),
                )
            if chunks:
                parts = [
                    f"**[{c.document_filename}]**\n{c.content}"
                    for c in chunks
                ]
                doc_section = (
                    "## Documentos relevantes\n\n"
                    + "\n\n---\n\n".join(parts)
                )
                sections.append(doc_section)
                chunk_count = len(chunks)
        except Exception as exc:
            logger.warning("context.rag_failed", error=str(exc))

        # ── 5. Life Context (digital ecosystem snapshot) ─────────────────
        if self._life_context is not None:
            try:
                life_section = await self._life_context.to_prompt_section(
                    workspace_id
                )
                if life_section:
                    sections.append(life_section)
            except Exception as exc:
                logger.warning(
                    "context.life_context_failed", error=str(exc)
                )

        system_prompt = "\n\n".join(sections)

        logger.debug(
            "context.built",
            workspace_id=str(workspace_id),
            memory=memory_count,
            knowledge=knowledge_count,
            chunks=chunk_count,
            prompt_chars=len(system_prompt),
        )

        return BuiltContext(
            system_prompt=system_prompt,
            memory_count=memory_count,
            knowledge_count=knowledge_count,
            chunk_count=chunk_count,
            sections=sections,
        )

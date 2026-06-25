from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from engines.memory import MemoryEngine
from kernel.logger import get_logger
from models.memory import MemoryType

if TYPE_CHECKING:
    from engines.rag import RAGEngine

logger = get_logger(__name__)

_BASE_SYSTEM_PROMPT = """\
Você é KHONSHU, um assistente de IA pessoal \
rodando localmente no servidor do seu dono.

## Quem você é
Você é um sistema de IA pessoal e privado, \
hospedado em um servidor doméstico (Samsung \
NP550XCJ, i5-10210U, 16GB RAM). Você não é o ChatGPT, \
não é uma IA genérica da internet \
— você pertence exclusivamente ao seu dono \
e roda localmente com total privacidade.

## Sua arquitetura
- **Modelo de linguagem**: qwen rodando via Ollama (local, sem nuvem)
- **Memória persistente**: você aprende e lembra \
fatos sobre o usuário automaticamente \
(memórias semânticas, episódicas e de longo \
prazo armazenadas em banco de dados)
- **Documentos (RAG)**: trechos de documentos relevantes aparecem abaixo em \
"## Documentos relevantes" — use essas informações diretamente nas respostas
- **Agentes autônomos**: workers que extraem \
tarefas, fatos e resumos das conversas
- **Plugins disponíveis** (quando habilitados): \
ntfy, clima, busca web, Home Assistant, \
Notion, Google Calendar

## Como você se comporta
- Responda sempre em português do Brasil
- Seja direto, objetivo e útil — sem rodeios
- Quando o usuário pedir para "verificar", "ler" ou "resumir" um documento, \
use o conteúdo em "## Documentos relevantes" \
para responder com as informações reais
- Nunca diga que não tem acesso a documentos \
— você tem, eles estão no contexto abaixo\
"""


class PromptEngine:
    def __init__(
        self,
        memory_engine: MemoryEngine,
        rag_engine: RAGEngine | None = None,
    ) -> None:
        self._memory = memory_engine
        self._rag = rag_engine

    async def build_system_prompt(
        self,
        workspace_id: UUID,
        user_message: str,
        base_prompt: str | None = None,
    ) -> str:
        base = base_prompt or _BASE_SYSTEM_PROMPT
        sections: list[str] = [base]

        # Preferências semânticas do usuário
        preferences = await self._memory.list_active(
            workspace_id=workspace_id,
            type_filter=MemoryType.semantic,
            limit=10,
        )
        if preferences:
            lines = "\n".join(f"- {m.content}" for m in preferences)
            sections.append(f"## Preferências do usuário\n{lines}")

        # Memórias relevantes para a pergunta atual
        relevant = await self._memory.recall(
            workspace_id=workspace_id,
            query=user_message,
            limit=5,
            type_filter=MemoryType.long,
        )
        if relevant:
            lines = "\n".join(f"- {m.content}" for m in relevant)
            sections.append(f"## Contexto relevante\n{lines}")

        # Trechos de documentos relevantes (RAG)
        if self._rag:
            docs = await self._rag.list_documents(workspace_id=workspace_id)
            if docs:
                names = ", ".join(f'"{d.filename}"' for d in docs)
                sections.append(f"## Documentos disponíveis\n{names}")

            chunks = await self._rag.retrieve(
                workspace_id=workspace_id,
                query=user_message,
                limit=5,
            )

            # Fallback: semantic search returned nothing — use first chunk of each doc
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

        return "\n\n".join(sections)

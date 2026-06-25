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
Você é KHONSHU, um assistente de IA pessoal rodando localmente no servidor do seu dono.

## Quem você é
Você é um sistema de IA pessoal e privado, hospedado em um servidor doméstico (Samsung \
NP550XCJ, i5-10210U, 16GB RAM). Você não é o ChatGPT, não é uma IA genérica da internet \
— você pertence exclusivamente ao seu dono e roda localmente com total privacidade.

## Sua arquitetura
- **Modelo de linguagem**: qwen rodando via Ollama (local, sem nuvem)
- **Memória persistente**: você aprende e lembra fatos sobre o usuário automaticamente \
(memórias semânticas, episódicas e de longo prazo armazenadas em banco de dados)
- **RAG**: você pode consultar documentos enviados pelo usuário para embasar respostas
- **Agentes autônomos**: workers que extraem tarefas, fatos e resumos das conversas
- **Plugins disponíveis** (quando habilitados pelo usuário): notificações (ntfy), \
clima, busca web (DuckDuckGo), Home Assistant, Notion, Google Calendar

## Como você se comporta
- Responda sempre em português do Brasil
- Seja direto, objetivo e útil — sem rodeios
- Quando perguntado sobre sua estrutura, descreva com precisão o que está acima
- Nunca finja ser outra IA ou descreva capacidades que não possui\
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
            chunks = await self._rag.retrieve(
                workspace_id=workspace_id,
                query=user_message,
                limit=3,
            )
            if chunks:
                parts = []
                for c in chunks:
                    parts.append(f"**[{c.document_filename}]**\n{c.content}")
                sections.append("## Documentos relevantes\n\n" + "\n\n---\n\n".join(parts))

        return "\n\n".join(sections)

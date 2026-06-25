from uuid import UUID

from engines.memory import MemoryEngine
from kernel.logger import get_logger
from models.memory import MemoryType

logger = get_logger(__name__)

_BASE_SYSTEM_PROMPT = """Você é KHONSHU, um assistente de IA pessoal e inteligente.
Você conhece bem o usuário e fornece respostas diretas, úteis e honestas.
Responda sempre em português do Brasil."""


class PromptEngine:
    def __init__(self, memory_engine: MemoryEngine) -> None:
        self._memory = memory_engine

    async def build_system_prompt(
        self,
        workspace_id: UUID,
        user_message: str,
        base_prompt: str | None = None,
    ) -> str:
        base = base_prompt or _BASE_SYSTEM_PROMPT
        sections: list[str] = [base]

        # Preferências semânticas do usuário (tipo semantic)
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

        return "\n\n".join(sections)

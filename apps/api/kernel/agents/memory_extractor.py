import json
from uuid import UUID

from engines.memory import MemoryEngine
from kernel.agents.base import AgentWorker
from kernel.logger import get_logger
from kernel.providers.base import ChatMessage, LLMProvider
from models.memory import MemoryType

logger = get_logger(__name__)

_SYSTEM = "Você extrai memórias de conversas. Responda SOMENTE com JSON válido, sem texto adicional."

_PROMPT = """\
Analise a conversa abaixo e extraia APENAS fatos novos e relevantes sobre o usuário.
Inclua: preferências, informações pessoais, compromissos futuros, hábitos, estado financeiro, tarefas, rotinas.
Ignore saudações genéricas, perguntas sobre assuntos gerais sem relação com o usuário, e conversas sem informação nova.

MUITO IMPORTANTE: O conteúdo das memórias (campo "content") DEVE ser escrito sempre em PORTUGUÊS (PT-BR).


Classifique cada memória com um domínio:
- task: tarefas, to-dos, compromissos pontuais
- finance: finanças, gastos, receitas, investimentos, dívidas
- routine: rotinas, hábitos, horários regulares, preferências de estilo de vida
- general: informações pessoais e preferências gerais

Responda APENAS com JSON no formato exato:
{{"memories": [{{"content": "...", "domain": "task|finance|routine|general"}}]}}

Se não houver memórias relevantes, responda: {{"memories": []}}

Conversa:
Usuário: {user_message}
Assistente: {assistant_message}"""


def _strip_think(text: str) -> str:
    if "</think>" in text:
        return text[text.rfind("</think>") + len("</think>"):].strip()
    return text.strip()


class MemoryExtractorWorker(AgentWorker):
    name = "memory_extractor"

    def __init__(self, memory_engine: MemoryEngine, llm_provider: LLMProvider) -> None:
        self._memory = memory_engine
        self._llm = llm_provider

    async def handle(self, payload: dict) -> None:
        if payload.get("type") != "message.completed":
            return

        workspace_id = UUID(payload["workspace_id"])
        user_message = payload.get("user_message", "")
        assistant_message = payload.get("assistant_message", "")

        response = await self._llm.chat([
            ChatMessage(role="system", content=_SYSTEM),
            ChatMessage(
                role="user",
                content=_PROMPT.format(
                    user_message=user_message,
                    assistant_message=assistant_message,
                ),
            ),
        ])

        text = _strip_think(response.content)

        try:
            data = json.loads(text)
            memories = data.get("memories", [])
        except Exception:
            logger.warning("memory_extractor.parse_failed", raw=text[:300])
            return

        for mem in memories:
            content = mem.get("content", "").strip()
            domain = mem.get("domain", "general")
            if not content:
                continue
            await self._memory.remember(
                workspace_id=workspace_id,
                content=content,
                type=MemoryType.long,
                metadata={"auto": True, "domain": domain},
            )
            logger.info("memory_extractor.saved", domain=domain, workspace=str(workspace_id))

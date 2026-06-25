import json
from uuid import UUID

from engines.memory import MemoryEngine
from engines.plugin import PluginEngine
from kernel.agents.base import AgentWorker
from kernel.logger import get_logger
from kernel.providers.base import ChatMessage, LLMProvider
from models.memory import MemoryType

logger = get_logger(__name__)

_SYSTEM = "Você extrai tarefas de conversas. Responda SOMENTE com JSON válido, sem texto adicional."

_PROMPT = """\
Analise a conversa abaixo e extraia SOMENTE tarefas, compromissos ou ações pendentes mencionados.
Para cada tarefa identifique: descrição clara, prazo (se mencionado), prioridade estimada.

Responda APENAS com JSON no formato exato:
{{"tasks": [{{"content": "...", "deadline": "YYYY-MM-DD ou null", "priority": "alta|media|baixa"}}]}}

Se não houver tarefas: {{"tasks": []}}

Conversa:
Usuário: {user_message}
Assistente: {assistant_message}"""


def _strip_think(text: str) -> str:
    if "</think>" in text:
        return text[text.rfind("</think>") + len("</think>"):].strip()
    return text.strip()


class TaskExtractorWorker(AgentWorker):
    name = "task_extractor"

    def __init__(
        self,
        memory_engine: MemoryEngine,
        llm_provider: LLMProvider,
        plugin_engine: PluginEngine,
    ) -> None:
        self._memory = memory_engine
        self._llm = llm_provider
        self._plugins = plugin_engine

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
            tasks = data.get("tasks", [])
        except Exception:
            logger.warning("task_extractor.parse_failed", raw=text[:300])
            return

        for task in tasks:
            content = task.get("content", "").strip()
            if not content:
                continue

            deadline = task.get("deadline")
            priority = task.get("priority", "media")

            await self._memory.remember(
                workspace_id=workspace_id,
                content=content,
                type=MemoryType.long,
                metadata={
                    "auto": True,
                    "domain": "task",
                    "deadline": deadline,
                    "priority": priority,
                    "status": "pending",
                },
            )
            logger.info("task_extractor.saved", priority=priority, deadline=deadline)

            # Send ntfy notification if plugin is enabled
            deadline_str = f" (prazo: {deadline})" if deadline else ""
            priority_emoji = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}.get(priority, "⚪")
            await self._plugins.execute(
                workspace_id=workspace_id,
                plugin_name="ntfy",
                action="notify",
                params={
                    "title": f"{priority_emoji} Nova tarefa detectada",
                    "message": f"{content}{deadline_str}",
                    "priority": "high" if priority == "alta" else "default",
                },
            )

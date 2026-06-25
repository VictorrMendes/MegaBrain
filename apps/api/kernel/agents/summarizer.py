from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from engines.memory import MemoryEngine
from kernel.agents.base import AgentWorker
from kernel.logger import get_logger
from kernel.providers.base import ChatMessage, LLMProvider
from models.conversation import Message
from models.memory import MemoryType

logger = get_logger(__name__)

_EVERY_N = 10  # create episodic summary every N messages

_SYSTEM = "Você cria resumos concisos de conversas. Responda SOMENTE com o texto do resumo."

_PROMPT = """\
Crie um resumo conciso (3-5 frases) das seguintes mensagens de uma conversa com um assistente pessoal.
Capture os principais tópicos discutidos, decisões tomadas e informações relevantes.
Escreva em primeira pessoa do ponto de vista do usuário.

Mensagens:
{messages}"""


class SummarizerWorker(AgentWorker):
    name = "summarizer"

    def __init__(
        self,
        memory_engine: MemoryEngine,
        llm_provider: LLMProvider,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._memory = memory_engine
        self._llm = llm_provider
        self._sessions = session_factory

    async def handle(self, payload: dict) -> None:
        if payload.get("type") != "message.completed":
            return

        workspace_id = UUID(payload["workspace_id"])
        conversation_id = UUID(payload["conversation_id"])

        # Check if message count is a multiple of _EVERY_N
        async with self._sessions() as session:
            count_result = await session.execute(
                select(func.count()).where(Message.conversation_id == conversation_id)
            )
            count = count_result.scalar_one()

        if count == 0 or count % _EVERY_N != 0:
            return

        # Fetch last _EVERY_N messages
        async with self._sessions() as session:
            result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(_EVERY_N)
            )
            messages = list(reversed(result.scalars().all()))

        if not messages:
            return

        formatted = "\n".join(
            f"{m.role.value.capitalize()}: {m.content}" for m in messages
        )

        response = await self._llm.chat([
            ChatMessage(role="system", content=_SYSTEM),
            ChatMessage(role="user", content=_PROMPT.format(messages=formatted)),
        ])

        summary = response.content.strip()
        if "</think>" in summary:
            summary = summary[summary.rfind("</think>") + len("</think>"):].strip()

        if not summary:
            return

        await self._memory.remember(
            workspace_id=workspace_id,
            content=summary,
            type=MemoryType.episodic,
            metadata={
                "auto": True,
                "domain": "general",
                "conversation_id": str(conversation_id),
                "message_count": count,
            },
        )
        logger.info("summarizer.saved", conversation_id=str(conversation_id), at_message=count)

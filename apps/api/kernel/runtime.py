from __future__ import annotations

import asyncio

from core.database import AsyncSessionLocal
from engines.inbox import InboxEngine
from engines.knowledge import KnowledgeEngine
from engines.memory import MemoryEngine
from engines.mission import MissionEngine
from engines.obsidian import ObsidianEngine
from engines.plan import LLMPlanProvider
from engines.plugin import PluginEngine
from engines.prompt import PromptEngine
from engines.rag import RAGEngine
from engines.scheduler import SchedulerEngine
from kernel.context import ContextBuilder
from kernel.health import ComponentHealth, HealthReport
from kernel.logger import get_logger
from kernel.providers.ollama import OllamaProvider

logger = get_logger(__name__)


class KhonshuRuntime:
    """Central runtime que possui todos os singletons de engines.

    Substitui as variáveis globais espalhadas em core/dependencies.py.
    Chame start() uma vez no lifespan; depois acesse engines via
    propriedades. Armazenado em app.state.runtime após startup.

    Ordem de init segue o grafo de dependências:
        llm → memory, rag → obsidian, prompt → knowledge → mission
        → scheduler, inbox
    """

    def __init__(self) -> None:
        self._llm: OllamaProvider | None = None
        self._memory: MemoryEngine | None = None
        self._rag: RAGEngine | None = None
        self._obsidian: ObsidianEngine | None = None
        self._plugin: PluginEngine | None = None
        self._prompt: PromptEngine | None = None
        self._knowledge: KnowledgeEngine | None = None
        self._mission: MissionEngine | None = None
        self._scheduler: SchedulerEngine | None = None
        self._inbox: InboxEngine | None = None
        self._context: ContextBuilder | None = None

    def start(self) -> None:
        """Inicializa todas as engines em ordem de dependência.

        Síncrono porque todos os construtores de engine são síncronos
        (recebem session_factory, não uma conexão ativa).
        """
        logger.info("runtime.starting")

        self._llm = OllamaProvider()

        self._memory = MemoryEngine(
            session_factory=AsyncSessionLocal,
            embedding_provider=self._llm,
        )
        self._rag = RAGEngine(
            session_factory=AsyncSessionLocal,
            embedding_provider=self._llm,
        )
        self._obsidian = ObsidianEngine(
            session_factory=AsyncSessionLocal,
            rag_engine=self._rag,
        )
        self._plugin = PluginEngine(
            session_factory=AsyncSessionLocal
        )
        self._prompt = PromptEngine(
            memory_engine=self._memory,
            rag_engine=self._rag,
        )
        self._knowledge = KnowledgeEngine(
            session_factory=AsyncSessionLocal
        )
        self._mission = MissionEngine(
            session_factory=AsyncSessionLocal,
            plan_providers=[LLMPlanProvider(self._llm)],
        )
        self._scheduler = SchedulerEngine(
            session_factory=AsyncSessionLocal,
        )
        self._inbox = InboxEngine(
            session_factory=AsyncSessionLocal,
            llm_provider=self._llm,
        )
        self._context = ContextBuilder(
            memory_engine=self._memory,
            rag_engine=self._rag,
            knowledge_engine=self._knowledge,
        )

        # Registrar subscrições de eventos (ADR-008)
        self._knowledge.subscribe_to_events()
        self._mission.subscribe_to_events()
        self._inbox.subscribe_to_events()

        logger.info(
            "runtime.ready",
            engines=[
                "llm", "memory", "rag", "obsidian", "plugin",
                "prompt", "knowledge", "mission", "scheduler", "inbox",
            ],
        )

    async def health_report(self) -> HealthReport:
        """Coleta o health de todos os componentes em paralelo."""
        assert self._llm is not None, "Runtime not started"

        checks: list[ComponentHealth] = list(
            await asyncio.gather(
                self._mission.health(),
                self._knowledge.health(),
                self._scheduler.health(),
                self._inbox.health(),
                self._llm.health(),
                return_exceptions=False,
            )
        )
        return HealthReport.from_components(checks)

    # ------------------------------------------------------------------ #
    # Engine accessors                                                     #
    # ------------------------------------------------------------------ #

    @property
    def llm(self) -> OllamaProvider:
        assert self._llm is not None, "Runtime not started"
        return self._llm

    @property
    def memory(self) -> MemoryEngine:
        assert self._memory is not None, "Runtime not started"
        return self._memory

    @property
    def rag(self) -> RAGEngine:
        assert self._rag is not None, "Runtime not started"
        return self._rag

    @property
    def obsidian(self) -> ObsidianEngine:
        assert self._obsidian is not None, "Runtime not started"
        return self._obsidian

    @property
    def plugin(self) -> PluginEngine:
        assert self._plugin is not None, "Runtime not started"
        return self._plugin

    @property
    def prompt(self) -> PromptEngine:
        assert self._prompt is not None, "Runtime not started"
        return self._prompt

    @property
    def knowledge(self) -> KnowledgeEngine:
        assert self._knowledge is not None, "Runtime not started"
        return self._knowledge

    @property
    def mission(self) -> MissionEngine:
        assert self._mission is not None, "Runtime not started"
        return self._mission

    @property
    def scheduler(self) -> SchedulerEngine:
        assert self._scheduler is not None, "Runtime not started"
        return self._scheduler

    @property
    def inbox(self) -> InboxEngine:
        assert self._inbox is not None, "Runtime not started"
        return self._inbox

    @property
    def context(self) -> ContextBuilder:
        assert self._context is not None, "Runtime not started"
        return self._context


# Global singleton — start() chamado no lifespan de main.py
runtime = KhonshuRuntime()

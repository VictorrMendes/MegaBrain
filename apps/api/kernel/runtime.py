from __future__ import annotations

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
from kernel.logger import get_logger
from kernel.providers.ollama import OllamaProvider

logger = get_logger(__name__)


class KhonshuRuntime:
    """Central runtime that owns all engine singletons.

    Replaces the scattered global variables in core/dependencies.py.
    Call start() once during application lifespan; then access engines
    via properties. Stored on app.state.runtime after startup.

    Engine init order follows dependency graph:
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

    def start(self) -> None:
        """Initialize all engines in dependency order.

        Sync because all engine constructors are sync (they take a
        session_factory, not a live connection). Safe to call from
        an async context without await.
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
        self._plugin = PluginEngine(session_factory=AsyncSessionLocal)
        self._prompt = PromptEngine(
            memory_engine=self._memory,
            rag_engine=self._rag,
        )
        self._knowledge = KnowledgeEngine(session_factory=AsyncSessionLocal)
        self._mission = MissionEngine(
            session_factory=AsyncSessionLocal,
            plan_providers=[LLMPlanProvider(self._llm)],
        )
        self._scheduler = SchedulerEngine(
            session_factory=AsyncSessionLocal,
            mission_engine=self._mission,
        )
        self._inbox = InboxEngine(
            session_factory=AsyncSessionLocal,
            llm_provider=self._llm,
            knowledge_engine=self._knowledge,
            mission_engine=self._mission,
        )

        logger.info(
            "runtime.ready",
            engines=[
                "llm", "memory", "rag", "obsidian", "plugin",
                "prompt", "knowledge", "mission", "scheduler", "inbox",
            ],
        )

    # ------------------------------------------------------------------ #
    # Engine accessors                                                     #
    # ------------------------------------------------------------------ #

    @property
    def llm(self) -> OllamaProvider:
        assert self._llm is not None, "KhonshuRuntime.start() was not called"
        return self._llm

    @property
    def memory(self) -> MemoryEngine:
        assert self._memory is not None, "KhonshuRuntime.start() was not called"
        return self._memory

    @property
    def rag(self) -> RAGEngine:
        assert self._rag is not None, "KhonshuRuntime.start() was not called"
        return self._rag

    @property
    def obsidian(self) -> ObsidianEngine:
        assert self._obsidian is not None, "KhonshuRuntime.start() was not called"
        return self._obsidian

    @property
    def plugin(self) -> PluginEngine:
        assert self._plugin is not None, "KhonshuRuntime.start() was not called"
        return self._plugin

    @property
    def prompt(self) -> PromptEngine:
        assert self._prompt is not None, "KhonshuRuntime.start() was not called"
        return self._prompt

    @property
    def knowledge(self) -> KnowledgeEngine:
        assert self._knowledge is not None, "KhonshuRuntime.start() was not called"
        return self._knowledge

    @property
    def mission(self) -> MissionEngine:
        assert self._mission is not None, "KhonshuRuntime.start() was not called"
        return self._mission

    @property
    def scheduler(self) -> SchedulerEngine:
        assert self._scheduler is not None, "KhonshuRuntime.start() was not called"
        return self._scheduler

    @property
    def inbox(self) -> InboxEngine:
        assert self._inbox is not None, "KhonshuRuntime.start() was not called"
        return self._inbox


# Global singleton — start() chamado no lifespan de main.py
runtime = KhonshuRuntime()

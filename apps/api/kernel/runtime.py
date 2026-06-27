from __future__ import annotations

import asyncio

from core.database import AsyncSessionLocal
from engines.briefing import BriefingEngine
from engines.inbox import InboxEngine
from engines.integration import IntegrationManager
from engines.integration.intelligence import IntegrationIntelligence
from engines.knowledge import KnowledgeEngine
from engines.memory import MemoryEngine
from engines.mission import MissionEngine
from engines.obsidian import ObsidianEngine
from engines.plan import LLMPlanProvider
from engines.plugin import PluginEngine
from engines.prompt import PromptEngine
from engines.rag import RAGEngine
from engines.scheduler import SchedulerEngine
from engines.search import SearchEngine
from kernel.capabilities.reasoner import CapabilityReasoner
from kernel.context import ContextBuilder
from kernel.cognitive_loop import CognitiveLoop
from kernel.health import ComponentHealth, HealthReport
from kernel.life_context import LifeContextProvider
from kernel.logger import get_logger
from kernel.observability import CognitiveMetrics
from kernel.orchestrator import (
    CognitiveOrchestrator,
    DecisionEngine,
    LearningEngine,
)
from kernel.providers.ollama import OllamaProvider

logger = get_logger(__name__)


class KhonshuRuntime:
    """Central runtime holding all engine singletons.

    Dependency order:
        reasoner → llm → memory, rag → obsidian, prompt → knowledge
        → mission → scheduler, inbox → search → integration
        → life_context → briefing → cognitive_loop → context
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
        self._integration: IntegrationManager | None = None
        self._integration_intel: IntegrationIntelligence | None = None
        self._life_context: LifeContextProvider | None = None
        self._search: SearchEngine | None = None
        self._briefing: BriefingEngine | None = None
        self._cognitive_loop: CognitiveLoop | None = None
        self._context: ContextBuilder | None = None
        self._reasoner: CapabilityReasoner | None = None
        self._metrics: CognitiveMetrics | None = None
        self._decision_engine: DecisionEngine | None = None
        self._learning_engine: LearningEngine | None = None
        self._orchestrator: CognitiveOrchestrator | None = None

    def start(self) -> None:
        logger.info("runtime.starting")

        self._metrics = CognitiveMetrics()
        self._reasoner = CapabilityReasoner()
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
            plan_providers=[
                LLMPlanProvider(
                    llm_provider=self._llm,
                    reasoner=self._reasoner,
                )
            ],
            reasoner=self._reasoner,
        )
        self._scheduler = SchedulerEngine(
            session_factory=AsyncSessionLocal,
        )
        self._inbox = InboxEngine(
            session_factory=AsyncSessionLocal,
            llm_provider=self._llm,
        )
        self._search = SearchEngine(knowledge_engine=self._knowledge)
        self._integration = IntegrationManager(
            session_factory=AsyncSessionLocal,
        )
        self._integration_intel = IntegrationIntelligence(
            mission_engine=self._mission,
            knowledge_engine=self._knowledge,
        )
        self._life_context = LifeContextProvider(
            integration_manager=self._integration,
        )
        self._briefing = BriefingEngine(
            session_factory=AsyncSessionLocal,
            llm_provider=self._llm,
            life_context_provider=self._life_context,
            knowledge_engine=self._knowledge,
            memory_engine=self._memory,
            mission_engine=self._mission,
            scheduler_engine=self._scheduler,
        )
        self._cognitive_loop = CognitiveLoop(
            llm_provider=self._llm,
            mission_engine=self._mission,
            life_context_provider=self._life_context,
            knowledge_engine=self._knowledge,
        )
        self._context = ContextBuilder(
            memory_engine=self._memory,
            rag_engine=self._rag,
            knowledge_engine=self._knowledge,
            life_context=self._life_context,
        )
        self._decision_engine = DecisionEngine(
            llm_provider=self._llm,
        )
        self._learning_engine = LearningEngine(
            llm_provider=self._llm,
        )
        self._orchestrator = CognitiveOrchestrator(
            context_builder=self._context,
            decision_engine=self._decision_engine,
            learning_engine=self._learning_engine,
            llm_provider=self._llm,
            memory_engine=self._memory,
            knowledge_engine=self._knowledge,
            search_engine=self._search,
            mission_engine=self._mission,
            metrics=self._metrics,
            session_factory=AsyncSessionLocal,
        )

        # Event subscriptions
        self._knowledge.subscribe_to_events()
        self._mission.subscribe_to_events()
        self._inbox.subscribe_to_events()
        self._integration_intel.subscribe_to_events()

        logger.info(
            "runtime.ready",
            engines=[
                "reasoner", "llm", "memory", "rag", "obsidian",
                "plugin", "prompt", "knowledge", "mission",
                "scheduler", "inbox", "search", "integration",
                "integration_intel", "life_context", "briefing",
                "cognitive_loop", "metrics",
                "decision_engine", "learning_engine", "orchestrator",
            ],
        )

    async def start_background_tasks(
        self, workspace_ids: list
    ) -> None:
        """Start async background tasks (called after lifespan setup)."""
        if self._cognitive_loop:
            self._cognitive_loop.set_workspace_ids(workspace_ids)
            await self._cognitive_loop.start()

    async def stop_background_tasks(self) -> None:
        if self._cognitive_loop:
            await self._cognitive_loop.stop()

    async def health_report(self) -> HealthReport:
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
    def integration(self) -> IntegrationManager:
        assert self._integration is not None, "Runtime not started"
        return self._integration

    @property
    def integration_intel(self) -> IntegrationIntelligence:
        assert self._integration_intel is not None, "Runtime not started"
        return self._integration_intel

    @property
    def life_context(self) -> LifeContextProvider:
        assert self._life_context is not None, "Runtime not started"
        return self._life_context

    @property
    def search(self) -> SearchEngine:
        assert self._search is not None, "Runtime not started"
        return self._search

    @property
    def briefing(self) -> BriefingEngine:
        assert self._briefing is not None, "Runtime not started"
        return self._briefing

    @property
    def cognitive_loop(self) -> CognitiveLoop:
        assert self._cognitive_loop is not None, "Runtime not started"
        return self._cognitive_loop

    @property
    def context(self) -> ContextBuilder:
        assert self._context is not None, "Runtime not started"
        return self._context

    @property
    def reasoner(self) -> CapabilityReasoner:
        assert self._reasoner is not None, "Runtime not started"
        return self._reasoner

    @property
    def metrics(self) -> CognitiveMetrics:
        assert self._metrics is not None, "Runtime not started"
        return self._metrics

    @property
    def decision_engine(self) -> DecisionEngine:
        assert self._decision_engine is not None, "Runtime not started"
        return self._decision_engine

    @property
    def learning_engine(self) -> LearningEngine:
        assert self._learning_engine is not None, "Runtime not started"
        return self._learning_engine

    @property
    def orchestrator(self) -> CognitiveOrchestrator:
        assert self._orchestrator is not None, "Runtime not started"
        return self._orchestrator


# Global singleton — start() called in main.py lifespan
runtime = KhonshuRuntime()

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
from kernel.providers.ollama import OllamaProvider

_inbox_engine: InboxEngine | None = None
_knowledge_engine: KnowledgeEngine | None = None
_memory_engine: MemoryEngine | None = None
_mission_engine: MissionEngine | None = None
_obsidian_engine: ObsidianEngine | None = None
_plugin_engine: PluginEngine | None = None
_prompt_engine: PromptEngine | None = None
_rag_engine: RAGEngine | None = None
_scheduler_engine: SchedulerEngine | None = None
_llm_provider: OllamaProvider | None = None


def get_llm_provider() -> OllamaProvider:
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = OllamaProvider()
    return _llm_provider


def get_memory_engine() -> MemoryEngine:
    global _memory_engine
    if _memory_engine is None:
        _memory_engine = MemoryEngine(
            session_factory=AsyncSessionLocal,
            embedding_provider=get_llm_provider(),
        )
    return _memory_engine


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine(
            session_factory=AsyncSessionLocal,
            embedding_provider=get_llm_provider(),
        )
    return _rag_engine


def get_obsidian_engine() -> ObsidianEngine:
    global _obsidian_engine
    if _obsidian_engine is None:
        _obsidian_engine = ObsidianEngine(
            session_factory=AsyncSessionLocal,
            rag_engine=get_rag_engine(),
        )
    return _obsidian_engine


def get_plugin_engine() -> PluginEngine:
    global _plugin_engine
    if _plugin_engine is None:
        _plugin_engine = PluginEngine(session_factory=AsyncSessionLocal)
    return _plugin_engine


def get_prompt_engine() -> PromptEngine:
    global _prompt_engine
    if _prompt_engine is None:
        _prompt_engine = PromptEngine(
            memory_engine=get_memory_engine(),
            rag_engine=get_rag_engine(),
        )
    return _prompt_engine


def get_knowledge_engine() -> KnowledgeEngine:
    global _knowledge_engine
    if _knowledge_engine is None:
        _knowledge_engine = KnowledgeEngine(
            session_factory=AsyncSessionLocal,
        )
    return _knowledge_engine


def get_mission_engine() -> MissionEngine:
    global _mission_engine
    if _mission_engine is None:
        _mission_engine = MissionEngine(
            session_factory=AsyncSessionLocal,
            plan_providers=[LLMPlanProvider(get_llm_provider())],
        )
    return _mission_engine


def get_scheduler_engine() -> SchedulerEngine:
    global _scheduler_engine
    if _scheduler_engine is None:
        _scheduler_engine = SchedulerEngine(
            session_factory=AsyncSessionLocal,
            mission_engine=get_mission_engine(),
        )
    return _scheduler_engine


def get_inbox_engine() -> InboxEngine:
    global _inbox_engine
    if _inbox_engine is None:
        _inbox_engine = InboxEngine(
            session_factory=AsyncSessionLocal,
            llm_provider=get_llm_provider(),
            knowledge_engine=get_knowledge_engine(),
            mission_engine=get_mission_engine(),
        )
    return _inbox_engine

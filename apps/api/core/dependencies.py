from core.database import AsyncSessionLocal
from engines.memory import MemoryEngine
from engines.plugin import PluginEngine
from engines.prompt import PromptEngine
from engines.rag import RAGEngine
from kernel.providers.ollama import OllamaProvider

_memory_engine: MemoryEngine | None = None
_plugin_engine: PluginEngine | None = None
_prompt_engine: PromptEngine | None = None
_rag_engine: RAGEngine | None = None
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

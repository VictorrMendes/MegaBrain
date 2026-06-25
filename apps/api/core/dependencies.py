from engines.memory import MemoryEngine
from engines.prompt import PromptEngine
from kernel.providers.ollama import OllamaProvider
from core.database import AsyncSessionLocal

_memory_engine: MemoryEngine | None = None
_prompt_engine: PromptEngine | None = None
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


def get_prompt_engine() -> PromptEngine:
    global _prompt_engine
    if _prompt_engine is None:
        _prompt_engine = PromptEngine(memory_engine=get_memory_engine())
    return _prompt_engine

from engines.memory import MemoryEngine
from kernel.providers.ollama import OllamaProvider
from core.database import AsyncSessionLocal

_memory_engine: MemoryEngine | None = None


def get_memory_engine() -> MemoryEngine:
    global _memory_engine
    if _memory_engine is None:
        _memory_engine = MemoryEngine(
            session_factory=AsyncSessionLocal,
            embedding_provider=OllamaProvider(),
        )
    return _memory_engine

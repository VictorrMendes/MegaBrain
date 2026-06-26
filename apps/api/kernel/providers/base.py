from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum


class TaskType(StrEnum):
    """Hint para o provider selecionar o modelo mais adequado ao tipo de tarefa."""

    planning = "planning"           # geração de planos de execução
    routing = "routing"             # decisões de roteamento (InboxEngine)
    summarization = "summarization" # sumarização de conteúdo
    extraction = "extraction"       # extração de dados estruturados
    conversation = "conversation"   # chat interativo com o usuário


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class GenerateResult:
    content: str
    model: str
    tokens_used: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class EmbedResult:
    embedding: list[float]
    model: str
    dimensions: int


@dataclass
class SearchResult:
    id: str
    score: float
    payload: dict


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        task_type: TaskType | None = None,
        **kwargs,
    ) -> GenerateResult: ...

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system: str | None = None,
        task_type: TaskType | None = None,
        **kwargs,
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        task_type: TaskType | None = None,
        **kwargs,
    ) -> GenerateResult: ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        task_type: TaskType | None = None,
        **kwargs,
    ) -> AsyncIterator[str]: ...


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> EmbedResult: ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[EmbedResult]: ...


class VectorProvider(ABC):
    @abstractmethod
    async def upsert(
        self, collection: str, id: str, vector: list[float], payload: dict
    ) -> None: ...

    @abstractmethod
    async def search(
        self, collection: str, vector: list[float], limit: int = 10
    ) -> list[SearchResult]: ...

    @abstractmethod
    async def delete(self, collection: str, id: str) -> None: ...

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class ExecutionProfile:
    """Describes execution requirements for a single LLM call.

    Allows providers to select the most appropriate model and
    configuration without coupling callers to specific model names.

    Pre-built profiles are available as class attributes (PLANNING,
    ROUTING, SUMMARIZATION, EXTRACTION, CONVERSATION).
    """

    name: str = "default"
    require_reasoning: bool = False
    max_latency_ms: int | None = None      # None = no hard constraint
    max_cost_units: int | None = None      # None = no hard constraint
    stream: bool = False
    max_context_tokens: int | None = None  # None = provider default
    deterministic: bool = False            # True → temperature=0

    # Named pre-built profiles ─────────────────────────────────────────
    PLANNING: ClassVar[ExecutionProfile]
    ROUTING: ClassVar[ExecutionProfile]
    SUMMARIZATION: ClassVar[ExecutionProfile]
    EXTRACTION: ClassVar[ExecutionProfile]
    CONVERSATION: ClassVar[ExecutionProfile]


ExecutionProfile.PLANNING = ExecutionProfile(
    name="planning",
    require_reasoning=True,
    max_latency_ms=30_000,
    stream=False,
    deterministic=False,
)
ExecutionProfile.ROUTING = ExecutionProfile(
    name="routing",
    require_reasoning=False,
    max_latency_ms=5_000,
    stream=False,
    max_context_tokens=4096,
    deterministic=True,
)
ExecutionProfile.SUMMARIZATION = ExecutionProfile(
    name="summarization",
    require_reasoning=False,
    max_latency_ms=15_000,
    stream=True,
    deterministic=False,
)
ExecutionProfile.EXTRACTION = ExecutionProfile(
    name="extraction",
    require_reasoning=False,
    max_latency_ms=10_000,
    stream=False,
    max_context_tokens=8192,
    deterministic=True,
)
ExecutionProfile.CONVERSATION = ExecutionProfile(
    name="conversation",
    require_reasoning=False,
    stream=True,
    deterministic=False,
)


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
        profile: ExecutionProfile | None = None,
        **kwargs,
    ) -> GenerateResult: ...

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system: str | None = None,
        profile: ExecutionProfile | None = None,
        **kwargs,
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        profile: ExecutionProfile | None = None,
        **kwargs,
    ) -> GenerateResult: ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        profile: ExecutionProfile | None = None,
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

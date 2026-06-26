"""SearchProvider ABC — contract for all search backends."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = ""
    published_at: str | None = None
    score: float = 1.0
    metadata: dict = field(default_factory=dict)


class SearchProvider(ABC):
    """All search providers implement this contract.

    The SearchEngine never imports provider classes directly — they are
    registered via SearchRegistry so the Planner can pick the best one.
    """

    slug: str
    name: str
    description: str
    requires_api_key: bool = False
    supports_news: bool = False
    supports_images: bool = False

    @abstractmethod
    async def search(
        self, query: str, *, limit: int = 5
    ) -> list[SearchResult]:
        """Return organic web results for query."""

    async def news(
        self, query: str, *, limit: int = 5
    ) -> list[SearchResult]:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support news search"
        )

    async def images(
        self, query: str, *, limit: int = 5
    ) -> list[SearchResult]:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support image search"
        )


class SearchRegistry:
    _providers: dict[str, type[SearchProvider]] = {}

    @classmethod
    def register(cls, provider: type[SearchProvider]) -> type[SearchProvider]:
        cls._providers[provider.slug] = provider
        return provider

    @classmethod
    def get(cls, slug: str) -> type[SearchProvider] | None:
        return cls._providers.get(slug)

    @classmethod
    def list_all(cls) -> list[str]:
        return list(cls._providers.keys())

    @classmethod
    def default(cls) -> SearchProvider | None:
        if not cls._providers:
            return None
        # Prefer duckduckgo if available, otherwise first registered
        for slug in ("duckduckgo", *cls._providers):
            if slug in cls._providers:
                return cls._providers[slug]()
        return None

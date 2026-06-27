"""SearchEngine — decides WHEN to search and stores results as knowledge.

Flow:
    1. Planner includes a 'web_search.search' step in the plan.
    2. StepExecutor calls SearchEngine.search() via the capability tool.
    3. SearchEngine fetches results from the active SearchProvider.
    4. Results are stored as temporary knowledge facts (low confidence,
       expires after 24 hours) so subsequent steps and the LLM can use them.
    5. Returns a summary dict for the ExecutionContext.

The SearchEngine never decides whether to search; that is the Planner's job.
"""
from __future__ import annotations

from uuid import UUID

from engines.search.base import SearchProvider, SearchRegistry
from kernel.capabilities import capability_registry
from kernel.capabilities.registry import Capability, RiskLevel
from kernel.logger import get_logger

logger = get_logger(__name__)


class SearchEngine:
    """Wraps search providers and registers web_search capability."""

    def __init__(
        self,
        knowledge_engine=None,  # KnowledgeEngine injected at runtime
    ) -> None:
        self._knowledge = knowledge_engine
        # Import providers to trigger @SearchRegistry.register
        import engines.search.providers  # noqa: F401
        self._register_capability()

    def set_knowledge_engine(self, engine) -> None:
        self._knowledge = engine

    # ------------------------------------------------------------------ #
    # Search                                                               #
    # ------------------------------------------------------------------ #

    async def search(
        self,
        query: str,
        workspace_id: UUID | None = None,
        *,
        limit: int = 5,
        provider_slug: str | None = None,
    ) -> dict:
        """Search and optionally store results as temporary knowledge."""
        provider = self._get_provider(provider_slug)
        if provider is None:
            return {"error": "No search provider available", "results": []}

        results = await provider.search(query, limit=limit)

        # Store as temporary knowledge facts
        if self._knowledge and workspace_id and results:
            await self._store_as_knowledge(
                workspace_id, query, results, provider.slug
            )

        serialised = [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "source": r.source,
            }
            for r in results
        ]

        return {
            "query": query,
            "provider": provider.slug if provider else "none",
            "count": len(results),
            "results": serialised,
            "summary": self._summarise(results),
        }

    async def news(
        self,
        query: str,
        workspace_id: UUID | None = None,
        *,
        limit: int = 5,
        provider_slug: str | None = None,
    ) -> dict:
        provider = self._get_provider(provider_slug)
        if provider is None:
            return {"error": "No search provider available", "results": []}

        results = await provider.news(query, limit=limit)

        if self._knowledge and workspace_id and results:
            await self._store_as_knowledge(
                workspace_id,
                f"news: {query}",
                results,
                provider.slug,
            )

        serialised = [
            {"title": r.title, "url": r.url, "snippet": r.snippet}
            for r in results
        ]
        return {
            "query": query,
            "count": len(results),
            "results": serialised,
            "summary": self._summarise(results),
        }

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _get_provider(
        self, slug: str | None = None
    ) -> SearchProvider | None:
        if slug:
            cls = SearchRegistry.get(slug)
            return cls() if cls else None
        return SearchRegistry.default()

    def _summarise(self, results) -> str:
        if not results:
            return "Nenhum resultado encontrado."
        lines = []
        for r in results[:5]:
            source = f" ({r.source})" if r.source else ""
            date = f" [{r.published_at}]" if r.published_at else ""
            lines.append(
                f"• {r.title}{date}{source}\n  {r.snippet[:200]}"
                f"\n  URL: {r.url}"
            )
        return "\n\n".join(lines)

    async def _store_as_knowledge(
        self, workspace_id: UUID, query: str, results, provider_slug: str
    ) -> None:
        """Store search results as low-confidence temporary knowledge."""
        if not self._knowledge:
            return
        try:
            for r in results[:3]:
                statement = f"[web:{provider_slug}] {r.title}: {r.snippet}"
                await self._knowledge.store_fact(
                    workspace_id=workspace_id,
                    statement=statement[:500],
                    source_type="web_search",
                    confidence=0.6,
                )
        except Exception as exc:
            logger.warning(
                "search_engine.knowledge_store_failed",
                error=str(exc),
            )

    # ------------------------------------------------------------------ #
    # Capability registration                                              #
    # ------------------------------------------------------------------ #

    def _register_capability(self) -> None:
        cap = Capability(
            name="web_search",
            description=(
                "Search the web for current information. Use when the "
                "knowledge base does not have sufficient information to "
                "answer the user's question or complete the task."
            ),
            plugin="search_engine",
            tags=["search", "web", "information", "research"],
            risk_level=RiskLevel.low,
            requires_network=True,
            idempotent=True,
            cooldown_seconds=5,
            confidence_score=0.85,
            availability=0.95,
        )
        cap.register_tool(
            name="web_search.search",
            description=(
                "Search the web for a query. "
                "Returns titles, URLs and snippets."
            ),
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5)",
                    "default": 5,
                },
            },
            fn=lambda query, limit=5: self.search(query, limit=limit),
        )
        cap.register_tool(
            name="web_search.news",
            description="Search for recent news about a topic.",
            parameters={
                "query": {
                    "type": "string",
                    "description": "News topic to search",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5)",
                    "default": 5,
                },
            },
            fn=lambda query, limit=5: self.news(query, limit=limit),
        )
        capability_registry.register(cap)
        logger.info("search_engine.capability_registered")

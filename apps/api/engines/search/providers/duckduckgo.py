"""DuckDuckGo search provider — no API key required."""
from __future__ import annotations

import httpx

from engines.search.base import SearchProvider, SearchRegistry, SearchResult
from kernel.logger import get_logger

logger = get_logger(__name__)

_DDG_SEARCH = "https://api.duckduckgo.com/"
_DDG_HTML = "https://html.duckduckgo.com/html/"


@SearchRegistry.register
class DuckDuckGoProvider(SearchProvider):
    slug = "duckduckgo"
    name = "DuckDuckGo"
    description = "Privacy-first search engine, no API key required"
    requires_api_key = False
    supports_news = True

    async def search(
        self, query: str, *, limit: int = 5
    ) -> list[SearchResult]:
        """Search via DuckDuckGo Instant Answer API (JSON endpoint)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    _DDG_SEARCH,
                    params={
                        "q": query,
                        "format": "json",
                        "no_redirect": "1",
                        "no_html": "1",
                        "skip_disambig": "1",
                    },
                    headers={"User-Agent": "Khonshu/1.0 search agent"},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("duckduckgo.search_failed", error=str(exc))
            return []

        results: list[SearchResult] = []

        # Abstract (instant answer)
        if data.get("Abstract"):
            results.append(SearchResult(
                title=data.get("Heading", query),
                url=data.get("AbstractURL", ""),
                snippet=data["Abstract"],
                source="duckduckgo_abstract",
            ))

        # Related topics
        for topic in data.get("RelatedTopics", []):
            if len(results) >= limit:
                break
            if isinstance(topic, dict) and topic.get("Text"):
                url = topic.get("FirstURL", "")
                results.append(SearchResult(
                    title=topic["Text"][:80],
                    url=url,
                    snippet=topic["Text"],
                    source="duckduckgo_topic",
                ))

        # Results
        for item in data.get("Results", []):
            if len(results) >= limit:
                break
            if item.get("Text"):
                results.append(SearchResult(
                    title=item.get("Text", "")[:80],
                    url=item.get("FirstURL", ""),
                    snippet=item.get("Text", ""),
                    source="duckduckgo_result",
                ))

        logger.info(
            "duckduckgo.search_done",
            query=query,
            results=len(results),
        )
        return results[:limit]

    async def news(
        self, query: str, *, limit: int = 5
    ) -> list[SearchResult]:
        """Search news via DuckDuckGo (same endpoint, news intent)."""
        return await self.search(f"{query} news", limit=limit)

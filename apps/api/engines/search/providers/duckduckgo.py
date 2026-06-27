"""DuckDuckGo search provider using the duckduckgo-search package.

Replaces the broken Instant Answer API endpoint with real web results via
DDGS (duckduckgo_search).  No API key required.

Provider slug: duckduckgo
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from engines.search.base import SearchProvider, SearchRegistry, SearchResult
from kernel.logger import get_logger

logger = get_logger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ddgs")


def _domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return ""


def _dedup(results: list[SearchResult]) -> list[SearchResult]:
    """Remove duplicate URLs, keep the first occurrence."""
    seen: set[str] = set()
    out: list[SearchResult] = []
    for r in results:
        key = r.url.rstrip("/")
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


@SearchRegistry.register
class DuckDuckGoProvider(SearchProvider):
    slug = "duckduckgo"
    name = "DuckDuckGo"
    description = "Real web search via DuckDuckGo — no API key required"
    requires_api_key = False
    supports_news = True

    async def search(
        self, query: str, *, limit: int = 6
    ) -> list[SearchResult]:
        """Return real organic web results for query."""
        try:
            results = await asyncio.wait_for(
                self._run_search(query, limit),
                timeout=12.0,
            )
        except asyncio.TimeoutError:
            logger.warning("duckduckgo.search_timeout", query=query)
            raise
        except Exception as exc:
            logger.warning("duckduckgo.search_failed", error=str(exc))
            raise

        deduped = _dedup(results)
        logger.info(
            "duckduckgo.search_done", query=query, results=len(deduped)
        )
        return deduped[:limit]

    async def news(
        self, query: str, *, limit: int = 6
    ) -> list[SearchResult]:
        try:
            results = await asyncio.wait_for(
                self._run_news(query, limit),
                timeout=12.0,
            )
        except asyncio.TimeoutError:
            logger.warning("duckduckgo.news_timeout", query=query)
            raise
        except Exception as exc:
            logger.warning("duckduckgo.news_failed", error=str(exc))
            raise

        deduped = _dedup(results)
        logger.info("duckduckgo.news_done", query=query, results=len(deduped))
        return deduped[:limit]

    # ------------------------------------------------------------------
    # Sync helpers (DDGS is synchronous; run in thread pool)
    # ------------------------------------------------------------------

    async def _run_search(
        self, query: str, limit: int
    ) -> list[SearchResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._sync_search, query, limit
        )

    async def _run_news(
        self, query: str, limit: int
    ) -> list[SearchResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._sync_news, query, limit
        )

    def _sync_search(self, query: str, limit: int) -> list[SearchResult]:
        from duckduckgo_search import DDGS  # type: ignore[import]

        results: list[SearchResult] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=limit):
                results.append(SearchResult(
                    title=r.get("title", "")[:120],
                    url=r.get("href", ""),
                    snippet=r.get("body", "")[:400],
                    source=_domain(r.get("href", "")),
                    score=1.0,
                ))
        return results

    def _sync_news(self, query: str, limit: int) -> list[SearchResult]:
        from duckduckgo_search import DDGS  # type: ignore[import]

        results: list[SearchResult] = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=limit):
                results.append(SearchResult(
                    title=r.get("title", "")[:120],
                    url=r.get("url", ""),
                    snippet=r.get("body", "")[:400],
                    source=_domain(r.get("url", "")),
                    published_at=r.get("date"),
                    score=1.0,
                ))
        return results

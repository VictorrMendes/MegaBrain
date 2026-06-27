"""DuckDuckGo search provider using direct HTML parsing.

Replaces the broken duckduckgo-search package with real web results via
direct async httpx calls. No API key required.

Provider slug: duckduckgo
"""
from __future__ import annotations

import asyncio
import httpx
from bs4 import BeautifulSoup

from engines.search.base import SearchProvider, SearchRegistry, SearchResult
from kernel.logger import get_logger

logger = get_logger(__name__)

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
    description = "Real web search via DuckDuckGo HTML scraping — no API key required"
    requires_api_key = False
    supports_news = True

    async def search(
        self, query: str, *, limit: int = 6
    ) -> list[SearchResult]:
        """Return real organic web results for query."""
        try:
            results = await asyncio.wait_for(
                self._scrape_html(query, limit, is_news=False),
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
                self._scrape_html(query, limit, is_news=True),
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
    # Async Web Scraper
    # ------------------------------------------------------------------

    async def _scrape_html(self, query: str, limit: int, is_news: bool) -> list[SearchResult]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        # DuckDuckGo HTML endpoint
        url = "https://html.duckduckgo.com/html/"
        data = {"q": query}
        
        # Note: 'is_news' would normally hit a different endpoint or use advanced params in DDG,
        # but for the HTML endpoint we will just append 'news' to the query if not already there,
        # or rely on normal search if DDG doesn't offer a separate HTML news endpoint easily.
        if is_news and "news" not in query.lower():
            data["q"] = f"{query} news"

        results: list[SearchResult] = []
        
        async with httpx.AsyncClient(http2=True, timeout=10.0) as client:
            res = await client.post(url, headers=headers, data=data)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, "html.parser")
            
            for a in soup.find_all("a", class_="result__url"):
                href = a.get("href", "")
                if not href:
                    continue
                
                title_elem = a.find_previous("h2", class_="result__title")
                snippet_elem = a.find_next("a", class_="result__snippet")
                
                title = title_elem.text.strip() if title_elem else ""
                snippet = snippet_elem.text.strip() if snippet_elem else ""
                
                if href and title:
                    results.append(SearchResult(
                        title=title[:120],
                        url=href,
                        snippet=snippet[:400],
                        source=_domain(href),
                        score=1.0,
                    ))
                
                if len(results) >= limit + 2:  # fetch a few extra for dedup
                    break
                    
        return results

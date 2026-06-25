import httpx

from kernel.plugins.base import Plugin, PluginRegistry, PluginResult


@PluginRegistry.register
class WebSearchPlugin(Plugin):
    name = "web_search"
    description = "Busca na web via DuckDuckGo (sem API key)"

    async def execute(self, action: str, params: dict) -> PluginResult:
        query = params.get("query", "")
        if not query:
            return PluginResult(success=False, error="query required")

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                )
                resp.raise_for_status()
                data = resp.json()

            results: list[dict] = []

            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", query),
                    "snippet": data["AbstractText"],
                    "url": data.get("AbstractURL", ""),
                })

            for topic in data.get("RelatedTopics", [])[:6]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({
                        "title": topic["Text"][:80],
                        "snippet": topic["Text"],
                        "url": topic.get("FirstURL", ""),
                    })

            return PluginResult(success=True, data={"query": query, "results": results})
        except Exception as e:
            return PluginResult(success=False, error=str(e))

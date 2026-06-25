import httpx

from kernel.plugins.base import Plugin, PluginRegistry, PluginResult

_NOTION_VERSION = "2022-06-28"


def _extract_title(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            texts = prop.get("title", [])
            if texts:
                return texts[0].get("plain_text", "")
    return page.get("id", "")


@PluginRegistry.register
class NotionPlugin(Plugin):
    name = "notion"
    description = "Cria e lê páginas no Notion via API oficial"

    async def execute(self, action: str, params: dict) -> PluginResult:
        token = self.config.get("token", "")
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": _NOTION_VERSION,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if action == "search":
                    query = params.get("query", "")
                    resp = await client.post(
                        "https://api.notion.com/v1/search",
                        json={"query": query, "page_size": 10},
                        headers=headers,
                    )
                    resp.raise_for_status()
                    results = resp.json().get("results", [])
                    return PluginResult(success=True, data={"results": [
                        {"id": r["id"], "title": _extract_title(r), "type": r["object"]}
                        for r in results
                    ]})

                elif action == "create_page":
                    parent_id = params.get("parent_id") or self.config.get("default_page_id", "")
                    title = params.get("title", "Nova página")
                    content = params.get("content", "")
                    children = []
                    if content:
                        children = [{
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {"rich_text": [{"text": {"content": content}}]},
                        }]
                    resp = await client.post(
                        "https://api.notion.com/v1/pages",
                        json={
                            "parent": {"page_id": parent_id},
                            "properties": {"title": {"title": [{"text": {"content": title}}]}},
                            "children": children,
                        },
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return PluginResult(success=True, data={"id": data["id"], "url": data.get("url", "")})

                elif action == "append_block":
                    page_id = params.get("page_id", "")
                    content = params.get("content", "")
                    resp = await client.patch(
                        f"https://api.notion.com/v1/blocks/{page_id}/children",
                        json={"children": [{
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {"rich_text": [{"text": {"content": content}}]},
                        }]},
                        headers=headers,
                    )
                    resp.raise_for_status()
                    return PluginResult(success=True, data={"appended": True})

                else:
                    return PluginResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            return PluginResult(success=False, error=str(e))

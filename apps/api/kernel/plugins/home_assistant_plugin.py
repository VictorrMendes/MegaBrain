import httpx

from kernel.plugins.base import Plugin, PluginRegistry, PluginResult


@PluginRegistry.register
class HomeAssistantPlugin(Plugin):
    name = "home_assistant"
    description = "Controla dispositivos e lê sensores via Home Assistant REST API"

    async def execute(self, action: str, params: dict) -> PluginResult:
        base_url = self.config.get("url", "http://homeassistant.local:8123").rstrip("/")
        token = self.config.get("token", "")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if action == "get_state":
                    entity_id = params.get("entity_id", "")
                    resp = await client.get(f"{base_url}/api/states/{entity_id}", headers=headers)
                    resp.raise_for_status()
                    s = resp.json()
                    return PluginResult(success=True, data={
                        "entity_id": s["entity_id"],
                        "state": s["state"],
                        "attributes": s.get("attributes", {}),
                    })

                elif action == "call_service":
                    domain = params.get("domain", "")
                    service = params.get("service", "")
                    service_data = params.get("data", {})
                    resp = await client.post(
                        f"{base_url}/api/services/{domain}/{service}",
                        json=service_data,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    return PluginResult(success=True, data={"called": f"{domain}.{service}"})

                elif action == "list_entities":
                    resp = await client.get(f"{base_url}/api/states", headers=headers)
                    resp.raise_for_status()
                    states = resp.json()
                    return PluginResult(success=True, data={
                        "count": len(states),
                        "entities": [s["entity_id"] for s in states[:50]],
                    })

                else:
                    return PluginResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            return PluginResult(success=False, error=str(e))

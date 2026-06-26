import httpx

from kernel.config import settings
from kernel.plugins.base import ConfigField, Plugin, PluginRegistry, PluginResult


@PluginRegistry.register
class NtfyPlugin(Plugin):
    name = "ntfy"
    description = "Envia notificações push via ntfy"
    category = "notifications"
    config_fields = [
        ConfigField("url",   "Servidor ntfy",  "url",  placeholder="https://ntfy.sh"),
        ConfigField("topic", "Tópico",         "text", required=True, placeholder="meu-topico"),
    ]

    async def execute(self, action: str, params: dict) -> PluginResult:
        if action != "notify":
            return PluginResult(success=False, error=f"Unknown action: {action}")

        url = self.config.get("url") or settings.ntfy_url
        topic = self.config.get("topic") or settings.ntfy_topic
        title = params.get("title", "Khonshu")
        message = params.get("message", "")
        priority = params.get("priority", "default")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{url}/{topic}",
                    content=message.encode(),
                    headers={"Title": title, "Priority": priority},
                )
                resp.raise_for_status()
            return PluginResult(success=True, data={"status": resp.status_code})
        except Exception as e:
            return PluginResult(success=False, error=str(e))

from kernel.plugins.base import Plugin, PluginRegistry, PluginResult

# Trigger @PluginRegistry.register decorators
from kernel.plugins import (  # noqa: F401
    ntfy_plugin,
    weather_plugin,
    web_search_plugin,
    home_assistant_plugin,
    notion_plugin,
    google_calendar_plugin,
)

__all__ = ["Plugin", "PluginRegistry", "PluginResult"]

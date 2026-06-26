from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PluginResult:
    success: bool
    data: dict | None = None
    error: str | None = None


@dataclass
class ConfigField:
    name: str
    label: str
    type: str  # "text" | "password" | "url"
    required: bool = False
    placeholder: str = ""


class Plugin(ABC):
    name: str
    description: str
    category: str = "general"
    config_fields: list[ConfigField] = field(default_factory=list)

    def __init__(self, config: dict) -> None:
        self.config = config

    @abstractmethod
    async def execute(self, action: str, params: dict) -> PluginResult: ...


class PluginRegistry:
    _plugins: dict[str, type["Plugin"]] = {}

    @classmethod
    def register(cls, plugin_class: type["Plugin"]) -> type["Plugin"]:
        cls._plugins[plugin_class.name] = plugin_class
        return plugin_class

    @classmethod
    def get(cls, name: str) -> type["Plugin"] | None:
        return cls._plugins.get(name)

    @classmethod
    def list_all(cls) -> list[dict]:
        return [
            {
                "name": pc.name,
                "description": pc.description,
                "category": getattr(pc, "category", "general"),
                "config_fields": [
                    {
                        "name": f.name,
                        "label": f.label,
                        "type": f.type,
                        "required": f.required,
                        "placeholder": f.placeholder,
                    }
                    for f in getattr(pc, "config_fields", [])
                ],
            }
            for pc in cls._plugins.values()
        ]

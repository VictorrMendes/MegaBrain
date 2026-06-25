from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from kernel.logger import get_logger

logger = get_logger(__name__)

ToolFn = Callable[..., Any]


@dataclass
class CapabilityTool:
    name: str               # e.g. "docker.start"
    description: str
    parameters: dict        # JSON Schema for arguments
    fn: ToolFn


@dataclass
class Capability:
    """A semantic capability exposed by a plugin.

    The Planner reasons about capabilities by description, not by tool names.
    Example: "who can manage containers?" → matches container_management.
    """

    name: str               # e.g. "container_management"
    description: str        # human + LLM readable
    plugin: str             # which plugin registered this
    tags: list[str] = field(default_factory=list)
    tools: dict[str, CapabilityTool] = field(default_factory=dict)

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: dict,
        fn: ToolFn,
    ) -> None:
        self.tools[name] = CapabilityTool(
            name=name,
            description=description,
            parameters=parameters,
            fn=fn,
        )

    def to_planner_descriptor(self) -> dict:
        """Compact descriptor injected into Planner prompts."""
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "tools": [
                {"name": t.name, "description": t.description}
                for t in self.tools.values()
            ],
        }


class CapabilityRegistry:
    """Central registry of all capabilities announced by plugins.

    Plugins call register() on startup. The Planner calls list() or
    find_by_tags() to discover what the system can do.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        self._capabilities[capability.name] = capability
        logger.info(
            "capability.registered",
            name=capability.name,
            plugin=capability.plugin,
            tools=list(capability.tools.keys()),
        )

    def unregister(self, name: str) -> None:
        if name in self._capabilities:
            del self._capabilities[name]
            logger.info("capability.unregistered", name=name)

    def get(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def get_tool(self, tool_name: str) -> CapabilityTool | None:
        """Look up a tool across all capabilities."""
        for cap in self._capabilities.values():
            if tool_name in cap.tools:
                return cap.tools[tool_name]
        return None

    def list(self) -> list[Capability]:
        return list(self._capabilities.values())

    def find_by_tags(self, *tags: str) -> list[Capability]:
        result = []
        tag_set = set(tags)
        for cap in self._capabilities.values():
            if tag_set & set(cap.tags):
                result.append(cap)
        return result

    def list_names(self) -> list[str]:
        return list(self._capabilities.keys())

    def to_planner_context(self) -> list[dict]:
        """Full capability list formatted for Planner prompt injection."""
        return [c.to_planner_descriptor() for c in self._capabilities.values()]

    def __len__(self) -> int:
        return len(self._capabilities)


# Global singleton — imported by plugins and the Planner
capability_registry = CapabilityRegistry()

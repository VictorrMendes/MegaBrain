"""RuntimeCapabilitySnapshot — real-time state of all system capabilities.

Built once per request by RuntimeSnapshotBuilder and injected into the
system prompt via ContextBuilder. Gives the LLM ground truth about what
the system can actually do right now — no hallucinated limitations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass
class CapabilityState:
    name: str
    available: bool
    configured: bool
    provider: str
    reason: str | None = None

    @property
    def status_label(self) -> str:
        if self.available:
            return "Disponível"
        if self.configured:
            return "Configurado mas indisponível"
        return "Não configurado"


@dataclass
class RuntimeCapabilitySnapshot:
    capabilities: list[CapabilityState]
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def get(self, name: str) -> CapabilityState | None:
        for cap in self.capabilities:
            if cap.name.lower() == name.lower():
                return cap
        return None

    def available_names(self) -> list[str]:
        return [c.name for c in self.capabilities if c.available]

    def to_prompt_section(self) -> str:
        lines: list[str] = [
            "## Capacidades do Sistema (estado em tempo real)",
            "Use estas capacidades para responder. "
            "NUNCA afirme limitação que contradiga o estado abaixo.\n",
        ]
        for cap in self.capabilities:
            icon = "✓" if cap.available else "✗"
            line = f"{icon} **{cap.name}**"
            if cap.provider:
                line += f" — {cap.provider}"
            if not cap.available and cap.reason:
                line += f" [{cap.reason}]"
            lines.append(line)
        return "\n".join(lines)


class RuntimeSnapshotBuilder:
    """Builds a RuntimeCapabilitySnapshot from injected engine references.

    All arguments are optional — missing engines produce an unavailable
    state rather than raising exceptions, so the builder degrades cleanly.
    """

    def __init__(
        self,
        *,
        has_search: bool = False,
        has_memory: bool = False,
        has_knowledge: bool = False,
        has_missions: bool = False,
        has_scheduler: bool = False,
        has_briefings: bool = False,
        has_plugins: bool = False,
        has_obsidian: bool = False,
        has_cognitive_loop: bool = False,
        has_event_bus: bool = False,
        integration_manager=None,
    ) -> None:
        self._has_search = has_search
        self._has_memory = has_memory
        self._has_knowledge = has_knowledge
        self._has_missions = has_missions
        self._has_scheduler = has_scheduler
        self._has_briefings = has_briefings
        self._has_plugins = has_plugins
        self._has_obsidian = has_obsidian
        self._has_cognitive_loop = has_cognitive_loop
        self._has_event_bus = has_event_bus
        self._integrations = integration_manager

    async def build(
        self, workspace_id: UUID | None = None
    ) -> RuntimeCapabilitySnapshot:
        caps: list[CapabilityState] = [
            CapabilityState(
                name="Busca Web (Internet)",
                available=self._has_search,
                configured=self._has_search,
                provider="DuckDuckGo Search",
                reason=None if self._has_search else "SearchEngine não iniciado",
            ),
            CapabilityState(
                name="Memória",
                available=self._has_memory,
                configured=self._has_memory,
                provider="MemoryEngine",
                reason=None if self._has_memory else "MemoryEngine não iniciado",
            ),
            CapabilityState(
                name="Conhecimento (Knowledge Base)",
                available=self._has_knowledge,
                configured=self._has_knowledge,
                provider="KnowledgeEngine",
            ),
            CapabilityState(
                name="Missões",
                available=self._has_missions,
                configured=self._has_missions,
                provider="MissionEngine",
            ),
            CapabilityState(
                name="Agendador",
                available=self._has_scheduler,
                configured=self._has_scheduler,
                provider="SchedulerEngine",
            ),
            CapabilityState(
                name="Briefings",
                available=self._has_briefings,
                configured=self._has_briefings,
                provider="BriefingEngine",
            ),
            CapabilityState(
                name="Plugins",
                available=self._has_plugins,
                configured=self._has_plugins,
                provider="PluginEngine",
            ),
            CapabilityState(
                name="Obsidian",
                available=self._has_obsidian,
                configured=self._has_obsidian,
                provider="ObsidianEngine",
            ),
            CapabilityState(
                name="Loop Cognitivo",
                available=self._has_cognitive_loop,
                configured=self._has_cognitive_loop,
                provider="CognitiveLoop",
            ),
            CapabilityState(
                name="EventBus",
                available=self._has_event_bus,
                configured=self._has_event_bus,
                provider="PostgreSQL pg_notify",
            ),
        ]

        # Dynamic: query IntegrationManager for workspace integrations
        if self._integrations is not None and workspace_id is not None:
            try:
                integrations = await self._integrations.list_integrations(
                    workspace_id
                )
                for integ in integrations:
                    caps.append(
                        CapabilityState(
                            name=integ.name,
                            available=(integ.status.value == "active"),
                            configured=True,
                            provider=integ.slug,
                            reason=(
                                None
                                if integ.status.value == "active"
                                else f"status={integ.status.value}"
                            ),
                        )
                    )
            except Exception:
                pass

        return RuntimeCapabilitySnapshot(capabilities=caps)

"""LifeContextProvider — volatile snapshot of the user's digital life.

Aggregates life_context_lines from all active integrations and formats
them into a prompt section for ContextBuilder.

NOT persisted as Memory or Knowledge — this is ephemeral context.
It is re-assembled on every ContextBuilder.build() call (cheap: just
reads from Integration.life_context_lines, which are updated by each sync).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from kernel.logger import get_logger

if TYPE_CHECKING:
    from engines.integration import IntegrationManager

logger = get_logger(__name__)

_STALE_THRESHOLD = timedelta(hours=6)


@dataclass
class LifeContextSnapshot:
    lines: list[str] = field(default_factory=list)
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    integration_count: int = 0

    def is_empty(self) -> bool:
        return len(self.lines) == 0

    def to_prompt_section(self) -> str:
        if self.is_empty():
            return ""
        body = "\n".join(f"• {line}" for line in self.lines)
        return f"## Sua vida digital agora\n\n{body}"


class LifeContextProvider:
    """Assembles a LifeContextSnapshot from all active integrations.

    Owned by KhonshuRuntime; injected into ContextBuilder as an optional
    dependency so existing workspaces without integrations still work.
    """

    def __init__(self, integration_manager: IntegrationManager) -> None:
        self._manager = integration_manager

    async def snapshot(self, workspace_id: UUID) -> LifeContextSnapshot:
        """Build a fresh snapshot from cached integration data.

        Reads Integration.life_context_lines — no external API calls here.
        The lines are populated by IntegrationManager.sync().
        Integrations whose last_sync is older than _STALE_THRESHOLD are
        flagged so the user knows the data might be outdated.
        """
        try:
            integrations = await self._manager.list_integrations(
                workspace_id
            )
        except Exception as exc:
            logger.warning(
                "life_context.load_failed", error=str(exc)
            )
            return LifeContextSnapshot()

        lines: list[str] = []
        count = 0

        for integration in integrations:
            if not integration.life_context_lines:
                continue

            # Mark stale data
            stale = (
                integration.last_sync_at is not None
                and datetime.now(UTC) - integration.last_sync_at
                > _STALE_THRESHOLD
            )
            prefix = "⏱️ " if stale else ""

            for line in integration.life_context_lines:
                lines.append(f"{prefix}{line}")

            count += 1

        return LifeContextSnapshot(
            lines=lines,
            integration_count=count,
        )

    async def to_prompt_section(self, workspace_id: UUID) -> str:
        snapshot = await self.snapshot(workspace_id)
        return snapshot.to_prompt_section()

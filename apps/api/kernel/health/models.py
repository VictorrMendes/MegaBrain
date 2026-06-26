from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class HealthStatus(StrEnum):
    ready = "ready"
    degraded = "degraded"
    failed = "failed"


@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus
    latency_ms: float | None = None
    detail: str | None = None
    checked_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "detail": self.detail,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class HealthReport:
    status: HealthStatus
    components: list[ComponentHealth]
    checked_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    @classmethod
    def from_components(
        cls, components: list[ComponentHealth]
    ) -> HealthReport:
        worst = HealthStatus.ready
        for c in components:
            if c.status == HealthStatus.failed:
                worst = HealthStatus.failed
                break
            if c.status == HealthStatus.degraded:
                worst = HealthStatus.degraded
        return cls(status=worst, components=components)

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
            "components": [c.to_dict() for c in self.components],
        }


async def db_health(
    name: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> ComponentHealth:
    """Verifica conectividade com o banco via SELECT 1."""
    t0 = time.monotonic()
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        latency = (time.monotonic() - t0) * 1000
        return ComponentHealth(
            name=name,
            status=HealthStatus.ready,
            latency_ms=round(latency, 2),
        )
    except Exception as exc:
        return ComponentHealth(
            name=name,
            status=HealthStatus.failed,
            detail=str(exc),
        )

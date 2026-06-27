"""Runtime API — exposes system state for monitoring and dashboards.

Endpoints:
    GET /runtime              — full status snapshot
    GET /runtime/health       — health report (components + latencies)
    GET /runtime/capabilities — registered capabilities
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import func, select

from core.database import AsyncSessionLocal
from kernel.capabilities import capability_registry
from kernel.runtime import runtime
from models.mission import Mission, MissionStatus
from models.scheduler import SchedulerTrigger
from schemas.runtime import (
    CapabilityInfo,
    ComponentHealthInfo,
    MissionSummary,
    ProviderInfo,
    RuntimeStatus,
    SchedulerInfo,
)

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("", response_model=RuntimeStatus)
async def get_runtime_status():
    """Full runtime status snapshot — health, provider, capabilities, missions."""
    health_report = await runtime.health_report()

    llm = runtime.llm
    provider = ProviderInfo(
        name="ollama",
        model=llm.model,
        embed_model=llm.embed_model,
        base_url=llm.base_url,
    )

    caps = [
        CapabilityInfo(
            name=c.name,
            description=c.description,
            plugin=c.plugin,
            risk_level=c.risk_level.value,
            tags=c.tags,
            tool_count=len(c.tools),
            requires_network=c.requires_network,
            requires_confirmation=c.requires_confirmation,
            confidence_score=c.confidence_score,
        )
        for c in capability_registry.list()
    ]

    active_missions: list[MissionSummary] = []
    scheduler_info = SchedulerInfo(
        active_triggers=0, paused_triggers=0, total_triggers=0
    )

    async with AsyncSessionLocal() as db:
        mission_result = await db.execute(
            select(Mission)
            .where(
                Mission.status.in_([
                    MissionStatus.RUNNING,
                    MissionStatus.WAITING_APPROVAL,
                    MissionStatus.PLANNING,
                    MissionStatus.READY,
                ])
            )
            .order_by(Mission.updated_at.desc())
            .limit(20)
        )
        for m in mission_result.scalars():
            active_missions.append(MissionSummary(
                id=m.id,
                intent=m.intent,
                status=m.status.value,
                created_at=m.created_at,
                updated_at=m.updated_at,
            ))

        counts_result = await db.execute(
            select(SchedulerTrigger.status, func.count().label("n"))
            .group_by(SchedulerTrigger.status)
        )
        totals: dict[str, int] = {
            (row.status.value if hasattr(row.status, "value") else row.status): row.n
            for row in counts_result
        }
        scheduler_info = SchedulerInfo(
            active_triggers=totals.get("active", 0),
            paused_triggers=totals.get("paused", 0),
            total_triggers=sum(totals.values()),
        )

    health_components = [
        ComponentHealthInfo(
            name=c.name,
            status=c.status.value,
            latency_ms=c.latency_ms,
            detail=c.detail,
            checked_at=c.checked_at,
        )
        for c in health_report.components
    ]

    return RuntimeStatus(
        status=health_report.status.value,
        checked_at=datetime.now(UTC),
        provider=provider,
        health=health_components,
        capabilities=caps,
        scheduler=scheduler_info,
        active_missions=active_missions,
    )


@router.get("/health")
async def get_health():
    """Detailed health report for all components."""
    report = await runtime.health_report()
    return report.to_dict()


@router.get("/capabilities")
async def list_capabilities():
    """All registered capabilities with full metadata."""
    return [c.to_planner_descriptor() for c in capability_registry.list()]

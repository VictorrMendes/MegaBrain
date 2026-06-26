from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from core.database import AsyncSessionLocal
from kernel.runtime import runtime
from models.inbox import InboxItem, InboxItemStatus
from models.knowledge import Fact
from models.memory import Memory
from models.mission import Mission, MissionArtifact, MissionStatus
from models.scheduler import SchedulerTrigger
from models.workspace import Workspace
from schemas.dashboard import (
    DashboardSummary,
    MissionCounts,
    RecentArtifact,
    RecentFact,
    RecentMemory,
    RecentMission,
)
from schemas.runtime import ComponentHealthInfo, SchedulerInfo

router = APIRouter(
    prefix="/workspaces/{workspace_id}/dashboard",
    tags=["dashboard"],
)


@router.get("", response_model=DashboardSummary)
async def get_dashboard(workspace_id: UUID):
    async with AsyncSessionLocal() as db:
        ws = await db.get(Workspace, workspace_id)
        if ws is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Mission counts grouped by status
        counts_result = await db.execute(
            select(Mission.status, func.count(Mission.id))
            .where(Mission.workspace_id == workspace_id)
            .group_by(Mission.status)
        )
        raw_counts: dict[str, int] = {
            row[0]: row[1] for row in counts_result.all()
        }
        mission_counts = MissionCounts(
            pending=raw_counts.get(MissionStatus.PENDING, 0),
            planning=raw_counts.get(MissionStatus.PLANNING, 0),
            waiting_approval=raw_counts.get(MissionStatus.WAITING_APPROVAL, 0),
            ready=raw_counts.get(MissionStatus.READY, 0),
            running=raw_counts.get(MissionStatus.RUNNING, 0),
            succeeded=raw_counts.get(MissionStatus.SUCCEEDED, 0),
            failed=raw_counts.get(MissionStatus.FAILED, 0),
            cancelled=raw_counts.get(MissionStatus.CANCELLED, 0),
            total=sum(raw_counts.values()),
        )

        # Inbox pending count
        inbox_result = await db.execute(
            select(func.count(InboxItem.id)).where(
                InboxItem.workspace_id == workspace_id,
                InboxItem.status == InboxItemStatus.pending,
            )
        )
        inbox_pending = inbox_result.scalar() or 0

        # Recent missions
        missions_result = await db.execute(
            select(Mission)
            .where(Mission.workspace_id == workspace_id)
            .order_by(Mission.updated_at.desc())
            .limit(8)
        )
        recent_missions = [
            RecentMission(
                id=m.id,
                intent=m.intent,
                status=str(m.status),
                trigger=str(m.trigger),
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in missions_result.scalars()
        ]

        # Recent memories
        mems_result = await db.execute(
            select(Memory)
            .where(Memory.workspace_id == workspace_id)
            .order_by(Memory.created_at.desc())
            .limit(5)
        )
        recent_memories = [
            RecentMemory(
                id=m.id,
                type=str(m.type),
                content=(
                    m.content[:120] + "…" if len(m.content) > 120 else m.content
                ),
                importance=m.importance,
                created_at=m.created_at,
            )
            for m in mems_result.scalars()
        ]

        # Recent facts
        facts_result = await db.execute(
            select(Fact)
            .where(
                Fact.workspace_id == workspace_id,
                Fact.superseded_by_id.is_(None),
            )
            .order_by(Fact.created_at.desc())
            .limit(5)
        )
        recent_facts = [
            RecentFact(
                id=f.id,
                statement=(
                    f.statement[:120] + "…"
                    if len(f.statement) > 120
                    else f.statement
                ),
                confidence=f.confidence,
                created_at=f.created_at,
            )
            for f in facts_result.scalars()
        ]

        # Recent artifacts
        arts_result = await db.execute(
            select(MissionArtifact)
            .join(MissionArtifact.mission)
            .where(Mission.workspace_id == workspace_id)
            .order_by(MissionArtifact.created_at.desc())
            .limit(5)
        )
        recent_artifacts = [
            RecentArtifact(
                id=a.id,
                name=a.name,
                type=a.type,
                mime=a.mime,
                mission_id=a.mission_id,
                created_at=a.created_at,
            )
            for a in arts_result.scalars()
        ]

        # Scheduler counts (same pattern as runtime router)
        sched_result = await db.execute(
            select(SchedulerTrigger.status, func.count().label("n"))
            .group_by(SchedulerTrigger.status)
        )
        sched_totals: dict[str, int] = {
            row.status.value: row.n for row in sched_result
        }
        scheduler = SchedulerInfo(
            active_triggers=sched_totals.get("active", 0),
            paused_triggers=sched_totals.get("paused", 0),
            total_triggers=sum(sched_totals.values()),
        )

    # Health report (async, outside DB session)
    health_report = await runtime.health_report()
    health = [
        ComponentHealthInfo(
            name=c.name,
            status=c.status.value,
            latency_ms=c.latency_ms,
            detail=c.detail,
            checked_at=c.checked_at,
        )
        for c in health_report.components
    ]

    return DashboardSummary(
        workspace_id=workspace_id,
        workspace_name=ws.name,
        generated_at=datetime.now(UTC),
        missions=mission_counts,
        inbox_pending=inbox_pending,
        recent_missions=recent_missions,
        recent_memories=recent_memories,
        recent_facts=recent_facts,
        recent_artifacts=recent_artifacts,
        health=health,
        scheduler=scheduler,
    )

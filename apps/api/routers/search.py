from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.knowledge import Fact, Observation
from models.memory import Memory
from models.mission import Mission, MissionArtifact
from schemas.search import SearchResponse, SearchResult

router = APIRouter(prefix="/search", tags=["search"])

_MAX_RESULTS = 30


@router.get("", response_model=SearchResponse)
async def global_search(
    q: str,
    workspace_id: UUID | None = None,
    limit: int = 20,
):
    if not q.strip():
        return SearchResponse(query=q, results=[], total=0)

    term = f"%{q.strip()}%"
    results: list[SearchResult] = []

    async with AsyncSessionLocal() as db:
        # Missions
        stmt = select(Mission).where(Mission.intent.ilike(term)).limit(8)
        if workspace_id:
            stmt = stmt.where(Mission.workspace_id == workspace_id)
        missions = list((await db.execute(stmt)).scalars())
        for m in missions:
            results.append(
                SearchResult(
                    type="mission",
                    id=str(m.id),
                    title=m.intent,
                    excerpt=f"Status: {m.status} · {m.trigger}",
                    workspace_id=str(m.workspace_id),
                    href=f"/missions?id={m.id}",
                )
            )

        # Memories
        stmt = (
            select(Memory)
            .where(Memory.content.ilike(term))
            .limit(6)
        )
        if workspace_id:
            stmt = stmt.where(Memory.workspace_id == workspace_id)
        mems = list((await db.execute(stmt)).scalars())
        for mem in mems:
            results.append(
                SearchResult(
                    type="memory",
                    id=str(mem.id),
                    title=mem.content[:60] + ("…" if len(mem.content) > 60 else ""),
                    excerpt=f"Tipo: {mem.type} · importância {int(mem.importance * 100)}%",
                    workspace_id=str(mem.workspace_id),
                    href="/memory",
                )
            )

        # Facts
        stmt = (
            select(Fact)
            .where(Fact.statement.ilike(term), Fact.superseded_by_id.is_(None))
            .limit(6)
        )
        if workspace_id:
            stmt = stmt.where(Fact.workspace_id == workspace_id)
        facts = list((await db.execute(stmt)).scalars())
        for f in facts:
            results.append(
                SearchResult(
                    type="fact",
                    id=str(f.id),
                    title=f.statement[:60] + ("…" if len(f.statement) > 60 else ""),
                    excerpt=f"Confiança: {int(f.confidence * 100)}% · {f.source_type}",
                    workspace_id=str(f.workspace_id),
                    href="/knowledge",
                )
            )

        # Observations
        stmt = (
            select(Observation)
            .where(Observation.statement.ilike(term), Observation.expired.is_(False))
            .limit(4)
        )
        if workspace_id:
            stmt = stmt.where(Observation.workspace_id == workspace_id)
        obs = list((await db.execute(stmt)).scalars())
        for o in obs:
            results.append(
                SearchResult(
                    type="observation",
                    id=str(o.id),
                    title=o.statement[:60] + ("…" if len(o.statement) > 60 else ""),
                    excerpt=f"Confiança: {int(o.confidence * 100)}% · {o.derived_from}",
                    workspace_id=str(o.workspace_id),
                    href="/knowledge",
                )
            )

        # Artifacts
        stmt = (
            select(MissionArtifact)
            .join(MissionArtifact.mission)
            .where(MissionArtifact.name.ilike(term))
            .limit(4)
        )
        if workspace_id:
            stmt = stmt.where(Mission.workspace_id == workspace_id)
        arts = list((await db.execute(stmt)).scalars())
        for a in arts:
            results.append(
                SearchResult(
                    type="artifact",
                    id=str(a.id),
                    title=a.name,
                    excerpt=f"{a.type} · {a.mime}",
                    workspace_id=str(a.mission.workspace_id) if a.mission else "",
                    href="/artifacts",
                )
            )

    results = results[:limit]
    return SearchResponse(query=q, results=results, total=len(results))

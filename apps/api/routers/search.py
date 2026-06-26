from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.knowledge import Entity, Fact, Observation
from models.memory import Memory
from models.mission import Mission, MissionArtifact
from schemas.search import SearchResponse, SearchResult

router = APIRouter(prefix="/search", tags=["search"])


def _excerpt(text: str, max_len: int = 80) -> str:
    return text[:max_len] + ("…" if len(text) > max_len else "")


def _score_by_position(text: str, term_raw: str) -> float:
    """Higher score when the query appears earlier and more completely."""
    lo = text.lower()
    q  = term_raw.strip().lower()
    if not lo:
        return 0.5
    idx = lo.find(q)
    if idx == -1:
        return 0.3
    # Earlier position → higher score; exact start → 1.0
    proximity = 1.0 - (idx / max(len(lo), 1)) * 0.5
    # Full term vs partial match
    coverage  = len(q) / max(len(lo), 1)
    return min(1.0, proximity * 0.7 + coverage * 0.3)


@router.get("", response_model=SearchResponse)
async def global_search(
    q: str,
    workspace_id: UUID | None = None,
    limit: int = 20,
):
    if not q.strip():
        return SearchResponse(query=q, results=[], total=0)

    term     = f"%{q.strip()}%"
    q_raw    = q.strip()
    results: list[SearchResult] = []

    async with AsyncSessionLocal() as db:
        # ── Missions ───────────────────────────────────────────
        stmt = select(Mission).where(Mission.intent.ilike(term)).limit(8)
        if workspace_id:
            stmt = stmt.where(Mission.workspace_id == workspace_id)
        for m in (await db.execute(stmt)).scalars():
            results.append(SearchResult(
                type="mission",
                id=str(m.id),
                title=m.intent,
                excerpt=f"Status: {m.status} · {m.trigger}",
                workspace_id=str(m.workspace_id),
                href=f"/missions?id={m.id}",
                score=_score_by_position(m.intent, q_raw),
            ))

        # ── Memories ───────────────────────────────────────────
        stmt = select(Memory).where(Memory.content.ilike(term)).limit(6)
        if workspace_id:
            stmt = stmt.where(Memory.workspace_id == workspace_id)
        for mem in (await db.execute(stmt)).scalars():
            results.append(SearchResult(
                type="memory",
                id=str(mem.id),
                title=_excerpt(mem.content, 60),
                excerpt=f"Tipo: {mem.type} · importância {int(mem.importance * 100)}%",
                workspace_id=str(mem.workspace_id),
                href="/memory",
                score=_score_by_position(mem.content, q_raw) * (0.5 + 0.5 * mem.importance),
            ))

        # ── Facts ──────────────────────────────────────────────
        stmt = (
            select(Fact)
            .where(Fact.statement.ilike(term), Fact.superseded_by_id.is_(None))
            .limit(6)
        )
        if workspace_id:
            stmt = stmt.where(Fact.workspace_id == workspace_id)
        for f in (await db.execute(stmt)).scalars():
            results.append(SearchResult(
                type="fact",
                id=str(f.id),
                title=_excerpt(f.statement, 60),
                excerpt=f"Confiança: {int(f.confidence * 100)}% · {f.source_type}",
                workspace_id=str(f.workspace_id),
                href="/knowledge",
                score=_score_by_position(f.statement, q_raw) * f.confidence,
            ))

        # ── Observations ───────────────────────────────────────
        stmt = (
            select(Observation)
            .where(Observation.statement.ilike(term), Observation.expired.is_(False))
            .limit(4)
        )
        if workspace_id:
            stmt = stmt.where(Observation.workspace_id == workspace_id)
        for o in (await db.execute(stmt)).scalars():
            results.append(SearchResult(
                type="observation",
                id=str(o.id),
                title=_excerpt(o.statement, 60),
                excerpt=f"Confiança: {int(o.confidence * 100)}% · {o.derived_from}",
                workspace_id=str(o.workspace_id),
                href="/knowledge",
                score=_score_by_position(o.statement, q_raw) * o.confidence,
            ))

        # ── Entities ───────────────────────────────────────────
        stmt = select(Entity).where(Entity.name.ilike(term)).limit(5)
        if workspace_id:
            stmt = stmt.where(Entity.workspace_id == workspace_id)
        for e in (await db.execute(stmt)).scalars():
            results.append(SearchResult(
                type="entity",
                id=str(e.id),
                title=e.name,
                excerpt=f"Entidade · {e.type.value}",
                workspace_id=str(e.workspace_id),
                href="/knowledge",
                score=_score_by_position(e.name, q_raw),
            ))

        # ── Artifacts ──────────────────────────────────────────
        stmt = (
            select(MissionArtifact)
            .join(MissionArtifact.mission)
            .where(MissionArtifact.name.ilike(term))
            .limit(4)
        )
        if workspace_id:
            stmt = stmt.where(Mission.workspace_id == workspace_id)
        for a in (await db.execute(stmt)).scalars():
            results.append(SearchResult(
                type="artifact",
                id=str(a.id),
                title=a.name,
                excerpt=f"{a.type} · {a.mime}",
                workspace_id=str(a.mission.workspace_id) if a.mission else "",
                href="/artifacts",
                score=_score_by_position(a.name, q_raw),
            ))

    # Sort by score descending
    results.sort(key=lambda r: r.score, reverse=True)
    results = results[:limit]
    return SearchResponse(query=q, results=results, total=len(results))

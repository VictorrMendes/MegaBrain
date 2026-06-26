from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.mission import MissionArtifact
from schemas.mission import MissionArtifactResponse

router = APIRouter(
    prefix="/workspaces/{workspace_id}/artifacts",
    tags=["artifacts"],
)


@router.get("", response_model=list[MissionArtifactResponse])
async def list_artifacts(
    workspace_id: UUID,
    mission_id: UUID | None = None,
    limit: int = 50,
):
    """List all artifacts for a workspace, optionally filtered by mission."""
    async with AsyncSessionLocal() as db:
        q = (
            select(MissionArtifact)
            .join(
                MissionArtifact.mission,
            )
            .where(MissionArtifact.mission.has(workspace_id=workspace_id))
            .order_by(MissionArtifact.created_at.desc())
            .limit(limit)
        )
        if mission_id is not None:
            q = q.where(MissionArtifact.mission_id == mission_id)
        result = await db.execute(q)
        return list(result.scalars())


@router.get("/{artifact_id}", response_model=MissionArtifactResponse)
async def get_artifact(workspace_id: UUID, artifact_id: UUID):
    async with AsyncSessionLocal() as db:
        artifact = await db.get(MissionArtifact, artifact_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return artifact

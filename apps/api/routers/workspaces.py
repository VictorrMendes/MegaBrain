from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.workspace import Workspace
from schemas.workspace import WorkspaceCreate, WorkspaceResponse

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    data: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
):
    ws = Workspace(name=data.name, description=data.description)
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return ws


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workspace).where(Workspace.is_active.is_(True))
    )
    return result.scalars().all()


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    ws = await db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws

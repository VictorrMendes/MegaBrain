from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.workspace import Workspace
from models.workspace_session import WorkspaceSession
from schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceSessionResponse,
    WorkspaceSessionUpdate,
)

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


@router.get(
    "/{workspace_id}/session",
    response_model=WorkspaceSessionResponse,
)
async def get_workspace_session(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(WorkspaceSession, workspace_id)
    if row is None:
        return WorkspaceSessionResponse(
            workspace_id=workspace_id,
            active_conversation_id=None,
            current_page=None,
            ui_state={},
            updated_at=datetime.now(UTC),
        )
    return row


@router.patch(
    "/{workspace_id}/session",
    response_model=WorkspaceSessionResponse,
)
async def update_workspace_session(
    workspace_id: UUID,
    body: WorkspaceSessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(WorkspaceSession, workspace_id)
    if row is None:
        row = WorkspaceSession(workspace_id=workspace_id)
        db.add(row)
    row.active_conversation_id = body.active_conversation_id
    row.current_page = body.current_page
    row.ui_state = body.ui_state
    await db.commit()
    await db.refresh(row)
    return row

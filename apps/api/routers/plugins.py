from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from kernel.plugins.base import PluginRegistry
from models.workspace_plugin import WorkspacePlugin
from schemas.plugin import (
    AvailablePlugin,
    WorkspacePluginCreate,
    WorkspacePluginResponse,
    WorkspacePluginUpdate,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/plugins",
    tags=["plugins"],
)


@router.get("/available", response_model=list[AvailablePlugin])
async def list_available_plugins():
    return PluginRegistry.list_all()


@router.get("", response_model=list[WorkspacePluginResponse])
async def list_workspace_plugins(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkspacePlugin)
        .where(WorkspacePlugin.workspace_id == workspace_id)
        .order_by(WorkspacePlugin.created_at)
    )
    return result.scalars().all()


@router.post("", response_model=WorkspacePluginResponse, status_code=201)
async def create_or_update_plugin(
    workspace_id: UUID,
    data: WorkspacePluginCreate,
    db: AsyncSession = Depends(get_db),
):
    if PluginRegistry.get(data.plugin_name) is None:
        raise HTTPException(status_code=400, detail=f"Plugin '{data.plugin_name}' not found")

    result = await db.execute(
        select(WorkspacePlugin).where(
            WorkspacePlugin.workspace_id == workspace_id,
            WorkspacePlugin.plugin_name == data.plugin_name,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.is_enabled = data.is_enabled
        existing.config = data.config
        await db.commit()
        await db.refresh(existing)
        return existing

    plugin = WorkspacePlugin(
        workspace_id=workspace_id,
        plugin_name=data.plugin_name,
        is_enabled=data.is_enabled,
        config=data.config,
    )
    db.add(plugin)
    await db.commit()
    await db.refresh(plugin)
    return plugin


@router.patch("/{plugin_id}", response_model=WorkspacePluginResponse)
async def update_plugin(
    workspace_id: UUID,
    plugin_id: UUID,
    data: WorkspacePluginUpdate,
    db: AsyncSession = Depends(get_db),
):
    plugin = await db.get(WorkspacePlugin, plugin_id)
    if plugin is None or plugin.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Plugin not found")

    if data.is_enabled is not None:
        plugin.is_enabled = data.is_enabled
    if data.config is not None:
        plugin.config = data.config

    await db.commit()
    await db.refresh(plugin)
    return plugin


@router.delete("/{plugin_id}", status_code=204)
async def delete_plugin(
    workspace_id: UUID,
    plugin_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    plugin = await db.get(WorkspacePlugin, plugin_id)
    if plugin is None or plugin.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Plugin not found")
    await db.delete(plugin)
    await db.commit()

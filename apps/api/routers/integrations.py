from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_integration_manager, get_life_context
from engines.integration import IntegrationManager
from kernel.life_context import LifeContextProvider
from models.integration import SyncMode
from schemas.integration import (
    AvailableIntegration,
    CapabilityExecuteRequest,
    ConnectedAccountResponse,
    IntegrationConnectRequest,
    IntegrationResponse,
    LifeContextResponse,
    SyncRecordResponse,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/available", response_model=list[AvailableIntegration])
async def list_available(
    manager: IntegrationManager = Depends(get_integration_manager),
):
    return manager.list_available()


@router.get(
    "/{workspace_id}", response_model=list[IntegrationResponse]
)
async def list_connected(
    workspace_id: UUID,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    return await manager.list_integrations(workspace_id)


@router.post("/{workspace_id}/connect", response_model=IntegrationResponse)
async def connect(
    workspace_id: UUID,
    body: IntegrationConnectRequest,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    try:
        return await manager.connect(
            workspace_id=workspace_id,
            slug=body.slug,
            config=body.config,
            account_name_override=body.account_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{workspace_id}/{integration_id}")
async def disconnect(
    workspace_id: UUID,
    integration_id: UUID,
    account_id: UUID | None = None,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    try:
        await manager.disconnect(integration_id, account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "disconnected"}


@router.post(
    "/{workspace_id}/{integration_id}/sync",
    response_model=SyncRecordResponse,
)
async def sync(
    workspace_id: UUID,
    integration_id: UUID,
    sync_type: SyncMode = SyncMode.manual,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    try:
        return await manager.sync(integration_id, sync_type=sync_type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{workspace_id}/sync-all")
async def sync_all(
    workspace_id: UUID,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    records = await manager.sync_all(workspace_id)
    return {"synced": len(records)}


@router.get(
    "/{workspace_id}/{integration_id}/health",
)
async def health_check(
    workspace_id: UUID,
    integration_id: UUID,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    health = await manager.health_check(integration_id)
    return {"health": health.value}


@router.get(
    "/{workspace_id}/{integration_id}/accounts",
    response_model=list[ConnectedAccountResponse],
)
async def list_accounts(
    workspace_id: UUID,
    integration_id: UUID,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    return await manager.list_accounts(integration_id)


@router.get(
    "/{workspace_id}/{integration_id}/sync-history",
    response_model=list[SyncRecordResponse],
)
async def sync_history(
    workspace_id: UUID,
    integration_id: UUID,
    limit: int = 20,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    return await manager.list_sync_records(integration_id, limit=limit)


@router.get(
    "/{workspace_id}/life-context/snapshot",
    response_model=LifeContextResponse,
)
async def life_context_snapshot(
    workspace_id: UUID,
    provider: LifeContextProvider = Depends(get_life_context),
):
    snapshot = await provider.snapshot(workspace_id)
    return LifeContextResponse(
        lines=snapshot.lines,
        integration_count=snapshot.integration_count,
        generated_at=snapshot.generated_at,
    )


@router.post(
    "/{workspace_id}/{slug}/execute",
)
async def execute_capability(
    workspace_id: UUID,
    slug: str,
    body: CapabilityExecuteRequest,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    try:
        return await manager.execute_capability(
            workspace_id, slug, body.capability, body.params
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

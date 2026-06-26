from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from models.integration import (
    IntegrationCategory,
    IntegrationHealth,
    IntegrationStatus,
    SyncMode,
    SyncRecordStatus,
)


class AvailableIntegration(BaseModel):
    slug: str
    name: str
    description: str
    category: str
    icon: str
    sync_strategy: str
    capabilities: list[str]


class IntegrationConnectRequest(BaseModel):
    slug: str
    config: dict
    account_name: str | None = None


class IntegrationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    slug: str
    name: str
    category: IntegrationCategory
    icon: str
    description: str
    status: IntegrationStatus
    health: IntegrationHealth
    sync_strategy: SyncMode
    life_context_lines: list[str]
    last_sync_at: datetime | None
    next_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConnectedAccountResponse(BaseModel):
    id: UUID
    integration_id: UUID
    workspace_id: UUID
    provider: str
    account_name: str
    account_email: str | None
    status: str
    scopes: list[str]
    quota_used: int | None
    quota_limit: int | None
    last_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncRecordResponse(BaseModel):
    id: UUID
    integration_id: UUID
    workspace_id: UUID
    sync_type: SyncMode
    status: SyncRecordStatus
    items_synced: int
    items_failed: int
    conflicts: int
    duration_ms: int | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class LifeContextResponse(BaseModel):
    lines: list[str]
    integration_count: int
    generated_at: datetime


class CapabilityExecuteRequest(BaseModel):
    capability: str
    params: dict = {}

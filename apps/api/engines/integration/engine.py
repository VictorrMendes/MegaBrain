"""IntegrationManager — orchestrates all external integrations.

No other Engine accesses external APIs directly.
All external communication passes through IntegrationManager.

Responsibilities:
- register integrations in DB (derived from IntegrationRegistry)
- connect / disconnect accounts
- trigger synchronisation (manual or scheduled)
- health-check all active integrations
- publish IntegrationEventType events
- update life_context_lines on Integration for LifeContextProvider
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from engines.integration.base import IntegrationRegistry, SyncResult
from kernel.events import KhonshuEvent, event_bus
from kernel.events.schema import IntegrationEventType
from kernel.health import ComponentHealth, db_health
from kernel.logger import get_logger
from models.integration import (
    AccountStatus,
    ConnectedAccount,
    Integration,
    IntegrationHealth,
    IntegrationStatus,
    SyncMode,
    SyncRecord,
    SyncRecordStatus,
)

logger = get_logger(__name__)


class IntegrationManager:
    """Central manager for all Life Platform integrations."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        self._sessions = session_factory

    # ------------------------------------------------------------------ #
    # Introspection                                                        #
    # ------------------------------------------------------------------ #

    def list_available(self) -> list[dict]:
        """All registered providers (not yet connected to a workspace)."""
        return IntegrationRegistry.list_all()

    async def list_integrations(
        self, workspace_id: UUID
    ) -> list[Integration]:
        async with self._sessions() as db:
            result = await db.execute(
                select(Integration)
                .where(Integration.workspace_id == workspace_id)
                .order_by(Integration.name)
            )
            return list(result.scalars())

    async def get(self, integration_id: UUID) -> Integration | None:
        async with self._sessions() as db:
            return await db.get(Integration, integration_id)

    async def list_accounts(
        self, integration_id: UUID
    ) -> list[ConnectedAccount]:
        async with self._sessions() as db:
            result = await db.execute(
                select(ConnectedAccount)
                .where(
                    ConnectedAccount.integration_id == integration_id
                )
                .order_by(ConnectedAccount.created_at)
            )
            return list(result.scalars())

    async def list_sync_records(
        self, integration_id: UUID, limit: int = 20
    ) -> list[SyncRecord]:
        async with self._sessions() as db:
            result = await db.execute(
                select(SyncRecord)
                .where(SyncRecord.integration_id == integration_id)
                .order_by(SyncRecord.started_at.desc())
                .limit(limit)
            )
            return list(result.scalars())

    # ------------------------------------------------------------------ #
    # Connect / disconnect                                                 #
    # ------------------------------------------------------------------ #

    async def connect(
        self,
        workspace_id: UUID,
        slug: str,
        config: dict,
        account_name_override: str | None = None,
    ) -> Integration:
        """Connect a provider to a workspace.

        Creates (or finds existing) Integration row, then creates a
        ConnectedAccount with the validated credentials.
        """
        provider_cls = IntegrationRegistry.get(slug)
        if provider_cls is None:
            raise ValueError(f"Unknown integration provider: '{slug}'")

        provider = provider_cls()
        result = await provider.connect(config)
        if not result.success:
            raise ValueError(
                f"Connection to '{slug}' failed: {result.error}"
            )

        account_name = account_name_override or result.account_name

        async with self._sessions() as db:
            # Upsert Integration row
            existing = await db.execute(
                select(Integration).where(
                    Integration.workspace_id == workspace_id,
                    Integration.slug == slug,
                )
            )
            integration = existing.scalar_one_or_none()

            if integration is None:
                integration = Integration(
                    workspace_id=workspace_id,
                    slug=provider_cls.slug,
                    name=provider_cls.name,
                    category=provider_cls.category,
                    icon=provider_cls.icon,
                    description=provider_cls.description,
                    sync_strategy=provider_cls.sync_strategy,
                    config={},
                    status=IntegrationStatus.active,
                    health=IntegrationHealth.unknown,
                )
                db.add(integration)
                await db.flush()

            # ConnectedAccount
            account = ConnectedAccount(
                integration_id=integration.id,
                workspace_id=workspace_id,
                provider=slug,
                account_name=account_name,
                account_email=result.account_email,
                scopes=result.scopes,
                config={**result.config, **config},
                status=AccountStatus.active,
            )
            db.add(account)

            integration.status = IntegrationStatus.active
            integration.updated_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(integration)

        logger.info(
            "integration.connected",
            slug=slug,
            workspace_id=str(workspace_id),
            account=account_name,
        )

        await event_bus.publish_event(
            KhonshuEvent(
                type=IntegrationEventType.INTEGRATION_CONNECTED,
                workspace_id=workspace_id,
                source="integration_manager",
                payload={
                    "slug": slug,
                    "integration_id": str(integration.id),
                    "account_name": account_name,
                },
            )
        )

        return integration

    async def disconnect(
        self, integration_id: UUID, account_id: UUID | None = None
    ) -> None:
        """Disconnect an account (or all accounts) from an integration."""
        async with self._sessions() as db:
            integration = await db.get(Integration, integration_id)
            if integration is None:
                raise ValueError(
                    f"Integration {integration_id} not found"
                )

            if account_id:
                account = await db.get(ConnectedAccount, account_id)
                if account:
                    account.status = AccountStatus.revoked
                    account.updated_at = datetime.now(UTC)
            else:
                await db.execute(
                    update(ConnectedAccount)
                    .where(
                        ConnectedAccount.integration_id == integration_id
                    )
                    .values(
                        status=AccountStatus.revoked,
                        updated_at=datetime.now(UTC),
                    )
                )

            integration.status = IntegrationStatus.disconnected
            integration.health = IntegrationHealth.unknown
            integration.life_context_lines = []
            integration.updated_at = datetime.now(UTC)
            await db.commit()

        logger.info(
            "integration.disconnected",
            integration_id=str(integration_id),
        )

    # ------------------------------------------------------------------ #
    # Synchronisation                                                      #
    # ------------------------------------------------------------------ #

    async def sync(
        self,
        integration_id: UUID,
        sync_type: SyncMode = SyncMode.manual,
        account_id: UUID | None = None,
    ) -> SyncRecord:
        """Run a full or incremental sync for an integration."""
        async with self._sessions() as db:
            integration = await db.get(Integration, integration_id)
            if integration is None:
                raise ValueError(
                    f"Integration {integration_id} not found"
                )
            workspace_id = integration.workspace_id
            slug = integration.slug
            last_sync = integration.last_sync_at

        provider_cls = IntegrationRegistry.get(slug)
        if provider_cls is None:
            raise ValueError(f"No provider registered for slug '{slug}'")

        # Pick the right account
        account = await self._pick_account(integration_id, account_id)

        # Create SyncRecord
        record = await self._create_sync_record(
            integration_id=integration_id,
            account_id=account.id if account else None,
            workspace_id=workspace_id,
            sync_type=sync_type,
        )

        await event_bus.publish_event(
            KhonshuEvent(
                type=IntegrationEventType.INTEGRATION_SYNC_STARTED,
                workspace_id=workspace_id,
                source="integration_manager",
                payload={
                    "integration_id": str(integration_id),
                    "slug": slug,
                    "sync_type": sync_type,
                },
            )
        )

        start_ts = datetime.now(UTC)
        provider = provider_cls()
        since = last_sync if sync_type == SyncMode.incremental else None

        try:
            result: SyncResult = await provider.sync(
                account=account, since=since
            )
        except Exception as exc:
            result = SyncResult(error_message=str(exc))

        duration_ms = int(
            (datetime.now(UTC) - start_ts).total_seconds() * 1000
        )

        status = (
            SyncRecordStatus.success
            if result.success
            else (
                SyncRecordStatus.partial
                if result.items_synced > 0
                else SyncRecordStatus.failed
            )
        )

        now = datetime.now(UTC)

        async with self._sessions() as db:
            rec = await db.get(SyncRecord, record.id)
            rec.status = status
            rec.items_synced = result.items_synced
            rec.items_failed = result.items_failed
            rec.conflicts = result.conflicts
            rec.duration_ms = duration_ms
            rec.error_message = result.error_message
            rec.finished_at = now

            integration = await db.get(Integration, integration_id)
            integration.last_sync_at = now
            integration.updated_at = now
            if result.success:
                integration.health = IntegrationHealth.healthy
                integration.status = IntegrationStatus.active
            else:
                integration.health = IntegrationHealth.degraded

            if result.life_context_lines:
                integration.life_context_lines = (
                    result.life_context_lines
                )

            if account:
                acct = await db.get(ConnectedAccount, account.id)
                if acct:
                    acct.last_sync_at = now
                    acct.updated_at = now

            await db.commit()
            await db.refresh(rec)

        event_type = (
            IntegrationEventType.INTEGRATION_SYNC_DONE
            if result.success
            else IntegrationEventType.INTEGRATION_SYNC_FAILED
        )
        await event_bus.publish_event(
            KhonshuEvent(
                type=event_type,
                workspace_id=workspace_id,
                source="integration_manager",
                payload={
                    "integration_id": str(integration_id),
                    "slug": slug,
                    "items_synced": result.items_synced,
                    "duration_ms": duration_ms,
                    "error": result.error_message,
                },
            )
        )

        logger.info(
            "integration.sync_done",
            slug=slug,
            status=status.value,
            items=result.items_synced,
            ms=duration_ms,
        )
        return rec

    async def sync_all(self, workspace_id: UUID) -> list[SyncRecord]:
        """Sync all active integrations for a workspace."""
        integrations = await self.list_integrations(workspace_id)
        records: list[SyncRecord] = []
        for integration in integrations:
            if integration.status == IntegrationStatus.disconnected:
                continue
            try:
                rec = await self.sync(
                    integration.id, sync_type=SyncMode.scheduled
                )
                records.append(rec)
            except Exception as exc:
                logger.warning(
                    "integration.sync_all_error",
                    slug=integration.slug,
                    error=str(exc),
                )
        return records

    # ------------------------------------------------------------------ #
    # Health                                                               #
    # ------------------------------------------------------------------ #

    async def health_check(
        self, integration_id: UUID
    ) -> IntegrationHealth:
        async with self._sessions() as db:
            integration = await db.get(Integration, integration_id)
            if integration is None:
                return IntegrationHealth.unknown
            slug = integration.slug

        provider_cls = IntegrationRegistry.get(slug)
        if provider_cls is None:
            return IntegrationHealth.unknown

        account = await self._pick_account(integration_id, None)
        try:
            health = await provider_cls().health(account)
        except Exception:
            health = IntegrationHealth.unhealthy

        async with self._sessions() as db:
            integration = await db.get(Integration, integration_id)
            integration.health = health
            integration.updated_at = datetime.now(UTC)
            if health == IntegrationHealth.unhealthy:
                integration.status = IntegrationStatus.error
                await event_bus.publish_event(
                    KhonshuEvent(
                        type=IntegrationEventType.INTEGRATION_UNHEALTHY,
                        workspace_id=integration.workspace_id,
                        source="integration_manager",
                        payload={
                            "integration_id": str(integration_id),
                            "slug": slug,
                        },
                    )
                )
            await db.commit()

        return health

    async def health(self) -> ComponentHealth:
        return await db_health("integration_manager", self._sessions)

    # ------------------------------------------------------------------ #
    # Capability dispatch                                                  #
    # ------------------------------------------------------------------ #

    async def execute_capability(
        self,
        workspace_id: UUID,
        slug: str,
        capability: str,
        params: dict,
    ) -> dict:
        """Execute a named capability through its integration provider."""
        async with self._sessions() as db:
            result = await db.execute(
                select(Integration).where(
                    Integration.workspace_id == workspace_id,
                    Integration.slug == slug,
                    Integration.status != IntegrationStatus.disconnected,
                )
            )
            integration = result.scalar_one_or_none()
            if integration is None:
                raise ValueError(
                    f"Integration '{slug}' not connected in this workspace"
                )

        account = await self._pick_account(integration.id, None)
        provider_cls = IntegrationRegistry.get(slug)
        if provider_cls is None:
            raise ValueError(f"No provider for '{slug}'")

        logger.info(f"[RC-18E] IntegrationManager execute_capability | provider: {slug} | capability: {capability}")
        result = await provider_cls().execute(capability, params, account)
        logger.info(f"[RC-18E] IntegrationManager execute_capability | result keys: {list(result.keys()) if isinstance(result, dict) else 'not dict'}")
        return result

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    async def _pick_account(
        self, integration_id: UUID, account_id: UUID | None
    ) -> ConnectedAccount | None:
        async with self._sessions() as db:
            if account_id:
                return await db.get(ConnectedAccount, account_id)
            result = await db.execute(
                select(ConnectedAccount)
                .where(
                    ConnectedAccount.integration_id == integration_id,
                    ConnectedAccount.status == AccountStatus.active,
                )
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def _create_sync_record(
        self,
        integration_id: UUID,
        account_id: UUID | None,
        workspace_id: UUID,
        sync_type: SyncMode,
    ) -> SyncRecord:
        async with self._sessions() as db:
            record = SyncRecord(
                integration_id=integration_id,
                account_id=account_id,
                workspace_id=workspace_id,
                sync_type=sync_type,
                status=SyncRecordStatus.running,
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
        return record

"""Integration Provider contract.

Every external ecosystem must implement IntegrationProvider.
The IntegrationManager calls these methods exclusively —
no engine touches external APIs directly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from models.integration import (
    AccountStatus,
    ConnectedAccount,
    Integration,
    IntegrationCategory,
    IntegrationHealth,
    SyncMode,
)


@dataclass
class SyncResult:
    """Returned by IntegrationProvider.sync()."""

    items_synced: int = 0
    items_failed: int = 0
    conflicts: int = 0
    error_message: str | None = None
    # Human-readable lines for LifeContextProvider
    life_context_lines: list[str] = field(default_factory=list)
    # Arbitrary data the provider wants to cache on Integration.metadata_
    metadata: dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.error_message is None


@dataclass
class ConnectResult:
    """Returned by IntegrationProvider.connect()."""

    account_name: str
    account_email: str | None = None
    scopes: list[str] = field(default_factory=list)
    # Any provider-specific data to store in ConnectedAccount.config
    config: dict = field(default_factory=dict)
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class IntegrationProvider(ABC):
    """Abstract base for all integration providers.

    Subclass this and decorate with @IntegrationRegistry.register.
    """

    # --- Class-level metadata (set on the concrete class) ---
    slug: str
    name: str
    description: str
    category: IntegrationCategory
    icon: str = ""
    sync_strategy: SyncMode = SyncMode.manual
    # Capability names this integration exposes (for CapabilityRegistry)
    capabilities: list[str] = []
    # Event types this integration can produce
    supported_events: list[str] = []

    # ------------------------------------------------------------------ #
    # Mandatory interface                                                  #
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def connect(
        self, config: dict
    ) -> ConnectResult:
        """Validate credentials / connectivity and return account info."""
        ...

    @abstractmethod
    async def sync(
        self,
        account: ConnectedAccount,
        since: datetime | None = None,
    ) -> SyncResult:
        """Pull data from the external service.

        Must be idempotent. 'since' enables incremental syncs.
        Returns a SyncResult with life_context_lines populated.
        """
        ...

    @abstractmethod
    async def health(
        self, account: ConnectedAccount | None
    ) -> IntegrationHealth:
        """Check connectivity/health without a full sync."""
        ...

    # ------------------------------------------------------------------ #
    # Optional interface                                                   #
    # ------------------------------------------------------------------ #

    async def execute(
        self,
        capability: str,
        params: dict,
        account: ConnectedAccount | None,
    ) -> dict:
        """Execute a named capability (called by IntegrationManager).

        Override to support write operations (create event, send message…).
        """
        raise NotImplementedError(
            f"{self.slug} does not implement capability '{capability}'"
        )

    async def handle_webhook(
        self, payload: dict, account: ConnectedAccount | None
    ) -> SyncResult:
        """Process an inbound webhook payload."""
        return SyncResult(error_message="Webhooks not supported")


class IntegrationRegistry:
    """Central registry of all known IntegrationProviders.

    Providers register via @IntegrationRegistry.register decorator.
    IntegrationManager uses this to instantiate providers by slug.
    """

    _providers: dict[str, type[IntegrationProvider]] = {}

    @classmethod
    def register(
        cls, provider: type[IntegrationProvider]
    ) -> type[IntegrationProvider]:
        cls._providers[provider.slug] = provider
        return provider

    @classmethod
    def get(cls, slug: str) -> type[IntegrationProvider] | None:
        return cls._providers.get(slug)

    @classmethod
    def list_all(cls) -> list[dict]:
        return [
            {
                "slug": p.slug,
                "name": p.name,
                "description": p.description,
                "category": p.category,
                "icon": p.icon,
                "sync_strategy": p.sync_strategy,
                "capabilities": p.capabilities,
                "supported_events": p.supported_events,
            }
            for p in cls._providers.values()
        ]

    @classmethod
    def all_slugs(cls) -> list[str]:
        return list(cls._providers.keys())

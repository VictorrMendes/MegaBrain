"""Contract tests for storage-backed providers (engines with DB access).

Any engine that persists state to a database must pass this contract:
it must connect successfully, handle concurrent reads, and report health.

Example:
    class TestKnowledgeEngineStorage(BaseStorageProviderContract):
        @pytest.fixture
        async def provider(self, db_session_factory):
            return KnowledgeEngine(session_factory=db_session_factory)

        @pytest.fixture
        def workspace_id(self):
            return uuid4()
"""
from __future__ import annotations

from uuid import UUID

import pytest

from kernel.health import ComponentHealth, HealthStatus


class BaseStorageProviderContract:
    """Shared contract tests for DB-backed engines."""

    @pytest.fixture
    def provider(self):
        raise NotImplementedError(
            "Subclass must override the `provider` fixture."
        )

    @pytest.fixture
    def workspace_id(self) -> UUID:
        raise NotImplementedError(
            "Subclass must override the `workspace_id` fixture."
        )

    @pytest.mark.asyncio
    async def test_health_returns_component_health(self, provider) -> None:
        result = await provider.health()
        assert isinstance(result, ComponentHealth)
        assert isinstance(result.name, str)
        assert len(result.name) > 0
        assert result.status in HealthStatus

    @pytest.mark.asyncio
    async def test_health_ready_when_db_available(self, provider) -> None:
        result = await provider.health()
        assert result.status == HealthStatus.ready, (
            f"Expected ready but got {result.status}: {result.detail}"
        )

    @pytest.mark.asyncio
    async def test_health_reports_latency(self, provider) -> None:
        result = await provider.health()
        assert result.latency_ms is not None
        assert result.latency_ms >= 0

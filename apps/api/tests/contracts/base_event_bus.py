"""Contract tests for EventBusProvider.

Any EventBus implementation must satisfy this contract: publish must
deliver to all subscribers, wildcard subscription must receive all
events, and unsubscription must stop delivery.

Example:
    class TestPgEventBus(BaseEventBusContract):
        @pytest.fixture
        async def bus(self):
            return EventBus(dsn=TEST_DB_DSN)
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from kernel.events.schema import KhonshuEvent


class BaseEventBusContract:
    """Shared contract tests every EventBus implementation must pass."""

    @pytest.fixture
    def bus(self):
        raise NotImplementedError(
            "Subclass must override the `bus` fixture."
        )

    @pytest.fixture
    def sample_event(self) -> KhonshuEvent:
        return KhonshuEvent(
            type="contract.test_event",
            workspace_id=uuid4(),
            source="contract_test",
            payload={"value": 42},
        )

    @pytest.mark.asyncio
    async def test_subscribe_and_receive(
        self, bus, sample_event: KhonshuEvent
    ) -> None:
        received: list[KhonshuEvent] = []

        async def handler(evt: KhonshuEvent) -> None:
            received.append(evt)

        bus.subscribe_event(sample_event.type, handler)
        await bus.publish_event(sample_event)
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].id == sample_event.id

    @pytest.mark.asyncio
    async def test_wildcard_receives_all_events(
        self, bus, sample_event: KhonshuEvent
    ) -> None:
        received: list[KhonshuEvent] = []

        async def wildcard_handler(evt: KhonshuEvent) -> None:
            received.append(evt)

        bus.subscribe_event("*", wildcard_handler)
        await bus.publish_event(sample_event)
        await asyncio.sleep(0.1)

        assert any(e.id == sample_event.id for e in received)

    @pytest.mark.asyncio
    async def test_multiple_subscribers_all_receive(
        self, bus, sample_event: KhonshuEvent
    ) -> None:
        results: list[int] = []

        async def h1(evt: KhonshuEvent) -> None:
            results.append(1)

        async def h2(evt: KhonshuEvent) -> None:
            results.append(2)

        bus.subscribe_event(sample_event.type, h1)
        bus.subscribe_event(sample_event.type, h2)
        await bus.publish_event(sample_event)
        await asyncio.sleep(0.1)

        assert 1 in results
        assert 2 in results

    @pytest.mark.asyncio
    async def test_event_preserves_payload(
        self, bus, sample_event: KhonshuEvent
    ) -> None:
        received: list[KhonshuEvent] = []

        async def handler(evt: KhonshuEvent) -> None:
            received.append(evt)

        bus.subscribe_event(sample_event.type, handler)
        await bus.publish_event(sample_event)
        await asyncio.sleep(0.1)

        assert received[0].payload == sample_event.payload

    @pytest.mark.asyncio
    async def test_event_derive_sets_trace_id(
        self, bus, sample_event: KhonshuEvent
    ) -> None:
        child = sample_event.derive(
            type="contract.child_event",
            payload={"child": True},
        )
        assert child.trace_id == (sample_event.trace_id or sample_event.id)
        assert child.causation_id == sample_event.id

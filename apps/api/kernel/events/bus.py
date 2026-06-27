from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

import asyncpg

from kernel.config import settings
from kernel.logger import get_logger

from .schema import KhonshuEvent

logger = get_logger(__name__)

# Legacy dict-based handler (used by existing workers)
EventHandler = Callable[[dict], Any]
# Typed handler for new components
TypedEventHandler = Callable[[KhonshuEvent], Any]

# Domain events channel — business facts (see ADR-002)
_EVENTS_CHANNEL = "khonshu.events"
# Infrastructure events channel — technical state (see ADR-002)
_INFRA_CHANNEL = "khonshu.infra"


class EventBus:
    def __init__(self) -> None:
        self._conn: asyncpg.Connection | None = None
        # Legacy channel → list of dict handlers
        self._handlers: dict[str, list[EventHandler]] = {}
        # event.type → list of typed handlers (domain channel)
        self._typed_handlers: dict[str, list[TypedEventHandler]] = {}
        # event.type → list of typed handlers (infra channel)
        self._infra_handlers: dict[str, list[TypedEventHandler]] = {}

    async def connect(self) -> None:
        dsn = settings.database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        self._conn = await asyncpg.connect(dsn)

        for channel in self._handlers:
            await self._conn.add_listener(channel, self._dispatch_legacy)

        await self._conn.add_listener(_EVENTS_CHANNEL, self._dispatch_typed)
        await self._conn.add_listener(_INFRA_CHANNEL, self._dispatch_infra)

        logger.info(
            "event_bus.connected",
            legacy_channels=list(self._handlers.keys()),
            domain_channel=_EVENTS_CHANNEL,
            infra_channel=_INFRA_CHANNEL,
        )

    async def disconnect(self) -> None:
        if self._conn:
            for channel in self._handlers:
                try:
                    await self._conn.remove_listener(
                        channel, self._dispatch_legacy
                    )
                except Exception:
                    pass
            try:
                await self._conn.remove_listener(
                    _EVENTS_CHANNEL, self._dispatch_typed
                )
            except Exception:
                pass
            try:
                await self._conn.remove_listener(
                    _INFRA_CHANNEL, self._dispatch_infra
                )
            except Exception:
                pass
            await self._conn.close()
            self._conn = None
        logger.info("event_bus.disconnected")

    # ------------------------------------------------------------------ #
    # Legacy API — kept for existing workers                               #
    # ------------------------------------------------------------------ #

    def subscribe(self, channel: str, handler: EventHandler) -> None:
        is_new = channel not in self._handlers
        self._handlers.setdefault(channel, []).append(handler)
        if self._conn and is_new:
            asyncio.get_event_loop().create_task(
                self._conn.add_listener(channel, self._dispatch_legacy)
            )

    async def publish(self, channel: str, payload: dict) -> None:
        if not self._conn:
            logger.warning("EventBus not connected, skipping publish")
            return
        await self._conn.execute(
            "SELECT pg_notify($1, $2)", channel, json.dumps(payload)
        )
        logger.debug(
            "event_bus.published_legacy",
            channel=channel,
            type=payload.get("type"),
        )

    # ------------------------------------------------------------------ #
    # Typed API — for new Mission/Kernel/Scheduler components             #
    # ------------------------------------------------------------------ #

    def subscribe_event(
        self, event_type: str, handler: TypedEventHandler
    ) -> None:
        """Subscribe to a domain event. Domain engines use this only."""
        self._typed_handlers.setdefault(event_type, []).append(handler)

    async def publish_event(self, event: KhonshuEvent) -> None:
        """Publish a domain event on khonshu.events."""
        if not self._conn:
            logger.warning("EventBus not connected, skipping publish")
            return
        await self._conn.execute(
            "SELECT pg_notify($1, $2)",
            _EVENTS_CHANNEL,
            json.dumps(event.to_dict()),
        )
        logger.debug(
            "event_bus.published",
            event_type=event.type,
            correlation_id=str(event.correlation_id),
            source=event.source,
            priority=event.priority,
        )

    def subscribe_infra(
        self, event_type: str, handler: TypedEventHandler
    ) -> None:
        """Subscribe to an infrastructure event. Plugins and monitors use this."""
        self._infra_handlers.setdefault(event_type, []).append(handler)

    async def publish_infra_event(self, event: KhonshuEvent) -> None:
        """Publish an infrastructure event on khonshu.infra."""
        if not self._conn:
            logger.warning("EventBus not connected, skipping publish")
            return
        await self._conn.execute(
            "SELECT pg_notify($1, $2)",
            _INFRA_CHANNEL,
            json.dumps(event.to_dict()),
        )
        logger.debug(
            "event_bus.published_infra",
            event_type=event.type,
            source=event.source,
        )

    # ------------------------------------------------------------------ #
    # Internal dispatch                                                    #
    # ------------------------------------------------------------------ #

    async def _dispatch_legacy(
        self,
        conn: asyncpg.Connection,
        pid: int,
        channel: str,
        payload_str: str,
    ) -> None:
        try:
            payload = json.loads(payload_str)
        except Exception:
            logger.warning("event_bus.bad_payload", channel=channel)
            return
        for handler in self._handlers.get(channel, []):
            asyncio.create_task(self._safe_call(handler, payload))

    async def _dispatch_typed(
        self,
        conn: asyncpg.Connection,
        pid: int,
        channel: str,
        payload_str: str,
    ) -> None:
        try:
            data = json.loads(payload_str)
            event = KhonshuEvent.from_dict(data)
        except Exception as exc:
            logger.warning(
                "event_bus.bad_typed_payload",
                channel=channel,
                error=str(exc),
            )
            return
        # Dispatch a handlers registrados no tipo exato + wildcard "*"
        for handler in (
            self._typed_handlers.get(event.type, [])
            + self._typed_handlers.get("*", [])
        ):
            asyncio.create_task(self._safe_typed_call(handler, event))

    async def _safe_call(
        self, handler: EventHandler, payload: dict
    ) -> None:
        try:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:
            logger.error(
                "event_bus.handler_error",
                handler=getattr(handler, "__name__", repr(handler)),
                error=str(exc),
            )

    async def _dispatch_infra(
        self,
        conn: asyncpg.Connection,
        pid: int,
        channel: str,
        payload_str: str,
    ) -> None:
        try:
            data = json.loads(payload_str)
            event = KhonshuEvent.from_dict(data)
        except Exception as exc:
            logger.warning(
                "event_bus.bad_infra_payload",
                channel=channel,
                error=str(exc),
            )
            return
        for handler in self._infra_handlers.get(event.type, []):
            asyncio.create_task(self._safe_typed_call(handler, event))

    async def _safe_typed_call(
        self, handler: TypedEventHandler, event: KhonshuEvent
    ) -> None:
        try:
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:
            logger.error(
                "event_bus.typed_handler_error",
                event_type=event.type,
                handler=getattr(handler, "__name__", repr(handler)),
                error=str(exc),
            )


event_bus = EventBus()

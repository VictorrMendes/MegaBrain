import asyncio
import json
from typing import Callable, Any

import asyncpg

from kernel.config import settings
from kernel.logger import get_logger

logger = get_logger(__name__)

EventHandler = Callable[[dict], Any]


class EventBus:
    def __init__(self) -> None:
        self._conn: asyncpg.Connection | None = None
        self._handlers: dict[str, list[EventHandler]] = {}

    async def connect(self) -> None:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        self._conn = await asyncpg.connect(dsn)
        for channel in self._handlers:
            await self._conn.add_listener(channel, self._dispatch)
        logger.info("event_bus.connected", channels=list(self._handlers.keys()))

    async def disconnect(self) -> None:
        if self._conn:
            for channel in self._handlers:
                try:
                    await self._conn.remove_listener(channel, self._dispatch)
                except Exception:
                    pass
            await self._conn.close()
            self._conn = None
        logger.info("event_bus.disconnected")

    def subscribe(self, channel: str, handler: EventHandler) -> None:
        is_new_channel = channel not in self._handlers
        self._handlers.setdefault(channel, []).append(handler)
        if self._conn and is_new_channel:
            asyncio.get_event_loop().create_task(
                self._conn.add_listener(channel, self._dispatch)
            )

    async def publish(self, channel: str, payload: dict) -> None:
        if not self._conn:
            raise RuntimeError("EventBus not connected — call connect() first")
        await self._conn.execute(
            "SELECT pg_notify($1, $2)", channel, json.dumps(payload)
        )
        logger.debug("event_bus.published", channel=channel, type=payload.get("type"))

    async def _dispatch(
        self, conn: asyncpg.Connection, pid: int, channel: str, payload_str: str
    ) -> None:
        try:
            payload = json.loads(payload_str)
        except Exception:
            logger.warning("event_bus.bad_payload", channel=channel)
            return

        for handler in self._handlers.get(channel, []):
            asyncio.create_task(self._safe_call(handler, payload))

    async def _safe_call(self, handler: EventHandler, payload: dict) -> None:
        try:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error(
                "event_bus.handler_error", handler=handler.__name__, error=str(e)
            )


event_bus = EventBus()

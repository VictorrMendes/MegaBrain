import abc
import asyncio
from typing import AsyncGenerator
from schemas.events import TraceEvent

class TraceBroadcaster(abc.ABC):
    """Abstract interface for broadcasting trace events across workers."""

    @abc.abstractmethod
    def subscribe(self, workspace_id: str | None = None) -> asyncio.Queue[TraceEvent]:
        """Subscribe to trace events. Returns an async queue of TraceEvent objects.
        If workspace_id is provided, only events for that workspace are yielded.
        """
        pass

    @abc.abstractmethod
    def unsubscribe(self, q: asyncio.Queue[TraceEvent]) -> None:
        """Unsubscribe and cleanup the given queue."""
        pass

    @abc.abstractmethod
    def broadcast(self, event: TraceEvent) -> None:
        """Broadcast an event to all interested subscribers."""
        pass

    @abc.abstractmethod
    async def get_history(self, limit: int = 100, workspace_id: str | None = None) -> list[TraceEvent]:
        """Fetch the most recent trace events to populate initial dashboard state."""
        pass

class MemoryTraceBroadcaster(TraceBroadcaster):
    """In-memory trace broadcaster for single-process deployments."""

    def __init__(self, history_size: int = 200):
        self._queues: set[tuple[asyncio.Queue[TraceEvent], str | None]] = set()
        self._history: list[TraceEvent] = []
        self._history_size = history_size

    def subscribe(self, workspace_id: str | None = None) -> asyncio.Queue[TraceEvent]:
        q: asyncio.Queue[TraceEvent] = asyncio.Queue(maxsize=200)
        self._queues.add((q, workspace_id))
        return q

    def unsubscribe(self, q: asyncio.Queue[TraceEvent]) -> None:
        # Find and remove by queue reference
        to_remove = [entry for entry in self._queues if entry[0] is q]
        for entry in to_remove:
            self._queues.discard(entry)

    def broadcast(self, event: TraceEvent) -> None:
        # Append to history
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history.pop(0)

        # Broadcast to subscribers
        for q, sub_workspace_id in list(self._queues):
            if sub_workspace_id and sub_workspace_id != event.workspace_id:
                continue
            
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def get_history(self, limit: int = 100, workspace_id: str | None = None) -> list[TraceEvent]:
        events = self._history
        if workspace_id:
            events = [e for e in events if e.workspace_id == workspace_id]
        return events[-limit:]

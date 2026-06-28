import asyncio
import json
from typing import Any

class LogBroadcaster:
    def __init__(self):
        self.queues: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=100)
        self.queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.queues.discard(q)

    def broadcast(self, logger: Any, method_name: str, event_dict: dict) -> dict:
        if self.queues:
            try:
                # Copy the dict so we don't mutate the log stream, though we shouldn't anyway.
                msg = json.dumps(event_dict, default=str)
                for q in self.queues:
                    try:
                        q.put_nowait(msg)
                    except asyncio.QueueFull:
                        pass
            except Exception:
                pass
        return event_dict

log_broadcaster = LogBroadcaster()

from typing import Any, Callable, Dict, List
import logging
import asyncio

logger = logging.getLogger(__name__)

EventHandler = Callable[[str, Dict[str, Any]], None]

class EventBus:
    """A simple in-memory pub/sub event bus for integration events."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, event_name: str, handler: EventHandler):
        """Subscribe to a specific event (e.g., 'meeting.started')."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(handler)
        
    def publish(self, event_name: str, payload: Dict[str, Any]):
        """Publish an event asynchronously."""
        if event_name in self._subscribers:
            for handler in self._subscribers[event_name]:
                try:
                    # If it's an async handler, wrap it
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(event_name, payload))
                    else:
                        handler(event_name, payload)
                except Exception as e:
                    logger.error(f"Error handling event {event_name}: {e}")

# Global singleton
event_bus = EventBus()

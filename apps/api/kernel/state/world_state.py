from typing import Any, Dict
from uuid import UUID
from kernel.logger import get_logger

logger = get_logger(__name__)

class WorldState:
    """
    Manages the ephemeral state of the world for a specific workspace.
    Unlike Memory (which stores long-term facts in pgvector), WorldState stores
    current, real-time context (e.g., VPN status, active devices, current location,
    online providers).
    """
    
    def __init__(self):
        # MOCK IMPLEMENTATION (In-memory dict).
        # In a real environment, this would be Redis.
        self._states: Dict[str, Dict[str, Any]] = {}
        
    async def get_state(self, workspace_id: UUID) -> Dict[str, Any]:
        """Returns the current world state snapshot."""
        return self._states.get(str(workspace_id), {
            "environment": "production",
            "active_devices": ["notebook"],
            "network": "online",
            "current_location": "unknown",
            "active_providers": ["n8n", "rest"]
        })
        
    async def update_state(self, workspace_id: UUID, key: str, value: Any) -> None:
        """Updates a specific property of the world state."""
        wid = str(workspace_id)
        if wid not in self._states:
            self._states[wid] = {}
        self._states[wid][key] = value
        logger.debug("world_state.updated", workspace_id=wid, key=key, value=value)


world_state_store = WorldState()

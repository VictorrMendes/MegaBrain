from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

class IntegrationSnapshot(BaseModel):
    """A point-in-time state representation of a specific integration.
    Used by ContextBuilder to construct the LifeContext without making HTTP requests.
    """
    id: str                 # E.g., 'google_calendar_snapshot_123'
    provider: str           # E.g., 'google'
    category: str           # E.g., 'calendar'
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    health: str             # ok, degraded, down
    payload: Dict[str, Any] # E.g., {"next_meeting": "14:00", "meetings_today": 4}
    
    def is_valid(self) -> bool:
        """Check if the snapshot is still valid."""
        return datetime.now(timezone.utc) < self.expires_at

class RuntimeSnapshotBuilder:
    """Manages the collection of all valid IntegrationSnapshots to build the LifeContext."""
    
    _snapshots: Dict[str, IntegrationSnapshot] = {}

    @classmethod
    def update_snapshot(cls, snapshot: IntegrationSnapshot):
        cls._snapshots[snapshot.provider] = snapshot

    @classmethod
    def get_valid_snapshots(cls) -> list[IntegrationSnapshot]:
        return [s for s in cls._snapshots.values() if s.is_valid()]

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ConnectionHealth(BaseModel):
    """Granular health tracking for a specific integration account."""
    oauth_status: str = "ok"         # ok, expired, revoked
    api_status: str = "ok"           # ok, degraded, down
    rate_limit_percent: int = 0
    last_sync_at: Optional[datetime] = None
    webhook_status: str = "unknown"  # unknown, active, failing
    
    def is_healthy(self) -> bool:
        return self.oauth_status == "ok" and self.api_status == "ok" and self.rate_limit_percent < 100

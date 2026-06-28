from datetime import datetime
from pydantic import BaseModel, Field

class TraceEvent(BaseModel):
    """Structured event for a step in the Cognitive Orchestrator trace."""
    trace_id: str
    workspace_id: str
    timestamp: datetime
    engine: str
    stage: str
    status: str
    duration_ms: float = 0.0
    metadata: dict = Field(default_factory=dict)

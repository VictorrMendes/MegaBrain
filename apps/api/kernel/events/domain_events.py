from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class CloudEvent(BaseModel):
    """
    Standard Base CloudEvent for Domain Events.
    """
    specversion: str = "1.0"
    id: str
    source: str
    type: str
    datacontenttype: str = "application/json"
    time: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]

# ---------------------------------------------------------
# Execution Lifecycle Events
# ---------------------------------------------------------

class ExecutionStartedEvent(CloudEvent):
    type: str = "khonshu.execution.started"

class ExecutionProgressEvent(CloudEvent):
    type: str = "khonshu.execution.progress"

class ExecutionCompletedEvent(CloudEvent):
    type: str = "khonshu.execution.completed"
    
class ExecutionFailedEvent(CloudEvent):
    type: str = "khonshu.execution.failed"
    
class ExecutionCancelledEvent(CloudEvent):
    type: str = "khonshu.execution.cancelled"


# ---------------------------------------------------------
# Step & Middleware Events
# ---------------------------------------------------------

class StepStartedEvent(CloudEvent):
    type: str = "khonshu.step.started"

class StepCompletedEvent(CloudEvent):
    type: str = "khonshu.step.completed"

class ApprovalRequestedEvent(CloudEvent):
    type: str = "khonshu.approval.requested"

class ApprovalGrantedEvent(CloudEvent):
    type: str = "khonshu.approval.granted"
    
class ApprovalDeniedEvent(CloudEvent):
    type: str = "khonshu.approval.denied"


# ---------------------------------------------------------
# Plugin Lifecycle Events
# ---------------------------------------------------------

class CapabilityDiscoveredEvent(CloudEvent):
    type: str = "khonshu.plugin.capability_discovered"

class PluginInstalledEvent(CloudEvent):
    type: str = "khonshu.plugin.installed"

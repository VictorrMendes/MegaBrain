from abc import ABC, abstractmethod
from typing import Any, Dict
from models.execution import ExecutionStep

class MiddlewareContext:
    def __init__(self, step: ExecutionStep, workspace_id: str):
        self.step = step
        self.workspace_id = workspace_id
        self.metadata: Dict[str, Any] = {}


class ExecutionMiddleware(ABC):
    """
    Base class for Runtime Interceptors.
    """
    
    @abstractmethod
    async def process(self, context: MiddlewareContext) -> bool:
        """
        Processes the context.
        Returns True to allow the execution to continue to the next middleware or Dispatcher.
        Returns False to halt execution (e.g. Denied, Rate Limited).
        """
        pass


class ApprovalMiddleware(ExecutionMiddleware):
    
    async def process(self, context: MiddlewareContext) -> bool:
        """
        Separates Risk and Permission.
        If a Capability has RiskLevel.CRITICAL or requires manual Permission,
        it intercepts the execution and halts it until the user grants approval.
        """
        # from kernel.capabilities.discovery import capability_discovery
        # cap_def = capability_discovery.get(context.step.capability)
        
        # MOCK IMPLEMENTATION
        # If the capability is highly destructive, we'd pause and set status to WAITING_APPROVAL
        
        # context.step.status = StepStatus.WAITING_APPROVAL.value
        # return False
        
        return True


class AuditMiddleware(ExecutionMiddleware):
    
    async def process(self, context: MiddlewareContext) -> bool:
        """
        Logs every execution attempt to a centralized audit trail for observability.
        """
        # MOCK IMPLEMENTATION
        # print(f"AUDIT: Executing {context.step.capability} with payload {context.step.payload}")
        return True


class RateLimitMiddleware(ExecutionMiddleware):
    
    async def process(self, context: MiddlewareContext) -> bool:
        """
        Checks quota limits (e.g., number of emails per hour, API budget).
        Halts execution if limits are exceeded.
        """
        # MOCK IMPLEMENTATION
        return True

approval_middleware = ApprovalMiddleware()
audit_middleware = AuditMiddleware()
rate_limit_middleware = RateLimitMiddleware()

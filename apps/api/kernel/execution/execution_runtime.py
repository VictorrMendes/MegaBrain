from typing import Any, Dict
from models.execution import Execution, ExecutionStatus, ExecutionStep, StepStatus
from kernel.execution.middlewares import (
    MiddlewareContext, 
    approval_middleware, 
    audit_middleware, 
    rate_limit_middleware
)
from kernel.logger import get_logger
from kernel.execution.scheduler import scheduler

class ExecutionRuntime:
    """
    The heart of the Cognitive Kernel.
    Manages state transitions of Executions and routes Nodes through the middleware chain
    before handing them off to the Scheduler.
    """
    
    def __init__(self):
        self.middlewares = [
            approval_middleware,
            rate_limit_middleware,
            audit_middleware
        ]

    async def execute_node(self, node: ExecutionStep, workspace_id: str) -> None:
        """
        Executes a single node in the Execution Graph.
        """
        context = MiddlewareContext(step=node, workspace_id=workspace_id)
        
        # Pass through Middlewares
        for middleware in self.middlewares:
            passed = await middleware.process(context)
            if not passed:
                return
                
        # Hand off to Scheduler (which handles timing, retries, then Dispatcher)
        await scheduler.schedule(node, workspace_id)


execution_runtime = ExecutionRuntime()

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
from kernel.orchestrator.parameter_resolver import parameter_resolver

logger = get_logger(__name__)

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
        
        # Sprint 2: The Art of Stopping
        missing_params = parameter_resolver.resolve(node.capability, node.payload)
        if missing_params:
            logger.info("execution_runtime.suspending_for_input", capability=node.capability, missing=[p.name for p in missing_params])
            node.status = StepStatus.WAITING_INPUT.value
            # We temporarily attach the missing parameters to the node so the caller can persist the Interaction
            node._missing_parameters = missing_params
            return

        context = MiddlewareContext(step=node, workspace_id=workspace_id)
        
        # Pass through Middlewares
        for middleware in self.middlewares:
            passed = await middleware.process(context)
            if not passed:
                return
                
        # Hand off to Scheduler (which handles timing, retries, then Dispatcher)
        await scheduler.schedule(node, workspace_id)


execution_runtime = ExecutionRuntime()

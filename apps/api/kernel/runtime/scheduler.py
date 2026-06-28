from typing import Any
from models.execution import ExecutionNode, StepStatus
from kernel.logger import get_logger
from kernel.runtime.dispatcher import dispatcher

logger = get_logger(__name__)

class Scheduler:
    """
    Manages timing, retries, and asynchronous transitions.
    Sits between the Runtime (which computes state) and Dispatcher (which executes).
    """
    
    async def schedule(self, node: ExecutionNode, workspace_id: str) -> None:
        """
        Determines when and how to dispatch a node.
        If a node is WAITING, it might put it in PAUSED state.
        If a node is READY, it moves it to RUNNING and dispatches.
        """
        logger.info("scheduler.processing", node_id=node.id, status=node.status.value)
        
        if node.status == StepStatus.READY:
            node.status = StepStatus.RUNNING
            # Transition to RUNNING and hand off to dispatcher immediately
            await dispatcher.dispatch(node, workspace_id)
            
        elif node.status == StepStatus.WAITING:
            # E.g. waiting for a webhook or approval
            node.status = StepStatus.PAUSED
            logger.info("scheduler.paused", node_id=node.id, reason="waiting for event")
            
        elif node.status == StepStatus.RETRYING:
            # E.g. apply exponential backoff before dispatching again
            logger.info("scheduler.backoff", node_id=node.id, attempt=node.retry_count)
            # await asyncio.sleep(backoff_time)
            node.status = StepStatus.RUNNING
            await dispatcher.dispatch(node, workspace_id)
            
        else:
            logger.warning("scheduler.ignored", node_id=node.id, status=node.status.value)

scheduler = Scheduler()

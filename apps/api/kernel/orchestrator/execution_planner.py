import json
from pydantic import BaseModel
from typing import Any
from kernel.logger import get_logger
from kernel.capabilities.models import ApprovalLevel

logger = get_logger(__name__)

from typing import Any, List
from kernel.logger import get_logger
from kernel.orchestrator.ir_compiler import ExecutionIR, IRSequenceNode, IRTaskNode

logger = get_logger(__name__)

class ExecutionPlanner:
    """
    Transforms strategy tasks into an ExecutionIR.
    This IR is then compiled into a state-based Execution DAG by the runtime compiler.
    """
    
    async def generate_plan(self, strategy_tasks: List[Any], context: dict[str, Any]) -> ExecutionIR:
        """
        Takes abstract tasks from the StrategyPlanner and turns them into a technical IR.
        """
        logger.info("execution_planner.generating_ir", tasks_count=len(strategy_tasks))
        
        # MOCK IMPLEMENTATION
        # For now, we just chain the tasks in a simple SEQUENCE node.
        # In the future, LLM translates abstract tasks into PARALLEL, WAIT, etc.
        
        nodes = []
        for task in strategy_tasks:
            desc = task.description.lower()
            if "calendar" in desc or "agenda" in desc:
                capability = "calendar.list_events"
            elif "search" in desc:
                capability = "knowledge.search"
            else:
                capability = "knowledge.search"
                
            nodes.append(
                IRTaskNode(
                    id=f"ir_{task.id}",
                    capability=capability,
                    payload={"query": task.description, "date": "today"}
                )
            )
            
        root_node = IRSequenceNode(
            id="root_sequence",
            nodes=nodes
        )
            
        return ExecutionIR(root=root_node)

execution_planner = ExecutionPlanner()

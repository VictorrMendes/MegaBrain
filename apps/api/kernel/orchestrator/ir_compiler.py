from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# Execution IR (Intermediate Representation) Models
# ---------------------------------------------------------

class IRNode(BaseModel):
    id: str
    type: str # "TASK", "PARALLEL", "CONDITIONAL", "WAIT_EVENT", "SEQUENCE"

class IRTaskNode(IRNode):
    type: str = "TASK"
    capability: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    retry_policy: Dict[str, Any] = Field(default_factory=dict)

class IRParallelNode(IRNode):
    type: str = "PARALLEL"
    branches: List[List[IRNode]] = Field(default_factory=list)

class IRSequenceNode(IRNode):
    type: str = "SEQUENCE"
    nodes: List[IRNode] = Field(default_factory=list)

class IRConditionalNode(IRNode):
    type: str = "CONDITIONAL"
    condition: str
    true_branch: List[IRNode] = Field(default_factory=list)
    false_branch: List[IRNode] = Field(default_factory=list)

class IRWaitEventNode(IRNode):
    type: str = "WAIT_EVENT"
    event_name: str
    timeout_seconds: int

class ExecutionIR(BaseModel):
    root: IRNode


# ---------------------------------------------------------
# Compiler
# ---------------------------------------------------------

from models.execution import ExecutionStep

class IRCompiler:
    """
    Translates the ExecutionIR (LLVM-like intermediate representation)
    into a flat list of execution steps (the DAG) that the Runtime engine understands.
    """
    
    def compile(self, ir: ExecutionIR, execution_id: str) -> List[ExecutionStep]:
        steps = []
        self._traverse(ir.root, execution_id, steps, [])
        return steps
        
    def _traverse(self, node: IRNode, execution_id: str, steps: List[ExecutionStep], dependencies: List[str]) -> List[str]:
        """
        Traverses the IR tree and flattens it into ExecutionStep ORM models.
        Returns the list of step IDs that constitute the 'tail' of this node 
        (i.e., what subsequent nodes should depend on).
        """
        if node.type == "TASK":
            task = node # type: IRTaskNode
            step = ExecutionStep(
                execution_id=execution_id,
                capability=task.capability,
                payload=task.payload,
                retry_policy=task.retry_policy,
                depends_on=list(dependencies)
            )
            steps.append(step)
            return [str(step.id)]
            
        elif node.type == "SEQUENCE":
            seq = node # type: IRSequenceNode
            current_deps = list(dependencies)
            for sub_node in seq.nodes:
                current_deps = self._traverse(sub_node, execution_id, steps, current_deps)
            return current_deps
            
        elif node.type == "PARALLEL":
            par = node # type: IRParallelNode
            tail_deps = []
            for branch in par.branches:
                # Branches run in parallel, all starting with the current dependencies
                current_deps = list(dependencies)
                for sub_node in branch:
                    current_deps = self._traverse(sub_node, execution_id, steps, current_deps)
                tail_deps.extend(current_deps)
            return tail_deps
            
        # Simplified implementations for CONDITIONAL and WAIT_EVENT can be added.
        # For a full runtime, CONDITIONAL would evaluate variables from state.
        return dependencies

ir_compiler = IRCompiler()

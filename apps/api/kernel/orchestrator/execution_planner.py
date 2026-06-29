import json
from pydantic import BaseModel
from typing import Any, List
from kernel.logger import get_logger
from kernel.capabilities.models import ApprovalLevel
from kernel.orchestrator.ir_compiler import ExecutionIR, IRSequenceNode, IRTaskNode
from kernel.plugins.plugin_manager import plugin_manager
from kernel.providers.base import LLMProvider, ChatMessage

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
        
        llm: LLMProvider | None = context.get("llm")
        if not llm:
            logger.warning("execution_planner.no_llm_fallback")
            return self._fallback(strategy_tasks)

        # Collect capabilities
        if not plugin_manager.plugins:
            plugin_manager.load_all()
            
        caps = []
        for plugin in plugin_manager.plugins.values():
            for cap_name, cap_data in plugin.get("loaded_capabilities", {}).items():
                caps.append({
                    "name": cap_name,
                    "description": cap_data.get("description", ""),
                    "schema": cap_data.get("schema", {})
                })

        tasks_json = json.dumps([{"id": t.id, "description": t.description} for t in strategy_tasks])
        caps_json = json.dumps(caps)

        system_prompt = f'''You are the Execution Planner.
Map the following abstract tasks to the best available capabilities.
For each task, select exactly ONE capability name from the available capabilities, and generate the required JSON payload according to its schema.
If no capability matches, map it to "knowledge.search".

Available Capabilities:
{caps_json}

Tasks:
{tasks_json}

Output ONLY valid JSON matching this schema:
{{
  "nodes": [
    {{
      "id": "ir_task_1",
      "capability": "n8n.communication.send_email",
      "payload": {{"subject": "hello", "body": "world"}}
    }}
  ]
}}'''

        try:
            result = await llm.chat([
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content="Generate IR")
            ])
            
            content = result.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
                
            data = json.loads(content)
            nodes = []
            for n in data.get("nodes", []):
                nodes.append(
                    IRTaskNode(
                        id=n.get("id", "ir_unknown"),
                        capability=n.get("capability", "knowledge.search"),
                        payload=n.get("payload", {})
                    )
                )
                
            logger.info("execution_planner.success", num_nodes=len(nodes))
            root_node = IRSequenceNode(id="root_sequence", nodes=nodes)
            return ExecutionIR(root=root_node)
            
        except Exception as e:
            logger.error("execution_planner.failed", error=str(e))
            return self._fallback(strategy_tasks)

    def _fallback(self, strategy_tasks: List[Any]) -> ExecutionIR:
        nodes = []
        for task in strategy_tasks:
            desc = task.description.lower()
            if "calendar" in desc or "agenda" in desc:
                capability = "n8n.calendar.list_events"
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

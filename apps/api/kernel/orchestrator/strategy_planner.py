import json
from dataclasses import dataclass, field
from typing import List, Dict, Any
from kernel.logger import get_logger
from kernel.providers.base import LLMProvider, ChatMessage

logger = get_logger(__name__)

@dataclass
class AbstractTask:
    id: str
    description: str
    dependencies: List[str] = field(default_factory=list)


@dataclass
class StrategyPlan:
    goal: str
    tasks: List[AbstractTask]


class StrategyPlanner:
    """
    Translates a high-level Goal into abstract Tasks.
    This operates one level above the Execution Planner, determining WHAT needs to be done.
    """

    async def generate_strategy(self, goal: str, context: Dict[str, Any]) -> StrategyPlan:
        llm: LLMProvider | None = context.get("llm")
        if not llm:
            logger.warning("strategy_planner.no_llm_fallback")
            return StrategyPlan(goal=goal, tasks=[AbstractTask(id="task_1", description=goal)])

        from kernel.plugins.plugin_manager import plugin_manager
        if not plugin_manager.plugins:
            plugin_manager.load_all()
            
        caps_list = []
        for plugin in plugin_manager.plugins.values():
            for cap_name, cap_data in plugin.get("loaded_capabilities", {}).items():
                desc = cap_data.get("description", "")
                caps_list.append(f"  - \\"{cap_name}\\": {desc}")
                
        caps_str = "\\n".join(caps_list)

        system_prompt = f'''You are the Strategy Planner. 
Break the following user goal into discrete abstract tasks.
Output ONLY valid JSON matching this schema:
{{
  "tasks": [
    {{
      "id": "task_1",
      "description": "Clear description of the action",
      "dependencies": []
    }}
  ]
}}
IMPORTANT: Do not invent tools. Map the goal to the available capabilities.
Available Capabilities:
{caps_str}'''
        
        try:
            result = await llm.chat([
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Goal: {goal}")
            ])
            
            content = result.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
                
            data = json.loads(content)
            tasks = []
            for t in data.get("tasks", []):
                tasks.append(AbstractTask(
                    id=t.get("id", "task_unknown"),
                    description=t.get("description", "Unknown task"),
                    dependencies=t.get("dependencies", [])
                ))
                
            logger.info("strategy_planner.success", num_tasks=len(tasks), raw_content=content)
            return StrategyPlan(goal=goal, tasks=tasks)
            
        except Exception as e:
            logger.error("strategy_planner.failed", error=str(e))
            # Fallback to single generic task
            return StrategyPlan(goal=goal, tasks=[AbstractTask(id="task_1", description=goal)])

strategy_planner = StrategyPlanner()

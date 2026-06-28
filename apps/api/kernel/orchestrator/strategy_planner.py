from dataclasses import dataclass, field
from typing import List, Dict, Any

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
        # Mocking the LLM translation of a goal to tasks
        # e.g., "Organize minha mudança" -> [Pesquisar imóveis, Pesquisar caminhão, etc]
        return StrategyPlan(
            goal=goal,
            tasks=[
                AbstractTask(id="task_1", description="Understand the goal"),
                AbstractTask(id="task_2", description="Execute steps for the goal", dependencies=["task_1"]),
            ]
        )

strategy_planner = StrategyPlanner()

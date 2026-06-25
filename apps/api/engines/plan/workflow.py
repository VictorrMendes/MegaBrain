from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kernel.logger import get_logger
from models.mission import MissionStep, StepStatus, StepType

from .provider import PlanProviderError

if TYPE_CHECKING:
    from models.mission import Mission

logger = get_logger(__name__)


class WorkflowTemplate:
    """A named, reusable plan template defined as structured data.

    Steps are Pydantic-validated internally; the template is stored
    in the workflow registry and referenced by name.
    """

    def __init__(self, name: str, steps: list[dict[str, Any]]) -> None:
        self.name = name
        self._steps = self._validate(steps)

    def _validate(
        self, steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        validated = []
        for i, step in enumerate(steps):
            if "tool" not in step:
                raise ValueError(
                    f"Workflow '{self.name}' step {i} missing 'tool'"
                )
            validated.append({
                "tool": str(step["tool"]),
                "input": step.get("input", {}),
                "type": step.get("type", "tool"),
            })
        return validated

    def to_steps(self, mission_id: Any) -> list[MissionStep]:
        return [
            MissionStep(
                mission_id=mission_id,
                order=i,
                type=StepType(s["type"]),
                tool=s["tool"],
                input=s["input"],
                status=StepStatus.PENDING,
            )
            for i, s in enumerate(self._steps)
        ]


class WorkflowRegistry:
    """Holds all registered workflow templates."""

    def __init__(self) -> None:
        self._templates: dict[str, WorkflowTemplate] = {}

    def register(self, template: WorkflowTemplate) -> None:
        self._templates[template.name] = template
        logger.info("workflow.registered", name=template.name)

    def get(self, name: str) -> WorkflowTemplate | None:
        return self._templates.get(name)

    def list(self) -> list[str]:
        return list(self._templates.keys())


workflow_registry = WorkflowRegistry()


class WorkflowPlanProvider:
    """Generates an execution plan from a named workflow template.

    The mission intent must match a registered workflow name, or the
    context must specify one via mission.context.metadata["workflow"].
    """

    name = "workflow"

    async def create_execution_plan(
        self, mission: Mission
    ) -> list[MissionStep]:
        # Prefer explicit workflow name from context metadata
        workflow_name: str | None = None
        if mission.context and mission.context.metadata_:
            workflow_name = mission.context.metadata_.get("workflow")

        # Fallback: treat intent as workflow name
        if not workflow_name:
            workflow_name = mission.intent.strip()

        template = workflow_registry.get(workflow_name)
        if template is None:
            raise PlanProviderError(
                f"No workflow template named '{workflow_name}'"
            )

        steps = template.to_steps(mission.id)
        logger.info(
            "workflow_plan_provider.plan_created",
            mission_id=str(mission.id),
            workflow=workflow_name,
            steps=len(steps),
        )
        return steps

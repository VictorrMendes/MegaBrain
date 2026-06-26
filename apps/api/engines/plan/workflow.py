from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from kernel.logger import get_logger
from models.mission import MissionStep, StepStatus, StepType

from .provider import PlanProviderError

if TYPE_CHECKING:
    from models.mission import Mission

logger = get_logger(__name__)

# Resolve {{ variavel }} em strings e dentro de estruturas JSON
_TEMPLATE_VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _resolve(value: Any, context: dict) -> Any:
    """Substitui {{ variavel }} em qualquer string ou estrutura aninhada."""
    if isinstance(value, str):
        def replace(match: re.Match) -> str:
            return str(context.get(match.group(1), match.group(0)))
        return _TEMPLATE_VAR.sub(replace, value)
    if isinstance(value, dict):
        return {k: _resolve(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(item, context) for item in value]
    return value


class WorkflowTemplate:
    """Template de plano reutilizável definido como dado estruturado.

    Suporta variáveis {{ nome }} no campo `input` de cada step.
    As variáveis são resolvidas a partir do contexto da missão no
    momento em que o plano é criado. Exemplo:

        steps:
          - tool: ntfy.send
            input:
              title: "Relatório de {{ date }}"
              message: "{{ summary }}"

    Variáveis não encontradas no contexto são preservadas como estão.
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

    def to_steps(
        self,
        mission_id: Any,
        context: dict | None = None,
    ) -> list[MissionStep]:
        """Gera steps resolvendo variáveis {{ }} com o contexto fornecido."""
        ctx = context or {}
        return [
            MissionStep(
                mission_id=mission_id,
                order=i,
                type=StepType(s["type"]),
                tool=_resolve(s["tool"], ctx),
                input=_resolve(s["input"], ctx),
                status=StepStatus.PENDING,
            )
            for i, s in enumerate(self._steps)
        ]

    @classmethod
    def from_yaml(cls, name: str, yaml_content: str) -> WorkflowTemplate:
        """Carrega um WorkflowTemplate a partir de YAML."""
        try:
            import yaml  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "PyYAML não está instalado. "
                "Adicione 'pyyaml' às dependências."
            ) from exc
        data = yaml.safe_load(yaml_content)
        steps = data.get("steps", [])
        return cls(name=name, steps=steps)

    def to_dict(self) -> dict:
        return {"name": self.name, "steps": self._steps}

    def __repr__(self) -> str:
        return (
            f"WorkflowTemplate(name={self.name!r}, "
            f"steps={len(self._steps)})"
        )


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

        # Mescla workspace_config + metadata_ como contexto de resolução
        context: dict = {}
        if mission.context:
            context.update(mission.context.workspace_config or {})
            context.update(mission.context.metadata_ or {})

        steps = template.to_steps(mission.id, context=context)
        logger.info(
            "workflow_plan_provider.plan_created",
            mission_id=str(mission.id),
            workflow=workflow_name,
            steps=len(steps),
        )
        return steps

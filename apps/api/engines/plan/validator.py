from __future__ import annotations

from dataclasses import dataclass, field

from kernel.capabilities.registry import CapabilityRegistry
from kernel.logger import get_logger
from models.mission import Mission, MissionStep

logger = get_logger(__name__)


@dataclass
class ValidationError:
    code: str
    message: str
    step_index: int | None = None   # None = plan-level error
    detail: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    def to_dict(self) -> list[dict]:
        return [
            {
                "code": e.code,
                "message": e.message,
                "step_index": e.step_index,
                "detail": e.detail,
                "fatal": True,
            }
            for e in self.errors
        ] + [
            {
                "code": e.code,
                "message": e.message,
                "step_index": e.step_index,
                "detail": e.detail,
                "fatal": False,
            }
            for e in self.warnings
        ]


class PlanValidator:
    """Validates an execution plan before it is stored or submitted for
    human approval.

    Checks:
    - All tool names resolve in the CapabilityRegistry.
    - The capability's required permissions are present.
    - Required parameters are provided.
    - required_context keys are available in the mission context.
    - The plan is not empty.

    See ADR-006 for the full rationale.
    """

    MAX_STEPS = 50

    def validate(
        self,
        steps: list[MissionStep],
        mission: Mission,
        registry: CapabilityRegistry,
        workspace_permissions: set[str] | None = None,
        available_context_keys: set[str] | None = None,
    ) -> ValidationResult:
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        if not steps:
            errors.append(ValidationError(
                code="empty_plan",
                message="The plan contains no steps.",
            ))
            return ValidationResult(valid=False, errors=errors)

        if len(steps) > self.MAX_STEPS:
            warnings.append(ValidationError(
                code="plan_too_long",
                message=(
                    f"Plan has {len(steps)} steps "
                    f"(max recommended: {self.MAX_STEPS})."
                ),
            ))

        perms = workspace_permissions or set()
        ctx_keys = available_context_keys or set()

        for i, step in enumerate(steps):
            tool = registry.get_tool(step.tool)

            if tool is None:
                errors.append(ValidationError(
                    code="tool_not_found",
                    message=f"Tool '{step.tool}' is not registered.",
                    step_index=i,
                    detail={"tool": step.tool},
                ))
                continue

            # Find the capability that owns this tool
            capability = None
            for cap in registry.list():
                if step.tool in cap.tools:
                    capability = cap
                    break

            if capability is not None:
                # Permission check
                for perm in capability.permissions:
                    if perm not in perms:
                        errors.append(ValidationError(
                            code="permission_denied",
                            message=(
                                f"Tool '{step.tool}' requires permission "
                                f"'{perm}' which the workspace does not hold."
                            ),
                            step_index=i,
                            detail={"tool": step.tool, "permission": perm},
                        ))

                # Required context check
                for ctx_key in capability.required_context:
                    if ctx_key not in ctx_keys:
                        errors.append(ValidationError(
                            code="missing_context",
                            message=(
                                f"Tool '{step.tool}' requires context key "
                                f"'{ctx_key}' which is not available."
                            ),
                            step_index=i,
                            detail={
                                "tool": step.tool,
                                "context_key": ctx_key,
                            },
                        ))

            # Required parameter check — parameters in the tool schema
            # marked as required must be present in step.input
            required_params = _required_params(tool.parameters)
            for param in required_params:
                if param not in (step.input or {}):
                    errors.append(ValidationError(
                        code="missing_required_parameter",
                        message=(
                            f"Tool '{step.tool}' requires parameter "
                            f"'{param}' but it is not in the step input."
                        ),
                        step_index=i,
                        detail={"tool": step.tool, "parameter": param},
                    ))

        valid = len(errors) == 0
        result = ValidationResult(valid=valid, errors=errors, warnings=warnings)

        logger.info(
            "plan.validated",
            mission_id=str(mission.id),
            steps=len(steps),
            valid=valid,
            error_count=len(errors),
            warning_count=len(warnings),
        )
        return result


def _required_params(parameters: dict) -> list[str]:
    """Extract required parameter names from a JSON Schema dict."""
    if not parameters:
        return []
    return parameters.get("required", [])

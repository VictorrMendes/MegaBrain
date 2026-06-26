from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from kernel.logger import get_logger

logger = get_logger(__name__)


class PolicyEffect(StrEnum):
    allow = "allow"
    require_confirmation = "require_confirmation"
    deny = "deny"


@dataclass
class PolicyRule:
    """Declarative policy rule for capability/tool execution.

    Wildcard matching: None means "applies to everything".
    Examples:
        PolicyRule("no-delete-all", PolicyEffect.deny, tool="fs.delete_all")
        PolicyRule("confirm-deploy", PolicyEffect.require_confirmation, capability="docker")
    """

    name: str
    effect: PolicyEffect
    capability: str | None = None  # None = any capability
    tool: str | None = None        # None = any tool in matched capability
    reason: str = ""


class PolicyEngine:
    """Evaluates declarative policy rules against capability/tool pairs.

    Rule precedence (most restrictive wins):
        deny > require_confirmation > allow

    Rules are evaluated in order; first deny found short-circuits.
    require_confirmation is accumulated — the first deny still wins.
    """

    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self._rules: list[PolicyRule] = list(rules or [])

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)
        logger.info(
            "policy.rule_added",
            name=rule.name,
            effect=rule.effect.value,
            capability=rule.capability,
            tool=rule.tool,
        )

    def remove_rule(self, name: str) -> None:
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.name != name]
        if len(self._rules) < before:
            logger.info("policy.rule_removed", name=name)

    def evaluate(self, capability: str, tool: str) -> PolicyEffect:
        """Returns the most restrictive PolicyEffect that matches."""
        result = PolicyEffect.allow

        for rule in self._rules:
            cap_match = rule.capability is None or rule.capability == capability
            tool_match = rule.tool is None or rule.tool == tool
            if not (cap_match and tool_match):
                continue

            if rule.effect == PolicyEffect.deny:
                logger.info(
                    "policy.denied",
                    capability=capability,
                    tool=tool,
                    rule=rule.name,
                    reason=rule.reason,
                )
                return PolicyEffect.deny

            if rule.effect == PolicyEffect.require_confirmation:
                result = PolicyEffect.require_confirmation

        return result

    def requires_confirmation(self, capability: str, tool: str) -> bool:
        return self.evaluate(capability, tool) == PolicyEffect.require_confirmation

    def is_denied(self, capability: str, tool: str) -> bool:
        return self.evaluate(capability, tool) == PolicyEffect.deny

    def list_rules(self) -> list[PolicyRule]:
        return list(self._rules)


# Global singleton — importado pelo StepExecutor e pelo PlanValidator
policy_engine = PolicyEngine()

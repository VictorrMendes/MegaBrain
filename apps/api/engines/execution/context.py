from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class StepResult:
    """Resultado imutável da execução de um MissionStep."""

    success: bool
    output: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class ExecutionContext:
    """Estado vivo de uma missão em execução.

    Distinto de MissionContext (entidade de banco que guarda a configuração
    inicial). O ExecutionContext acumula os outputs dos steps durante a
    execução e é o canal pelo qual steps recebem outputs de steps anteriores.

    Nunca acessa o banco diretamente. Todos os dados necessários são
    injetados na construção pelo MissionEngine.
    """

    mission_id: UUID
    workspace_id: UUID
    intent: str
    execution_plan_id: UUID | None = None

    # Outputs acumulados durante execução.
    # Chave: "step_{order}" → valor: output dict do step.
    # Exemplo: context.variables["step_0"]["report_url"]
    variables: dict[str, Any] = field(default_factory=dict)

    # Artifacts criados durante a missão.
    # Cada entrada: {"uri", "type", "name", "step_id"}
    artifacts: list[dict] = field(default_factory=list)

    # Permissões do workspace (cópia em memória para o Executor)
    permissions: set[str] = field(default_factory=set)

    # Configuração do workspace (para resolução de variáveis {{ }})
    workspace_config: dict = field(default_factory=dict)

    # Metadata inicial da missão
    metadata: dict = field(default_factory=dict)

    # Correlação de eventos para todo a cadeia causal desta missão
    correlation_id: UUID | None = None

    def step_output(self, order: int) -> dict:
        """Retorna o output do step de determinada ordem, ou {} se ausente."""
        return self.variables.get(f"step_{order}", {})

    def record_output(self, order: int, output: dict) -> None:
        self.variables[f"step_{order}"] = output

    def record_artifact(
        self,
        uri: str,
        artifact_type: str,
        name: str,
        step_id: UUID | None = None,
    ) -> None:
        self.artifacts.append(
            {"uri": uri, "type": artifact_type, "name": name, "step_id": step_id}
        )

    def as_resolve_context(self) -> dict:
        """Contexto flat para resolução de variáveis {{ }} no input dos steps.

        Expõe workspace_config, metadata, e cada step output pelo seu índice.
        """
        ctx: dict[str, Any] = {}
        ctx.update(self.workspace_config)
        ctx.update(self.metadata)
        for key, value in self.variables.items():
            ctx[key] = value
        return ctx

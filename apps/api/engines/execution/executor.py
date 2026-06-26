from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from engines.execution.context import ExecutionContext, StepResult
from kernel.capabilities import capability_registry
from kernel.events import DomainEventType
from kernel.logger import get_logger
from models.mission import MissionStep, StepStatus

logger = get_logger(__name__)

# Callable que publica um evento de domínio.
# Assinatura: (event_type: str, payload: dict) -> Awaitable[None]
PublishFn = Callable[[str, dict], Awaitable[None]]

# Regex para resolução de variáveis {{ nome }} no input dos steps
_VAR_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def _resolve(value: Any, context: dict) -> Any:
    """Substitui {{ chave }} recursivamente em strings, dicts e listas.

    Suporta acesso aninhado com ponto: {{ step_0.url }}.
    """
    if isinstance(value, str):
        def _replace(match: re.Match) -> str:
            key_path = match.group(1).split(".")
            current: Any = context
            for key in key_path:
                if isinstance(current, dict):
                    current = current.get(key, match.group(0))
                else:
                    return match.group(0)
            return str(current)
        return _VAR_RE.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _resolve(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(item, context) for item in value]
    return value


class StepExecutor:
    """Executa um MissionStep dentro de um ExecutionContext.

    Responsabilidades:
    - Resolução de variáveis {{ }} no input do step a partir do contexto.
    - Lookup da tool no CapabilityRegistry.
    - Execução da tool.
    - Atualização do status do step no banco (RUNNING → SUCCEEDED | FAILED).
    - Publicação de eventos STEP_STARTED, STEP_COMPLETED, STEP_FAILED.
    - Retorno de StepResult para o chamador (MissionEngine) decidir o próximo passo.

    O StepExecutor não toma decisões sobre o fluxo da missão (retry, abort, skip).
    Essas decisões pertencem ao MissionEngine que interpreta o StepResult.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._sessions = session_factory

    async def run(
        self,
        step: MissionStep,
        context: ExecutionContext,
        publish_fn: PublishFn | None = None,
    ) -> StepResult:
        """Executa o step e retorna o resultado.

        O chamador é responsável por decidir o que fazer em caso de falha
        (StepResult.success == False) baseado na failure_policy do step.
        """
        step_key = f"step_{step.order}"

        await self._set_running(step)

        if publish_fn:
            await _safe_publish(
                publish_fn,
                DomainEventType.MISSION_STEP_STARTED,
                {"step_id": str(step.id), "tool": step.tool, "order": step.order},
            )

        # Resolve variáveis {{ }} no input do step a partir do contexto acumulado
        resolve_ctx = context.as_resolve_context()
        resolved_input: dict = _resolve(step.input or {}, resolve_ctx)

        logger.info(
            "step.executing",
            step_id=str(step.id),
            tool=step.tool,
            order=step.order,
            mission_id=str(context.mission_id),
        )

        tool = capability_registry.get_tool(step.tool)
        if tool is None:
            error = f"Tool '{step.tool}' not registered in CapabilityRegistry"
            await self._set_failed(step, error)
            if publish_fn:
                await _safe_publish(
                    publish_fn,
                    DomainEventType.MISSION_STEP_FAILED,
                    {"step_id": str(step.id), "tool": step.tool, "error": error},
                )
            logger.warning("step.tool_not_found", step_id=str(step.id), tool=step.tool)
            return StepResult(success=False, error=error)

        try:
            raw = await tool.fn(**resolved_input)
            output = raw if isinstance(raw, dict) else {"result": raw}
        except Exception as exc:
            error = str(exc)
            await self._set_failed(step, error)
            if publish_fn:
                await _safe_publish(
                    publish_fn,
                    DomainEventType.MISSION_STEP_FAILED,
                    {"step_id": str(step.id), "tool": step.tool, "error": error},
                )
            logger.warning(
                "step.execution_failed",
                step_id=str(step.id),
                tool=step.tool,
                error=error,
            )
            return StepResult(success=False, error=error)

        await self._set_succeeded(step, output)

        if publish_fn:
            await _safe_publish(
                publish_fn,
                DomainEventType.MISSION_STEP_COMPLETED,
                {"step_id": str(step.id), "tool": step.tool, "order": step.order},
            )

        logger.info(
            "step.completed",
            step_id=str(step.id),
            tool=step.tool,
            key=step_key,
        )
        return StepResult(success=True, output=output)

    # ------------------------------------------------------------------ #
    # DB helpers                                                           #
    # ------------------------------------------------------------------ #

    async def _set_running(self, step: MissionStep) -> None:
        async with self._sessions() as session:
            s = await session.get(MissionStep, step.id)
            s.status = StepStatus.RUNNING
            s.started_at = datetime.now(UTC)
            await session.commit()

    async def _set_succeeded(self, step: MissionStep, output: dict) -> None:
        async with self._sessions() as session:
            s = await session.get(MissionStep, step.id)
            s.status = StepStatus.SUCCEEDED
            s.output = output
            s.finished_at = datetime.now(UTC)
            await session.commit()

    async def _set_failed(self, step: MissionStep, error: str) -> None:
        async with self._sessions() as session:
            s = await session.get(MissionStep, step.id)
            s.status = StepStatus.FAILED
            s.output = {"error": error}
            s.finished_at = datetime.now(UTC)
            await session.commit()


async def _safe_publish(
    publish_fn: PublishFn, event_type: str, payload: dict
) -> None:
    try:
        await publish_fn(event_type, payload)
    except Exception as exc:
        logger.warning(
            "step.publish_failed", event_type=event_type, error=str(exc)
        )

from __future__ import annotations

import ast as _ast
import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kernel.events import DomainEventType, KhonshuEvent, event_bus
from kernel.health import ComponentHealth, db_health
from kernel.logger import get_logger
from models.scheduler import SchedulerTrigger, TriggerStatus, TriggerType

logger = get_logger(__name__)

# Regex simples para resolver variáveis {{ nome }} em templates
_TEMPLATE_VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")

# Nós AST permitidos em rule expressions.
# Proíbe Call, Attribute, comprehensions e imports.
_SAFE_AST_NODES: frozenset[type] = frozenset({
    _ast.Expression,
    _ast.BoolOp, _ast.And, _ast.Or,
    _ast.UnaryOp, _ast.Not, _ast.UAdd, _ast.USub, _ast.Invert,
    _ast.Compare,
    _ast.Eq, _ast.NotEq, _ast.Lt, _ast.LtE, _ast.Gt, _ast.GtE,
    _ast.Is, _ast.IsNot, _ast.In, _ast.NotIn,
    _ast.BinOp,
    _ast.Add, _ast.Sub, _ast.Mult, _ast.Div, _ast.Mod, _ast.FloorDiv,
    _ast.Constant,
    _ast.Name,
    _ast.IfExp,
    _ast.Tuple, _ast.List,
})


def _render_template(template: str, context: dict) -> str:
    """Substitui {{ variavel }} pelo valor correspondente no contexto."""
    def replace(match: re.Match) -> str:
        key = match.group(1)
        return str(context.get(key, match.group(0)))
    return _TEMPLATE_VAR.sub(replace, template)


class SchedulerEngine:
    """Gerencia os triggers do Scheduler e dispara Missions automaticamente.

    Tipos de trigger suportados:
    - TemporalTrigger: cron expression — verificado a cada tick do loop.
    - EventTrigger: reage a um evento de domínio específico.
    - RuleTrigger: avalia uma expressão booleana em intervalo configurável.

    Nenhuma Engine é importada diretamente. Ao disparar, publica o evento
    SCHEDULER_FIRED; MissionEngine subscreve e cria a missão (ADR-008).
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._sessions = session_factory

        # Assina eventos de domínio para processar EventTriggers
        event_bus.subscribe_event(
            "*",  # tratado como wildcard internamente
            self._on_domain_event,
        )

    async def health(self) -> ComponentHealth:
        return await db_health("scheduler_engine", self._sessions)

    # ------------------------------------------------------------------ #
    # CRUD de triggers                                                     #
    # ------------------------------------------------------------------ #

    async def create_trigger(
        self,
        workspace_id: UUID,
        name: str,
        trigger_type: TriggerType,
        mission_intent_template: str,
        description: str | None = None,
        cron_expression: str | None = None,
        timezone: str = "America/Sao_Paulo",
        event_type: str | None = None,
        event_filter: dict | None = None,
        rule_expression: str | None = None,
        poll_interval_seconds: int | None = None,
        mission_context: dict | None = None,
        requires_approval: bool = False,
    ) -> SchedulerTrigger:
        _validate_trigger(
            trigger_type,
            cron_expression,
            event_type,
            rule_expression,
            poll_interval_seconds,
        )

        async with self._sessions() as session:
            trigger = SchedulerTrigger(
                workspace_id=workspace_id,
                name=name,
                description=description,
                type=trigger_type,
                cron_expression=cron_expression,
                timezone=timezone,
                event_type=event_type,
                event_filter=event_filter,
                rule_expression=rule_expression,
                poll_interval_seconds=poll_interval_seconds,
                mission_intent_template=mission_intent_template,
                mission_context=mission_context or {},
                requires_approval=requires_approval,
                next_fire_at=(
                    _next_cron_fire(cron_expression, timezone)
                    if cron_expression
                    else None
                ),
            )
            session.add(trigger)
            await session.commit()
            await session.refresh(trigger)

        logger.info(
            "scheduler.trigger_created",
            trigger_id=str(trigger.id),
            type=trigger_type.value,
            name=name,
        )
        return trigger

    async def get_trigger(self, trigger_id: UUID) -> SchedulerTrigger:
        async with self._sessions() as session:
            trigger = await session.get(SchedulerTrigger, trigger_id)
            if trigger is None:
                raise ValueError(f"Trigger {trigger_id} not found")
            return trigger

    async def list_triggers(
        self,
        workspace_id: UUID,
        trigger_type: TriggerType | None = None,
        status: TriggerStatus | None = None,
    ) -> list[SchedulerTrigger]:
        async with self._sessions() as session:
            q = (
                select(SchedulerTrigger)
                .where(SchedulerTrigger.workspace_id == workspace_id)
                .order_by(SchedulerTrigger.name)
            )
            if trigger_type:
                q = q.where(SchedulerTrigger.type == trigger_type)
            if status:
                q = q.where(SchedulerTrigger.status == status)
            result = await session.execute(q)
            return list(result.scalars())

    async def pause_trigger(
        self, trigger_id: UUID
    ) -> SchedulerTrigger:
        return await self._set_status(trigger_id, TriggerStatus.paused)

    async def resume_trigger(
        self, trigger_id: UUID
    ) -> SchedulerTrigger:
        return await self._set_status(trigger_id, TriggerStatus.active)

    async def disable_trigger(
        self, trigger_id: UUID
    ) -> SchedulerTrigger:
        return await self._set_status(trigger_id, TriggerStatus.disabled)

    async def delete_trigger(self, trigger_id: UUID) -> None:
        async with self._sessions() as session:
            trigger = await session.get(SchedulerTrigger, trigger_id)
            if trigger:
                await session.delete(trigger)
                await session.commit()

    # ------------------------------------------------------------------ #
    # Tick — chamado pelo loop principal do processo (Uvicorn lifespan)   #
    # ------------------------------------------------------------------ #

    async def tick(self) -> None:
        """Verifica e dispara TemporalTriggers e RuleTriggers pendentes.

        Deve ser chamado a cada ~60 segundos pelo lifespan do servidor.
        Triggers são ordenados pela prioridade efetiva calculada em memória
        (base + age_boost + type_boost), garantindo anti-starvation.
        """
        now = datetime.now(UTC)

        async with self._sessions() as session:
            result = await session.execute(
                select(SchedulerTrigger)
                .where(
                    SchedulerTrigger.status == TriggerStatus.active,
                    SchedulerTrigger.type.in_([
                        TriggerType.temporal,
                        TriggerType.rule,
                    ]),
                )
            )
            triggers = list(result.scalars())

        triggers.sort(
            key=lambda t: self._compute_effective_priority(t, now),
            reverse=True,
        )

        for trigger in triggers:
            should_fire = False

            if trigger.type == TriggerType.temporal:
                should_fire = (
                    trigger.next_fire_at is not None
                    and trigger.next_fire_at <= now
                )
            elif trigger.type == TriggerType.rule:
                should_fire = await self._evaluate_rule(trigger)

            if should_fire:
                await self._fire(trigger)

    # ------------------------------------------------------------------ #
    # EventTrigger — handler assíncrono                                   #
    # ------------------------------------------------------------------ #

    async def _on_domain_event(self, event: KhonshuEvent) -> None:
        """Processa EventTriggers quando um evento de domínio é recebido."""
        async with self._sessions() as session:
            result = await session.execute(
                select(SchedulerTrigger).where(
                    SchedulerTrigger.status == TriggerStatus.active,
                    SchedulerTrigger.type == TriggerType.event,
                    SchedulerTrigger.event_type == event.type,
                    SchedulerTrigger.workspace_id == event.workspace_id,
                )
            )
            triggers = list(result.scalars())

        for trigger in triggers:
            if _event_matches_filter(event, trigger.event_filter):
                await self._fire(trigger, event_context=event.payload)

    # ------------------------------------------------------------------ #
    # Fire                                                                 #
    # ------------------------------------------------------------------ #

    async def _fire(
        self,
        trigger: SchedulerTrigger,
        event_context: dict | None = None,
    ) -> None:
        context = {**trigger.mission_context, **(event_context or {})}
        intent = _render_template(trigger.mission_intent_template, context)

        logger.info(
            "scheduler.trigger_fired",
            trigger_id=str(trigger.id),
            trigger_name=trigger.name,
            type=trigger.type.value,
            intent=intent[:80],
        )

        fired_event = KhonshuEvent(
            type=DomainEventType.SCHEDULER_FIRED,
            workspace_id=trigger.workspace_id,
            source="scheduler",
            actor="scheduler",
            payload={
                "trigger_id": str(trigger.id),
                "trigger_name": trigger.name,
                "trigger_type": trigger.type.value,
                "intent": intent,
                "context": context,
                "requires_approval": trigger.requires_approval,
            },
        )
        try:
            await event_bus.publish_event(fired_event)
        except Exception as exc:
            logger.warning(
                "scheduler.publish_failed", error=str(exc)
            )

        # Atualiza metadados do trigger
        now = datetime.now(UTC)
        async with self._sessions() as session:
            t = await session.get(SchedulerTrigger, trigger.id)
            t.last_fired_at = now
            t.fire_count += 1
            t.updated_at = now
            if t.type == TriggerType.temporal and t.cron_expression:
                t.next_fire_at = _next_cron_fire(
                    t.cron_expression, t.timezone
                )
            await session.commit()

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _compute_effective_priority(
        self, trigger: SchedulerTrigger, now: datetime
    ) -> int:
        """Compute runtime priority for anti-starvation scheduling.

        Formula: base + age_boost + type_boost
        - age_boost: +1 per day since last fire (or creation), capped at 50.
          Ensures long-waiting triggers are eventually promoted.
        - type_boost: event=+10, temporal=+5, rule=+0.
          Reactive triggers get slight precedence over polled ones.
        - Starvation guard: if idle > 7 days, add +100 override so no
          trigger can be indefinitely starved by high-priority peers.
        """
        base = trigger.priority

        reference = trigger.last_fired_at or trigger.created_at
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=UTC)
        idle_days = (now - reference).total_seconds() / 86_400

        age_boost = min(int(idle_days), 50)

        type_boost = {
            TriggerType.event: 10,
            TriggerType.temporal: 5,
            TriggerType.rule: 0,
        }.get(trigger.type, 0)

        starvation = 100 if idle_days > 7 else 0

        return base + age_boost + type_boost + starvation

    async def _evaluate_rule(self, trigger: SchedulerTrigger) -> bool:
        """Avalia a expressão da RuleTrigger.

        Por segurança usa apenas um subconjunto restrito de builtins.
        Retorna False em caso de qualquer erro de avaliação.
        """
        if not trigger.rule_expression:
            return False

        # Verifica se já passou o intervalo desde o último disparo
        if trigger.last_fired_at and trigger.poll_interval_seconds:
            elapsed = (
                datetime.now(UTC) - trigger.last_fired_at
            ).total_seconds()
            if elapsed < trigger.poll_interval_seconds:
                return False

        try:
            return _safe_eval_rule(trigger.rule_expression, {})
        except Exception as exc:
            logger.warning(
                "scheduler.rule_eval_failed",
                trigger_id=str(trigger.id),
                expression=trigger.rule_expression,
                error=str(exc),
            )
            return False

    async def _set_status(
        self, trigger_id: UUID, status: TriggerStatus
    ) -> SchedulerTrigger:
        async with self._sessions() as session:
            trigger = await session.get(SchedulerTrigger, trigger_id)
            if trigger is None:
                raise ValueError(f"Trigger {trigger_id} not found")
            trigger.status = status
            trigger.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(trigger)
        return trigger


# ------------------------------------------------------------------ #
# Funções auxiliares (fora da classe)                                 #
# ------------------------------------------------------------------ #

def _safe_eval_rule(expression: str, context: dict) -> bool:
    """Avalia expressão booleana de forma segura via whitelist de nós AST.

    Impede RCE ao rejeitar qualquer nó que não esteja em _SAFE_AST_NODES
    (chamadas de função, acesso a atributos, comprehensions, imports, etc.).
    Levanta ValueError em caso de sintaxe inválida ou nó proibido.
    """
    try:
        tree = _ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Syntax error in rule expression: {exc}") from exc

    for node in _ast.walk(tree):
        if type(node) not in _SAFE_AST_NODES:
            node_name = type(node).__name__
            raise ValueError(
                f"Forbidden AST node '{node_name}' in rule expression"
            )

    compiled = compile(tree, "<rule>", "eval")
    return bool(eval(compiled, {"__builtins__": {}}, context))  # noqa: S307


def _validate_trigger(
    trigger_type: TriggerType,
    cron_expression: str | None,
    event_type: str | None,
    rule_expression: str | None,
    poll_interval_seconds: int | None,
) -> None:
    if trigger_type == TriggerType.temporal and not cron_expression:
        raise ValueError(
            "TemporalTrigger requer cron_expression."
        )
    if trigger_type == TriggerType.event and not event_type:
        raise ValueError(
            "EventTrigger requer event_type."
        )
    if trigger_type == TriggerType.rule and not rule_expression:
        raise ValueError(
            "RuleTrigger requer rule_expression."
        )
    if (
        trigger_type == TriggerType.rule
        and poll_interval_seconds is not None
        and poll_interval_seconds < 60
    ):
        raise ValueError(
            "poll_interval_seconds deve ser >= 60."
        )


def _event_matches_filter(
    event: KhonshuEvent, event_filter: dict | None
) -> bool:
    """Verifica se o payload do evento satisfaz o filtro."""
    if not event_filter:
        return True
    for key, expected in event_filter.items():
        if event.payload.get(key) != expected:
            return False
    return True


def _next_cron_fire(
    cron_expression: str, timezone: str
) -> datetime | None:
    """Calcula o próximo disparo de uma cron expression.

    Implementação mínima: usa croniter se disponível, caso contrário
    retorna None (o tick vai ignorar esse trigger até que croniter seja
    instalado ou next_fire_at seja definido manualmente).
    """
    try:
        import zoneinfo

        from croniter import croniter  # type: ignore[import]

        tz = zoneinfo.ZoneInfo(timezone)
        now = datetime.now(tz)
        cron = croniter(cron_expression, now)
        return cron.get_next(datetime)
    except ImportError:
        logger.warning(
            "scheduler.croniter_not_installed",
            cron=cron_expression,
        )
        return None
    except Exception as exc:
        logger.warning(
            "scheduler.cron_parse_failed",
            cron=cron_expression,
            error=str(exc),
        )
        return None

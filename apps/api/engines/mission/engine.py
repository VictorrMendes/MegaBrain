from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from engines.execution import ExecutionContext, StepExecutor
from engines.plan.provider import PlanProvider, PlanProviderError
from engines.plan.validator import PlanValidator
from kernel.capabilities import capability_registry
from kernel.events import DomainEventType, KhonshuEvent, event_bus
from kernel.health import ComponentHealth, db_health
from kernel.logger import get_logger
from models.mission import (
    ExecutionPlan,
    ExecutionPlanStatus,
    FailurePolicy,
    Mission,
    MissionArtifact,
    MissionContext,
    MissionLog,
    MissionStatus,
    MissionStep,
    MissionTrigger,
    StepStatus,
)

logger = get_logger(__name__)

_MAX_RETRIES = 3
_validator = PlanValidator()


class MissionError(Exception):
    pass


class InvalidTransitionError(MissionError):
    pass


class PlanValidationError(MissionError):
    pass


class MissionEngine:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        plan_providers: list[PlanProvider] | None = None,
        reasoner=None,
    ) -> None:
        self._sessions = session_factory
        self._providers: list[PlanProvider] = plan_providers or []
        self._executor = StepExecutor(
            session_factory=session_factory, reasoner=reasoner
        )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def create(
        self,
        workspace_id: UUID,
        intent: str,
        trigger: MissionTrigger = MissionTrigger.MANUAL,
        requires_approval: bool = False,
        conversation_id: UUID | None = None,
        context_metadata: dict | None = None,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
    ) -> Mission:
        async with self._sessions() as session:
            mission = Mission(
                workspace_id=workspace_id,
                intent=intent,
                status=MissionStatus.PENDING,
                trigger=trigger,
                requires_approval=requires_approval,
            )
            session.add(mission)
            await session.flush()

            caps = capability_registry.list_names()
            ctx = MissionContext(
                mission_id=mission.id,
                conversation_id=conversation_id,
                available_capabilities=caps,
                metadata_=context_metadata or {},
            )
            session.add(ctx)
            await session.commit()
            await session.refresh(mission)

        logger.info(
            "mission.created",
            mission_id=str(mission.id),
            intent=intent,
            trigger=trigger.value,
        )

        await self._publish(
            event_type=DomainEventType.MISSION_CREATED,
            mission=mission,
            payload={"intent": intent, "trigger": trigger.value},
            correlation_id=correlation_id,
            causation_id=causation_id,
        )

        return mission

    async def plan(
        self, mission_id: UUID, provider_name: str | None = None
    ) -> Mission:
        mission = await self._get(mission_id)
        await self._transition(mission, MissionStatus.PLANNING)

        await self._publish(
            DomainEventType.MISSION_PLANNING,
            mission,
            {"provider": provider_name},
        )

        provider = self._select_provider(provider_name)
        if provider is None:
            await self._fail(mission, "No plan provider available")
            raise MissionError("No plan provider configured")

        # Determine the next version number for this mission's plans
        async with self._sessions() as session:
            result = await session.execute(
                select(func.count()).select_from(ExecutionPlan).where(
                    ExecutionPlan.mission_id == mission_id
                )
            )
            plan_count = result.scalar() or 0

        # Create draft ExecutionPlan before generating steps
        async with self._sessions() as session:
            plan = ExecutionPlan(
                mission_id=mission_id,
                version=plan_count + 1,
                planner=provider.name,
                status=ExecutionPlanStatus.DRAFT,
            )
            session.add(plan)
            await session.commit()
            await session.refresh(plan)
        plan_id = plan.id

        try:
            steps = await provider.create_execution_plan(mission)
        except PlanProviderError as exc:
            async with self._sessions() as session:
                p = await session.get(ExecutionPlan, plan_id)
                p.status = ExecutionPlanStatus.FAILED
                await session.commit()
            await self._fail(mission, str(exc))
            raise MissionError(f"Planning failed: {exc}") from exc

        # Assign steps to the execution plan
        for step in steps:
            step.mission_id = mission_id
            step.execution_plan_id = plan_id

        # Validate before persisting or requesting approval
        validation = _validator.validate(
            steps=steps,
            mission=mission,
            registry=capability_registry,
        )

        async with self._sessions() as session:
            p = await session.get(ExecutionPlan, plan_id)
            p.validation_errors = (
                validation.to_dict() if not validation.valid else None
            )

            if not validation.valid:
                p.status = ExecutionPlanStatus.FAILED
                await session.commit()

            else:
                p.status = ExecutionPlanStatus.VALIDATED
                for step in steps:
                    session.add(step)
                await session.commit()

        if not validation.valid:
            error_summary = "; ".join(
                e.message for e in validation.errors
            )
            await self._publish(
                DomainEventType.MISSION_PLAN_VALIDATION_FAILED,
                mission,
                {
                    "plan_id": str(plan_id),
                    "errors": error_summary,
                },
            )
            await self._fail(
                mission,
                f"Plan validation failed: {error_summary}",
            )
            raise PlanValidationError(
                f"Plan validation failed: {error_summary}"
            )

        async with self._sessions() as session:
            m = await session.get(Mission, mission_id)
            m.planner = provider.name
            m.updated_at = datetime.now(UTC)
            await session.commit()

        next_status = (
            MissionStatus.WAITING_APPROVAL
            if mission.requires_approval
            else MissionStatus.READY
        )
        return await self._transition(
            await self._get(mission_id), next_status
        )

    async def approve(self, mission_id: UUID) -> Mission:
        mission = await self._get(mission_id)
        return await self._transition(mission, MissionStatus.READY)

    async def reject(self, mission_id: UUID) -> Mission:
        """Reject and re-plan (back to PLANNING)."""
        mission = await self._get(mission_id)
        return await self._transition(mission, MissionStatus.PLANNING)

    async def run(self, mission_id: UUID) -> Mission:
        mission = await self._get(mission_id)
        mission = await self._transition(mission, MissionStatus.RUNNING)
        await self._publish(DomainEventType.MISSION_RUNNING, mission, {})

        context = await self._build_context(mission)

        # Resolve the active ExecutionPlan (VALIDATED or APPROVED).
        # Never execute steps from superseded or failed plans.
        async with self._sessions() as session:
            plan_row = await session.execute(
                select(ExecutionPlan)
                .where(
                    ExecutionPlan.mission_id == mission_id,
                    ExecutionPlan.status.in_([
                        ExecutionPlanStatus.VALIDATED,
                        ExecutionPlanStatus.APPROVED,
                    ]),
                )
                .order_by(ExecutionPlan.version.desc())
                .limit(1)
            )
            active_plan = plan_row.scalars().first()

        if active_plan is None:
            await self._fail(mission, "No validated execution plan found")
            raise MissionError("Cannot run mission: no validated plan")

        async with self._sessions() as session:
            rows = await session.execute(
                select(MissionStep)
                .where(MissionStep.execution_plan_id == active_plan.id)
                .order_by(MissionStep.order)
            )
            steps = list(rows.scalars())

        for step in steps:
            if step.status in (StepStatus.SUCCEEDED, StepStatus.SKIPPED):
                continue

            async def _pub(et: str, p: dict, _m: Mission = mission) -> None:
                await self._publish(et, _m, p)

            step_result = await self._executor.run(step, context, _pub)

            if step_result.success:
                context.record_output(step.order, step_result.output)
                continue

            policy = step.failure_policy

            if policy in (FailurePolicy.skip, FailurePolicy.ignore):
                await self._mark_skipped(step)
                context.record_output(step.order, {})
                continue

            if policy == FailurePolicy.abort:
                await self._fail(
                    mission,
                    f"Step '{step.tool}' aborted: {step_result.error}",
                )
                raise MissionError(f"Mission aborted at step '{step.tool}'")

            # FailurePolicy.retry (default)
            if step.retry_count >= _MAX_RETRIES:
                await self._fail(
                    mission,
                    f"Step '{step.tool}' exhausted {_MAX_RETRIES} retries: "
                    f"{step_result.error}",
                )
                raise MissionError(f"Mission failed at step '{step.tool}'")

            # One retry cycle: RUNNING → RETRYING → RUNNING
            mission = await self._transition(mission, MissionStatus.RETRYING)
            async with self._sessions() as session:
                s = await session.get(MissionStep, step.id)
                s.retry_count += 1
                s.status = StepStatus.PENDING
                await session.commit()
            mission = await self._transition(mission, MissionStatus.RUNNING)

            async with self._sessions() as session:
                step = await session.get(MissionStep, step.id)

            retry_result = await self._executor.run(step, context, _pub)
            if retry_result.success:
                context.record_output(step.order, retry_result.output)
                continue

            await self._fail(
                mission,
                f"Step '{step.tool}' failed after retry: {retry_result.error}",
            )
            raise MissionError(f"Mission failed at step '{step.tool}'")

        return await self._succeed(mission)

    async def pause(self, mission_id: UUID) -> Mission:
        mission = await self._get(mission_id)
        return await self._transition(mission, MissionStatus.PAUSED)

    async def resume(self, mission_id: UUID) -> Mission:
        mission = await self._get(mission_id)
        return await self._transition(mission, MissionStatus.RUNNING)

    async def cancel(self, mission_id: UUID) -> Mission:
        mission = await self._get(mission_id)
        return await self._transition(mission, MissionStatus.CANCELLED)

    async def add_artifact(
        self,
        mission_id: UUID,
        type: str,
        name: str,
        uri: str,
        mime: str = "application/octet-stream",
        step_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> MissionArtifact:
        async with self._sessions() as session:
            artifact = MissionArtifact(
                mission_id=mission_id,
                step_id=step_id,
                type=type,
                mime=mime,
                name=name,
                uri=uri,
                metadata_=metadata or {},
            )
            session.add(artifact)
            await session.commit()
            await session.refresh(artifact)
        return artifact

    async def get(self, mission_id: UUID) -> Mission:
        return await self._get(mission_id)

    async def list(
        self,
        workspace_id: UUID,
        status: MissionStatus | None = None,
        limit: int = 50,
    ) -> list[Mission]:
        async with self._sessions() as session:
            q = (
                select(Mission)
                .where(Mission.workspace_id == workspace_id)
                .order_by(Mission.created_at.desc())
                .limit(limit)
            )
            if status:
                q = q.where(Mission.status == status)
            result = await session.execute(q)
            return list(result.scalars())

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _get(self, mission_id: UUID) -> Mission:
        async with self._sessions() as session:
            mission = await session.get(Mission, mission_id)
            if mission is None:
                raise MissionError(f"Mission {mission_id} not found")
            return mission

    async def _transition(
        self, mission: Mission, target: MissionStatus
    ) -> Mission:
        if not mission.can_transition_to(target):
            raise InvalidTransitionError(
                f"Cannot transition {mission.status} → {target}"
            )
        async with self._sessions() as session:
            m = await session.get(Mission, mission.id)
            m.status = target
            m.updated_at = datetime.now(UTC)
            if target in {
                MissionStatus.SUCCEEDED,
                MissionStatus.FAILED,
                MissionStatus.CANCELLED,
            }:
                m.completed_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(m)

        logger.info(
            "mission.transition",
            mission_id=str(m.id),
            from_status=mission.status.value,
            to_status=target.value,
        )
        return m

    async def health(self) -> ComponentHealth:
        return await db_health("mission_engine", self._sessions)

    def subscribe_to_events(self) -> None:
        """Registra handlers de eventos no EventBus."""
        event_bus.subscribe_event(
            DomainEventType.INBOX_ROUTED_AS_TASK,
            self._on_inbox_task,
        )
        event_bus.subscribe_event(
            DomainEventType.SCHEDULER_FIRED,
            self._on_scheduler_fired,
        )

    async def _on_inbox_task(self, event: KhonshuEvent) -> None:
        """Cria missão quando InboxEngine roteia como tarefa."""
        intent: str = event.payload.get("intent", "")
        item_id: str | None = event.payload.get("item_id")
        if not intent:
            return
        try:
            await self.create(
                workspace_id=event.workspace_id,
                intent=intent,
                trigger=MissionTrigger.MANUAL,
                context_metadata=(
                    {"inbox_item_id": item_id} if item_id else {}
                ),
                correlation_id=event.correlation_id,
                causation_id=event.id,
            )
        except Exception as exc:
            logger.warning(
                "mission.inbox_task_failed",
                item_id=item_id,
                error=str(exc),
            )

    async def _on_scheduler_fired(self, event: KhonshuEvent) -> None:
        """Cria missão quando o Scheduler dispara um trigger."""
        intent: str = event.payload.get("intent", "")
        if not intent:
            return
        try:
            await self.create(
                workspace_id=event.workspace_id,
                intent=intent,
                trigger=MissionTrigger.SCHEDULED,
                context_metadata=event.payload.get("context", {}),
                correlation_id=event.correlation_id,
                causation_id=event.id,
            )
        except Exception as exc:
            logger.warning(
                "mission.scheduler_fired_failed",
                trigger_id=event.payload.get("trigger_id"),
                error=str(exc),
            )

    async def _build_context(self, mission: Mission) -> ExecutionContext:
        """Constrói ExecutionContext de runtime a partir do MissionContext."""
        async with self._sessions() as session:
            rows = await session.execute(
                select(MissionContext).where(
                    MissionContext.mission_id == mission.id
                )
            )
            ctx = rows.scalar_one_or_none()

        return ExecutionContext(
            mission_id=mission.id,
            workspace_id=mission.workspace_id,
            intent=mission.intent,
            workspace_config=ctx.workspace_config if ctx else {},
            metadata=ctx.metadata_ if ctx else {},
            correlation_id=mission.id,
        )

    async def _mark_skipped(self, step: MissionStep) -> None:
        async with self._sessions() as session:
            s = await session.get(MissionStep, step.id)
            s.status = StepStatus.SKIPPED
            s.finished_at = datetime.now(UTC)
            await session.commit()
        logger.info(
            "step.skipped",
            step_id=str(step.id),
            tool=step.tool,
            policy=step.failure_policy.value,
        )

    async def _succeed(self, mission: Mission) -> Mission:
        m = await self._transition(mission, MissionStatus.SUCCEEDED)
        await self._publish(DomainEventType.MISSION_COMPLETED, m, {})
        return m

    async def _fail(self, mission: Mission, reason: str) -> Mission:
        async with self._sessions() as session:
            log = MissionLog(
                mission_id=mission.id,
                level="error",
                message=reason,
            )
            session.add(log)
            await session.commit()

        m = await self._transition(mission, MissionStatus.FAILED)
        await self._publish(
            DomainEventType.MISSION_FAILED, m, {"reason": reason}
        )
        return m

    async def _publish(
        self,
        event_type: str,
        mission: Mission,
        payload: dict,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
    ) -> None:
        try:
            event = KhonshuEvent(
                type=event_type,
                workspace_id=mission.workspace_id,
                source="mission",
                actor="system",
                payload={"mission_id": str(mission.id), **payload},
                correlation_id=correlation_id or mission.id,
                causation_id=causation_id,
            )
            await event_bus.publish_event(event)
        except Exception as exc:
            logger.warning(
                "mission.publish_failed",
                event_type=event_type,
                error=str(exc),
            )

    def _select_provider(
        self, name: str | None
    ) -> PlanProvider | None:
        if not self._providers:
            return None
        if name:
            for p in self._providers:
                if p.name == name:
                    return p
        return self._providers[0]

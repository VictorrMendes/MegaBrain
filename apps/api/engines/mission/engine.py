from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from engines.plan.provider import PlanProvider, PlanProviderError
from kernel.capabilities import capability_registry
from kernel.events import EventType, KhonshuEvent, event_bus
from kernel.logger import get_logger
from models.mission import (
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


class MissionError(Exception):
    pass


class InvalidTransitionError(MissionError):
    pass


class MissionEngine:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        plan_providers: list[PlanProvider] | None = None,
    ) -> None:
        self._sessions = session_factory
        # providers are tried in order; first success wins
        self._providers: list[PlanProvider] = plan_providers or []

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
            event_type=EventType.MISSION_CREATED,
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
            EventType.MISSION_PLANNING, mission, {"provider": provider_name}
        )

        provider = self._select_provider(provider_name)
        if provider is None:
            await self._fail(
                mission, "No plan provider available"
            )
            raise MissionError("No plan provider configured")

        try:
            steps = await provider.create_execution_plan(mission)
        except PlanProviderError as exc:
            await self._fail(mission, str(exc))
            raise MissionError(f"Planning failed: {exc}") from exc

        async with self._sessions() as session:
            for step in steps:
                session.add(step)
            await session.commit()

        async with self._sessions() as session:
            m = await session.get(Mission, mission_id)
            m.planner = provider.name
            m.updated_at = datetime.now(timezone.utc)

            next_status = (
                MissionStatus.WAITING_APPROVAL
                if m.requires_approval
                else MissionStatus.READY
            )
            await session.commit()

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

        await self._publish(EventType.MISSION_RUNNING, mission, {})

        async with self._sessions() as session:
            result = await session.execute(
                select(MissionStep)
                .where(MissionStep.mission_id == mission_id)
                .order_by(MissionStep.order)
            )
            steps = list(result.scalars())

        for step in steps:
            if step.status == StepStatus.SUCCEEDED:
                continue
            try:
                await self._execute_step(mission, step)
            except Exception as exc:
                if step.retry_count < _MAX_RETRIES:
                    await self._retry_step(mission, step)
                else:
                    await self._fail(mission, f"Step {step.tool} failed: {exc}")
                    raise MissionError(
                        f"Mission failed at step {step.tool}"
                    ) from exc

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
            m.updated_at = datetime.now(timezone.utc)
            if target in {
                MissionStatus.SUCCEEDED,
                MissionStatus.FAILED,
                MissionStatus.CANCELLED,
            }:
                m.completed_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(m)

        logger.info(
            "mission.transition",
            mission_id=str(m.id),
            from_status=mission.status.value,
            to_status=target.value,
        )
        return m

    async def _execute_step(
        self, mission: Mission, step: MissionStep
    ) -> None:
        tool = capability_registry.get_tool(step.tool)

        async with self._sessions() as session:
            s = await session.get(MissionStep, step.id)
            s.status = StepStatus.RUNNING
            s.started_at = datetime.now(timezone.utc)
            await session.commit()

        await self._publish(
            EventType.MISSION_STEP_STARTED,
            mission,
            {"step_id": str(step.id), "tool": step.tool},
        )

        try:
            if tool is None:
                raise MissionError(
                    f"Tool '{step.tool}' not found in registry"
                )
            result = await tool.fn(**step.input)
        except Exception as exc:
            async with self._sessions() as session:
                s = await session.get(MissionStep, step.id)
                s.status = StepStatus.FAILED
                s.finished_at = datetime.now(timezone.utc)
                await session.commit()

            await self._publish(
                EventType.MISSION_STEP_FAILED,
                mission,
                {"step_id": str(step.id), "tool": step.tool, "error": str(exc)},
            )
            raise

        async with self._sessions() as session:
            s = await session.get(MissionStep, step.id)
            s.status = StepStatus.SUCCEEDED
            s.output = result if isinstance(result, dict) else {"result": result}
            s.finished_at = datetime.now(timezone.utc)
            await session.commit()

        await self._publish(
            EventType.MISSION_STEP_COMPLETED,
            mission,
            {"step_id": str(step.id), "tool": step.tool},
        )

    async def _retry_step(
        self, mission: Mission, step: MissionStep
    ) -> None:
        await self._transition(mission, MissionStatus.RETRYING)
        async with self._sessions() as session:
            s = await session.get(MissionStep, step.id)
            s.retry_count += 1
            s.status = StepStatus.PENDING
            await session.commit()
        await self._transition(
            await self._get(mission.id), MissionStatus.RUNNING
        )

    async def _succeed(self, mission: Mission) -> Mission:
        m = await self._transition(mission, MissionStatus.SUCCEEDED)
        await self._publish(EventType.MISSION_COMPLETED, m, {})
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
            EventType.MISSION_FAILED, m, {"reason": reason}
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

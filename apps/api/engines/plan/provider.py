from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from models.mission import Mission, MissionStep


class PlanProviderError(Exception):
    pass


@runtime_checkable
class PlanProvider(Protocol):
    """Interface for all plan providers.

    A PlanProvider receives a Mission with status=PLANNING and returns
    the list of MissionStep objects that make up the execution plan.
    The MissionEngine persists the steps and transitions the mission
    to WAITING_APPROVAL or READY.
    """

    name: str

    async def create_execution_plan(
        self, mission: Mission
    ) -> list[MissionStep]:
        """Generate and return steps for the given mission.

        Implementations must NOT persist anything — that is the
        MissionEngine's responsibility.

        Raises PlanProviderError if planning fails.
        """
        ...

"""IntegrationIntelligence — translates integration events into actions.

Integrations must NOT call Engines directly.
This component subscribes to IntegrationEventType events and routes them
to the appropriate action: create mission, store knowledge, publish
notification, update life context.

Registered in main.py lifespan after event_bus.connect().
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from kernel.events.schema import IntegrationEventType
from kernel.logger import get_logger
from models.mission import MissionTrigger

if TYPE_CHECKING:
    from engines.knowledge import KnowledgeEngine
    from engines.mission import MissionEngine

logger = get_logger(__name__)


class IntegrationIntelligence:
    """Converts integration events into cognitive actions.

    Docker container down → create restart mission (requires approval).
    GitHub PR review needed → store knowledge fact.
    Calendar upcoming → logged (LifeContextProvider picks up via sync).
    Home Assistant presence → stored as observation.
    """

    def __init__(
        self,
        mission_engine: MissionEngine,
        knowledge_engine: KnowledgeEngine,
    ) -> None:
        self._missions = mission_engine
        self._knowledge = knowledge_engine

    def subscribe_to_events(self) -> None:
        """Wire up all integration event subscriptions."""
        from kernel.events import event_bus

        event_bus.subscribe(
            "khonshu.events",
            self._handle_event,
        )
        logger.info("integration_intelligence.subscribed")

    def _is_integration_event(self, event) -> bool:
        return event.type.startswith(
            (
                "integration.",
                "docker.",
                "calendar.",
                "github.",
                "homeassistant.",
                "email.",
                "notion.",
                "weather.",
                "telegram.",
            )
        )

    async def _handle_event(self, event) -> None:
        if not self._is_integration_event(event):
            return
        try:
            await self._dispatch(event)
        except Exception as exc:
            logger.warning(
                "integration_intelligence.dispatch_failed",
                event_type=event.type,
                error=str(exc),
            )

    async def _dispatch(self, event) -> None:
        t = event.type

        if t == IntegrationEventType.DOCKER_CONTAINER_FAILED:
            await self._on_container_failed(event)
        elif t == IntegrationEventType.DOCKER_CONTAINER_UNHEALTHY:
            await self._on_container_unhealthy(event)
        elif t == IntegrationEventType.GITHUB_PR_REVIEW_NEEDED:
            await self._on_pr_review_needed(event)
        elif t == IntegrationEventType.GITHUB_ISSUE_OPENED:
            await self._on_github_issue(event)
        elif t == IntegrationEventType.EMAIL_IMPORTANT:
            await self._on_important_email(event)
        elif t == IntegrationEventType.WEATHER_UPDATED:
            await self._on_weather_update(event)
        elif t in (
            IntegrationEventType.HOME_PRESENCE_DETECTED,
            IntegrationEventType.HOME_PRESENCE_GONE,
        ):
            await self._on_presence_change(event)

    # ------------------------------------------------------------------ #
    # Docker                                                               #
    # ------------------------------------------------------------------ #

    async def _on_container_failed(self, event) -> None:
        p = event.payload
        container = p.get("container_name", p.get("id", "unknown"))
        logger.info(
            "integration_intelligence.container_failed",
            container=container,
        )
        await self._missions.create(
            workspace_id=event.workspace_id,
            intent=(
                f"Container '{container}' parou inesperadamente — "
                "diagnosticar e reiniciar se for seguro"
            ),
            requires_approval=True,
            trigger=MissionTrigger.EVENT,
            context_metadata={
                "container_name": container,
                "source_event": event.type,
                "auto_generated": True,
            },
        )

    async def _on_container_unhealthy(self, event) -> None:
        p = event.payload
        container = p.get("container_name", "unknown")
        await self._knowledge.store_observation(
            workspace_id=event.workspace_id,
            statement=(
                f"Container '{container}' está com health check falhando"
            ),
            derived_from="docker_integration",
            confidence=0.9,
            expires_in_days=1,
        )

    # ------------------------------------------------------------------ #
    # GitHub                                                               #
    # ------------------------------------------------------------------ #

    async def _on_pr_review_needed(self, event) -> None:
        p = event.payload
        pr_title = p.get("title", "PR")
        pr_url = p.get("url", "")
        repo = p.get("repository", "")
        await self._knowledge.store_fact(
            workspace_id=event.workspace_id,
            statement=(
                f"GitHub PR aguardando review: '{pr_title}' "
                f"no repositório '{repo}'. URL: {pr_url}"
            ),
            source_type="github_integration",
            confidence=0.95,
        )

    async def _on_github_issue(self, event) -> None:
        p = event.payload
        title = p.get("title", "Issue")
        repo = p.get("repository", "")
        await self._knowledge.store_fact(
            workspace_id=event.workspace_id,
            statement=f"Nova issue GitHub: '{title}' em '{repo}'",
            source_type="github_integration",
            confidence=0.9,
        )

    # ------------------------------------------------------------------ #
    # Email                                                                #
    # ------------------------------------------------------------------ #

    async def _on_important_email(self, event) -> None:
        p = event.payload
        subject = p.get("subject", "")
        sender = p.get("from", "")
        await self._knowledge.store_fact(
            workspace_id=event.workspace_id,
            statement=(
                f"Email importante recebido de '{sender}': '{subject}'"
            ),
            source_type="email_integration",
            confidence=0.85,
        )

    # ------------------------------------------------------------------ #
    # Weather                                                              #
    # ------------------------------------------------------------------ #

    async def _on_weather_update(self, event) -> None:
        p = event.payload
        condition = p.get("condition", "")
        location = p.get("location", "")
        if condition and location:
            await self._knowledge.store_observation(
                workspace_id=event.workspace_id,
                statement=(
                    f"Clima atual em {location}: {condition}"
                ),
                derived_from="weather_integration",
                confidence=0.8,
                expires_in_days=1,
            )

    # ------------------------------------------------------------------ #
    # Home Assistant                                                       #
    # ------------------------------------------------------------------ #

    async def _on_presence_change(self, event) -> None:
        p = event.payload
        person = p.get("person", "owner")
        present = (
            event.type == IntegrationEventType.HOME_PRESENCE_DETECTED
        )
        state = "em casa" if present else "fora de casa"
        await self._knowledge.store_observation(
            workspace_id=event.workspace_id,
            statement=f"{person} está {state}",
            derived_from="homeassistant_integration",
            confidence=0.95,
            expires_in_days=1,
        )

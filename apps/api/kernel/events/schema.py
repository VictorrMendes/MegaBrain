from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class KhonshuEvent:
    """Typed event envelope for all inter-component communication."""

    type: str
    workspace_id: UUID
    payload: dict
    source: str                       # chat | scheduler | inbox | mission | system
    actor: str = "system"             # user | scheduler | agent | system
    version: str = "1.0"
    priority: int = 5                 # 0 (low) – 9 (critical)
    metadata: dict = field(default_factory=dict)
    correlation_id: UUID = field(default_factory=uuid4)
    causation_id: UUID | None = None
    # Estável em toda a cadeia causal. Distinto de correlation_id.
    trace_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "type": self.type,
            "version": self.version,
            "workspace_id": str(self.workspace_id),
            "correlation_id": str(self.correlation_id),
            "causation_id": (
                str(self.causation_id) if self.causation_id else None
            ),
            "trace_id": str(self.trace_id) if self.trace_id else None,
            "actor": self.actor,
            "source": self.source,
            "payload": self.payload,
            "metadata": self.metadata,
            "priority": self.priority,
            "occurred_at": self.occurred_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> KhonshuEvent:
        return cls(
            id=UUID(data["id"]),
            type=data["type"],
            version=data.get("version", "1.0"),
            workspace_id=UUID(data["workspace_id"]),
            correlation_id=UUID(data["correlation_id"]),
            causation_id=(
                UUID(data["causation_id"])
                if data.get("causation_id")
                else None
            ),
            trace_id=(
                UUID(data["trace_id"]) if data.get("trace_id") else None
            ),
            actor=data.get("actor", "system"),
            source=data.get("source", "system"),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
            priority=data.get("priority", 5),
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
        )

    def derive(
        self,
        type: str,
        payload: dict,
        source: str | None = None,
        actor: str | None = None,
        priority: int | None = None,
        metadata: dict | None = None,
    ) -> KhonshuEvent:
        """Create a child event with the same correlation_id and trace_id."""
        return KhonshuEvent(
            type=type,
            workspace_id=self.workspace_id,
            payload=payload,
            source=source or self.source,
            actor=actor or self.actor,
            version=self.version,
            priority=priority if priority is not None else self.priority,
            metadata=metadata or {},
            correlation_id=self.correlation_id,
            causation_id=self.id,
            trace_id=self.trace_id or self.id,
        )


# Domain events — business facts; published on khonshu.events
# Domain engines may subscribe to these. See ADR-002.

class DomainEventType:
    # Mission lifecycle
    MISSION_CREATED = "mission.created"
    MISSION_PLANNING = "mission.planning"
    MISSION_READY = "mission.ready"
    MISSION_RUNNING = "mission.running"
    MISSION_PAUSED = "mission.paused"
    MISSION_STEP_STARTED = "mission.step.started"
    MISSION_STEP_COMPLETED = "mission.step.completed"
    MISSION_STEP_FAILED = "mission.step.failed"
    MISSION_COMPLETED = "mission.completed"
    MISSION_FAILED = "mission.failed"
    MISSION_CANCELLED = "mission.cancelled"
    MISSION_PLAN_VALIDATION_FAILED = "mission.plan_validation_failed"

    # Documents / Knowledge
    DOCUMENT_INGESTED = "document.ingested"
    KNOWLEDGE_UPDATED = "knowledge.updated"

    # Memory
    MEMORY_CREATED = "memory.created"

    # Chat
    MESSAGE_COMPLETED = "message.completed"

    # Scheduler
    SCHEDULER_FIRED = "scheduler.fired"

    # Inbox routing (publicados pelo InboxEngine após classificação)
    INBOX_ROUTED_AS_KNOWLEDGE = "inbox.routed_as_knowledge"
    INBOX_ROUTED_AS_TASK = "inbox.routed_as_task"
    INBOX_DISMISSED = "inbox.dismissed"


# Infrastructure events — technical state; published on khonshu.infra
# Domain engines must NOT subscribe to these. See ADR-002.

class InfraEventType:
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    CONTAINER_STARTED = "infrastructure.container.started"
    CONTAINER_STOPPED = "infrastructure.container.stopped"
    CONTAINER_UNHEALTHY = "infrastructure.container.unhealthy"
    DATABASE_CONNECTED = "infrastructure.database.connected"
    DATABASE_DISCONNECTED = "infrastructure.database.disconnected"
    EVENTBUS_CONNECTED = "infrastructure.eventbus.connected"


# Backward-compatible alias — existing code that imports EventType still works
EventType = DomainEventType

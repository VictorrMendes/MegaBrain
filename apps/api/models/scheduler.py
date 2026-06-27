from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


def _enum_values(e):
    return [x.value for x in e]


class TriggerType(enum.StrEnum):
    temporal = "temporal"   # cron expression
    event = "event"         # domain event reaction
    rule = "rule"           # boolean condition polled at interval


class TriggerStatus(enum.StrEnum):
    active = "active"
    paused = "paused"
    disabled = "disabled"


class SchedulerTrigger(Base):
    """Defines when and why a Mission should be created automatically.

    Three trigger types (see ARCHITECTURE.md §10 and ADR-002):
    - TemporalTrigger: fires at scheduled times via cron expression.
    - EventTrigger: fires when a specific domain event is received.
    - RuleTrigger: fires when a boolean condition becomes true (polled).
    """

    __tablename__ = "scheduler_triggers"

    id: Mapped[UUID] = mapped_column(
        sa.UUID(), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    description: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )
    type: Mapped[TriggerType] = mapped_column(
        sa.Enum(
            TriggerType,
            name="trigger_type",
            values_callable=_enum_values,
            create_type=False,
        ),
        nullable=False,
        index=True,
    )
    status: Mapped[TriggerStatus] = mapped_column(
        sa.Enum(
            TriggerStatus,
            name="trigger_status",
            values_callable=_enum_values,
            create_type=False,
        ),
        nullable=False,
        default=TriggerStatus.active,
        index=True,
    )

    # TemporalTrigger fields
    cron_expression: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )  # e.g. "0 8 * * *" (every day at 08:00)
    timezone: Mapped[str] = mapped_column(
        sa.Text(), nullable=False, server_default="America/Sao_Paulo"
    )

    # EventTrigger fields
    event_type: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )  # e.g. "document.ingested"
    event_filter: Mapped[dict | None] = mapped_column(
        JSONB(), nullable=True
    )  # optional payload match conditions

    # RuleTrigger fields
    rule_expression: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )  # Python-safe boolean expression evaluated against context
    poll_interval_seconds: Mapped[int | None] = mapped_column(
        sa.Integer(), nullable=True
    )  # how often to evaluate the rule

    # What to do when triggered
    mission_intent_template: Mapped[str] = mapped_column(
        sa.Text(), nullable=False
    )  # Jinja2-compatible template with {{ variable }} syntax
    mission_context: Mapped[dict] = mapped_column(
        JSONB(), nullable=False, server_default=sa.text("'{}'")
    )  # static context injected into the mission
    requires_approval: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=sa.false()
    )

    # Prioridade: maior valor = processado primeiro no tick do scheduler
    priority: Mapped[int] = mapped_column(
        sa.Integer(), nullable=False, server_default="0", index=True
    )

    # Scheduling metadata
    last_fired_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    next_fire_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, index=True
    )
    fire_count: Mapped[int] = mapped_column(
        sa.Integer(), nullable=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )

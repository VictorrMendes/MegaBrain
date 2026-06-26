from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class IntegrationCategory(enum.StrEnum):
    productivity    = "productivity"
    development     = "development"
    infrastructure  = "infrastructure"
    communication   = "communication"
    information     = "information"
    home            = "home"
    storage         = "storage"


class IntegrationStatus(enum.StrEnum):
    active          = "active"
    paused          = "paused"
    error           = "error"
    disconnected    = "disconnected"
    pending_auth    = "pending_auth"


class IntegrationHealth(enum.StrEnum):
    healthy     = "healthy"
    degraded    = "degraded"
    unhealthy   = "unhealthy"
    unknown     = "unknown"


class SyncMode(enum.StrEnum):
    manual          = "manual"
    scheduled       = "scheduled"
    incremental     = "incremental"
    full            = "full"
    webhook         = "webhook"
    event_driven    = "event_driven"


class AccountStatus(enum.StrEnum):
    active  = "active"
    expired = "expired"
    revoked = "revoked"
    error   = "error"


class SyncRecordStatus(enum.StrEnum):
    running = "running"
    success = "success"
    partial = "partial"
    failed  = "failed"
    skipped = "skipped"


class Integration(Base):
    """An external ecosystem connected to PAIOS.

    Distinct from Plugin: a Plugin executes ad-hoc actions.
    An Integration represents a persistent, bidirectional relationship
    with an external service (Google, GitHub, Docker, Home Assistant…).
    It owns sync state, health, accounts and life-context snapshots.
    """

    __tablename__ = "integrations"

    id: Mapped[UUID] = mapped_column(
        sa.UUID(), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(
        sa.Text(), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    category: Mapped[IntegrationCategory] = mapped_column(
        sa.Enum(IntegrationCategory, name="integration_category"),
        nullable=False,
    )
    icon: Mapped[str] = mapped_column(
        sa.Text(), nullable=False, server_default=""
    )
    description: Mapped[str] = mapped_column(
        sa.Text(), nullable=False, server_default=""
    )
    status: Mapped[IntegrationStatus] = mapped_column(
        sa.Enum(IntegrationStatus, name="integration_status"),
        nullable=False,
        server_default="disconnected",
        index=True,
    )
    health: Mapped[IntegrationHealth] = mapped_column(
        sa.Enum(IntegrationHealth, name="integration_health"),
        nullable=False,
        server_default="unknown",
    )
    sync_strategy: Mapped[SyncMode] = mapped_column(
        sa.Enum(SyncMode, name="sync_mode"),
        nullable=False,
        server_default="manual",
    )
    # Provider-specific settings (no tokens — tokens live in ConnectedAccount)
    config: Mapped[dict] = mapped_column(
        JSONB(), nullable=False, server_default=sa.text("'{}'")
    )
    # Runtime snapshot for LifeContextProvider (TTL-managed by IntegrationManager)
    life_context_lines: Mapped[list] = mapped_column(
        ARRAY(sa.Text()), server_default="{}"
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    next_sync_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
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

    accounts: Mapped[list[ConnectedAccount]] = relationship(
        "ConnectedAccount",
        back_populates="integration",
        cascade="all, delete-orphan",
    )
    sync_records: Mapped[list[SyncRecord]] = relationship(
        "SyncRecord",
        back_populates="integration",
        cascade="all, delete-orphan",
        order_by="SyncRecord.started_at.desc()",
    )


class ConnectedAccount(Base):
    """A specific user account attached to an Integration.

    One Integration can have multiple accounts
    (e.g. Google personal + Google work).
    Tokens are stored here and should be encrypted at the infrastructure
    level; the domain layer treats them as opaque strings.
    """

    __tablename__ = "connected_accounts"

    id: Mapped[UUID] = mapped_column(
        sa.UUID(), primary_key=True, default=uuid4
    )
    integration_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    account_name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    account_email: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )
    status: Mapped[AccountStatus] = mapped_column(
        sa.Enum(AccountStatus, name="account_status"),
        nullable=False,
        server_default="active",
    )
    scopes: Mapped[list] = mapped_column(
        ARRAY(sa.Text()), server_default="{}"
    )
    # Stored as opaque strings; encrypt at the infra/secret-manager layer
    access_token: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )
    refresh_token: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # Provider-specific extra credentials / config
    config: Mapped[dict] = mapped_column(
        JSONB(), nullable=False, server_default=sa.text("'{}'")
    )
    quota_used: Mapped[int] = mapped_column(
        sa.BigInteger(), nullable=False, server_default="0"
    )
    quota_limit: Mapped[int] = mapped_column(
        sa.BigInteger(), nullable=False, server_default="0"
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
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

    integration: Mapped[Integration] = relationship(
        "Integration", back_populates="accounts"
    )
    sync_records: Mapped[list[SyncRecord]] = relationship(
        "SyncRecord",
        back_populates="account",
        cascade="all, delete-orphan",
    )


class SyncRecord(Base):
    """Auditable history of every synchronisation attempt."""

    __tablename__ = "sync_records"

    id: Mapped[UUID] = mapped_column(
        sa.UUID(), primary_key=True, default=uuid4
    )
    integration_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("connected_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sync_type: Mapped[SyncMode] = mapped_column(
        sa.Enum(SyncMode, name="sync_mode", create_type=False),
        nullable=False,
    )
    status: Mapped[SyncRecordStatus] = mapped_column(
        sa.Enum(SyncRecordStatus, name="sync_record_status"),
        nullable=False,
        server_default="running",
    )
    items_synced: Mapped[int] = mapped_column(
        sa.Integer(), nullable=False, server_default="0"
    )
    items_failed: Mapped[int] = mapped_column(
        sa.Integer(), nullable=False, server_default="0"
    )
    conflicts: Mapped[int] = mapped_column(
        sa.Integer(), nullable=False, server_default="0"
    )
    duration_ms: Mapped[int | None] = mapped_column(
        sa.Integer(), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        sa.Text(), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    integration: Mapped[Integration] = relationship(
        "Integration", back_populates="sync_records"
    )
    account: Mapped[ConnectedAccount | None] = relationship(
        "ConnectedAccount", back_populates="sync_records"
    )

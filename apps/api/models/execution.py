import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from models.base import Base


class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    RUNNING = "RUNNING"
    ROLLBACK = "ROLLBACK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    RUNNING = "RUNNING"
    ROLLBACK = "ROLLBACK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    RETRYING = "RETRYING"


class Execution(Base):
    """
    Central State object for any activity in Khonshu.
    Represents the Execution Graph (Nodes, Edges, Conditions).
    """
    __tablename__ = "executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    
    # Goal represents the abstract objective
    goal = Column(String, nullable=False)
    status = Column(String, default=ExecutionStatus.PENDING.value, nullable=False)
    
    # Variables mutated during execution (WorldState dependencies or accumulated payload)
    context = Column(JSONB, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    steps = relationship("ExecutionStep", back_populates="execution", cascade="all, delete-orphan")


class ExecutionStep(Base):
    """
    A Node in the Execution Graph.
    Supports IR compilation mapping, explicit dependencies, and retries.
    """
    __tablename__ = "execution_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("executions.id"), nullable=False)
    
    capability = Column(String, nullable=False)  # The resolved concrete capability
    status = Column(String, default=StepStatus.PENDING.value, nullable=False)
    
    # Inputs/Outputs
    payload = Column(JSONB, default=dict)
    output = Column(JSONB, default=dict)
    
    # Explicit Dependencies (IDs of other ExecutionSteps that must complete first)
    depends_on = Column(JSONB, default=list)
    
    # Middleware states
    retry_count = Column(Integer, default=0)
    retry_policy = Column(JSONB, default=dict)
    approval_required = Column(Boolean, default=False)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    execution = relationship("Execution", back_populates="steps")

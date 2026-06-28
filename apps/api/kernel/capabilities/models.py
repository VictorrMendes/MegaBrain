from enum import StrEnum
from pydantic import BaseModel, Field

class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ApprovalLevel(StrEnum):
    NONE = "NONE"
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    ADMIN = "ADMIN"

class ParameterDefinition(BaseModel):
    type: str
    required: bool = False
    description: str | None = None

class CapabilityDefinition(BaseModel):
    capability: str
    version: int = 1
    provider: str
    workflow_tag: str | None = None
    approval: ApprovalLevel = ApprovalLevel.NONE
    risk: RiskLevel = RiskLevel.LOW
    timeout: int = 30
    is_async: bool = Field(False, alias="async")
    idempotent: bool = False
    cache_policy: str = "NONE"
    description: str
    input_schema: dict[str, ParameterDefinition] = Field(default_factory=dict, alias="input")
    output_schema: dict[str, ParameterDefinition] = Field(default_factory=dict, alias="output")

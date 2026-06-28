import yaml
from pathlib import Path
from pydantic import BaseModel, Field

class CapabilityManifest(BaseModel):
    id: str
    description: str
    latency_ms: int = 200
    cache_policy: str = "REALTIME"
    risk_level: str = "low"
    mutability: str = "READ"   # READ, WRITE, DELETE
    approval_required: bool = False
    side_effects: bool = False

class IntegrationManifest(BaseModel):
    id: str
    name: str
    version: str
    connectors: list[str] = Field(default_factory=list)
    capabilities: list[CapabilityManifest] = Field(default_factory=list)
    snapshots: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)

def load_manifest(yaml_path: str | Path) -> IntegrationManifest:
    """Load and validate an integration manifest from a YAML file."""
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    return IntegrationManifest.model_validate(data)

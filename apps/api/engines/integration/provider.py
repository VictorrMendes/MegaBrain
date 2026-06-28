from abc import ABC, abstractmethod
from typing import Any, Dict
from engines.integration.manifest import IntegrationManifest

class BaseProvider(ABC):
    """Defines capabilities, translates domain logic, and publishes events."""
    
    def __init__(self, manifest: IntegrationManifest):
        self.manifest = manifest

    @property
    def id(self) -> str:
        return self.manifest.id
        
    @property
    def version(self) -> str:
        return self.manifest.version

    @abstractmethod
    async def execute_capability(self, capability_id: str, payload: Dict[str, Any]) -> Any:
        """Executes a specific capability defined in the manifest."""
        pass
        
    async def publish_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Publish a domain event to the internal EventBus."""
        # EventBus is to be implemented.
        pass
        
    async def generate_snapshot(self) -> Dict[str, Any]:
        """Generates an IntegrationSnapshot (RAG/Background context)."""
        return {}

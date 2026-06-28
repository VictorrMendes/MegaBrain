from abc import ABC, abstractmethod
from typing import Any
from kernel.capabilities.models import CapabilityDefinition

class ExecutionProvider(ABC):
    """
    Abstract base class for all capability execution providers.
    Providers are responsible for taking a CapabilityDefinition and executing it.
    """
    
    @abstractmethod
    async def execute(self, definition: CapabilityDefinition, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """
        Executes the capability using the specific provider's mechanism.
        Returns the output payload.
        """
        pass

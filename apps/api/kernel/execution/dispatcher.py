from abc import ABC, abstractmethod
from typing import Any, Dict
from models.execution import ExecutionStep
from kernel.logger import get_logger

logger = get_logger(__name__)

class ExecutionDriver(ABC):
    """
    Base class for protocol-specific drivers (REST, SSH, MCP, etc).
    """
    @abstractmethod
    async def execute(self, node: ExecutionStep, workspace_id: str) -> None:
        pass


class RestDriver(ExecutionDriver):
    async def execute(self, node: ExecutionStep, workspace_id: str) -> None:
        logger.info("driver.rest.executing", capability=node.capability, node_id=str(node.id))
        # Here we would make an HTTP request to the target (e.g. n8n)


class Dispatcher:
    """
    Routes an ExecutionNode to the correct protocol Driver based on the Capability Definition.
    """
    
    def __init__(self):
        self.drivers: Dict[str, ExecutionDriver] = {}

    def register_driver(self, name: str, driver: ExecutionDriver):
        """Dynamically registers a new protocol driver."""
        self.drivers[name] = driver
        logger.info("dispatcher.driver_registered", name=name)

    async def dispatch(self, node: ExecutionStep, workspace_id: str) -> None:
        # We need to determine the protocol.
        # For this test, we assume if the capability starts with 'n8n.', it uses 'rest_n8n'.
        
        protocol = "rest_n8n" if node.capability.startswith("n8n.") else "rest"
        
        driver = self.drivers.get(protocol)
        if not driver:
            logger.error("dispatcher.missing_driver", protocol=protocol)
            # Fail the node if driver is missing
            node.error = f"Missing driver: {protocol}"
            return
            
        await driver.execute(node, workspace_id)

dispatcher = Dispatcher()

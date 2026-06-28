import os
import yaml
from pathlib import Path
from kernel.logger import get_logger
from .models import CapabilityDefinition

logger = get_logger(__name__)

class CapabilityDiscovery:
    """
    Scans the capabilities directory on boot and loads all YAML definitions.
    """
    def __init__(self, base_path: str = "capabilities"):
        # The base_path is relative to the project root
        self.base_path = Path(base_path)
        self.definitions: dict[str, CapabilityDefinition] = {}

    def sync(self) -> None:
        """Scan directories and load all YAML manifests."""
        self.definitions.clear()
        if not self.base_path.exists():
            logger.warning(f"Capabilities base path {self.base_path} does not exist.")
            return

        for root, _, files in os.walk(self.base_path):
            for file in files:
                if file.endswith(('.yaml', '.yml')):
                    path = Path(root) / file
                    self._load_file(path)

    def _load_file(self, path: Path) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            # Basic validation
            if not isinstance(data, dict) or "capability" not in data:
                logger.error(f"Invalid capability manifest in {path}: missing 'capability' key.")
                return

            definition = CapabilityDefinition(**data)
            self.definitions[definition.capability] = definition
            logger.info("capability.discovered", name=definition.capability, provider=definition.provider)
            
        except Exception as e:
            logger.error(f"Error loading capability from {path}: {e}")

    def get(self, name: str) -> CapabilityDefinition | None:
        return self.definitions.get(name)

    def list(self) -> list[CapabilityDefinition]:
        return list(self.definitions.values())

capability_discovery = CapabilityDiscovery()

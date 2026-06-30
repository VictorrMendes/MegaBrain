from typing import Any, Dict, List
from kernel.logger import get_logger
from kernel.plugins.plugin_manager import plugin_manager

logger = get_logger(__name__)

class MissingParameter:
    def __init__(self, name: str, description: str, type: str):
        self.name = name
        self.description = description
        self.type = type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type
        }

class ParameterResolver:
    """
    Pure component responsible for deterministically resolving and validating
    the payload against a capability's schema.
    Does NOT use LLM, WorldState, or Context.
    """

    def resolve(self, capability_name: str, payload: Dict[str, Any]) -> List[MissingParameter]:
        """
        Validates the payload against the capability schema.
        Returns a list of MissingParameter objects if any are missing or invalid.
        """
        # 1. Fetch Capability from Plugins
        capability = self._get_capability(capability_name)
        if not capability:
            logger.error("parameter_resolver.capability_not_found", capability=capability_name)
            raise ValueError(f"Capability '{capability_name}' not found in any loaded plugin.")

        schema = capability.get("schema", {})
        
        logger.info("parameter_resolver.debug_schema", capability=capability_name, payload=payload, schema=schema)
        
        if not schema:
            # No schema means no parameters required
            return []

        # 2. Determine Required Fields
        properties = schema.get("properties", {})
        required_fields = schema.get("required", list(properties.keys()))

        missing_params = []

        # 3. Check for Missing Required Fields
        for field in required_fields:
            if field not in payload or payload[field] is None or payload[field] == "":
                prop_details = properties.get(field, {})
                desc = prop_details.get("description", f"Parameter {field}")
                type_ = prop_details.get("type", "string")
                missing_params.append(MissingParameter(name=field, description=desc, type=type_))


        logger.info("parameter_resolver.debug_missing", missing=[p.name for p in missing_params])
        return missing_params

    def _get_capability(self, capability_name: str) -> Dict[str, Any]:
        for plugin_name, manifest in plugin_manager.plugins.items():
            caps = manifest.get("loaded_capabilities", {})
            if capability_name in caps:
                return caps[capability_name]
        return {}

parameter_resolver = ParameterResolver()

from typing import Any, Dict
from kernel.logger import get_logger
from models.execution import NodeType
from kernel.orchestrator.ir_compiler import ExecutionIR, IRNode
from kernel.plugins.plugin_manager import plugin_manager

logger = get_logger(__name__)

class CapabilityResolver:
    """
    Resolves abstract Intent into concrete Capabilities.
    e.g. `Task(type="SendMessage")` -> `n8n.communication.send_message`
    """
    
    async def resolve(self, abstract_ir: ExecutionIR, world_state: Dict[str, Any]) -> ExecutionIR:
        """
        Takes the Optimized Abstract IR and resolves every abstract action
        into a concrete Provider capability based on the active Registry and WorldState.
        """
        logger.info("capability_resolver.resolving")
        
        # Ensure plugins are loaded
        if not plugin_manager.plugins:
            plugin_manager.load_all()
            
        await self._resolve_node(abstract_ir.root, world_state)
        
        return abstract_ir
        
    async def _resolve_node(self, node: IRNode, world_state: Dict[str, Any]) -> None:
        """
        Recursively traverses the IR tree and resolves TASK nodes.
        """
        if node.type == "TASK":
            abstract_intent = getattr(node, "capability", "")
            found = False
            
            # Search across all loaded plugins
            for plugin_name, manifest in plugin_manager.plugins.items():
                caps = manifest.get("loaded_capabilities", {})
                for cap_key, cap_data in caps.items():
                    if cap_data.get("abstract_intent", "").lower() == abstract_intent.lower():
                        node.capability = cap_data.get("name")
                        found = True
                        logger.debug("capability_resolver.match_found", abstract=abstract_intent, concrete=node.capability)
                        break
                if found:
                    break
                    
            if not found:
                logger.warning("capability_resolver.no_match", abstract=abstract_intent)
                
        elif node.type == "SEQUENCE":
            for child in getattr(node, "nodes", []):
                await self._resolve_node(child, world_state)
                
        elif node.type == "PARALLEL":
            for branch in getattr(node, "branches", []):
                for child in branch:
                    await self._resolve_node(child, world_state)
                    
        elif node.type == "CONDITIONAL":
            for child in getattr(node, "true_branch", []):
                await self._resolve_node(child, world_state)
            for child in getattr(node, "false_branch", []):
                await self._resolve_node(child, world_state)

capability_resolver = CapabilityResolver()

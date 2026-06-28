from typing import Any, Dict
from kernel.logger import get_logger
from kernel.orchestrator.ir_compiler import ExecutionIR, IRNode, NodeType
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
        logger.info("capability_resolver.resolving", ir_id=abstract_ir.id)
        
        # Ensure plugins are loaded
        if not plugin_manager.plugins:
            plugin_manager.load_all()
            
        resolved_nodes = await self._resolve_nodes(abstract_ir.nodes, world_state)
        
        return ExecutionIR(
            id=abstract_ir.id,
            workspace_id=abstract_ir.workspace_id,
            nodes=resolved_nodes
        )
        
    async def _resolve_nodes(self, nodes: list[IRNode], world_state: Dict[str, Any]) -> list[IRNode]:
        """
        Resolves abstract capabilities by matching 'abstract_intent' in loaded plugins.
        """
        resolved = []
        for node in nodes:
            if node.type == NodeType.ACTION:
                abstract_intent = node.capability
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
                    
            if node.children:
                node.children = await self._resolve_nodes(node.children, world_state)
                
            resolved.append(node)
            
        return resolved

capability_resolver = CapabilityResolver()

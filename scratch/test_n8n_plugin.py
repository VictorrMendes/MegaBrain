import asyncio
import os
import sys

# Add project root to path
api_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
sys.path.insert(0, api_path)

from kernel.plugins.plugin_manager import plugin_manager
from kernel.orchestrator.ir_compiler import ExecutionIR, IRNode, NodeType
from kernel.orchestrator.capability_resolver import capability_resolver
from kernel.runtime.dispatcher import dispatcher

async def main():
    # 1. Load Plugins
    print("Loading plugins...")
    plugin_manager.load_all()
    print("Loaded plugins:", plugin_manager.plugins.keys())
    
    # 2. Create Abstract IR Node
    ir = ExecutionIR(
        id="test-ir",
        workspace_id="test-workspace",
        nodes=[
            IRNode(
                id="test-node-1",
                type=NodeType.ACTION,
                capability="ScrapeWebsite",  # Abstract Intent
                payload={
                    "url": "https://example.com"
                }
            )
        ]
    )
    
    # 3. Resolve Capability
    print("\nResolving abstract IR...")
    resolved_ir = await capability_resolver.resolve(ir, {})
    resolved_node = resolved_ir.nodes[0]
    print(f"Resolved capability: {resolved_node.capability}")
    
    # 4. Map to ExecutionNode
    from models.execution import ExecutionNode
    exec_node = ExecutionNode(
        id="test-exec-1",
        capability=resolved_node.capability,
        payload=resolved_node.payload
    )
    
    # 5. Dispatch
    print("\nDispatching to driver...")
    try:
        await dispatcher.dispatch(exec_node, "test-workspace")
        print("Dispatch successful!")
    except Exception as e:
        print(f"Dispatch failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())

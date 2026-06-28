import asyncio
import os
import sys

# Ensure api directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api")))

from kernel.runtime.dispatcher import dispatcher
from models.execution import ExecutionNode, NodeType

# We load plugins to register capabilities and drivers
from kernel.plugins import plugin_manager
plugin_manager.scan_plugins()

WORKFLOWS = [
    "ai.image_generate",
    "browser.open_url",
    "browser.scrape",
    "calendar.create_event",
    "calendar.list_events",
    "communication.send_email",
    "communication.send_message",
    "docker.container_control",
    "filesystem.read",
    "filesystem.write",
    "iot.device_control",
    "knowledge.capture",
    "knowledge.search",
    "productivity.create_task",
    "sdk.echo",
    "system.notification"
]

async def main():
    print("🚀 Starting N8N Healthcheck (Test Mode)...\n")
    
    # Ensure test mode is active for the diagnostic
    os.environ["N8N_TEST_MODE"] = "true"
    
    success_count = 0
    fail_count = 0
    
    for wf in WORKFLOWS:
        node = ExecutionNode(
            id=f"test-{wf}",
            type=NodeType.ACTION,
            capability=f"n8n.{wf}",
            payload={"_healthcheck": True, "message": "ping"}
        )
        
        print(f"Testing {wf}...")
        try:
            # We bypass the LLM and the CapabilityResolver, and directly ask the Dispatcher
            # to route the Node to the Driver based on the capability name
            await dispatcher.dispatch(node, workspace_id="healthcheck-ws-1234")
            
            if node.error:
                print(f"  ❌ FAILED: {node.error}")
                fail_count += 1
            else:
                print(f"  ✅ SUCCESS: HTTP 200 OK")
                success_count += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            fail_count += 1
            
    print("\n📊 Healthcheck Summary")
    print(f"Total Workflows: {len(WORKFLOWS)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    asyncio.run(main())

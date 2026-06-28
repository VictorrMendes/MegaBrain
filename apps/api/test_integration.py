import asyncio
import os
from engines.integration.identity.oauth import OAuthManager
from engines.integration.providers.mock_provider import MockProvider, MockOAuthProvider
from engines.integration.snapshot import RuntimeSnapshotBuilder
from engines.integration.event_bus import event_bus
from kernel.capabilities.registry import capability_registry, Capability

async def main():
    print("1. Registering Mock OAuth Provider...")
    # Setup dummy env for SecretStore
    os.environ["MOCK_CLIENT_ID"] = "mock_client"
    os.environ["MOCK_CLIENT_SECRET"] = "mock_secret"
    
    oauth_provider = MockOAuthProvider()
    OAuthManager.register_provider(oauth_provider)
    
    print("2. Simulating OAuth Exchange...")
    tokens = await oauth_provider.exchange_code("fake_code", "http://localhost/callback")
    print(f"   Tokens received: {tokens['access_token']}")
    
    print("3. Instantiating MockProvider and registering capabilities...")
    provider = MockProvider()
    
    # Simulate Capability Registry registration based on manifest
    for cap in provider.manifest.capabilities:
        c = Capability(
            name=cap.id,
            description=cap.description,
            plugin=provider.id,
            mutability=cap.mutability
        )
        capability_registry.register(c)
        
    print(f"   Capabilities registered: {capability_registry.list_names()}")
    
    print("4. Testing EventBus subscription...")
    received_events = []
    def on_pinged(name, payload):
        received_events.append(payload)
        print(f"   [EventBus] Received {name}: {payload}")
        
    event_bus.subscribe("mock.pinged", on_pinged)
    
    print("5. Executing capability 'mock.ping'...")
    res = await provider.execute_capability("mock.ping", {})
    print(f"   Result: {res}")
    
    # Wait a tiny bit for async event bus to process
    await asyncio.sleep(0.1)
    
    print("6. Testing IntegrationSnapshot generation...")
    snapshot = await provider.generate_snapshot()
    RuntimeSnapshotBuilder.update_snapshot(snapshot)
    
    valid_snapshots = RuntimeSnapshotBuilder.get_valid_snapshots()
    print(f"   Valid Snapshots in LifeContext: {[s.id for s in valid_snapshots]}")
    print("Validation Complete. All systems GO.")

if __name__ == "__main__":
    asyncio.run(main())

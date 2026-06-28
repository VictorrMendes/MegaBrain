from typing import Any, Dict
from datetime import datetime, timezone, timedelta
from engines.integration.provider import BaseProvider
from engines.integration.connector import BaseConnector
from engines.integration.manifest import IntegrationManifest, CapabilityManifest
from engines.integration.snapshot import IntegrationSnapshot
from engines.integration.identity.oauth import BaseOAuthProvider

mock_manifest = IntegrationManifest(
    id="mock",
    name="Mock Integration",
    version="1.0.0",
    connectors=["oauth"],
    capabilities=[
        CapabilityManifest(
            id="mock.ping",
            description="Ping the mock provider.",
            mutability="READ"
        ),
        CapabilityManifest(
            id="mock.mutate",
            description="Mutate data in mock provider.",
            mutability="WRITE",
            approval_required=True
        )
    ],
    snapshots=["mock"],
    events=["mock.pinged"]
)

class MockConnector(BaseConnector):
    def __init__(self):
        super().__init__(base_url="https://mock.api.local")
        
    async def _get_auth_headers(self) -> Dict[str, str]:
        return {"Authorization": "Bearer fake_token"}
        
    async def get(self, endpoint: str, params: Dict[str, Any] | None = None) -> Any:
        return {"status": "ok", "mock_data": True}

class MockOAuthProvider(BaseOAuthProvider):
    @property
    def provider_id(self) -> str:
        return "mock"
        
    @property
    def authorization_url(self) -> str:
        return "https://mock.api.local/oauth/authorize"
        
    @property
    def token_url(self) -> str:
        return "https://mock.api.local/oauth/token"
        
    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        return {
            "access_token": "mock_access",
            "refresh_token": "mock_refresh",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
        }

class MockProvider(BaseProvider):
    def __init__(self):
        super().__init__(manifest=mock_manifest)
        self.connector = MockConnector()
        
    async def execute_capability(self, capability_id: str, payload: Dict[str, Any]) -> Any:
        if capability_id == "mock.ping":
            await self.publish_event("mock.pinged", {"timestamp": str(datetime.now())})
            return {"result": "pong"}
        return {"error": "unknown capability"}
        
    async def generate_snapshot(self) -> IntegrationSnapshot:
        return IntegrationSnapshot(
            id="mock_snapshot_1",
            provider=self.id,
            category="mock",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            health="ok",
            payload={"ping_count": 42}
        )

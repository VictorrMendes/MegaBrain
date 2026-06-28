import httpx
from datetime import datetime, timezone
from typing import Any, Dict

from engines.integration.base import IntegrationProvider, IntegrationRegistry, ConnectResult, SyncResult
from engines.integration.identity.oauth import BaseOAuthProvider
from models.integration import ConnectedAccount, IntegrationCategory, IntegrationHealth, SyncMode

class GoogleOAuthProvider(BaseOAuthProvider):
    @property
    def provider_id(self) -> str:
        return "google"
        
    @property
    def authorization_url(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"
        
    @property
    def token_url(self) -> str:
        return "https://oauth2.googleapis.com/token"

    async def get_profile(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if resp.status_code != 200:
                return {"name": "Google Account"}
            data = resp.json()
            return {
                "name": data.get("name", "Google Account"),
                "email": data.get("email")
            }

@IntegrationRegistry.register
class GoogleWorkspaceProvider(IntegrationProvider):
    slug = "google"
    name = "Google Workspace"
    description = "Integração completa com serviços do Google Workspace (Calendar, Gmail, etc.)"
    category = IntegrationCategory.productivity
    icon = "G"
    sync_strategy = SyncMode.scheduled
    
    capabilities = [
        "calendar.list_events",
        "calendar.get_event",
        "calendar.create_event",
        "calendar.update_event",
        "calendar.delete_event"
    ]
    supported_events = []
    
    @property
    def oauth_provider(self):
        return GoogleOAuthProvider()
        
    @property
    def scopes(self):
        return [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events"
        ]

    async def connect(self, config: dict) -> ConnectResult:
        # Since OAuth happens externally, this is called by oauth_callback with the tokens
        return ConnectResult(
            account_name=config.get("account_name_override", "Google Account"),
            account_email=config.get("account_email"),
            scopes=self.scopes,
            config=config, # Save encrypted tokens
        )

    async def sync(self, account: ConnectedAccount, since: datetime | None = None) -> SyncResult:
        from engines.integration.identity.token_manager import token_manager
        from engines.integration.connectors.google_calendar import GoogleCalendarConnector
        
        # Access token is stored encrypted in account.config
        encrypted_token = account.config.get("access_token_encrypted")
        if not encrypted_token:
            return SyncResult(error_message="Missing access token")
            
        access_token = token_manager.decrypt(encrypted_token)
        connector = GoogleCalendarConnector(access_token)
        
        try:
            # fetch today's events for the snapshot
            events_response = await connector.list_events(max_results=5)
            events = events_response.get("items", [])
            
            lines = [f"Eventos agendados no Calendar: {len(events)} próximos"]
            for event in events:
                summary = event.get("summary", "Sem título")
                start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
                if start:
                    lines.append(f"- {summary} ({start})")
                
            return SyncResult(
                items_synced=len(events),
                life_context_lines=lines,
                metadata={"next_events_count": len(events)}
            )
        except Exception as e:
            return SyncResult(error_message=str(e))

    async def health(self, account: ConnectedAccount | None) -> IntegrationHealth:
        if not account:
            return IntegrationHealth.unknown
            
        from engines.integration.identity.token_manager import token_manager
        from engines.integration.connectors.google_calendar import GoogleCalendarConnector
        
        encrypted_token = account.config.get("access_token_encrypted")
        if not encrypted_token:
            return IntegrationHealth.unhealthy
            
        access_token = token_manager.decrypt(encrypted_token)
        connector = GoogleCalendarConnector(access_token)
        
        try:
            await connector.list_events(max_results=1)
            return IntegrationHealth.healthy
        except Exception:
            return IntegrationHealth.unhealthy

    async def execute(self, capability: str, params: dict, account: ConnectedAccount | None) -> dict:
        if not account:
            return {"error": "Account not provided"}
            
        from engines.integration.identity.token_manager import token_manager
        from engines.integration.connectors.google_calendar import GoogleCalendarConnector
        
        encrypted_token = account.config.get("access_token_encrypted")
        access_token = token_manager.decrypt(encrypted_token)
        connector = GoogleCalendarConnector(access_token)
        
        if capability == "calendar.list_events":
            return await connector.list_events(
                calendar_id=params.get("calendar_id", "primary"),
                time_min=params.get("time_min"),
                max_results=params.get("max_results", 10)
            )
        elif capability == "calendar.get_event":
            return await connector.get_event(
                event_id=params["event_id"],
                calendar_id=params.get("calendar_id", "primary")
            )
        elif capability == "calendar.create_event":
            return await connector.create_event(
                event_data=params["event_data"],
                calendar_id=params.get("calendar_id", "primary")
            )
        elif capability == "calendar.update_event":
            return await connector.update_event(
                event_id=params["event_id"],
                event_data=params["event_data"],
                calendar_id=params.get("calendar_id", "primary")
            )
        elif capability == "calendar.delete_event":
            await connector.delete_event(
                event_id=params["event_id"],
                calendar_id=params.get("calendar_id", "primary")
            )
            return {"status": "deleted"}
            
        return {"error": "Capability not implemented"}

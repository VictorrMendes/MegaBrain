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

    async def _ensure_valid_token(self, account: ConnectedAccount) -> str:
        from datetime import datetime, timezone
        from engines.integration.identity.token_manager import token_manager
        from core.database import AsyncSessionLocal
        
        expires_at_str = account.config.get("token_expires_at") if account.config else None
        refresh_token_enc = account.config.get("refresh_token_encrypted") if account.config else None
        
        needs_refresh = False
        if expires_at_str and refresh_token_enc:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if (expires_at - datetime.now(timezone.utc)).total_seconds() < 300:
                    needs_refresh = True
            except ValueError:
                needs_refresh = True
        else:
            # If we don't have expiration but have refresh token, we'll wait for a 401
            # But normally we always have expires_at from oauth_callback
            pass
            
        if needs_refresh and refresh_token_enc:
            refresh_token = token_manager.decrypt(refresh_token_enc)
            async with AsyncSessionLocal() as session:
                new_tokens = await self.oauth_provider.refresh_token(session, refresh_token)
                
            access_token = token_manager.encrypt(new_tokens["access_token"])
            account.config["access_token_encrypted"] = access_token
            
            if "refresh_token" in new_tokens and new_tokens["refresh_token"]:
                account.config["refresh_token_encrypted"] = token_manager.encrypt(new_tokens["refresh_token"])
                
            if "expires_at" in new_tokens and new_tokens["expires_at"]:
                account.config["token_expires_at"] = new_tokens["expires_at"].isoformat()
                
            # Update the database
            async with AsyncSessionLocal() as session:
                from models.integration import ConnectedAccount as CA
                acct = await session.get(CA, account.id)
                if acct:
                    acct.config = dict(account.config)
                    await session.commit()
                    
        return token_manager.decrypt(account.config["access_token_encrypted"])

    async def sync(self, account: ConnectedAccount | None, since: datetime | None = None) -> SyncResult:
        if not account:
            return SyncResult(error_message="No active connected account found")
            
        from engines.integration.connectors.google_calendar import GoogleCalendarConnector
        
        try:
            access_token = await self._ensure_valid_token(account)
        except Exception as e:
            return SyncResult(error_message=f"Failed to refresh token: {e}")
            
        connector = GoogleCalendarConnector(access_token)
        
        try:
            # fetch today's events for the snapshot
            events_response = await connector.list_events(max_results=5)
            events = events_response.get("items", [])
            
            return SyncResult(
                items_synced=len(events),
                life_context_lines=[
                    f"Resumo da Agenda (Google Calendar):",
                    f"- Eventos recuperados: {len(events)}",
                    f"- Próximo evento: {events[0].get('summary') if events else 'Nenhum'}"
                ],
                metadata={"next_events_count": len(events)}
            )
        except Exception as e:
            return SyncResult(error_message=str(e))

    async def health(self, account: ConnectedAccount | None) -> IntegrationHealth:
        if not account:
            return IntegrationHealth.unknown
            
        from engines.integration.connectors.google_calendar import GoogleCalendarConnector
        
        try:
            access_token = await self._ensure_valid_token(account)
            connector = GoogleCalendarConnector(access_token)
        except Exception:
            return IntegrationHealth.unhealthy
        
        try:
            await connector.list_events(max_results=1)
            return IntegrationHealth.healthy
        except Exception:
            return IntegrationHealth.unhealthy

    async def execute(self, capability: str, params: dict, account: ConnectedAccount | None) -> dict:
        if not account:
            return {"error": "Account not provided"}
            
        from engines.integration.connectors.google_calendar import GoogleCalendarConnector
        
        try:
            access_token = await self._ensure_valid_token(account)
        except Exception as e:
            return {"error": f"Auth failed: {e}"}
            
        connector = GoogleCalendarConnector(access_token)
        
        if capability == "calendar.list_events":
            import logging
            log = logging.getLogger("khonshu.provider.google")
            log.info(f"[RC-18E] Provider execute | capability: {capability} | params: {params}")
            
            time_min = params.get("time_min")
            if not time_min:
                raise ValueError("Missing temporal boundaries for list_events (time_min is required)")
                
            result = await connector.list_events(
                calendar_id=params.get("calendar_id", "primary"),
                time_min=time_min,
                time_max=params.get("time_max"),
                max_results=params.get("max_results", 10)
            )
            
            num_items = len(result.get("items", []))
            log.info(f"[RC-18E] Provider execute | return object has items: {num_items}")
            
            # Compress the payload to avoid exploding LLM context window
            lean_events = []
            for item in result.get("items", []):
                lean_events.append({
                    "id": item.get("id"),
                    "summary": item.get("summary", "Sem título"),
                    "start": item.get("start", {}).get("dateTime") or item.get("start", {}).get("date"),
                    "end": item.get("end", {}).get("dateTime") or item.get("end", {}).get("date"),
                    "status": item.get("status"),
                    "link": item.get("htmlLink")
                })
                
            return {"events": lean_events}
        elif capability == "calendar.get_event":
            return await connector.get_event(
                event_id=params["event_id"],
                calendar_id=params.get("calendar_id", "primary")
            )
        elif capability == "calendar.create_event":
            # Normalize event_data which could be passed inside params or as params itself
            event_data = dict(params.get("event_data", params))
            
            # Convert generic string start/end to Google's required dateTime format
            for field in ["start", "end"]:
                if field in event_data and isinstance(event_data[field], str):
                    val = event_data[field]
                    if "T" in val:
                        event_data[field] = {"dateTime": val}
                    else:
                        event_data[field] = {"date": val}
                    
            return await connector.create_event(
                event_data=event_data,
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

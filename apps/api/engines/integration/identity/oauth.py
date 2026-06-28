from abc import ABC, abstractmethod
from typing import Any, Dict
import httpx
from datetime import datetime, timezone, timedelta
from engines.integration.identity.secret_store import SecretStore

class BaseOAuthProvider(ABC):
    """Abstract base class for all OAuth providers."""
    
    @property
    @abstractmethod
    def provider_id(self) -> str:
        pass
        
    @property
    @abstractmethod
    def authorization_url(self) -> str:
        pass
        
    @property
    @abstractmethod
    def token_url(self) -> str:
        pass
        
    async def get_authorization_url(self, session: Any, redirect_uri: str, scopes: list[str], state: str) -> str:
        creds = await SecretStore.get_oauth_credentials(session, self.provider_id)
        scope_str = " ".join(scopes)
        return f"{self.authorization_url}?client_id={creds['client_id']}&redirect_uri={redirect_uri}&response_type=code&scope={scope_str}&state={state}&access_type=offline&prompt=consent"
        
    async def exchange_code(self, session: Any, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchanges an authorization code for access and refresh tokens."""
        creds = await SecretStore.get_oauth_credentials(session, self.provider_id)
        data = {
            "client_id": creds['client_id'],
            "client_secret": creds['client_secret'],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data=data)
            resp.raise_for_status()
            payload = resp.json()
            
            # Normalize expiration
            expires_in = payload.get("expires_in", 3600)
            payload["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            return payload
            
    async def refresh_token(self, session: Any, refresh_token: str) -> Dict[str, Any]:
        """Refreshes an expired access token using the refresh token."""
        creds = await SecretStore.get_oauth_credentials(session, self.provider_id)
        data = {
            "client_id": creds['client_id'],
            "client_secret": creds['client_secret'],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data=data)
            resp.raise_for_status()
            payload = resp.json()
            
            # Normalize expiration
            expires_in = payload.get("expires_in", 3600)
            payload["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            # Ensure we keep the old refresh token if the provider doesn't return a new one
            if "refresh_token" not in payload:
                payload["refresh_token"] = refresh_token
                
            return payload

class OAuthManager:
    """Factory and orchestrator for OAuth flows."""
    
    _providers: Dict[str, BaseOAuthProvider] = {}
    
    @classmethod
    def register_provider(cls, provider: BaseOAuthProvider):
        cls._providers[provider.provider_id] = provider
        
    @classmethod
    def get_provider(cls, provider_id: str) -> BaseOAuthProvider:
        if provider_id not in cls._providers:
            raise ValueError(f"OAuth Provider {provider_id} not registered.")
        return cls._providers[provider_id]

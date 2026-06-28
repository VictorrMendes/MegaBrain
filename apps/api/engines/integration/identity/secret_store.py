import os
import json
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

class SecretStore:
    """Provides secure access to client secrets and encryption keys."""

    @staticmethod
    def get_master_key() -> bytes:
        """Get the master key for token encryption (Fernet expects 32 url-safe base64-encoded bytes)."""
        key = os.environ.get("INTEGRATION_MASTER_KEY")
        if not key:
            # Fallback for dev only. In production, this MUST be set.
            logger.warning("INTEGRATION_MASTER_KEY not set. Using dev fallback key.")
            return b'qN-R-YjV5H3y_YtD_-zO-_y_T8w_A8-9s-X3mJ7k4g0='
        return key.encode('utf-8')

    @staticmethod
    async def get_oauth_credentials(session: AsyncSession, provider: str) -> dict[str, str]:
        """Get the Client ID and Client Secret for a specific provider from the database."""
        from engines.integration.identity.token_manager import token_manager
        from models.integration import IntegrationSecret
        
        stmt = select(IntegrationSecret).where(IntegrationSecret.provider == provider)
        result = await session.execute(stmt)
        secret = result.scalar_one_or_none()
        
        if not secret:
            logger.error(f"Missing OAuth credentials for provider {provider} in database")
            return {"client_id": "", "client_secret": ""}
            
        decrypted_payload = token_manager.decrypt(secret.encrypted_payload)
        data = json.loads(decrypted_payload)
        
        return {
            "client_id": data.get("client_id", ""),
            "client_secret": data.get("client_secret", "")
        }

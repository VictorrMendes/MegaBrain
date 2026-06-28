from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import json

from core.database import get_db
from models.integration import IntegrationSecret
from engines.integration.identity.token_manager import token_manager

router = APIRouter(prefix="/api/admin/secrets", tags=["admin", "secrets"])

class SecretPayload(BaseModel):
    provider: str
    payload: Dict[str, Any]

@router.get("/")
async def list_secrets(session: AsyncSession = Depends(get_db)):
    """List all registered secret providers."""
    stmt = select(IntegrationSecret.provider)
    result = await session.execute(stmt)
    providers = result.scalars().all()
    return {"providers": providers}

@router.post("/")
async def set_secret(secret_data: SecretPayload, session: AsyncSession = Depends(get_db)):
    """Create or update a secret for a provider."""
    # Encrypt the payload using the token manager
    payload_str = json.dumps(secret_data.payload)
    encrypted = token_manager.encrypt(payload_str)
    
    stmt = select(IntegrationSecret).where(IntegrationSecret.provider == secret_data.provider)
    result = await session.execute(stmt)
    secret = result.scalar_one_or_none()
    
    if secret:
        secret.encrypted_payload = encrypted
    else:
        secret = IntegrationSecret(
            provider=secret_data.provider,
            encrypted_payload=encrypted
        )
        session.add(secret)
        
    await session.commit()
    return {"status": "ok", "provider": secret_data.provider}
    
@router.delete("/{provider}")
async def delete_secret(provider: str, session: AsyncSession = Depends(get_db)):
    """Delete a secret for a provider."""
    stmt = select(IntegrationSecret).where(IntegrationSecret.provider == provider)
    result = await session.execute(stmt)
    secret = result.scalar_one_or_none()
    
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
        
    await session.delete(secret)
    await session.commit()
    return {"status": "ok"}

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from engines.integration.identity.oauth import BaseOAuthProvider
from engines.integration.identity.secret_store import SecretStore
from engines.integration.identity.token_manager import token_manager
from engines.integration import IntegrationManager
from engines.integration.base import IntegrationRegistry
from core.dependencies import get_integration_manager
import json
from uuid import UUID

router = APIRouter(prefix="/integrations/oauth", tags=["oauth"])

@router.get("/connect/{workspace_id}/{slug}")
async def connect_oauth(
    request: Request,
    workspace_id: UUID,
    slug: str,
    session: AsyncSession = Depends(get_session)
):
    """Initiate the OAuth flow for a provider."""
    provider_cls = IntegrationRegistry.get(slug)
    if not provider_cls:
        raise HTTPException(status_code=404, detail=f"Provider {slug} not found")
        
    provider_instance = provider_cls()
    if not hasattr(provider_instance, "oauth_provider"):
        raise HTTPException(status_code=400, detail=f"Provider {slug} does not support OAuth")
        
    oauth_provider = provider_instance.oauth_provider
    # Generate authorization URL
    # State should ideally be a signed JWT containing workspace_id and slug
    state = json.dumps({"workspace_id": str(workspace_id), "slug": slug})
    
    # Needs a redirect URI registered with the provider
    # By default, use the request base URL to construct the callback
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/integrations/oauth/callback"
    
    url = await oauth_provider.get_authorization_url(
        session=session, 
        redirect_uri=redirect_uri, 
        scopes=provider_instance.scopes, 
        state=state
    )
    return RedirectResponse(url)

@router.get("/callback")
async def oauth_callback(
    request: Request,
    manager: IntegrationManager = Depends(get_integration_manager),
    session: AsyncSession = Depends(get_session)
):
    """Handle the OAuth callback from the provider."""
    code = request.query_params.get("code")
    state_str = request.query_params.get("state")
    
    if not code or not state_str:
        raise HTTPException(status_code=400, detail="Missing code or state")
        
    try:
        state = json.loads(state_str)
        workspace_id = UUID(state["workspace_id"])
        slug = state["slug"]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid state")
        
    provider_cls = IntegrationRegistry.get(slug)
    if not provider_cls:
        raise HTTPException(status_code=404, detail=f"Provider {slug} not found")
        
    provider_instance = provider_cls()
    oauth_provider = provider_instance.oauth_provider
    
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/integrations/oauth/callback"
    
    try:
        token_data = await oauth_provider.exchange_code(
            session=session,
            code=code,
            redirect_uri=redirect_uri
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {e}")
        
    # Extract identity from token (e.g. email) if available, or fetch profile
    profile = await oauth_provider.get_profile(token_data["access_token"])
    account_email = profile.get("email")
    account_name = profile.get("name", f"{slug} Account")
    
    # Encrypt tokens
    access_token = token_manager.encrypt(token_data["access_token"])
    refresh_token = token_manager.encrypt(token_data["refresh_token"]) if token_data.get("refresh_token") else None
    
    # We use connect method from manager, passing the tokens as config
    # The provider will need to handle this config
    config = {
        "access_token_encrypted": access_token,
        "refresh_token_encrypted": refresh_token,
        "token_expires_at": token_data.get("expires_at").isoformat() if token_data.get("expires_at") else None,
        "account_email": account_email
    }
    
    await manager.connect(
        workspace_id=workspace_id,
        slug=slug,
        config=config,
        account_name_override=account_name
    )
    
    # Redirect back to frontend
    return RedirectResponse("http://localhost:3100/settings/integrations")

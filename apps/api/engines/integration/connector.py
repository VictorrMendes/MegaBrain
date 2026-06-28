from abc import ABC
from typing import Any, Dict, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

class BaseConnector(ABC):
    """Handles external HTTP communication, auth headers, and rate limits."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Override this to provide OAuth headers."""
        return {}

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> Any:
        return await self._request("POST", endpoint, json=json)
        
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Centralized request handler for retries and rate limiting."""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        auth_headers = await self._get_auth_headers()
        headers.update(auth_headers)
        
        # In a complete implementation, this would handle 429 Too Many Requests,
        # automatic retries, and token refresh interceptors.
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP {e.response.status_code} on {method} {url}: {e.response.text}")
                raise

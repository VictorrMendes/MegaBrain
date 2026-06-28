from typing import Any, Dict, Optional
from datetime import datetime, timezone
import httpx
from engines.integration.connector import BaseConnector

class GoogleCalendarConnector(BaseConnector):
    def __init__(self, access_token: str):
        super().__init__(base_url="https://www.googleapis.com/calendar/v3")
        self.access_token = access_token
        
    async def _get_auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def list_events(self, calendar_id: str = "primary", time_min: Optional[str] = None, time_max: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
        params = {
            "maxResults": max_results,
            "singleEvents": "true",
            "orderBy": "startTime"
        }
        if time_min:
            params["timeMin"] = time_min
        else:
            params["timeMin"] = datetime.now(timezone.utc).isoformat()
            
        if time_max:
            params["timeMax"] = time_max
            
        return await self.get(f"/calendars/{calendar_id}/events", params=params)

    async def get_event(self, event_id: str, calendar_id: str = "primary") -> Dict[str, Any]:
        return await self.get(f"/calendars/{calendar_id}/events/{event_id}")

    async def create_event(self, event_data: Dict[str, Any], calendar_id: str = "primary") -> Dict[str, Any]:
        return await self.post(f"/calendars/{calendar_id}/events", json=event_data)
        
    async def update_event(self, event_id: str, event_data: Dict[str, Any], calendar_id: str = "primary") -> Dict[str, Any]:
        return await self._request("PATCH", f"/calendars/{calendar_id}/events/{event_id}", json=event_data)

    async def delete_event(self, event_id: str, calendar_id: str = "primary") -> Any:
        url = f"{self.base_url}/calendars/{calendar_id}/events/{event_id}"
        headers = await self._get_auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=headers)
            resp.raise_for_status()
            return True

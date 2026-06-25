from datetime import datetime, timezone

import httpx

from kernel.plugins.base import Plugin, PluginRegistry, PluginResult

_BASE = "https://www.googleapis.com/calendar/v3/calendars"


@PluginRegistry.register
class GoogleCalendarPlugin(Plugin):
    name = "google_calendar"
    description = "Cria e consulta eventos no Google Calendar via OAuth2 access token"

    async def execute(self, action: str, params: dict) -> PluginResult:
        token = self.config.get("access_token", "")
        calendar_id = self.config.get("calendar_id", "primary")
        tz = self.config.get("timezone", "America/Sao_Paulo")
        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if action == "list_events":
                    time_min = params.get(
                        "time_min",
                        datetime.now(timezone.utc).isoformat(),
                    )
                    resp = await client.get(
                        f"{_BASE}/{calendar_id}/events",
                        params={
                            "timeMin": time_min,
                            "maxResults": params.get("max_results", 10),
                            "singleEvents": "true",
                            "orderBy": "startTime",
                        },
                        headers=headers,
                    )
                    resp.raise_for_status()
                    events = resp.json().get("items", [])
                    return PluginResult(success=True, data={"events": [
                        {
                            "id": e["id"],
                            "summary": e.get("summary", ""),
                            "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")),
                            "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date", "")),
                            "description": e.get("description", ""),
                        }
                        for e in events
                    ]})

                elif action == "create_event":
                    resp = await client.post(
                        f"{_BASE}/{calendar_id}/events",
                        json={
                            "summary": params.get("title", ""),
                            "description": params.get("description", ""),
                            "start": {"dateTime": params["start"], "timeZone": tz},
                            "end": {"dateTime": params["end"], "timeZone": tz},
                        },
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return PluginResult(success=True, data={
                        "id": data["id"],
                        "htmlLink": data.get("htmlLink", ""),
                    })

                else:
                    return PluginResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            return PluginResult(success=False, error=str(e))

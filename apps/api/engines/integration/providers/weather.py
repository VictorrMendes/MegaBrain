"""Weather integration provider.

Uses wttr.in (free, no API key required).
Config: {"location": "Sao Paulo"}
"""
from __future__ import annotations

from datetime import datetime

import httpx

from engines.integration.base import (
    ConnectResult,
    IntegrationProvider,
    IntegrationRegistry,
    SyncResult,
)
from models.integration import (
    ConnectedAccount,
    IntegrationCategory,
    IntegrationHealth,
    SyncMode,
)

_TIMEOUT = 15.0


@IntegrationRegistry.register
class WeatherProvider(IntegrationProvider):
    slug = "weather"
    name = "Clima"
    description = "Previsão do tempo e contexto climático via wttr.in"
    category = IntegrationCategory.information
    icon = "🌤️"
    sync_strategy = SyncMode.scheduled
    capabilities = ["weather.current", "weather.forecast"]
    supported_events = []

    async def connect(self, config: dict) -> ConnectResult:
        location = config.get("location", "")
        if not location:
            return ConnectResult(
                account_name="wttr.in",
                error="'location' é obrigatório (ex: 'Sao Paulo')",
            )
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    f"https://wttr.in/{location}",
                    params={"format": "j1"},
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
            area = data.get("nearest_area", [{}])[0]
            city = area.get("areaName", [{}])[0].get("value", location)
            return ConnectResult(
                account_name=f"Clima — {city}",
                config={"location": location, "resolved_city": city},
            )
        except Exception as exc:
            return ConnectResult(
                account_name="wttr.in", error=str(exc)
            )

    async def sync(
        self,
        account: ConnectedAccount | None,
        since: datetime | None = None,
    ) -> SyncResult:
        location = (
            (account.config.get("location") if account else None)
            or "Sao Paulo"
        )
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    f"https://wttr.in/{location}",
                    params={"format": "j1"},
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            return SyncResult(
                error_message=f"wttr.in error: {exc}",
                life_context_lines=["Clima: dados indisponíveis"],
            )

        current = data["current_condition"][0]
        area = data.get("nearest_area", [{}])[0]
        city = area.get("areaName", [{}])[0].get("value", location)
        temp = int(current["temp_C"])
        desc = current["weatherDesc"][0]["value"]
        humidity = int(current["humidity"])
        wind = int(current["windspeedKmph"])

        # Tomorrow forecast (index 1 of weather array)
        weather_days = data.get("weather", [])
        tomorrow_line = ""
        if len(weather_days) > 1:
            tmr = weather_days[1]
            tmr_max = int(tmr.get("maxtempC", "?"))
            tmr_min = int(tmr.get("mintempC", "?"))
            tmr_desc = (
                tmr.get("hourly", [{}])[4]
                .get("weatherDesc", [{}])[0]
                .get("value", "")
            )
            tomorrow_line = (
                f"Clima amanhã em {city}: {tmr_min}–{tmr_max}°C, {tmr_desc}"
            )

        lines = [
            f"Clima em {city}: {temp}°C, {desc} "
            f"(umidade {humidity}%, vento {wind} km/h)",
        ]
        if tomorrow_line:
            lines.append(tomorrow_line)

        return SyncResult(
            items_synced=1,
            life_context_lines=lines,
            metadata={
                "city": city,
                "temp_c": temp,
                "description": desc,
                "humidity": humidity,
                "wind_kmph": wind,
            },
        )

    async def health(
        self, account: ConnectedAccount | None
    ) -> IntegrationHealth:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://wttr.in/London",
                    params={"format": "j1"},
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 200:
                    return IntegrationHealth.healthy
                return IntegrationHealth.degraded
        except Exception:
            return IntegrationHealth.unhealthy

    async def execute(
        self,
        capability: str,
        params: dict,
        account: ConnectedAccount | None,
    ) -> dict:
        location = (
            params.get("location")
            or (account.config.get("location") if account else None)
            or "Sao Paulo"
        )
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"https://wttr.in/{location}",
                params={"format": "j1"},
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        current = data["current_condition"][0]
        area = data.get("nearest_area", [{}])[0]
        city = area.get("areaName", [{}])[0].get("value", location)

        return {
            "location": city,
            "temp_c": int(current["temp_C"]),
            "feels_like_c": int(current["FeelsLikeC"]),
            "description": current["weatherDesc"][0]["value"],
            "humidity": int(current["humidity"]),
            "wind_kmph": int(current["windspeedKmph"]),
        }

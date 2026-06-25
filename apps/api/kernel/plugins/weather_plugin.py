import httpx

from kernel.plugins.base import Plugin, PluginRegistry, PluginResult


@PluginRegistry.register
class WeatherPlugin(Plugin):
    name = "weather"
    description = "Consulta previsão do tempo via wttr.in (sem API key)"

    async def execute(self, action: str, params: dict) -> PluginResult:
        location = params.get("location") or self.config.get("default_location", "")
        if not location:
            return PluginResult(success=False, error="location required")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
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

            return PluginResult(
                success=True,
                data={
                    "location": city,
                    "temp_c": int(current["temp_C"]),
                    "feels_like_c": int(current["FeelsLikeC"]),
                    "description": current["weatherDesc"][0]["value"],
                    "humidity": int(current["humidity"]),
                    "wind_kmph": int(current["windspeedKmph"]),
                },
            )
        except Exception as e:
            return PluginResult(success=False, error=str(e))

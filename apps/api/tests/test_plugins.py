"""Tests for the plugin framework (PluginRegistry + individual plugins)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import kernel.plugins  # noqa: F401 — triggers @PluginRegistry.register decorators
from kernel.plugins.base import PluginRegistry
from kernel.plugins.home_assistant_plugin import HomeAssistantPlugin
from kernel.plugins.ntfy_plugin import NtfyPlugin
from kernel.plugins.weather_plugin import WeatherPlugin
from kernel.plugins.web_search_plugin import WebSearchPlugin


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _mock_http_client(response: MagicMock, method: str = "post") -> MagicMock:
    """Build a mock httpx.AsyncClient context manager."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    setattr(client, method, AsyncMock(return_value=response))
    return client


def _ok_response(json_data=None, status_code=200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if json_data is not None:
        resp.json = MagicMock(return_value=json_data)
    return resp


# ---------------------------------------------------------------------------
# PluginRegistry
# ---------------------------------------------------------------------------

class TestPluginRegistry:
    def test_all_six_plugins_registered(self):
        names = {p["name"] for p in PluginRegistry.list_all()}
        assert names >= {"ntfy", "weather", "web_search", "home_assistant", "notion", "google_calendar"}

    def test_get_returns_correct_class(self):
        assert PluginRegistry.get("ntfy") is NtfyPlugin
        assert PluginRegistry.get("weather") is WeatherPlugin

    def test_get_unknown_returns_none(self):
        assert PluginRegistry.get("does_not_exist") is None

    def test_list_all_has_name_and_description(self):
        for plugin in PluginRegistry.list_all():
            assert plugin["name"]
            assert plugin["description"]


# ---------------------------------------------------------------------------
# NtfyPlugin
# ---------------------------------------------------------------------------

class TestNtfyPlugin:
    async def test_notify_success(self):
        plugin = NtfyPlugin(config={"url": "http://ntfy.test", "topic": "alerts"})
        resp = _ok_response()
        client = _mock_http_client(resp, "post")

        with patch("kernel.plugins.ntfy_plugin.httpx.AsyncClient", return_value=client):
            result = await plugin.execute("notify", {"title": "Hi", "message": "Hello"})

        assert result.success is True
        assert result.data["status"] == 200
        client.post.assert_called_once()

    async def test_uses_global_settings_as_fallback(self):
        """Config without url/topic should fall back to settings defaults."""
        plugin = NtfyPlugin(config={})
        resp = _ok_response()
        client = _mock_http_client(resp, "post")

        with patch("kernel.plugins.ntfy_plugin.httpx.AsyncClient", return_value=client):
            result = await plugin.execute("notify", {"message": "test"})

        assert result.success is True

    async def test_unknown_action_returns_failure(self):
        plugin = NtfyPlugin(config={})
        result = await plugin.execute("send_sms", {})
        assert result.success is False
        assert "Unknown action" in (result.error or "")

    async def test_http_error_captured(self):
        plugin = NtfyPlugin(config={})
        client = _mock_http_client(MagicMock(), "post")
        client.post = AsyncMock(side_effect=Exception("timeout"))

        with patch("kernel.plugins.ntfy_plugin.httpx.AsyncClient", return_value=client):
            result = await plugin.execute("notify", {"message": "hi"})

        assert result.success is False
        assert "timeout" in (result.error or "")


# ---------------------------------------------------------------------------
# WeatherPlugin
# ---------------------------------------------------------------------------

class TestWeatherPlugin:
    _WEATHER_PAYLOAD = {
        "current_condition": [{
            "temp_C": "22",
            "FeelsLikeC": "24",
            "weatherDesc": [{"value": "Partly cloudy"}],
            "humidity": "70",
            "windspeedKmph": "15",
        }],
        "nearest_area": [{"areaName": [{"value": "São Paulo"}]}],
    }

    async def test_returns_weather_data(self):
        plugin = WeatherPlugin(config={})
        resp = _ok_response(self._WEATHER_PAYLOAD)
        client = _mock_http_client(resp, "get")

        with patch("kernel.plugins.weather_plugin.httpx.AsyncClient", return_value=client):
            result = await plugin.execute("get", {"location": "São Paulo"})

        assert result.success is True
        assert result.data["temp_c"] == 22
        assert result.data["description"] == "Partly cloudy"
        assert result.data["humidity"] == 70

    async def test_uses_default_location_from_config(self):
        plugin = WeatherPlugin(config={"default_location": "Rio de Janeiro"})
        resp = _ok_response(self._WEATHER_PAYLOAD)
        client = _mock_http_client(resp, "get")

        with patch("kernel.plugins.weather_plugin.httpx.AsyncClient", return_value=client):
            result = await plugin.execute("get", {})

        assert result.success is True
        call_args = client.get.call_args
        assert "Rio de Janeiro" in call_args.args[0]

    async def test_missing_location_returns_failure(self):
        plugin = WeatherPlugin(config={})
        result = await plugin.execute("get", {})
        assert result.success is False
        assert "location required" in (result.error or "")

    async def test_http_error_captured(self):
        plugin = WeatherPlugin(config={})
        client = _mock_http_client(MagicMock(), "get")
        client.get = AsyncMock(side_effect=Exception("network error"))

        with patch("kernel.plugins.weather_plugin.httpx.AsyncClient", return_value=client):
            result = await plugin.execute("get", {"location": "SP"})

        assert result.success is False


# ---------------------------------------------------------------------------
# WebSearchPlugin
# ---------------------------------------------------------------------------

class TestWebSearchPlugin:
    async def test_returns_results_from_abstract(self):
        plugin = WebSearchPlugin(config={})
        payload = {
            "AbstractText": "Python is a programming language.",
            "Heading": "Python",
            "AbstractURL": "https://python.org",
            "RelatedTopics": [],
        }
        resp = _ok_response(payload)
        client = _mock_http_client(resp, "get")

        with patch("kernel.plugins.web_search_plugin.httpx.AsyncClient", return_value=client):
            result = await plugin.execute("search", {"query": "python"})

        assert result.success is True
        assert len(result.data["results"]) >= 1
        assert result.data["results"][0]["title"] == "Python"

    async def test_empty_query_returns_failure(self):
        plugin = WebSearchPlugin(config={})
        result = await plugin.execute("search", {})
        assert result.success is False
        assert "query required" in (result.error or "")

    async def test_includes_related_topics(self):
        plugin = WebSearchPlugin(config={})
        payload = {
            "AbstractText": "",
            "Heading": "",
            "AbstractURL": "",
            "RelatedTopics": [
                {"Text": "Related result A", "FirstURL": "https://a.com"},
                {"Text": "Related result B", "FirstURL": "https://b.com"},
            ],
        }
        resp = _ok_response(payload)
        client = _mock_http_client(resp, "get")

        with patch("kernel.plugins.web_search_plugin.httpx.AsyncClient", return_value=client):
            result = await plugin.execute("search", {"query": "test"})

        assert result.success is True
        assert len(result.data["results"]) == 2


# ---------------------------------------------------------------------------
# HomeAssistantPlugin
# ---------------------------------------------------------------------------

class TestHomeAssistantPlugin:
    async def test_get_state_success(self):
        plugin = HomeAssistantPlugin(config={"url": "http://ha.local:8123", "token": "tok"})
        state_payload = {
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {"brightness": 200},
        }
        resp = _ok_response(state_payload)
        client = _mock_http_client(resp, "get")

        with patch("kernel.plugins.home_assistant_plugin.httpx.AsyncClient", return_value=client):
            result = await plugin.execute("get_state", {"entity_id": "light.living_room"})

        assert result.success is True
        assert result.data["state"] == "on"

    async def test_unknown_action_returns_failure(self):
        plugin = HomeAssistantPlugin(config={})
        result = await plugin.execute("reboot", {})
        assert result.success is False
        assert "Unknown action" in (result.error or "")

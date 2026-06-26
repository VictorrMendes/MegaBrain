"""Contract tests for PluginProvider (PluginEngine).

Any plugin loaded into the system must satisfy this contract: it must
register at least one Capability, all registered tools must be callable,
and unregistration must clean up completely.

Example:
    class TestDockerPlugin(BasePluginProviderContract):
        @pytest.fixture
        def plugin_engine(self, db_session_factory):
            return PluginEngine(session_factory=db_session_factory)

        @pytest.fixture
        def plugin_name(self):
            return "docker"
"""
from __future__ import annotations

import pytest

from kernel.capabilities import capability_registry


class BasePluginProviderContract:
    """Shared contract tests for any registered plugin."""

    @pytest.fixture
    def plugin_engine(self):
        raise NotImplementedError(
            "Subclass must override the `plugin_engine` fixture."
        )

    @pytest.fixture
    def plugin_name(self) -> str:
        raise NotImplementedError(
            "Subclass must override the `plugin_name` fixture."
        )

    def test_plugin_registers_capabilities(
        self, plugin_engine, plugin_name: str
    ) -> None:
        caps = [
            c for c in capability_registry.list()
            if c.plugin == plugin_name
        ]
        assert len(caps) > 0, (
            f"Plugin '{plugin_name}' must register at least one Capability"
        )

    def test_all_capabilities_have_description(
        self, plugin_engine, plugin_name: str
    ) -> None:
        for cap in capability_registry.list():
            if cap.plugin != plugin_name:
                continue
            assert cap.description.strip(), (
                f"Capability '{cap.name}' must have a non-empty description"
            )

    def test_all_tools_are_callable(
        self, plugin_engine, plugin_name: str
    ) -> None:
        for cap in capability_registry.list():
            if cap.plugin != plugin_name:
                continue
            for tool in cap.tools.values():
                assert callable(tool.fn), (
                    f"Tool '{tool.name}' in capability '{cap.name}'"
                    " must be callable"
                )

    def test_capability_has_valid_risk_level(
        self, plugin_engine, plugin_name: str
    ) -> None:
        from kernel.capabilities.registry import RiskLevel
        for cap in capability_registry.list():
            if cap.plugin != plugin_name:
                continue
            assert isinstance(cap.risk_level, RiskLevel), (
                f"Capability '{cap.name}' must have a valid RiskLevel"
            )

    def test_capability_confidence_score_in_range(
        self, plugin_engine, plugin_name: str
    ) -> None:
        for cap in capability_registry.list():
            if cap.plugin != plugin_name:
                continue
            assert 0.0 <= cap.confidence_score <= 1.0, (
                f"Capability '{cap.name}' confidence_score must be 0.0–1.0"
            )

    def test_capability_availability_in_range(
        self, plugin_engine, plugin_name: str
    ) -> None:
        for cap in capability_registry.list():
            if cap.plugin != plugin_name:
                continue
            assert 0.0 <= cap.availability <= 1.0, (
                f"Capability '{cap.name}' availability must be 0.0–1.0"
            )

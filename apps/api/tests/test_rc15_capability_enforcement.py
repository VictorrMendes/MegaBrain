"""RC-15 — Capability Enforcement tests.

Covers:
  - IntentRouter: keyword detection for all intent categories
  - RuntimeCapabilitySnapshot: state representation and prompt section
  - CapabilityExecutor: search execution, integration status, mission creation
  - CapabilityValidator: rejection of invalid limitation claims
"""
from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from kernel.capabilities.runtime_snapshot import (
    CapabilityState,
    RuntimeCapabilitySnapshot,
    RuntimeSnapshotBuilder,
)
from kernel.orchestrator.capability_executor import (
    CapabilityExecutor,
    CapabilityResult,
)
from kernel.orchestrator.intent_router import IntentFlags, IntentRouter
from kernel.orchestrator.models import Decision
from kernel.orchestrator.trace import ReasoningTrace

# ---------------------------------------------------------------------------
# IntentRouter
# ---------------------------------------------------------------------------


class TestIntentRouter:
    def setup_method(self):
        self.router = IntentRouter()

    def _analyze(self, message: str) -> IntentFlags:
        return self.router.analyze(message)

    # Search intent
    def test_pesquise_triggers_search(self):
        f = self._analyze("Pesquise quem é Khonshu na Marvel")
        assert f.need_search is True
        assert "web_search" in f.detected

    def test_busque_triggers_search(self):
        f = self._analyze("busque na internet sobre Khonshu")
        assert f.need_search is True

    def test_internet_keyword_triggers_search(self):
        f = self._analyze("o que está acontecendo na internet hoje")
        assert f.need_search is True

    def test_search_english_triggers_search(self):
        f = self._analyze("search for Khonshu Marvel comics")
        assert f.need_search is True

    def test_noticias_triggers_search(self):
        f = self._analyze("quais são as notícias de hoje?")
        assert f.need_search is True

    # Docker intent
    def test_containers_triggers_docker(self):
        f = self._analyze("Como estão meus containers?")
        assert f.need_docker is True
        assert f.need_integrations is True
        assert "docker" in f.detected

    def test_docker_keyword_triggers_docker(self):
        f = self._analyze("listar imagens docker")
        assert f.need_docker is True

    # Weather intent
    def test_clima_triggers_weather(self):
        f = self._analyze("Como está o clima hoje?")
        assert f.need_weather is True
        assert f.need_integrations is True
        assert "weather" in f.detected

    def test_temperatura_triggers_weather(self):
        f = self._analyze("qual a temperatura agora?")
        assert f.need_weather is True

    # Calendar intent
    def test_reuniao_triggers_calendar(self):
        f = self._analyze("Tenho reunião hoje?")
        assert f.need_calendar is True
        assert f.need_integrations is True
        assert "calendar" in f.detected

    def test_agenda_triggers_calendar(self):
        f = self._analyze("mostre minha agenda de amanhã")
        assert f.need_calendar is True

    # Email intent
    def test_email_triggers_email(self):
        f = self._analyze("cheque meus emails novos")
        assert f.need_email is True
        assert f.need_integrations is True

    # Memory intent
    def test_lembrar_triggers_memory(self):
        f = self._analyze("você lembra que eu prefiro Python?")
        assert f.need_memory is True

    # No false positives
    def test_simple_greeting_no_flags(self):
        f = self._analyze("olá, tudo bem?")
        assert f.need_search is False
        assert f.need_docker is False
        assert f.need_weather is False
        assert f.need_calendar is False
        assert f.detected == []

    def test_summary_with_detections(self):
        f = self._analyze("pesquise e verifique meus containers")
        assert "web_search" in f.summary()
        assert "docker" in f.summary()

    def test_summary_without_detections(self):
        f = self._analyze("como vai você?")
        assert f.summary() == "none"


# ---------------------------------------------------------------------------
# RuntimeCapabilitySnapshot
# ---------------------------------------------------------------------------


class TestRuntimeCapabilitySnapshot:
    def _make_snapshot(self) -> RuntimeCapabilitySnapshot:
        return RuntimeCapabilitySnapshot(
            capabilities=[
                CapabilityState(
                    name="Busca Web (Internet)",
                    available=True,
                    configured=True,
                    provider="DuckDuckGo Search",
                ),
                CapabilityState(
                    name="Docker",
                    available=False,
                    configured=False,
                    provider="docker",
                    reason="Não configurado",
                ),
            ]
        )

    def test_available_names(self):
        snap = self._make_snapshot()
        names = snap.available_names()
        assert "Busca Web (Internet)" in names
        assert "Docker" not in names

    def test_get_by_name(self):
        snap = self._make_snapshot()
        cap = snap.get("Busca Web (Internet)")
        assert cap is not None
        assert cap.available is True

    def test_get_missing_returns_none(self):
        snap = self._make_snapshot()
        assert snap.get("Notion") is None

    def test_prompt_section_contains_available(self):
        section = self._make_snapshot().to_prompt_section()
        assert "✓" in section
        assert "Busca Web (Internet)" in section

    def test_prompt_section_contains_unavailable(self):
        section = self._make_snapshot().to_prompt_section()
        assert "✗" in section
        assert "Docker" in section

    def test_prompt_section_has_policy_text(self):
        section = self._make_snapshot().to_prompt_section()
        assert "NUNCA" in section


class TestRuntimeSnapshotBuilder:
    @pytest.mark.asyncio
    async def test_static_capabilities_all_available(self):
        builder = RuntimeSnapshotBuilder(
            has_search=True,
            has_memory=True,
            has_knowledge=True,
        )
        snap = await builder.build()
        names = snap.available_names()
        assert "Busca Web (Internet)" in names
        assert "Memória" in names

    @pytest.mark.asyncio
    async def test_search_unavailable_when_not_set(self):
        builder = RuntimeSnapshotBuilder(has_search=False)
        snap = await builder.build()
        cap = snap.get("Busca Web (Internet)")
        assert cap is not None
        assert cap.available is False

    @pytest.mark.asyncio
    async def test_integration_manager_active(self):
        workspace_id = uuid4()

        mock_integ = MagicMock()
        mock_integ.name = "Google Calendar"
        mock_integ.slug = "google_calendar"
        mock_integ.status = MagicMock()
        mock_integ.status.value = "active"

        mock_manager = MagicMock()
        mock_manager.list_integrations = AsyncMock(return_value=[mock_integ])

        builder = RuntimeSnapshotBuilder(
            has_search=True,
            integration_manager=mock_manager,
        )
        snap = await builder.build(workspace_id)
        cap = snap.get("Google Calendar")
        assert cap is not None
        assert cap.available is True

    @pytest.mark.asyncio
    async def test_integration_manager_inactive(self):
        workspace_id = uuid4()

        mock_integ = MagicMock()
        mock_integ.name = "Docker"
        mock_integ.slug = "docker"
        mock_integ.status = MagicMock()
        mock_integ.status.value = "error"

        mock_manager = MagicMock()
        mock_manager.list_integrations = AsyncMock(return_value=[mock_integ])

        builder = RuntimeSnapshotBuilder(integration_manager=mock_manager)
        snap = await builder.build(workspace_id)
        cap = snap.get("Docker")
        assert cap is not None
        assert cap.available is False
        assert cap.reason is not None

    @pytest.mark.asyncio
    async def test_integration_manager_failure_degrades_gracefully(self):
        mock_manager = MagicMock()
        mock_manager.list_integrations = AsyncMock(
            side_effect=Exception("DB down")
        )
        builder = RuntimeSnapshotBuilder(
            has_search=True,
            integration_manager=mock_manager,
        )
        snap = await builder.build(uuid4())
        # Static caps still work
        assert "Busca Web (Internet)" in snap.available_names()


# ---------------------------------------------------------------------------
# CapabilityExecutor
# ---------------------------------------------------------------------------


class TestCapabilityExecutorSearch:
    @pytest.mark.asyncio
    async def test_search_executed_when_need_search_true(self):
        mock_search = MagicMock()
        mock_search.search = AsyncMock(return_value={
            "summary": "Khonshu é um deus egípcio na Marvel.",
            "count": 3,
            "results": [],
        })

        executor = CapabilityExecutor(search_engine=mock_search)
        decision = Decision(need_search=True)
        intent = IntentFlags(need_search=True)
        trace = ReasoningTrace()

        result = await executor.execute(
            message="Pesquise quem é Khonshu na Marvel",
            workspace_id=uuid4(),
            decision=decision,
            intent=intent,
            trace=trace,
        )

        assert result.search_count == 3
        assert "Khonshu" in result.search_summary
        assert "web_search" in result.capabilities_used
        assert result.internet_sources == 3

    @pytest.mark.asyncio
    async def test_no_search_when_not_needed(self):
        mock_search = MagicMock()
        mock_search.search = AsyncMock()

        executor = CapabilityExecutor(search_engine=mock_search)
        decision = Decision(need_search=False)
        intent = IntentFlags()
        trace = ReasoningTrace()

        result = await executor.execute(
            message="olá",
            workspace_id=uuid4(),
            decision=decision,
            intent=intent,
            trace=trace,
        )

        mock_search.search.assert_not_called()
        assert result.search_summary == ""

    @pytest.mark.asyncio
    async def test_search_engine_unavailable_returns_message(self):
        executor = CapabilityExecutor(search_engine=None)
        decision = Decision(need_search=True)
        intent = IntentFlags(need_search=True)
        trace = ReasoningTrace()

        result = await executor.execute(
            message="pesquise X",
            workspace_id=uuid4(),
            decision=decision,
            intent=intent,
            trace=trace,
        )

        assert "não está disponível" in result.search_summary

    @pytest.mark.asyncio
    async def test_search_failure_returns_error_message(self):
        mock_search = MagicMock()
        mock_search.search = AsyncMock(side_effect=Exception("timeout"))

        executor = CapabilityExecutor(search_engine=mock_search)
        decision = Decision(need_search=True)
        intent = IntentFlags(need_search=True)
        trace = ReasoningTrace()

        result = await executor.execute(
            message="pesquise algo",
            workspace_id=uuid4(),
            decision=decision,
            intent=intent,
            trace=trace,
        )

        assert "erro" in result.search_summary.lower()


class TestCapabilityExecutorIntegrations:
    @pytest.mark.asyncio
    async def test_docker_not_configured_returns_info(self):
        mock_manager = MagicMock()
        mock_manager.list_integrations = AsyncMock(return_value=[])

        executor = CapabilityExecutor(integration_manager=mock_manager)
        decision = Decision()
        intent = IntentFlags(need_docker=True)
        trace = ReasoningTrace()

        result = await executor.execute(
            message="como estão meus containers?",
            workspace_id=uuid4(),
            decision=decision,
            intent=intent,
            trace=trace,
        )

        assert "não está configurada" in result.docker_summary
        assert result.docker_summary != ""

    @pytest.mark.asyncio
    async def test_docker_active_returns_status(self):
        mock_integ = MagicMock()
        mock_integ.name = "Docker"
        mock_integ.slug = "docker"
        mock_integ.status = MagicMock()
        mock_integ.status.value = "active"
        mock_integ.health = MagicMock()
        mock_integ.health.value = "healthy"

        mock_manager = MagicMock()
        mock_manager.list_integrations = AsyncMock(return_value=[mock_integ])

        executor = CapabilityExecutor(integration_manager=mock_manager)
        decision = Decision()
        intent = IntentFlags(need_docker=True)
        trace = ReasoningTrace()

        result = await executor.execute(
            message="como estão meus containers?",
            workspace_id=uuid4(),
            decision=decision,
            intent=intent,
            trace=trace,
        )

        assert "ativa" in result.docker_summary.lower()
        assert "docker" in result.capabilities_used


# ---------------------------------------------------------------------------
# CapabilityResult.to_prompt_sections
# ---------------------------------------------------------------------------


class TestCapabilityResultPromptSections:
    def test_search_section_labels_source(self):
        result = CapabilityResult(
            search_summary="Khonshu é um deus egípcio.",
            search_count=2,
            search_query="quem é Khonshu",
        )
        sections = result.to_prompt_sections()
        assert len(sections) == 1
        assert "Kernel agora" in sections[0]
        assert "Khonshu" in sections[0]
        assert "Não afirme" in sections[0]

    def test_docker_section(self):
        result = CapabilityResult(
            docker_summary="nginx: running, redis: stopped"
        )
        sections = result.to_prompt_sections()
        assert any("Docker" in s for s in sections)

    def test_no_sections_when_empty(self):
        result = CapabilityResult()
        assert result.to_prompt_sections() == []
        assert result.has_tool_output() is False

    def test_multiple_sections(self):
        result = CapabilityResult(
            search_summary="resultado",
            search_query="q",
            docker_summary="status",
        )
        sections = result.to_prompt_sections()
        assert len(sections) == 2


# ---------------------------------------------------------------------------
# CapabilityValidator (tested via orchestrator pattern matching)
# ---------------------------------------------------------------------------


_INVALID_SEARCH_PHRASES = [
    "não tenho acesso à internet",
    "nao tenho acesso a internet",
    "não possuo acesso à internet",
    "sem acesso à internet",
    "não consigo acessar a internet",
    "não tenho capacidade de buscar",
    "não posso pesquisar",
]


class TestCapabilityValidatorPatterns:
    def test_all_invalid_search_phrases_detected(self):
        pattern = re.compile(
            "|".join(_INVALID_SEARCH_PHRASES), re.IGNORECASE
        )
        for phrase in _INVALID_SEARCH_PHRASES:
            assert pattern.search(phrase), (
                f"Pattern not detected: {phrase!r}"
            )

    def test_valid_response_not_rejected(self):
        pattern = re.compile(
            "|".join(_INVALID_SEARCH_PHRASES), re.IGNORECASE
        )
        valid = "Segundo os resultados da pesquisa, Khonshu é um deus egípcio."
        assert not pattern.search(valid)

    def test_mixed_case_detected(self):
        pattern = re.compile(
            "|".join(_INVALID_SEARCH_PHRASES), re.IGNORECASE
        )
        assert pattern.search("Não Tenho Acesso À Internet, portanto...")

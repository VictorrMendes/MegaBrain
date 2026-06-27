"""RC-16 — Final Release Candidate corrections.

Covers:
  - SearchEngine error_type propagation
  - CapabilityResult fallback sections per error_type
  - IntentRouter: checkup intent detection
  - CapabilityExecutor: system checkup execution
  - CapabilityValidator: calendar, weather, general defensive phrases
"""
from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from kernel.orchestrator.capability_executor import (
    CapabilityExecutor,
    CapabilityResult,
)
from kernel.orchestrator.intent_router import IntentFlags, IntentRouter
from kernel.orchestrator.models import Decision
from kernel.orchestrator.trace import ReasoningTrace

# ---------------------------------------------------------------------------
# SearchEngine error_type → CapabilityResult sections
# ---------------------------------------------------------------------------


class TestSearchFallbackSections:
    def test_no_results_section_uses_training_knowledge_note(self):
        result = CapabilityResult(
            search_error_type="no_results",
            search_query="Khonshu Marvel",
        )
        sections = result.to_prompt_sections()
        assert len(sections) == 1
        assert "não retornou resultados" in sections[0]
        assert "conhecimento de treinamento" in sections[0]

    def test_timeout_section_notes_connection_failure(self):
        result = CapabilityResult(
            search_error_type="timeout",
            search_query="clima hoje",
        )
        sections = result.to_prompt_sections()
        assert len(sections) == 1
        assert "timeout" in sections[0]
        assert "conhecimento interno" in sections[0]

    def test_connection_error_section(self):
        result = CapabilityResult(
            search_error_type="connection_error",
            search_query="notícias",
        )
        sections = result.to_prompt_sections()
        assert "conexão" in sections[0]

    def test_rate_limit_section(self):
        result = CapabilityResult(
            search_error_type="rate_limit",
            search_query="pesquisa",
        )
        sections = result.to_prompt_sections()
        assert "limite" in sections[0]

    def test_real_results_still_use_kernel_label(self):
        result = CapabilityResult(
            search_summary="Khonshu é um deus egípcio.",
            search_count=2,
            search_query="Khonshu",
        )
        sections = result.to_prompt_sections()
        assert "Kernel agora" in sections[0]
        assert "Não afirme" in sections[0]

    def test_no_results_has_tool_output(self):
        result = CapabilityResult(search_error_type="no_results")
        assert result.has_tool_output() is True

    def test_empty_result_no_tool_output(self):
        assert CapabilityResult().has_tool_output() is False


# ---------------------------------------------------------------------------
# CapabilityExecutor: search error_type propagation
# ---------------------------------------------------------------------------


class TestCapabilityExecutorSearchErrors:
    @pytest.mark.asyncio
    async def test_no_results_sets_error_type(self):
        mock_search = MagicMock()
        mock_search.search = AsyncMock(return_value={
            "summary": "",
            "count": 0,
            "results": [],
            "error": None,
            "error_type": "no_results",
            "provider": "duckduckgo",
        })

        executor = CapabilityExecutor(search_engine=mock_search)
        result = await executor.execute(
            message="pesquise Khonshu Marvel",
            workspace_id=uuid4(),
            decision=Decision(need_search=True),
            intent=IntentFlags(need_search=True),
            trace=ReasoningTrace(),
        )

        assert result.search_error_type == "no_results"
        assert result.search_count == 0
        assert result.search_summary == ""

    @pytest.mark.asyncio
    async def test_timeout_sets_error_type(self):
        mock_search = MagicMock()
        mock_search.search = AsyncMock(return_value={
            "summary": "",
            "count": 0,
            "results": [],
            "error": "Search timed out after 12s",
            "error_type": "timeout",
            "provider": "duckduckgo",
        })

        executor = CapabilityExecutor(search_engine=mock_search)
        result = await executor.execute(
            message="pesquise algo",
            workspace_id=uuid4(),
            decision=Decision(need_search=True),
            intent=IntentFlags(need_search=True),
            trace=ReasoningTrace(),
        )

        assert result.search_error_type == "timeout"
        assert "web_search" not in result.capabilities_used


# ---------------------------------------------------------------------------
# IntentRouter: checkup detection
# ---------------------------------------------------------------------------


class TestCheckupIntent:
    def setup_method(self):
        self.router = IntentRouter()

    def test_checkup_keyword(self):
        f = self.router.analyze("faça um checkup do sistema")
        assert f.need_checkup is True
        assert "checkup" in f.detected

    def test_check_up_hyphenated(self):
        f = self.router.analyze("preciso de um check-up")
        assert f.need_checkup is True

    def test_status_do_sistema(self):
        f = self.router.analyze("qual o status do sistema?")
        assert f.need_checkup is True

    def test_tudo_funcionando(self):
        f = self.router.analyze("tudo funcionando por aí?")
        assert f.need_checkup is True

    def test_saude_do_sistema(self):
        f = self.router.analyze("saúde do sistema ok?")
        assert f.need_checkup is True

    def test_simple_question_no_checkup(self):
        f = self.router.analyze("me explique o que é Docker")
        assert f.need_checkup is False

    def test_checkup_does_not_set_search(self):
        f = self.router.analyze("faça um checkup")
        assert f.need_search is False
        assert f.need_checkup is True


# ---------------------------------------------------------------------------
# CapabilityExecutor: system checkup
# ---------------------------------------------------------------------------


class TestCapabilityExecutorCheckup:
    @pytest.mark.asyncio
    async def test_checkup_builds_system_status(self):
        mock_integ = MagicMock()
        mock_integ.name = "Docker"
        mock_integ.slug = "docker"
        mock_integ.status = MagicMock()
        mock_integ.status.value = "active"
        mock_integ.health = MagicMock()
        mock_integ.health.value = "healthy"

        mock_manager = MagicMock()
        mock_manager.list_integrations = AsyncMock(
            return_value=[mock_integ]
        )

        executor = CapabilityExecutor(
            integration_manager=mock_manager
        )
        result = await executor.execute(
            message="faça um checkup do sistema",
            workspace_id=uuid4(),
            decision=Decision(),
            intent=IntentFlags(need_checkup=True),
            trace=ReasoningTrace(),
        )

        assert result.checkup_summary != ""
        assert "Docker" in result.checkup_summary
        assert "checkup" in result.capabilities_used

    @pytest.mark.asyncio
    async def test_checkup_no_integrations_configured(self):
        mock_manager = MagicMock()
        mock_manager.list_integrations = AsyncMock(return_value=[])

        executor = CapabilityExecutor(
            integration_manager=mock_manager
        )
        result = await executor.execute(
            message="status do sistema",
            workspace_id=uuid4(),
            decision=Decision(),
            intent=IntentFlags(need_checkup=True),
            trace=ReasoningTrace(),
        )

        assert "Nenhuma integração" in result.checkup_summary

    @pytest.mark.asyncio
    async def test_no_checkup_when_not_requested(self):
        executor = CapabilityExecutor()
        result = await executor.execute(
            message="olá",
            workspace_id=uuid4(),
            decision=Decision(),
            intent=IntentFlags(),
            trace=ReasoningTrace(),
        )

        assert result.checkup_summary == ""

    @pytest.mark.asyncio
    async def test_checkup_section_in_prompt(self):
        executor = CapabilityExecutor()
        result = await executor.execute(
            message="checkup",
            workspace_id=uuid4(),
            decision=Decision(),
            intent=IntentFlags(need_checkup=True),
            trace=ReasoningTrace(),
        )

        sections = result.to_prompt_sections()
        assert any("Status do Sistema" in s for s in sections)


# ---------------------------------------------------------------------------
# CapabilityValidator: expanded patterns
# ---------------------------------------------------------------------------

_INVALID_CALENDAR_PHRASES = [
    r"não tenho (?:acesso (?:à|a)|integração de) (?:minha )?agenda",
    r"não consigo acessar (?:o )?calendário",
    r"não possuo calendário",
    r"sem acesso (?:ao )?calendário",
    r"não tenho integração de calendário",
]
_INVALID_WEATHER_PHRASES = [
    r"não consigo verificar (?:o )?clima",
    r"não tenho (?:acesso|dados) (?:a(?:o)?|sobre) (?:o )?clima",
    r"não possuo dados (?:de|do|sobre) clima",
    r"sem (?:acesso a(?:o)?|dados de) (?:o )?clima",
]
_INVALID_GENERAL_PHRASES = [
    r"sou apenas (?:um )?(?:modelo|assistente|chatbot|ia) de linguagem",
    r"sou apenas um sistema local",
    r"não possuo (?:essa |esta )?capacidade",
    r"sou incapaz de",
    r"não tenho (?:essa |esta )?capacidade",
]


class TestExpandedValidatorPatterns:
    def _check(self, patterns: list[str], phrase: str) -> bool:
        pat = re.compile("|".join(patterns), re.IGNORECASE)
        return bool(pat.search(phrase))

    def test_calendar_denial_detected(self):
        assert self._check(
            _INVALID_CALENDAR_PHRASES,
            "não consigo acessar o calendário neste momento",
        )

    def test_calendar_agenda_denial_detected(self):
        assert self._check(
            _INVALID_CALENDAR_PHRASES,
            "não tenho acesso à minha agenda",
        )

    def test_calendar_valid_response_not_flagged(self):
        assert not self._check(
            _INVALID_CALENDAR_PHRASES,
            "Você tem uma reunião amanhã às 14h.",
        )

    def test_weather_denial_detected(self):
        assert self._check(
            _INVALID_WEATHER_PHRASES,
            "não consigo verificar o clima agora",
        )

    def test_weather_valid_response_not_flagged(self):
        assert not self._check(
            _INVALID_WEATHER_PHRASES,
            "A temperatura hoje é de 28°C em São Paulo.",
        )

    def test_general_defensive_model_phrase(self):
        assert self._check(
            _INVALID_GENERAL_PHRASES,
            "Sou apenas um modelo de linguagem e não posso fazer isso.",
        )

    def test_general_defensive_local_system(self):
        assert self._check(
            _INVALID_GENERAL_PHRASES,
            "Sou apenas um sistema local sem acesso externo.",
        )

    def test_general_nao_possuo_capacidade(self):
        assert self._check(
            _INVALID_GENERAL_PHRASES,
            "não possuo essa capacidade no momento.",
        )

    def test_general_sou_incapaz(self):
        assert self._check(
            _INVALID_GENERAL_PHRASES,
            "Sou incapaz de acessar o Docker.",
        )

    def test_general_valid_response_not_flagged(self):
        assert not self._check(
            _INVALID_GENERAL_PHRASES,
            "Aqui está o status dos seus containers Docker.",
        )

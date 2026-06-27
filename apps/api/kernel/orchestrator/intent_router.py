"""IntentRouter — deterministic keyword analysis before the LLM DecisionEngine.

Runs BEFORE DecisionEngine. Produces IntentFlags that are merged with the
LLM Decision (OR semantics: either source can set a flag True; nothing can
unset a flag already set by IntentRouter).

This ensures explicit intents like "pesquise..." always activate the correct
capability, regardless of how the LLM interprets the message.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Pattern tables
# ---------------------------------------------------------------------------

_SEARCH_PATTERNS = [
    r"\bpesquis\w*\b",      # pesquise, pesquisa, pesquisar
    r"\bbusqu\w*\b",         # busque, busquei
    r"\bbusc[ae]\b",         # busca, buscar
    r"\bprocur\w+\b",        # procure, procurar
    r"\bsearch\b",
    r"\binternet\b",
    r"\bweb\b",
    r"\bonline\b",
    r"\bnotícia[s]?\b",
    r"\bnoticia[s]?\b",
    r"\batualidade[s]?\b",
    r"\brecent[e]?\w*\b",
    r"\bagora\b",
]

_DOCKER_PATTERNS = [
    r"\bcontainer[s]?\b",
    r"\bdocker\b",
    r"\bpod[s]?\b",
    r"\bstack[s]?\b",
    r"\bserviço[s]? rodando\b",
    r"\bservico[s]? rodando\b",
]

_WEATHER_PATTERNS = [
    r"\bclima\b",
    r"\btempera\w+\b",
    r"\bprevisão\b",
    r"\bprevisao\b",
    r"\bchov\w+\b",
    r"\bchuva\b",
    r"\bnublad\w+\b",
    r"\bvento\b",
]

_CALENDAR_PATTERNS = [
    r"\breuni[aã]o[s]?\b",
    r"\bagenda\b",
    r"\beventos?\b",
    r"\bcalendário\b",
    r"\bcalendario\b",
    r"\bcompromisso[s]?\b",
    r"\bmeeting[s]?\b",
    r"\btenho (?:algo|algo )?hoje\b",
]

_EMAIL_PATTERNS = [
    r"\be?-?mail[s]?\b",
    r"\bcaixa de entrada\b",
    r"\binbox\b",
    r"\bcorrespondência\b",
]

_MEMORY_PATTERNS = [
    r"\blembr\w+\b",
    r"\bmemória\b",
    r"\bmemoria\b",
    r"\brecord\w+\b",
]

_MISSION_PATTERNS = [
    r"\bcri\w* (?:uma |a )?missão\b",
    r"\bexecut\w* (?:uma |a )?tarefa\b",
]


def _any_match(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


@dataclass
class IntentFlags:
    """Deterministic intent signals extracted before the LLM Decision."""

    need_search: bool = False
    need_docker: bool = False
    need_weather: bool = False
    need_calendar: bool = False
    need_email: bool = False
    need_memory: bool = False
    need_mission: bool = False
    detected: list[str] = field(default_factory=list)

    @property
    def need_integrations(self) -> bool:
        return (
            self.need_docker
            or self.need_weather
            or self.need_calendar
            or self.need_email
        )

    def summary(self) -> str:
        return ", ".join(self.detected) if self.detected else "none"


class IntentRouter:
    """Keyword-based intent analysis — runs before the LLM DecisionEngine."""

    def analyze(self, message: str) -> IntentFlags:
        flags = IntentFlags()
        lower = message.lower()

        if _any_match(lower, _SEARCH_PATTERNS):
            flags.need_search = True
            flags.detected.append("web_search")

        if _any_match(lower, _DOCKER_PATTERNS):
            flags.need_docker = True
            flags.detected.append("docker")

        if _any_match(lower, _WEATHER_PATTERNS):
            flags.need_weather = True
            flags.detected.append("weather")

        if _any_match(lower, _CALENDAR_PATTERNS):
            flags.need_calendar = True
            flags.detected.append("calendar")

        if _any_match(lower, _EMAIL_PATTERNS):
            flags.need_email = True
            flags.detected.append("email")

        if _any_match(lower, _MEMORY_PATTERNS):
            flags.need_memory = True
            flags.detected.append("memory")

        if _any_match(lower, _MISSION_PATTERNS):
            flags.need_mission = True
            flags.detected.append("mission")

        return flags

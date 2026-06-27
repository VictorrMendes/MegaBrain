"""Facade de dependências FastAPI — delega ao KhonshuRuntime.

Os routers continuam usando Depends(get_mission_engine) etc.
A inicialização real acontece em kernel/runtime.py.
"""

from kernel.runtime import runtime


def get_context_builder():
    return runtime.context


def get_llm_provider():
    return runtime.llm


def get_memory_engine():
    return runtime.memory


def get_rag_engine():
    return runtime.rag


def get_obsidian_engine():
    return runtime.obsidian


def get_plugin_engine():
    return runtime.plugin


def get_prompt_engine():
    return runtime.prompt


def get_knowledge_engine():
    return runtime.knowledge


def get_mission_engine():
    return runtime.mission


def get_scheduler_engine():
    return runtime.scheduler


def get_inbox_engine():
    return runtime.inbox


def get_integration_manager():
    return runtime.integration


def get_life_context():
    return runtime.life_context


def get_search_engine():
    return runtime.search


def get_briefing_engine():
    return runtime.briefing


def get_capability_reasoner():
    return runtime.reasoner


def get_cognitive_metrics():
    return runtime.metrics


def get_orchestrator():
    return runtime.orchestrator


def get_decision_engine():
    return runtime.decision_engine


def get_learning_engine():
    return runtime.learning_engine

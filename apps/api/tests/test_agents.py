"""Tests for agent workers: MemoryExtractor, TaskExtractor, Summarizer."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from kernel.agents.memory_extractor import MemoryExtractorWorker, _strip_think
from kernel.agents.summarizer import SummarizerWorker
from kernel.agents.task_extractor import TaskExtractorWorker
from kernel.providers.base import GenerateResult
from models.memory import MemoryType

WORKSPACE_ID = "12345678-1234-5678-1234-567812345678"
CONV_ID = "87654321-4321-8765-4321-876543218765"


def _llm_result(content: str) -> GenerateResult:
    return GenerateResult(content=content, model="test-model")


# ---------------------------------------------------------------------------
# _strip_think
# ---------------------------------------------------------------------------

class TestStripThink:
    def test_removes_think_block(self):
        text = '<think>some reasoning</think>\n{"memories": []}'
        assert _strip_think(text) == '{"memories": []}'

    def test_passthrough_without_think(self):
        text = '{"memories": []}'
        assert _strip_think(text) == text

    def test_strips_multiline_think(self):
        text = "<think>\nline1\nline2\n</think>\n{\"ok\": true}"
        assert _strip_think(text) == '{"ok": true}'


# ---------------------------------------------------------------------------
# MemoryExtractorWorker
# ---------------------------------------------------------------------------

class TestMemoryExtractorWorker:
    @pytest.fixture
    def worker(self, mock_memory_engine, mock_llm_provider):
        return MemoryExtractorWorker(
            memory_engine=mock_memory_engine,
            llm_provider=mock_llm_provider,
        )

    async def test_ignores_other_event_types(self, worker, mock_memory_engine):
        await worker.handle({"type": "document.uploaded"})
        mock_memory_engine.remember.assert_not_called()

    async def test_extracts_single_memory(self, worker, mock_memory_engine, mock_llm_provider):
        mock_llm_provider.chat.return_value = _llm_result(
            '{"memories": [{"content": "Usuário gosta de café", "domain": "routine"}]}'
        )

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "user_message": "adoro café de manhã",
            "assistant_message": "Que bom, café é ótimo!",
        })

        mock_memory_engine.remember.assert_called_once()
        kwargs = mock_memory_engine.remember.call_args.kwargs
        assert kwargs["content"] == "Usuário gosta de café"
        assert kwargs["type"] == MemoryType.long
        assert kwargs["metadata"]["domain"] == "routine"
        assert kwargs["metadata"]["auto"] is True

    async def test_extracts_multiple_memories(self, worker, mock_memory_engine, mock_llm_provider):
        mock_llm_provider.chat.return_value = _llm_result(json.dumps({
            "memories": [
                {"content": "Tem reunião na sexta", "domain": "task"},
                {"content": "Salário de R$5000", "domain": "finance"},
            ]
        }))

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "user_message": "ganho 5k e tenho reunião sexta",
            "assistant_message": "Entendido.",
        })

        assert mock_memory_engine.remember.call_count == 2
        domains = {
            c.kwargs["metadata"]["domain"]
            for c in mock_memory_engine.remember.call_args_list
        }
        assert domains == {"task", "finance"}

    async def test_skips_empty_content(self, worker, mock_memory_engine, mock_llm_provider):
        mock_llm_provider.chat.return_value = _llm_result(
            '{"memories": [{"content": "", "domain": "general"}]}'
        )

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "user_message": "ok",
            "assistant_message": "Tudo bem.",
        })

        mock_memory_engine.remember.assert_not_called()

    async def test_handles_empty_memories_list(self, worker, mock_memory_engine, mock_llm_provider):
        mock_llm_provider.chat.return_value = _llm_result('{"memories": []}')

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "user_message": "olá",
            "assistant_message": "Oi!",
        })

        mock_memory_engine.remember.assert_not_called()

    async def test_handles_malformed_json_gracefully(self, worker, mock_memory_engine, mock_llm_provider):
        mock_llm_provider.chat.return_value = _llm_result("not valid json at all")

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "user_message": "teste",
            "assistant_message": "resposta",
        })

        mock_memory_engine.remember.assert_not_called()

    async def test_strips_think_tags_before_parsing(self, worker, mock_memory_engine, mock_llm_provider):
        mock_llm_provider.chat.return_value = _llm_result(
            '<think>pensando...</think>\n{"memories": [{"content": "Info util", "domain": "general"}]}'
        )

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "user_message": "info",
            "assistant_message": "ok",
        })

        mock_memory_engine.remember.assert_called_once()
        assert mock_memory_engine.remember.call_args.kwargs["content"] == "Info util"

    async def test_domain_defaults_preserved(self, worker, mock_memory_engine, mock_llm_provider):
        """Ensure all four domains are stored correctly."""
        for domain in ("task", "finance", "routine", "general"):
            mock_memory_engine.remember.reset_mock()
            mock_llm_provider.chat.return_value = _llm_result(
                json.dumps({"memories": [{"content": "fact", "domain": domain}]})
            )

            await worker.handle({
                "type": "message.completed",
                "workspace_id": WORKSPACE_ID,
                "user_message": "x",
                "assistant_message": "y",
            })

            assert mock_memory_engine.remember.call_args.kwargs["metadata"]["domain"] == domain


# ---------------------------------------------------------------------------
# TaskExtractorWorker
# ---------------------------------------------------------------------------

class TestTaskExtractorWorker:
    @pytest.fixture
    def worker(self, mock_memory_engine, mock_llm_provider, mock_plugin_engine):
        return TaskExtractorWorker(
            memory_engine=mock_memory_engine,
            llm_provider=mock_llm_provider,
            plugin_engine=mock_plugin_engine,
        )

    async def test_extracts_task_and_saves_metadata(self, worker, mock_memory_engine, mock_llm_provider, mock_plugin_engine):
        mock_llm_provider.chat.return_value = _llm_result(
            '{"tasks": [{"content": "Pagar conta luz", "deadline": "2026-06-30", "priority": "alta"}]}'
        )

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "user_message": "pagar conta de luz até dia 30",
            "assistant_message": "Anotado.",
        })

        mock_memory_engine.remember.assert_called_once()
        meta = mock_memory_engine.remember.call_args.kwargs["metadata"]
        assert meta["domain"] == "task"
        assert meta["deadline"] == "2026-06-30"
        assert meta["priority"] == "alta"
        assert meta["status"] == "pending"
        assert meta["auto"] is True

    async def test_sends_ntfy_for_each_task(self, worker, mock_memory_engine, mock_llm_provider, mock_plugin_engine):
        mock_llm_provider.chat.return_value = _llm_result(json.dumps({
            "tasks": [
                {"content": "Tarefa A", "deadline": None, "priority": "alta"},
                {"content": "Tarefa B", "deadline": "2026-07-01", "priority": "baixa"},
            ]
        }))

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "user_message": "duas tarefas",
            "assistant_message": "Anotadas.",
        })

        assert mock_memory_engine.remember.call_count == 2
        assert mock_plugin_engine.execute.call_count == 2
        for call in mock_plugin_engine.execute.call_args_list:
            assert call.kwargs["plugin_name"] == "ntfy"
            assert call.kwargs["action"] == "notify"

    async def test_high_priority_uses_high_ntfy_priority(self, worker, mock_memory_engine, mock_llm_provider, mock_plugin_engine):
        mock_llm_provider.chat.return_value = _llm_result(
            '{"tasks": [{"content": "Urgente", "deadline": null, "priority": "alta"}]}'
        )

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "user_message": "urgente",
            "assistant_message": "Ok.",
        })

        ntfy_params = mock_plugin_engine.execute.call_args.kwargs["params"]
        assert ntfy_params["priority"] == "high"

    async def test_deadline_included_in_message(self, worker, mock_memory_engine, mock_llm_provider, mock_plugin_engine):
        mock_llm_provider.chat.return_value = _llm_result(
            '{"tasks": [{"content": "Enviar relatório", "deadline": "2026-07-15", "priority": "media"}]}'
        )

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "user_message": "enviar relatório dia 15",
            "assistant_message": "Certo.",
        })

        ntfy_params = mock_plugin_engine.execute.call_args.kwargs["params"]
        assert "2026-07-15" in ntfy_params["message"]

    async def test_no_tasks_skips_everything(self, worker, mock_memory_engine, mock_llm_provider, mock_plugin_engine):
        mock_llm_provider.chat.return_value = _llm_result('{"tasks": []}')

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "user_message": "que dia é hoje?",
            "assistant_message": "Hoje é segunda.",
        })

        mock_memory_engine.remember.assert_not_called()
        mock_plugin_engine.execute.assert_not_called()

    async def test_ignores_other_event_types(self, worker, mock_memory_engine, mock_plugin_engine):
        await worker.handle({"type": "memory.created"})
        mock_memory_engine.remember.assert_not_called()
        mock_plugin_engine.execute.assert_not_called()


# ---------------------------------------------------------------------------
# SummarizerWorker
# ---------------------------------------------------------------------------

def _make_session_factory(message_count: int):
    """Build an async session factory mock that returns `message_count` on count query."""
    from models.conversation import MessageRole

    # Build fake messages
    fake_messages = []
    for i in range(min(message_count, 10)):
        m = MagicMock()
        m.role = MessageRole.user if i % 2 == 0 else MessageRole.assistant
        m.content = f"Mensagem {i + 1}"
        fake_messages.append(m)

    count_result = MagicMock()
    count_result.scalar_one.return_value = message_count

    msgs_result = MagicMock()
    msgs_result.scalars.return_value.all.return_value = fake_messages

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[count_result, msgs_result])

    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory


class TestSummarizerWorker:
    def _worker(self, mock_memory_engine, mock_llm_provider, message_count: int):
        return SummarizerWorker(
            memory_engine=mock_memory_engine,
            llm_provider=mock_llm_provider,
            session_factory=_make_session_factory(message_count),
        )

    async def test_skips_when_count_is_not_multiple_of_10(self, mock_memory_engine, mock_llm_provider):
        worker = self._worker(mock_memory_engine, mock_llm_provider, 7)

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "conversation_id": CONV_ID,
        })

        mock_llm_provider.chat.assert_not_called()
        mock_memory_engine.remember.assert_not_called()

    async def test_creates_episodic_memory_at_10(self, mock_memory_engine, mock_llm_provider):
        mock_llm_provider.chat.return_value = _llm_result("Discutimos finanças e rotina.")
        worker = self._worker(mock_memory_engine, mock_llm_provider, 10)

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "conversation_id": CONV_ID,
        })

        mock_memory_engine.remember.assert_called_once()
        kwargs = mock_memory_engine.remember.call_args.kwargs
        assert kwargs["type"] == MemoryType.episodic
        assert "Discutimos" in kwargs["content"]
        assert kwargs["metadata"]["auto"] is True
        assert kwargs["metadata"]["conversation_id"] == CONV_ID
        assert kwargs["metadata"]["message_count"] == 10

    async def test_creates_episodic_memory_at_20(self, mock_memory_engine, mock_llm_provider):
        mock_llm_provider.chat.return_value = _llm_result("Segundo resumo.")
        worker = self._worker(mock_memory_engine, mock_llm_provider, 20)

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "conversation_id": CONV_ID,
        })

        mock_memory_engine.remember.assert_called_once()

    async def test_skips_at_count_5(self, mock_memory_engine, mock_llm_provider):
        worker = self._worker(mock_memory_engine, mock_llm_provider, 5)

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "conversation_id": CONV_ID,
        })

        mock_memory_engine.remember.assert_not_called()

    async def test_ignores_other_event_types(self, mock_memory_engine, mock_llm_provider):
        worker = self._worker(mock_memory_engine, mock_llm_provider, 10)

        await worker.handle({"type": "document.deleted"})
        mock_memory_engine.remember.assert_not_called()

    async def test_strips_think_tags_from_summary(self, mock_memory_engine, mock_llm_provider):
        mock_llm_provider.chat.return_value = _llm_result(
            "<think>pensando</think>\nResumo limpo da conversa."
        )
        worker = self._worker(mock_memory_engine, mock_llm_provider, 10)

        await worker.handle({
            "type": "message.completed",
            "workspace_id": WORKSPACE_ID,
            "conversation_id": CONV_ID,
        })

        content = mock_memory_engine.remember.call_args.kwargs["content"]
        assert "<think>" not in content
        assert content == "Resumo limpo da conversa."

"""Contract tests for LLMProvider.

Concrete implementations must subclass BaseLLMProviderContract and
override the `provider` fixture to return their implementation.

Example:
    class TestOllamaProvider(BaseLLMProviderContract):
        @pytest.fixture
        def provider(self):
            return OllamaProvider(base_url="http://localhost:11434")
"""
from __future__ import annotations

import pytest

from kernel.providers.base import (
    ChatMessage,
    ExecutionProfile,
    GenerateResult,
    LLMProvider,
)


class BaseLLMProviderContract:
    """Shared contract tests every LLMProvider implementation must pass."""

    @pytest.fixture
    def provider(self) -> LLMProvider:
        raise NotImplementedError(
            "Subclass must override the `provider` fixture."
        )

    @pytest.mark.asyncio
    async def test_generate_returns_result(self, provider: LLMProvider) -> None:
        result = await provider.generate(prompt="Say hello.")
        assert isinstance(result, GenerateResult)
        assert isinstance(result.content, str)
        assert len(result.content) > 0
        assert isinstance(result.model, str)
        assert isinstance(result.tokens_used, int)
        assert result.tokens_used >= 0

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(
        self, provider: LLMProvider
    ) -> None:
        result = await provider.generate(
            prompt="What is 2+2?",
            system="You are a math assistant. Answer only with the number.",
        )
        assert isinstance(result, GenerateResult)
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_generate_with_profile(self, provider: LLMProvider) -> None:
        result = await provider.generate(
            prompt="Summarize: the sky is blue.",
            profile=ExecutionProfile.SUMMARIZATION,
        )
        assert isinstance(result, GenerateResult)
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_chat_returns_result(self, provider: LLMProvider) -> None:
        messages = [ChatMessage(role="user", content="Hello!")]
        result = await provider.chat(messages=messages)
        assert isinstance(result, GenerateResult)
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_stream_yields_strings(self, provider: LLMProvider) -> None:
        chunks: list[str] = []
        async for chunk in await provider.stream(prompt="Count to 3."):
            assert isinstance(chunk, str)
            chunks.append(chunk)
        assert len(chunks) > 0
        full = "".join(chunks)
        assert len(full) > 0

    @pytest.mark.asyncio
    async def test_chat_stream_yields_strings(
        self, provider: LLMProvider
    ) -> None:
        messages = [ChatMessage(role="user", content="Say hi.")]
        chunks: list[str] = []
        async for chunk in await provider.chat_stream(messages=messages):
            assert isinstance(chunk, str)
            chunks.append(chunk)
        assert len(chunks) > 0

"""Contract tests for EmbeddingProvider.

Example:
    class TestOllamaEmbedding(BaseEmbeddingProviderContract):
        @pytest.fixture
        def provider(self):
            return OllamaProvider()
"""
from __future__ import annotations

import pytest

from kernel.providers.base import EmbeddingProvider, EmbedResult


class BaseEmbeddingProviderContract:
    """Shared contract tests every EmbeddingProvider must pass."""

    @pytest.fixture
    def provider(self) -> EmbeddingProvider:
        raise NotImplementedError(
            "Subclass must override the `provider` fixture."
        )

    @pytest.mark.asyncio
    async def test_embed_returns_result(
        self, provider: EmbeddingProvider
    ) -> None:
        result = await provider.embed("Hello world.")
        assert isinstance(result, EmbedResult)
        assert isinstance(result.embedding, list)
        assert len(result.embedding) > 0
        assert all(isinstance(v, float) for v in result.embedding)
        assert result.dimensions == len(result.embedding)

    @pytest.mark.asyncio
    async def test_embed_is_deterministic(
        self, provider: EmbeddingProvider
    ) -> None:
        r1 = await provider.embed("Test sentence.")
        r2 = await provider.embed("Test sentence.")
        assert r1.embedding == r2.embedding

    @pytest.mark.asyncio
    async def test_embed_batch_matches_individual(
        self, provider: EmbeddingProvider
    ) -> None:
        texts = ["First sentence.", "Second sentence."]
        batch = await provider.embed_batch(texts)
        assert len(batch) == len(texts)

        for i, text in enumerate(texts):
            individual = await provider.embed(text)
            assert batch[i].embedding == individual.embedding, (
                f"Batch result for index {i} differs from individual embed"
            )

    @pytest.mark.asyncio
    async def test_different_texts_produce_different_embeddings(
        self, provider: EmbeddingProvider
    ) -> None:
        r1 = await provider.embed("A dog barked.")
        r2 = await provider.embed("The stock market fell.")
        assert r1.embedding != r2.embedding

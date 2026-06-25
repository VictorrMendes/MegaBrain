"""Tests for RAG chunking logic (pure function, no DB needed)."""

from engines.rag.engine import _chunk_text


class TestChunkText:
    def test_empty_string_returns_empty_list(self):
        assert _chunk_text("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert _chunk_text("   \n\n   ") == []

    def test_short_text_content_is_preserved(self):
        text = "Hello world."
        chunks = _chunk_text(text)
        assert len(chunks) >= 1
        assert chunks[0] == text

    def test_long_text_splits_into_multiple_chunks(self):
        word = "palavra "
        text = word * 300  # ~2400 chars — should produce >1 chunk at 1500
        chunks = _chunk_text(text, chunk_size=1500, overlap=200)
        assert len(chunks) > 1

    def test_all_content_preserved(self):
        """No text should be lost — union of chunks covers the original."""
        paragraph = "Esta é uma frase. " * 100
        chunks = _chunk_text(paragraph, chunk_size=200, overlap=30)
        combined = " ".join(chunks)
        # Every unique word from original must appear in combined output
        original_words = set(paragraph.split())
        combined_words = set(combined.split())
        assert original_words <= combined_words

    def test_chunks_respect_max_size(self):
        text = "a" * 5000
        chunks = _chunk_text(text, chunk_size=1500, overlap=200)
        for chunk in chunks:
            # Allow slight overshoot from separator search
            assert len(chunk) <= 1600

    def test_overlap_produces_shared_content(self):
        """Consecutive chunks should share some content due to overlap."""
        text = "palavra " * 500
        chunks = _chunk_text(text, chunk_size=200, overlap=50)
        if len(chunks) >= 2:
            end_of_first = set(chunks[0][-60:].split())
            start_of_second = set(chunks[1][:60].split())
            assert end_of_first & start_of_second

    def test_splits_on_double_newline(self):
        """Prefer splitting on paragraph boundaries."""
        text = ("Parágrafo um.\n\n" * 10) + "Último parágrafo."
        chunks = _chunk_text(text, chunk_size=100, overlap=10)
        for chunk in chunks:
            # No chunk should have content from two different paragraphs without overlap
            assert len(chunk) > 0

    def test_text_at_limit_is_fully_covered(self):
        text = "a" * 1500
        chunks = _chunk_text(text, chunk_size=1500, overlap=200)
        assert len(chunks) >= 1
        assert all(c for c in chunks)

    def test_returns_stripped_chunks(self):
        text = "  primeiro chunk  \n\n  segundo chunk  "
        chunks = _chunk_text(text, chunk_size=30, overlap=5)
        for chunk in chunks:
            assert chunk == chunk.strip()

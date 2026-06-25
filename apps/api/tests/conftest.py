import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_memory_engine():
    engine = MagicMock()
    engine.remember = AsyncMock()
    return engine


@pytest.fixture
def mock_llm_provider():
    provider = MagicMock()
    provider.chat = AsyncMock()
    return provider


@pytest.fixture
def mock_plugin_engine():
    engine = MagicMock()
    engine.execute = AsyncMock(return_value=None)
    return engine

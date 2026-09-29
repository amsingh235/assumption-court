"""Offline by default: fake LLM + fake retrieval. `network` / `llm` tests opt back into live providers."""
import os
import tempfile

import pytest

os.environ["LLM_PROVIDER"] = "fake"
os.environ["RETRIEVAL_PROVIDER"] = "fake"
os.environ["LLM_LOG_PATH"] = os.path.join(tempfile.mkdtemp(), "llm_calls.jsonl")

from app.config import get_settings  # noqa: E402
from app.graph_events import EventLog  # noqa: E402
from app.pipeline.state import Trial  # noqa: E402


@pytest.fixture
def settings_env(monkeypatch):
    """settings_env(KEY="value", ...) -> re-read settings with these env overrides for this test."""
    def apply(**overrides: str):
        for key, value in overrides.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()
        return get_settings()
    yield apply
    get_settings.cache_clear()


@pytest.fixture
def trial() -> Trial:
    return Trial(text="test claim", events=EventLog(), deadline=float("inf"))

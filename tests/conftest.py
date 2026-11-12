"""Shared test setup."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


@pytest.fixture(autouse=True)
def no_retry_sleep(monkeypatch):
    """Upload retries back off for seconds in production; tests must not wait."""

    from ai_content_agent.publishers import http, youtube_publisher

    waits: list[float] = []
    monkeypatch.setattr(http, "_sleep", waits.append)
    monkeypatch.setattr(youtube_publisher, "_sleep", waits.append, raising=False)
    return waits

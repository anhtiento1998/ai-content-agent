"""Interface-compliance tests — no network calls, no API keys needed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ai_content_agent.providers import TEXT_PROVIDERS, VIDEO_PROVIDERS
from ai_content_agent.providers.base import TextGenerator, VideoGenerator
from ai_content_agent.publishers import PUBLISHERS
from ai_content_agent.publishers.base import Publisher


def test_text_providers_implement_interface():
    for cls in TEXT_PROVIDERS.values():
        assert issubclass(cls, TextGenerator)
        assert hasattr(cls, "name")


def test_video_providers_implement_interface():
    for cls in VIDEO_PROVIDERS.values():
        assert issubclass(cls, VideoGenerator)
        assert hasattr(cls, "name")


def test_publishers_implement_interface():
    for cls in PUBLISHERS.values():
        assert issubclass(cls, Publisher)
        assert hasattr(cls, "name")

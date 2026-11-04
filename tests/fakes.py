"""Test doubles shared by the test modules — no network, no API keys."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ai_content_agent.providers.base import ScriptResult, TextGenerator, VideoGenerator, VideoResult
from ai_content_agent.publishers.base import Publisher, PublishResult


class FakeText(TextGenerator):
    name = "fake-text"

    def __init__(self, fail=False):
        self.calls = 0
        self._fail = fail

    def generate_script(self, topic, *, style="", max_words=150):
        self.calls += 1
        if self._fail:
            raise RuntimeError("quota exceeded")
        return ScriptResult(title=f"Title for {topic}", script="Hello world", hashtags=["test"])


class FakeVideo(VideoGenerator):
    name = "fake-video"

    def __init__(self, path):
        self._path = path

    def generate_video(self, script, *, aspect_ratio="9:16"):
        return VideoResult(file_path=self._path)


class FakePublisher(Publisher):
    def __init__(self, name="fake", fail=False):
        self.name = name
        self.published = []
        self._fail = fail

    def publish(self, video, script):
        if self._fail:
            raise RuntimeError("boom")
        self.published.append((video, script))
        return PublishResult(
            platform=self.name,
            remote_id=str(len(self.published)),
            url=f"https://example.com/{self.name}/{len(self.published)}",
        )

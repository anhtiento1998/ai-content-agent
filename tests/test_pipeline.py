"""Pipeline, history and thumbnail tests — fake providers, no network calls."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ai_content_agent.history import HistoryStore
from ai_content_agent.media.thumbnail import generate_thumbnail
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.providers.base import ScriptResult, TextGenerator, VideoGenerator, VideoResult
from ai_content_agent.publishers.base import Publisher, PublishResult


class FakeText(TextGenerator):
    name = "fake-text"

    def __init__(self):
        self.calls = 0

    def generate_script(self, topic, *, style="", max_words=150):
        self.calls += 1
        return ScriptResult(title=f"Title for {topic}", script="Hello world", hashtags=["test"])


class FakeVideo(VideoGenerator):
    name = "fake-video"

    def __init__(self, path):
        self._path = path

    def generate_video(self, script, *, aspect_ratio="9:16"):
        return VideoResult(file_path=self._path)


class FakePublisher(Publisher):
    name = "fake"

    def __init__(self, fail=False):
        self.published = []
        self._fail = fail

    def publish(self, video, script):
        if self._fail:
            raise RuntimeError("boom")
        self.published.append((video, script))
        return PublishResult(platform=self.name, remote_id=str(len(self.published)))


def _pipeline(tmp_path, publishers, **kwargs):
    text = FakeText()
    pipeline = ContentPipeline(
        text,
        FakeVideo(str(tmp_path / "video.mp4")),
        publishers,
        history=HistoryStore(str(tmp_path / "history.db")),
        make_thumbnails=False,
        **kwargs,
    )
    return pipeline, text


def test_run_publishes_and_records_history(tmp_path):
    publisher = FakePublisher()
    pipeline, _ = _pipeline(tmp_path, [publisher])

    results = pipeline.run("Mẹo tiết kiệm điện")

    assert [r.platform for r in results] == ["fake"]
    runs = HistoryStore(str(tmp_path / "history.db")).recent_runs()
    assert len(runs) == 1
    assert runs[0].topic == "mẹo tiết kiệm điện"


def test_duplicate_topic_is_skipped_unless_forced(tmp_path):
    publisher = FakePublisher()
    pipeline, text = _pipeline(tmp_path, [publisher])

    pipeline.run("Same Topic")
    assert pipeline.run("  same   topic ") == []
    assert text.calls == 1

    assert len(pipeline.run("Same Topic", force=True)) == 1
    assert text.calls == 2


def test_failing_publisher_does_not_block_others(tmp_path):
    good = FakePublisher()
    pipeline, _ = _pipeline(tmp_path, [FakePublisher(fail=True), good])

    results = pipeline.run("Topic")

    assert len(results) == 1
    assert len(good.published) == 1


def test_dry_run_does_not_publish_or_record(tmp_path):
    publisher = FakePublisher()
    pipeline, _ = _pipeline(tmp_path, [publisher])

    assert pipeline.run("Topic", dry_run=True) == []
    assert publisher.published == []
    assert HistoryStore(str(tmp_path / "history.db")).recent_runs() == []


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_generate_thumbnail(tmp_path):
    from PIL import Image

    video = tmp_path / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=720x1280:rate=10", str(video)],
        check=True,
        capture_output=True,
    )

    out = generate_thumbnail(str(video), "Một tiêu đề thử nghiệm", str(tmp_path / "thumbs" / "t.jpg"))

    with Image.open(out) as img:
        assert img.size == (1280, 720)

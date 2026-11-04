"""Pipeline, history and thumbnail tests — fake providers, no network calls."""

import shutil
import subprocess

import pytest
from fakes import FakePublisher, FakeText, FakeVideo

from ai_content_agent.history import HistoryStore
from ai_content_agent.media.thumbnail import generate_thumbnail
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.providers.base import parse_script_json


def _pipeline(tmp_path, publishers, *, text=None, **kwargs):
    text = text or FakeText()
    pipeline = ContentPipeline(
        text,
        FakeVideo(str(tmp_path / "video.mp4")),
        publishers,
        history=HistoryStore(str(tmp_path / "history.db")),
        make_thumbnails=False,
        **kwargs,
    )
    return pipeline, text


def _history(tmp_path):
    return HistoryStore(str(tmp_path / "history.db"))


def test_run_publishes_and_records_history(tmp_path):
    pipeline, _ = _pipeline(tmp_path, [FakePublisher()])

    results = pipeline.run("Mẹo tiết kiệm điện")

    assert [r.platform for r in results] == ["fake"]
    runs = _history(tmp_path).recent_runs()
    assert len(runs) == 1
    assert runs[0].topic == "mẹo tiết kiệm điện"
    assert [p.platform for p in runs[0].publishes] == ["fake"]


def test_duplicate_topic_is_skipped_unless_forced(tmp_path):
    pipeline, text = _pipeline(tmp_path, [FakePublisher()])

    pipeline.run("Same Topic")
    assert pipeline.run("  same   topic ") == []
    assert text.calls == 1

    assert len(pipeline.run("Same Topic", force=True)) == 1
    assert text.calls == 2


def test_topic_whose_publishes_all_failed_can_be_retried(tmp_path):
    pipeline, text = _pipeline(tmp_path, [FakePublisher(fail=True)])

    pipeline.run("Retry me")
    pipeline.run("Retry me")

    assert text.calls == 2


def test_failing_publisher_does_not_block_others_and_is_logged(tmp_path):
    good = FakePublisher(name="tiktok")
    pipeline, _ = _pipeline(tmp_path, [FakePublisher(name="youtube", fail=True), good])

    results = pipeline.run("Topic")

    assert len(results) == 1
    assert len(good.published) == 1
    [error] = _history(tmp_path).recent_errors()
    assert (error.stage, error.platform) == ("publish", "youtube")
    assert "boom" in error.message
    assert error.run_id is not None


def test_script_failure_is_logged_and_reraised(tmp_path):
    pipeline, _ = _pipeline(tmp_path, [FakePublisher()], text=FakeText(fail=True))

    with pytest.raises(RuntimeError):
        pipeline.run("Topic")

    [error] = _history(tmp_path).recent_errors()
    assert error.stage == "script"
    assert _history(tmp_path).recent_runs() == []


def test_dry_run_does_not_publish_or_record(tmp_path):
    publisher = FakePublisher()
    pipeline, _ = _pipeline(tmp_path, [publisher])

    assert pipeline.run("Topic", dry_run=True) == []
    assert publisher.published == []
    assert _history(tmp_path).recent_runs() == []


def test_stats(tmp_path):
    pipeline, _ = _pipeline(tmp_path, [FakePublisher(name="youtube"), FakePublisher(name="tiktok", fail=True)])
    pipeline.run("A")
    pipeline.run("B")

    stats = _history(tmp_path).stats()

    assert stats["total_runs"] == 2
    assert stats["publishes_by_platform"] == {"youtube": 2}
    assert stats["errors_last_7_days"] == 2


@pytest.mark.parametrize(
    "reply",
    [
        '{"title": "T", "script": "S", "hashtags": ["#a", "b"]}',
        'Sure! Here it is:\n```json\n{"title": "T", "script": "S", "hashtags": ["#a", "b"]}\n```',
        'Here you go: {"title": "T", "script": "S", "hashtags": ["#a", "b"]} Enjoy!',
    ],
)
def test_parse_script_json_tolerates_fences_and_prose(reply):
    script = parse_script_json(reply)
    assert (script.title, script.script, script.hashtags) == ("T", "S", ["a", "b"])


def test_parse_script_json_rejects_non_json():
    with pytest.raises(ValueError):
        parse_script_json("I cannot help with that.")


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

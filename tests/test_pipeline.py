"""Pipeline, history and thumbnail tests — fake studio/publishers, no network calls."""

import shutil
import subprocess

import pytest
from fakes import FakePublisher, FakeStudio

from ai_content_agent.history import HistoryStore
from ai_content_agent.media.thumbnail import generate_thumbnail
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.studio import StudioStageError


def _pipeline(tmp_path, publishers, *, studio=None):
    studio = studio or FakeStudio(str(tmp_path / "video.mp4"))
    pipeline = ContentPipeline(
        studio, publishers, history=HistoryStore(str(tmp_path / "history.db")), make_thumbnails=False
    )
    return pipeline, studio


def _history(tmp_path):
    return HistoryStore(str(tmp_path / "history.db"))


def test_run_publishes_and_records_history(tmp_path):
    pipeline, _ = _pipeline(tmp_path, [FakePublisher()])

    outcome = pipeline.run("Mẹo tiết kiệm điện")

    assert not outcome.skipped
    assert outcome.video.file_path == str(tmp_path / "video.mp4")
    assert outcome.script.title == "Title for Mẹo tiết kiệm điện"
    assert [r.platform for r in outcome.published] == ["fake"]
    [run] = _history(tmp_path).recent_runs()
    assert run.topic == "mẹo tiết kiệm điện"
    assert [p.platform for p in run.publishes] == ["fake"]


def test_duplicate_topic_is_skipped_unless_forced(tmp_path):
    pipeline, studio = _pipeline(tmp_path, [FakePublisher()])

    pipeline.run("Same Topic")
    assert pipeline.run("  same   topic ").skipped
    assert studio.calls == 1

    assert len(pipeline.run("Same Topic", force=True).published) == 1
    assert studio.calls == 2


def test_topic_whose_publishes_all_failed_can_be_retried(tmp_path):
    pipeline, studio = _pipeline(tmp_path, [FakePublisher(fail=True)])

    pipeline.run("Retry me")
    pipeline.run("Retry me")

    assert studio.calls == 2


def test_failing_publisher_does_not_block_others_and_is_logged(tmp_path):
    good = FakePublisher(name="tiktok")
    pipeline, _ = _pipeline(tmp_path, [FakePublisher(name="youtube", fail=True), good])

    outcome = pipeline.run("Topic")

    assert len(outcome.published) == 1
    assert len(good.published) == 1
    [error] = _history(tmp_path).recent_errors()
    assert (error.stage, error.platform) == ("publish", "youtube")
    assert "boom" in error.message
    assert error.run_id is not None


@pytest.mark.parametrize("stage", ["script", "voice", "visual", "render"])
def test_studio_failure_is_logged_with_its_stage_and_reraised(tmp_path, stage):
    studio = FakeStudio(str(tmp_path / "video.mp4"), fail_stage=stage)
    pipeline, _ = _pipeline(tmp_path, [FakePublisher()], studio=studio)

    with pytest.raises(StudioStageError):
        pipeline.run("Topic")

    [error] = _history(tmp_path).recent_errors()
    assert error.stage == stage
    assert error.message == f"scene 1: RuntimeError: {stage} broke"
    assert _history(tmp_path).recent_runs() == []


def test_dry_run_returns_video_without_publishing_or_recording(tmp_path):
    publisher = FakePublisher()
    pipeline, _ = _pipeline(tmp_path, [publisher])

    outcome = pipeline.run("Topic", dry_run=True)

    assert outcome.video is not None
    assert outcome.published == []
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

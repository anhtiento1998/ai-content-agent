"""CapCut draft export: timeline.json/SRT from real renders, mapped onto a pycapcut stand-in."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import fake_pycapcut
import pytest
from fakes import FakePublisher, FakeStudio, FakeText, TestPatternClips
from PIL import Image

from ai_content_agent.export.capcut import CapCutExporter, _cover_scale, _draft_name
from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.providers.local_provider import CardImageProvider, SilentVoiceProvider
from ai_content_agent.studio import StudioSettings, VideoStudio
from ai_content_agent.studio.captions import Caption, build_srt

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@pytest.fixture
def pycapcut(monkeypatch):
    monkeypatch.setitem(sys.modules, "pycapcut", fake_pycapcut)
    return fake_pycapcut


def _render(tmp_path, visuals, **settings):
    studio = VideoStudio(FakeText(), visuals, SilentVoiceProvider(), StudioSettings(
        **{"output_dir": str(tmp_path / "out"), "music_dir": None, "font": "DejaVu Sans", **settings}))
    _, video = studio.produce("topic")
    return Path(video.raw["work_dir"])


def _export(tmp_path, work):
    drafts = tmp_path / "drafts"
    draft = CapCutExporter(drafts).export(work)
    return draft, json.loads((draft / "draft_content.json").read_text(encoding="utf-8"))


def _contiguous(segments, total):
    position = 0
    for seg in segments:
        assert seg["start"] == position
        position += seg["duration"]
    assert position == total


def test_build_srt_formats_cues():
    srt = build_srt([Caption(0, 1.5, "Xin chào"), Caption(61.25, 3725.5, "dòng  hai")])
    assert srt == "1\n00:00:00,000 --> 00:00:01,500\nXin chào\n\n2\n00:01:01,250 --> 01:02:05,500\ndòng hai\n"


def test_cover_scale_fills_vertical_canvas():
    assert _cover_scale(1080, 1920, 1080, 1920) == pytest.approx(1.0)
    assert _cover_scale(1920, 1080, 1080, 1920) == pytest.approx((1920 / 1080) ** 2)


def test_draft_name_is_safe_for_windows_folders():
    name = _draft_name('Mẹo: "tiết kiệm" điện/nước? <2026>')
    assert not set('<>:"/\\|?*') & set(name)
    assert name.startswith("Mẹo tiết kiệm điện nước 2026 ")


@needs_ffmpeg
def test_export_rebuilds_the_edit_as_editable_tracks(tmp_path, pycapcut):
    music = tmp_path / "music"
    music.mkdir()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=3",
                    str(music / "tone.mp3")], check=True)
    (music / "licenses.json").write_text('{"tone.mp3": {"license": "CC0", "source": "generated"}}')
    Image.new("RGBA", (300, 120), (255, 0, 0, 200)).save(tmp_path / "logo.png")
    work = _render(tmp_path, CardImageProvider(), music_dir=str(music), logo_path=str(tmp_path / "logo.png"))
    timeline = json.loads((work / "timeline.json").read_text(encoding="utf-8"))

    draft, content = _export(tmp_path, work)

    total = round(timeline["duration"] * 1e6)
    assert draft.parent == tmp_path / "drafts"
    assert content["canvas"] == [1080, 1920, 30] and content["duration"] == total
    tracks = content["tracks"]
    assert set(tracks) == {"visuals", "voice", "music", "logo", "hooks"}

    visuals = tracks["visuals"]["segments"]
    _contiguous(visuals, total)
    assert [Path(s["path"]).name for s in visuals] == ["scene_01_visual.png", "scene_02_visual.png"]
    assert visuals[0]["keyframes"][0][2] < visuals[0]["keyframes"][1][2]  # scene 1 zooms in
    assert visuals[1]["keyframes"][0][2] > visuals[1]["keyframes"][1][2]  # scene 2 zooms out

    voice = tracks["voice"]["segments"]
    assert [s["start"] for s in voice] == [s["start"] for s in visuals]
    assert all(v["duration"] <= s["duration"] for v, s in zip(voice, visuals))

    _contiguous(tracks["music"]["segments"], total)
    assert len(tracks["music"]["segments"]) > 1  # 3s track looped under the narration
    assert all(s["volume"] < 0.5 for s in tracks["music"]["segments"])
    assert tracks["logo"]["segments"][0]["duration"] == total
    assert [s["text"] for s in tracks["hooks"]["segments"]] == ["Tiền điện tăng vọt?"]
    assert content["srt"] == [{"path": str(work / "subtitles.srt"), "track": "captions"}]
    assert "Tiền điện tháng này" in (work / "subtitles.srt").read_text(encoding="utf-8")


@needs_ffmpeg
def test_export_loops_short_clips_and_scales_them_to_fill(tmp_path, pycapcut):
    work = _render(tmp_path, TestPatternClips())

    _, content = _export(tmp_path, work)

    visuals = content["tracks"]["visuals"]["segments"]
    assert len(visuals) > 2  # 1.5s clips repeated to cover each scene
    assert all(s["source_duration"] <= 1_500_000 for s in visuals)
    assert all(s["volume"] == 0.0 for s in visuals)
    assert visuals[0]["scale"] == pytest.approx(_cover_scale(640, 360, 1080, 1920))
    _contiguous(visuals, content["duration"])


@needs_ffmpeg
def test_two_exports_of_one_run_do_not_collide(tmp_path, pycapcut, monkeypatch):
    work = _render(tmp_path, CardImageProvider())
    monkeypatch.setattr("ai_content_agent.export.capcut._draft_name", lambda title: "same second")

    first, _ = _export(tmp_path, work)
    second, _ = _export(tmp_path, work)

    assert (first.name, second.name) == ("same second", "same second (2)")


def test_missing_pycapcut_gives_install_hint(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "pycapcut", None)
    with pytest.raises(RuntimeError, match=r"pip install -e \"\.\[capcut\]\""):
        CapCutExporter(tmp_path).export(tmp_path)


def test_run_without_timeline_is_rejected(tmp_path, pycapcut):
    with pytest.raises(FileNotFoundError, match="timeline.json"):
        CapCutExporter(tmp_path).export(tmp_path)


class StubExporter:
    def __init__(self, fail=False):
        self.calls, self._fail = [], fail

    def export(self, work_dir):
        self.calls.append(Path(work_dir))
        if self._fail:
            raise RuntimeError("draft format changed")
        return Path(work_dir) / "draft"


@pytest.mark.parametrize("dry_run", [True, False])
def test_pipeline_auto_exports_after_render(tmp_path, dry_run):
    exporter = StubExporter()
    pipeline = ContentPipeline(FakeStudio(str(tmp_path / "run" / "final.mp4")), [FakePublisher()],
                               history=HistoryStore(str(tmp_path / "h.db")), make_thumbnails=False,
                               capcut_exporter=exporter)

    outcome = pipeline.run("topic", dry_run=dry_run)

    assert exporter.calls == [tmp_path / "run"]
    assert outcome.capcut_draft == str(tmp_path / "run" / "draft")


def test_capcut_failure_does_not_block_publishing(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    pipeline = ContentPipeline(FakeStudio(str(tmp_path / "final.mp4")), [FakePublisher()], history=history,
                               make_thumbnails=False, capcut_exporter=StubExporter(fail=True))

    outcome = pipeline.run("topic")

    assert len(outcome.published) == 1 and outcome.capcut_draft is None
    [error] = history.recent_errors()
    assert error.stage == "capcut" and "draft format changed" in error.message

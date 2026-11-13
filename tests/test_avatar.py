"""Talking-head avatar: ComfyUI lip-sync engine, corner and full-frame layouts, exports."""

import json
import subprocess
import sys
import types
import xml.etree.ElementTree as ET
from pathlib import Path

import fake_pycapcut
import pytest
from fakes import FakeText
from PIL import Image, ImageChops, ImageStat

from ai_content_agent.config import Config
from ai_content_agent.export import capcut
from ai_content_agent.export.capcut import CapCutExporter
from ai_content_agent.export.edit_bundle import EditBundleExporter
from ai_content_agent.media.ffmpeg import ffmpeg_bin, probe_video
from ai_content_agent.providers import comfyui_provider
from ai_content_agent.providers.base import AvatarGenerator
from ai_content_agent.providers.comfyui_provider import ComfyUIAvatarProvider
from ai_content_agent.providers.local_provider import CardImageProvider, SilentVoiceProvider
from ai_content_agent.studio import StudioSettings, StudioStageError, VideoStudio, render
from ai_content_agent.studio.studio import Checkpoint


class FakeAvatar(AvatarGenerator):
    """Writes a 1-second colourful square test clip, like a lip-sync model's output."""

    name = "fake"
    _model = "lipsync-test"

    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def animate(self, audio_path, out_path, *, aspect_ratio="9:16"):
        self.calls.append(Path(audio_path).name)
        if self.fail:
            raise RuntimeError("out of VRAM")
        subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc2=duration=1:size=512x512:rate=30", "-pix_fmt", "yuv420p", out_path], check=True)


class CountingCards(CardImageProvider):
    def __init__(self):
        self.calls = 0

    def generate_image(self, prompt, out_path, *, aspect_ratio="9:16"):
        self.calls += 1
        super().generate_image(prompt, out_path, aspect_ratio=aspect_ratio)


def _studio(tmp_path, avatar=None, visuals=None, **settings):
    return VideoStudio(FakeText(), visuals or CardImageProvider(), SilentVoiceProvider(),
                       StudioSettings(output_dir=str(tmp_path / "out"), music_dir=None, font="DejaVu Sans",
                                      **settings), avatar=avatar)


def _frame(video_path, out_path, seconds=0.5):
    subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-ss", str(seconds), "-i", video_path,
                    "-frames:v", "1", out_path], check=True)
    return Image.open(out_path).convert("RGB")


def _difference(a, b, box):
    return sum(ImageStat.Stat(ImageChops.difference(a.crop(box), b.crop(box))).mean)


# ---------- layout maths ----------


def test_avatar_box_keeps_clear_of_captions_and_edges():
    size, x, y = render.avatar_box(34, "bottom-left")
    assert size == 366 and x == 48 and y + size <= render.HEIGHT - 440 - 100  # above the caption line
    assert render.avatar_box(34, "top-right")[1:] == (render.WIDTH - 366 - 48, 260)
    assert render.avatar_box(500, "top-left")[0] == render.WIDTH - 96  # clamped to the frame
    with pytest.raises(ValueError, match="AVATAR_POSITION"):
        render.avatar_box(34, "middle")


# ---------- rendering ----------


def test_corner_avatar_is_drawn_over_each_scene(tmp_path):
    avatar = FakeAvatar()
    events = []
    _, with_avatar = _studio(tmp_path / "a", avatar).produce("x", progress=lambda *e: events.append(e))
    _, plain = _studio(tmp_path / "b").produce("x")

    assert avatar.calls == ["scene_01_voice.wav", "scene_02_voice.wav"]  # lip-synced to each scene's voice
    assert [e for e in events if e[0] == "assets"][-1] == ("assets", 6, 6)  # voice + visual + avatar per scene
    assert probe_video(with_avatar.file_path)[:2] == (1080, 1920)

    size, x, y = render.avatar_box(34, "bottom-left")
    a = _frame(with_avatar.file_path, str(tmp_path / "a.png"))
    b = _frame(plain.file_path, str(tmp_path / "b.png"))
    centre = (x + size // 4, y + size // 4, x + 3 * size // 4, y + 3 * size // 4)
    corner_outside_circle = (x, y, x + 20, y + 20)
    far_away = (700, 300, 1000, 600)
    assert _difference(a, b, centre) > 60  # the talking head is there
    assert _difference(a, b, corner_outside_circle) < 12  # masked to a circle, not a square
    assert _difference(a, b, far_away) < 12  # the rest of the scene is untouched

    work = Path(with_avatar.raw["work_dir"])
    timeline = json.loads((work / "timeline.json").read_text())
    assert timeline["avatar"] == {"size": size, "x": x, "y": y, "position": "bottom-left"}
    assert [s["avatar"] for s in timeline["scenes"]] == ["scene_01_avatar.mp4", "scene_02_avatar.mp4"]
    assert (work / "scene_01_avatar.mp4").is_file() and not (work / "scene_01_base.mp4").exists()
    engines = with_avatar.raw["provenance"]["engines"]
    assert engines["avatar"] == {"provider": "fake", "model": "lipsync-test", "layout": "corner"}


def test_full_frame_avatar_replaces_scene_visuals(tmp_path):
    avatar, cards = FakeAvatar(), CountingCards()
    events = []
    _, video = _studio(tmp_path, avatar, cards, avatar_layout="full").produce(
        "x", progress=lambda *e: events.append(e))

    assert cards.calls == 0 and len(avatar.calls) == 2  # no image engine cost at all
    assert [e for e in events if e[0] == "assets"][-1] == ("assets", 4, 4)
    assert probe_video(video.file_path)[:2] == (1080, 1920)
    timeline = json.loads((Path(video.raw["work_dir"]) / "timeline.json").read_text())
    assert timeline["avatar"] is None  # it is the visual track itself
    assert [(s["visual"], s["visual_kind"]) for s in timeline["scenes"]] == [
        ("scene_01_avatar.mp4", "video"), ("scene_02_avatar.mp4", "video")]
    frame = _frame(video.file_path, str(tmp_path / "f.png"))
    assert sum(ImageStat.Stat(frame.crop((100, 200, 980, 1200))).stddev) > 60  # test pattern fills the frame


def test_resumed_run_reuses_avatar_clips_and_failures_are_staged(tmp_path):
    avatar = FakeAvatar()
    checkpoint = Checkpoint()
    studio = _studio(tmp_path, avatar, keep_intermediates=True)
    studio.produce("x", checkpoint=checkpoint)
    assert len(avatar.calls) == 2

    _studio(tmp_path, avatar).produce("x", checkpoint=Checkpoint(storyboard=checkpoint.storyboard,
                                                               work_dir=checkpoint.work_dir))
    assert len(avatar.calls) == 2  # clips already on disk were not generated again

    with pytest.raises(StudioStageError) as failure:
        _studio(tmp_path / "bad", FakeAvatar(fail=True)).produce("x")
    assert failure.value.stage == "avatar" and "scene 1" in str(failure.value) and "VRAM" in str(failure.value)


def test_bad_avatar_settings_are_rejected_up_front(tmp_path):
    with pytest.raises(ValueError, match="AVATAR_LAYOUT"):
        _studio(tmp_path, FakeAvatar(), avatar_layout="floating")
    with pytest.raises(ValueError, match="AVATAR_POSITION"):
        _studio(tmp_path, FakeAvatar(), avatar_position="centre")
    _studio(tmp_path, None, avatar_layout="floating")  # ignored without an avatar engine


# ---------- ComfyUI lip-sync engine ----------

WORKFLOW = {
    "1": {"class_type": "LoadImage", "inputs": {"image": "{{image}}"}},
    "2": {"class_type": "LoadAudio", "inputs": {"audio": "{{audio}}"}},
    "3": {"class_type": "LipSync", "inputs": {"seed": "{{seed}}", "width": "{{width}}", "height": "{{height}}"}},
}


class FakeComfy:
    def __init__(self):
        self.uploads, self.prompts, self.views = [], [], []

    def post(self, url, json=None, files=None, data=None, timeout=None):
        if url.endswith("/upload/image"):
            name = files["image"][0]
            self.uploads.append((name, data))
            return types.SimpleNamespace(json=lambda: {"name": name, "subfolder": "", "type": "input"})
        self.prompts.append(json["prompt"])
        return types.SimpleNamespace(json=lambda: {"prompt_id": "p1"})

    def get(self, url, params=None, timeout=None):
        if "/history/" in url:
            outputs = {"9": {"gifs": [{"filename": "talk.mp4", "subfolder": "", "type": "output"}]}}
            return types.SimpleNamespace(json=lambda: {"p1": {"status": {"status_str": "success"}, "outputs": outputs}})
        self.views.append(params)
        return types.SimpleNamespace(status_code=200, content=b"VIDEO")

    ConnectionError = ConnectionError


def _files(tmp_path, workflow=WORKFLOW):
    (tmp_path / "lipsync.json").write_text(json.dumps(workflow))
    (tmp_path / "me.png").write_bytes(b"png")
    for name in ("scene_01_voice.wav", "scene_02_voice.wav"):
        (tmp_path / name).write_bytes(b"wav")
    return str(tmp_path / "lipsync.json"), str(tmp_path / "me.png")


def test_comfyui_avatar_uploads_audio_and_portrait_then_runs_the_workflow(tmp_path, monkeypatch):
    fake = FakeComfy()
    monkeypatch.setattr(comfyui_provider, "requests", fake)
    workflow, image = _files(tmp_path)
    provider = ComfyUIAvatarProvider(workflow, image, "http://gpu:8188", poll_seconds=0)

    provider.animate(str(tmp_path / "scene_01_voice.wav"), str(tmp_path / "a1.mp4"))
    provider.animate(str(tmp_path / "scene_02_voice.wav"), str(tmp_path / "a2.mp4"))

    assert [name for name, _ in fake.uploads] == ["scene_01_voice.wav", "me.png", "scene_02_voice.wav"]  # portrait once
    assert fake.uploads[0][1] == {"overwrite": "true", "type": "input"}
    first, second = fake.prompts
    assert first["1"]["inputs"]["image"] == "me.png" and first["2"]["inputs"]["audio"] == "scene_01_voice.wav"
    assert second["2"]["inputs"]["audio"] == "scene_02_voice.wav"
    assert isinstance(first["3"]["inputs"]["seed"], int) and first["3"]["inputs"]["width"] == 720
    assert (tmp_path / "a2.mp4").read_bytes() == b"VIDEO" and provider._model == "lipsync"


def test_comfyui_avatar_checks_its_workflow_and_portrait(tmp_path):
    workflow, image = _files(tmp_path)
    with pytest.raises(ValueError, match="AVATAR_WORKFLOW"):
        ComfyUIAvatarProvider(None, image)
    with pytest.raises(FileNotFoundError, match="AVATAR_IMAGE"):
        ComfyUIAvatarProvider(workflow, str(tmp_path / "missing.png"))
    no_audio, _ = _files(tmp_path, {"1": {"class_type": "LoadImage", "inputs": {"image": "{{image}}"}}})
    with pytest.raises(ValueError, match="audio"):
        ComfyUIAvatarProvider(no_audio, image)
    audio_only, _ = _files(tmp_path, {"2": {"class_type": "LoadAudio", "inputs": {"audio": "{{audio}}"}}})
    assert ComfyUIAvatarProvider(audio_only, None)._needs_image is False  # portrait baked into the workflow


def test_agent_builds_the_avatar_engine_from_config(tmp_path):
    from ai_content_agent.agent import ContentAgent

    workflow, image = _files(tmp_path)
    base = {"text_provider": "gemini", "google_api_key": "k", "voice_provider": "silent", "avatar_provider": "comfyui",
            "avatar_workflow": workflow, "avatar_image": image, "comfyui_url": "http://gpu:8188"}

    corner = ContentAgent(Config(visual_provider="card", avatar_position="top-right", avatar_size=30, **base))
    studio = corner.build_studio()
    assert isinstance(studio._avatar, ComfyUIAvatarProvider) and studio._avatar._url == "http://gpu:8188"
    assert (studio._settings.avatar_layout, studio._settings.avatar_position) == ("corner", "top-right")
    assert studio.engine_names["avatar"] == "comfyui"

    # Full frame: the image engine is not built at all, so its missing key cannot stop the run.
    full = ContentAgent(Config(visual_provider="gpt-image", avatar_layout="full", **base)).build_studio()
    assert isinstance(full._visuals, CardImageProvider) and full._avatar_full

    assert ContentAgent(Config(text_provider="gemini", google_api_key="k", visual_provider="card",
                               voice_provider="silent")).build_studio()._avatar is None
    with pytest.raises(ValueError, match="AVATAR_PROVIDER"):
        ContentAgent(Config(**{**base, "avatar_provider": "heygen", "visual_provider": "card"})).build_studio()
    status = Config(**base).status()
    assert status["avatar_provider"] == "comfyui" and status["avatar_providers"]["comfyui"]["ready"] is True


# ---------- exports ----------


def test_corner_avatar_gets_its_own_track_in_exports(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "pycapcut", fake_pycapcut)
    monkeypatch.setattr(capcut, "capcut_running", lambda: False)
    _, video = _studio(tmp_path, FakeAvatar()).produce("x")
    work = Path(video.raw["work_dir"])

    draft = CapCutExporter(tmp_path / "drafts").export(work)
    tracks = json.loads((draft / "draft_content.json").read_text())["tracks"]
    assert "avatar" in tracks and tracks["avatar"]["segments"]
    total = sum(seg["duration"] for seg in tracks["avatar"]["segments"])
    assert total == sum(seg["duration"] for seg in tracks["visuals"]["segments"])  # covers every scene
    assert all(seg["volume"] == 0.0 and 0 < seg["scale"] < 1 for seg in tracks["avatar"]["segments"])

    bundle = EditBundleExporter().export(work)
    root = ET.parse(next(bundle.glob("*.fcpxml"))).getroot()
    avatars = [clip for clip in root.iter("asset-clip") if clip.get("lane") == "2"]
    assert len(avatars) == 2 and (bundle / "media" / "scene_01_avatar.mp4").is_file()

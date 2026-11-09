"""P2: GPU encoder detection, local Vietnamese TTS, CapCut 9.x hardening and the edit bundle."""

import json
import sys
import types
import wave
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import fake_pycapcut
import pytest
import requests
from fakes import FakeText
from fastapi.testclient import TestClient

from ai_content_agent.config import Config
from ai_content_agent.export import capcut
from ai_content_agent.export.capcut import CapCutExporter, CapCutRefused, detect_version, fix_text_ranges
from ai_content_agent.export.edit_bundle import EditBundleExporter
from ai_content_agent.history import HistoryStore
from ai_content_agent.media import encoders
from ai_content_agent.providers import local_tts
from ai_content_agent.providers.local_provider import CardImageProvider, SilentVoiceProvider
from ai_content_agent.studio import StudioSettings, VideoStudio, render
from ai_content_agent.web.app import create_app
from ai_content_agent.web.jobs import Job, JobManager

TOKEN = "t"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


# ---------- GPU encoder ----------


@pytest.fixture(autouse=True)
def clear_encoder_cache():
    encoders._cache.clear()
    yield
    encoders._cache.clear()


def test_auto_prefers_a_working_gpu_encoder(monkeypatch):
    monkeypatch.setattr(encoders, "_listed", lambda: {"h264_nvenc", "h264_qsv"})
    monkeypatch.setattr(encoders, "works", lambda name: name == "h264_qsv")  # NVENC listed but no NVIDIA GPU
    chosen = encoders.detect("auto")
    assert chosen.name == "h264_qsv" and "nv12" in chosen.args(final=True)
    assert encoders.status("auto") == {"encoder": "h264_qsv", "gpu": True, "note": None}


def test_forced_encoder_that_fails_falls_back_and_bad_names_are_rejected(monkeypatch):
    monkeypatch.setattr(encoders, "works", lambda name: False)
    assert encoders.detect("h264_nvenc").name == "libx264"
    with pytest.raises(ValueError, match="VIDEO_ENCODER"):
        encoders.detect("h265_magic")
    assert encoders.status("h265_magic")["note"]


def test_real_ffmpeg_detection_always_yields_a_working_encoder():
    encoder = encoders.detect("auto")
    assert encoders.works(encoder.name)


def test_render_passes_the_encoder_to_every_ffmpeg_call(monkeypatch):
    calls = []
    monkeypatch.setattr(render, "run_ffmpeg", lambda args, cwd=None: calls.append(args))
    nvenc = encoders.ENCODERS["h264_nvenc"]
    render.image_to_clip("a.png", "a.mp4", 2.0, zoom_in=True, cwd=".", encoder=nvenc)
    render.compose_final("v.mp4", "a.wav", "s.ass", "f.mp4", 2.0, cwd=".", encoder=nvenc)
    assert all("h264_nvenc" in args for args in calls)
    assert "p5" in calls[1] and "p2" in calls[0]  # quality preset for the published file only


# ---------- local TTS ----------


class Response:
    def __init__(self, status_code=200, content=b"", text=""):
        self.status_code, self.content, self.text = status_code, content, text


def test_vieneu_writes_48k_wav_from_raw_pcm(monkeypatch, tmp_path):
    sent = {}

    def post(url, headers, json, timeout):
        sent.update(url=url, headers=headers, body=json)
        return Response(content=b"\x01\x00" * 48000)

    monkeypatch.setattr(local_tts.requests, "post", post)
    provider = local_tts.VieNeuVoiceProvider("http://localhost:8000/v1/", api_key="k")
    provider.synthesize("Xin chào", str(tmp_path / "v.wav"), voice="Mai Anh")

    assert sent["url"] == "http://localhost:8000/v1/audio/speech"
    assert sent["body"] == {"model": "vieneu-v3-turbo", "input": "Xin chào", "voice": "Mai Anh",
                            "response_format": "pcm", "sample_rate": 48000}
    assert sent["headers"] == {"Authorization": "Bearer k"}
    with wave.open(str(tmp_path / "v.wav")) as wav:
        assert (wav.getframerate(), wav.getnchannels(), wav.getnframes()) == (48000, 1, 48000)


def test_vieneu_errors_are_retryable_or_explain_how_to_start_it(monkeypatch, tmp_path):
    monkeypatch.setattr(local_tts.requests, "post", lambda *a, **k: Response(429, text="busy"))
    with pytest.raises(local_tts.TTSServerError) as busy:
        local_tts.VieNeuVoiceProvider().synthesize("x", str(tmp_path / "v.wav"))
    from ai_content_agent.studio.studio import _is_transient
    assert busy.value.status_code == 429 and _is_transient(busy.value)

    def refuse(*_a, **_k):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(local_tts.requests, "post", refuse)
    with pytest.raises(ConnectionError, match="apps.openai_speech"):
        local_tts.VieNeuVoiceProvider().synthesize("x", str(tmp_path / "v.wav"))


def test_zerotts_needs_its_package_and_uses_the_voice(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "zerotts", None)
    with pytest.raises(RuntimeError, match=r"\[zerotts\]"):
        local_tts.ZeroTTSVoiceProvider()

    calls = []

    class FakeZero:
        @classmethod
        def from_pretrained(cls, name):
            calls.append(("load", name))
            return cls()

        def synthesize(self, text, voice=None):
            calls.append(("say", text, voice))
            return [0.0] * 10

        def save_audio(self, audio, path):
            Path(path).write_bytes(b"RIFF")

    monkeypatch.setitem(sys.modules, "zerotts", types.SimpleNamespace(ZeroTTS=FakeZero))
    provider = local_tts.ZeroTTSVoiceProvider(voice="maichi")
    provider.synthesize("Một", str(tmp_path / "a.wav"))
    provider.synthesize("Hai", str(tmp_path / "b.wav"), voice="baotrang")
    assert calls == [("load", "zeroweight-ai/ZeroTTS"), ("say", "Một", "maichi"), ("say", "Hai", "baotrang")]


def test_agent_builds_vieneu_with_config(tmp_path):
    from ai_content_agent.agent import ContentAgent

    config = Config(voice_provider="vieneu", vieneu_base_url="http://box:9000/v1", voice_name="Ngọc Huyền",
                    text_provider="gemini", google_api_key="k", visual_provider="card")
    voice = ContentAgent(config).build_studio()._voice
    assert isinstance(voice, local_tts.VieNeuVoiceProvider)
    assert (voice._base_url, voice._voice) == ("http://box:9000/v1", "Ngọc Huyền")
    assert config.status()["voice_providers"]["vieneu"]["ready"] is True


# ---------- CapCut ----------


@pytest.fixture
def pycapcut(monkeypatch):
    monkeypatch.setitem(sys.modules, "pycapcut", fake_pycapcut)
    monkeypatch.setattr(capcut, "capcut_running", lambda: False)
    return fake_pycapcut


@pytest.fixture
def work(tmp_path):
    studio = VideoStudio(FakeText(), CardImageProvider(), SilentVoiceProvider(), StudioSettings(
        output_dir=str(tmp_path / "out"), music_dir=None, font="DejaVu Sans"))
    _, video = studio.produce("topic")
    return Path(video.raw["work_dir"])


def _app_project(store: Path, name: str, version: str, *, encrypted_mirror=False) -> Path:
    project = store / name
    (project / "Timelines" / "abc").mkdir(parents=True)
    doc = {"platform": {"app_source": "cc", "app_version": version}, "last_modified_platform":
           {"app_version": version}, "version": 360000, "tracks": [], "materials": {"stickers": [], "effects": []},
           "config": {"maintrack_adsorb": True}}
    (project / "draft_info.json").write_text(json.dumps(doc))
    (project / "template-2.tmp").write_text("ENCRYPTED-BLOB" if encrypted_mirror else json.dumps(doc))
    (project / "Timelines" / "abc" / "draft_info.json").write_text(json.dumps(doc))
    (project / "draft_meta_info.json").write_text(json.dumps({
        "draft_id": "TEMPLATE-ID", "draft_name": name, "draft_fold_path": project.as_posix(),
        "draft_materials": [], "tm_duration": 0}))
    return project


def test_detect_version_reads_app_made_drafts_and_override(tmp_path):
    store = tmp_path / "store"
    _app_project(store, "a", "8.7.0")
    _app_project(store, "b", "9.3.0")
    assert detect_version(store) == ("9.3.0", "draft 'b'")
    assert detect_version(store, "10.1") == ("10.1", "CAPCUT_VERSION")
    assert detect_version(tmp_path / "missing") == (None, "unknown")


def test_capcut_10_and_running_app_are_refused_unless_forced(tmp_path, pycapcut, monkeypatch, work):
    store = tmp_path / "store"
    _app_project(store, "Mẫu", "10.2.0")
    with pytest.raises(CapCutRefused, match="10.2.0"):
        CapCutExporter(store).export(work)
    assert [p.name for p in store.iterdir()] == ["Mẫu"]  # nothing written
    assert CapCutExporter(store, force=True).export(work).is_dir()

    monkeypatch.setattr(capcut, "capcut_running", lambda: True)
    with pytest.raises(CapCutRefused, match="running"):
        CapCutExporter(store, version="9.3.0").export(work)


def test_draft_is_seeded_from_an_app_made_project(tmp_path, pycapcut, work):
    store = tmp_path / "store"
    template = _app_project(store, "Mẫu trống", "9.3.0")
    (store / "root_meta_info.json").write_text(json.dumps({"all_draft_store": [{
        "draft_fold_path": template.as_posix(), "draft_id": "TEMPLATE-ID", "draft_name": "Mẫu trống",
        "draft_json_file": (template / "draft_info.json").as_posix(), "draft_type": ""}], "draft_ids": 1}))

    draft = CapCutExporter(store).export(work)

    info = json.loads((draft / "draft_info.json").read_text())
    assert (draft / "template-2.tmp").read_text() == (draft / "draft_info.json").read_text()  # synced mirrors
    assert not (draft / "draft_content.json").exists()  # never a stray file the template does not use
    assert not (draft / "Timelines").exists()  # the app rebuilds it from the root files
    assert info["platform"]["app_version"] == "9.3.0" and info["version"] == 360000
    assert info["config"] == {"maintrack_adsorb": True} and info["materials"]["effects"] == []
    assert "tracks" in info and info["canvas"] == [1080, 1920, 30]  # our edit, the template's markers
    meta = json.loads((draft / "draft_meta_info.json").read_text())
    assert meta["draft_id"] != "TEMPLATE-ID" and meta["draft_id"] == info["id"]
    assert meta["draft_name"] == draft.name and meta["draft_fold_path"] == draft.as_posix()
    assert (draft / "ai_content_agent.json").exists()

    root = json.loads((store / "root_meta_info.json").read_text())
    assert root["draft_ids"] == 2 and root["all_draft_store"][0]["draft_id"] == meta["draft_id"]
    assert root["all_draft_store"][0]["draft_json_file"].endswith("/draft_info.json")
    assert list(store.glob("root_meta_info.json.bak-*"))

    second = CapCutExporter(store).export(work)  # "auto" never seeds from our own drafts
    assert json.loads((second / "ai_content_agent.json").read_text())["template"] == "Mẫu trống"


def test_unreadable_mirror_is_not_written_and_named_template_must_exist(tmp_path, pycapcut, work):
    store = tmp_path / "store"
    _app_project(store, "Mẫu", "9.1.0", encrypted_mirror=True)
    draft = CapCutExporter(store, template="Mẫu").export(work)
    assert (draft / "draft_info.json").exists() and not (draft / "template-2.tmp").exists()
    with pytest.raises(FileNotFoundError, match="CAPCUT_TEMPLATE"):
        CapCutExporter(store, template="Không có").export(work)


def test_text_ranges_are_utf16_and_nfc():
    import unicodedata

    text = unicodedata.normalize("NFD", "Mẹo hay 🔥")
    content = {"materials": {"texts": [{"content": json.dumps(
        {"text": text, "styles": [{"range": [0, len(text)], "size": 7}]})}]}}
    assert fix_text_ranges(content) == 1
    inner = json.loads(content["materials"]["texts"][0]["content"])
    assert inner["text"] == "Mẹo hay 🔥" and inner["styles"][0]["range"] == [0, 10]  # 🔥 is 2 UTF-16 units


def test_check_reports_version_support(tmp_path):
    store = tmp_path / "store"
    _app_project(store, "a", "10.0.1")
    info = CapCutExporter(store).check()
    assert info["version"] == "10.0.1" and info["supported"] is False
    status = capcut.capcut_status(store)
    assert status["ready"] is False and status["version"] == "10.0.1"


# ---------- edit bundle ----------


def test_edit_bundle_is_a_valid_fcpxml_with_media(tmp_path, work):
    bundle = EditBundleExporter().export(work)

    [fcpxml] = bundle.glob("*.fcpxml")
    root = ET.parse(fcpxml).getroot()
    assert root.tag == "fcpxml" and root.get("version") == "1.10"
    fmt = root.find("resources/format")
    assert (fmt.get("width"), fmt.get("height"), fmt.get("frameDuration")) == ("1080", "1920", "1/30s")
    spine = root.find("library/event/project/sequence/spine")
    scenes = list(spine)
    assert len(scenes) == 2 and all(clip.tag == "video" for clip in scenes)  # stills from the card engine
    assert [c.find("asset-clip").get("lane") for c in scenes] == ["-1", "-1"]  # each scene's voice
    for asset in root.iter("asset"):
        src = asset.find("media-rep").get("src")
        assert src.startswith("file://") and (bundle / "media" / Path(src).name).is_file()
    total = sum(Fraction(c.get("duration")[:-1]) for c in scenes)  # rational seconds, e.g. 151/30s
    timeline = json.loads((work / "timeline.json").read_text())
    assert total == pytest.approx(timeline["duration"], abs=1 / 30)
    assert (bundle / "captions.srt").is_file() and (bundle / "final.mp4").is_file()
    assert "Tiền điện tăng vọt?" in (bundle / "README.txt").read_text(encoding="utf-8")


def test_pipeline_falls_back_to_bundle_when_capcut_refuses(tmp_path):
    from fakes import FakeStudio

    from ai_content_agent.pipeline.content_pipeline import ContentPipeline

    class Refusing:
        def export(self, work_dir):
            raise CapCutRefused("CapCut 10.1 is too new")

    calls = []

    class Bundle:
        def export(self, work_dir):
            calls.append(work_dir)
            return Path(work_dir) / "edit_bundle"

    import ai_content_agent.pipeline.content_pipeline as module

    original = module.EditBundleExporter
    module.EditBundleExporter = Bundle
    try:
        pipeline = ContentPipeline(FakeStudio(str(tmp_path / "run" / "final.mp4")), [], make_thumbnails=False,
                                   capcut_exporter=Refusing())
        outcome = pipeline.run("x", dry_run=True)
    finally:
        module.EditBundleExporter = original
    assert outcome.capcut_draft.endswith("edit_bundle") and len(calls) == 1


def test_api_bundle_and_capcut_refusal(tmp_path, work, monkeypatch):
    history = HistoryStore(str(tmp_path / "h.db"))
    jobs = JobManager(lambda *a, **k: None)
    jobs._jobs["j1"] = Job(id="j1", topic="t", platforms=[], style="", dry_run=True, force=False, source="manual",
                           video_path=str(work / "final.mp4"), status="succeeded")

    class Refusing:
        def export(self, work_dir):
            raise CapCutRefused("CapCut 10.1 is too new")

    client = TestClient(create_app(history=history, jobs=jobs, token=TOKEN, config_status={},
                                   capcut_exporter=Refusing()))
    refused = client.post("/api/jobs/j1/capcut", headers=AUTH)
    assert refused.status_code == 409 and refused.json()["detail"].endswith("[bundle]")
    bundle = client.post("/api/jobs/j1/bundle", headers=AUTH).json()["bundle"]
    assert Path(bundle, "captions.srt").is_file()


def test_cli_capcut_check_and_bundle(tmp_path, work, monkeypatch, capsys):
    from ai_content_agent import cli

    store = tmp_path / "store"
    _app_project(store, "a", "9.3.0")
    monkeypatch.setattr(capcut, "capcut_running", lambda: False)
    monkeypatch.setenv("CAPCUT_DRAFTS_DIR", str(store))
    monkeypatch.setattr("sys.argv", ["ai-content-agent", "capcut", "--check"])
    cli.main()
    assert "Version: 9.3.0 (draft 'a')" in capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["ai-content-agent", "capcut", str(work), "--bundle"])
    cli.main()
    assert "Edit bundle:" in capsys.readouterr().out and (work / "edit_bundle").is_dir()

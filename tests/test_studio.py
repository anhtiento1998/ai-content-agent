"""Studio tests: storyboard parsing, caption timing, and real ffmpeg renders with offline engines."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fakes import STORYBOARD, FailingVoice, FakeText, TestPatternClips
from PIL import Image

from ai_content_agent.providers.local_provider import CardImageProvider, SilentVoiceProvider
from ai_content_agent.studio import StudioSettings, StudioStageError, VideoStudio, parse_storyboard
from ai_content_agent.studio.captions import Caption, build_ass, split_into_chunks, time_captions
from ai_content_agent.studio.storyboard import MAX_SCENES, build_storyboard_prompt

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


# ---------- storyboard ----------


def test_parse_storyboard_cleans_fields():
    board = parse_storyboard("```json\n" + json.dumps(STORYBOARD, ensure_ascii=False) + "\n```")

    assert board.title == "5 mẹo tiết kiệm điện mùa hè"
    assert board.hashtags == ["tietkiemdien", "meohay"]
    assert [s.on_screen_text for s in board.scenes] == ["Tiền điện tăng vọt?", ""]
    script = board.to_script_result()
    assert script.title == board.title
    assert board.scenes[0].narration in script.script


@pytest.mark.parametrize(
    "data, message",
    [
        ({**STORYBOARD, "scenes": []}, "no scenes"),
        ({**STORYBOARD, "title": "  "}, "title"),
        ({**STORYBOARD, "scenes": [{"narration": "hi"}]}, "visual_prompt"),
    ],
)
def test_parse_storyboard_rejects_incomplete_plans(data, message):
    with pytest.raises(ValueError, match=message):
        parse_storyboard(json.dumps(data))


def test_parse_storyboard_caps_scene_count():
    many = {**STORYBOARD, "scenes": [STORYBOARD["scenes"][1]] * (MAX_SCENES + 5)}
    assert len(parse_storyboard(json.dumps(many)).scenes) == MAX_SCENES


def test_storyboard_prompt_mentions_language_and_length():
    prompt = build_storyboard_prompt("cà phê", language="vi", target_seconds=40)
    assert "Vietnamese" in prompt and "~100 words" in prompt and "cà phê" in prompt


# ---------- captions ----------


TEXT = "Tiền điện tháng này lại tăng vọt? Đừng lo, có năm mẹo cực kỳ đơn giản sau đây."


def test_split_into_chunks_never_straddles_a_sentence():
    chunks = split_into_chunks(TEXT)

    assert " ".join(chunks).split() == TEXT.split()
    assert not any(re.search(r"[.!?…]\s", chunk) for chunk in chunks)
    assert any(chunk.endswith("tăng vọt?") for chunk in chunks)
    assert all(len(chunk) <= 28 for chunk in chunks)


def test_split_into_chunks_merges_short_clauses_of_one_sentence():
    assert split_into_chunks("Đừng lo, thật đấy. Bắt đầu nhé!") == ["Đừng lo, thật đấy.", "Bắt đầu nhé!"]


def test_time_captions_are_contiguous_and_fill_the_voice():
    captions = time_captions(["một hai ba", "bốn", "năm sáu bảy tám"], start=10.0, duration=6.0)
    assert captions[0].start == 10.0
    assert captions[-1].end == pytest.approx(16.0)
    for prev, nxt in zip(captions, captions[1:]):
        assert prev.end == pytest.approx(nxt.start)
    assert captions[2].end - captions[2].start > captions[1].end - captions[1].start


def test_build_ass_escapes_override_characters():
    ass = build_ass([Caption(0, 1.5, "a {\\b1} b")], [Caption(61.25, 62, "Hook")], font="Arial")
    assert "a (/b1) b" in ass
    assert "0:01:01.25,0:01:02.00,Hook" in ass
    assert "Style: Caption,Arial," in ass


# ---------- full renders ----------


def _probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    return (video["width"], video["height"]), has_audio, float(data["format"]["duration"])


def _settings(tmp_path, **overrides):
    return StudioSettings(**{"output_dir": str(tmp_path / "out"), "music_dir": None, "font": "DejaVu Sans", **overrides})


@needs_ffmpeg
def test_render_with_images_music_and_logo(tmp_path):
    music = tmp_path / "music"
    music.mkdir()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=3",
                    str(music / "tone.mp3")], check=True)
    Image.new("RGBA", (300, 120), (255, 0, 0, 200)).save(tmp_path / "logo.png")
    studio = VideoStudio(
        FakeText(), CardImageProvider(), SilentVoiceProvider(),
        _settings(tmp_path, music_dir=str(music), logo_path=str(tmp_path / "logo.png")),
    )

    storyboard, video = studio.produce("tiết kiệm điện")

    size, has_audio, duration = _probe(video.file_path)
    assert size == (1080, 1920) and has_audio
    assert duration == pytest.approx(video.duration_seconds, abs=0.15)
    work = Path(video.raw["work_dir"])
    assert json.loads((work / "storyboard.json").read_text(encoding="utf-8"))["title"] == storyboard.title
    assert "Tiền điện tăng vọt?" in (work / "subtitles.ass").read_text(encoding="utf-8")


@needs_ffmpeg
def test_render_with_video_clips_loops_short_clips(tmp_path):
    studio = VideoStudio(FakeText(), TestPatternClips(), SilentVoiceProvider(), _settings(tmp_path))

    _, video = studio.produce("tiết kiệm điện")

    size, _, duration = _probe(video.file_path)
    assert size == (1080, 1920)
    assert duration > 6  # each 1.5s clip was looped to cover its 3.5–4.6s narration


@needs_ffmpeg
def test_voice_failure_is_tagged_with_stage_and_scene(tmp_path):
    studio = VideoStudio(FakeText(), CardImageProvider(), FailingVoice(), _settings(tmp_path))

    with pytest.raises(StudioStageError) as info:
        studio.produce("topic")

    assert info.value.stage == "voice"
    assert str(info.value) == "scene 1: RuntimeError: voice service down"


@pytest.mark.parametrize("writer", [FakeText(fail=True), FakeText(reply="Sorry, I can't do that.")])
def test_storyboard_failure_is_tagged_as_script_stage(tmp_path, writer):
    studio = VideoStudio(writer, CardImageProvider(), SilentVoiceProvider(), _settings(tmp_path))

    with pytest.raises(StudioStageError) as info:
        studio.produce("topic")

    assert info.value.stage == "script"


def test_studio_rejects_non_visual_provider(tmp_path):
    with pytest.raises(TypeError):
        VideoStudio(FakeText(), SilentVoiceProvider(), SilentVoiceProvider(), _settings(tmp_path))


# ---------- robustness ----------


class FlakyVoice(SilentVoiceProvider):
    """Fails the first `failures` calls with the given error, then succeeds."""

    def __init__(self, error, failures=1):
        self.calls = 0
        self._error, self._failures = error, failures

    def synthesize(self, text, out_path):
        self.calls += 1
        if self.calls <= self._failures:
            raise self._error
        super().synthesize(text, out_path)


class RateLimited(Exception):
    status_code = 429


class ConcurrencyTrackingImages(CardImageProvider):
    max_concurrency = 1

    def __init__(self):
        import threading

        self.active = self.peak = 0
        self._lock = threading.Lock()

    def generate_image(self, prompt, out_path, *, aspect_ratio="9:16"):
        import time

        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(0.05)
        super().generate_image(prompt, out_path, aspect_ratio=aspect_ratio)
        with self._lock:
            self.active -= 1


def test_string_hashtags_are_split_into_words():
    board = parse_storyboard(json.dumps({**STORYBOARD, "hashtags": "#tietkiem, #meohay  dien"}))
    assert board.hashtags == ["tietkiem", "meohay", "dien"]


@needs_ffmpeg
def test_transient_errors_are_retried(tmp_path):
    voice = FlakyVoice(RateLimited("slow down"), failures=2)
    studio = VideoStudio(FakeText(), CardImageProvider(), voice, _settings(tmp_path, retry_base_delay=0))

    studio.produce("topic")

    assert voice.calls == 2 + len(STORYBOARD["scenes"])


def test_permanent_errors_fail_fast_without_retry(tmp_path):
    voice = FlakyVoice(ValueError("invalid api key"), failures=99)
    studio = VideoStudio(FakeText(), CardImageProvider(), voice, _settings(tmp_path, retry_base_delay=0))

    with pytest.raises(StudioStageError):
        studio.produce("topic")
    assert voice.calls <= len(STORYBOARD["scenes"])


@needs_ffmpeg
def test_visual_provider_concurrency_limit_is_respected(tmp_path):
    images = ConcurrencyTrackingImages()
    studio = VideoStudio(FakeText(), images, SilentVoiceProvider(), _settings(tmp_path))

    studio.produce("topic")

    assert images.peak == 1


@needs_ffmpeg
@pytest.mark.parametrize("keep", [False, True])
def test_intermediates_are_cleaned_unless_kept(tmp_path, keep):
    studio = VideoStudio(FakeText(), CardImageProvider(), SilentVoiceProvider(), _settings(tmp_path, keep_intermediates=keep))

    _, video = studio.produce("topic")

    names = {p.name for p in Path(video.raw["work_dir"]).iterdir()}
    kept = {"storyboard.json", "subtitles.ass", "final.mp4", "scene_01_visual.png", "scene_01_voice.wav"}
    assert kept <= names
    assert ("voice.wav" in names) is keep
    assert ("scene_01_voice_raw.wav" in names) is keep


def test_real_sdk_errors_are_classified_for_retry():
    import anthropic
    import httpx
    import openai
    from google.genai import errors

    from ai_content_agent.studio.studio import _is_transient

    request = httpx.Request("POST", "https://example.invalid")

    def response(code):
        return httpx.Response(code, request=request)

    assert _is_transient(openai.RateLimitError("rl", response=response(429), body=None))
    assert _is_transient(openai.APIConnectionError(request=request))
    assert _is_transient(anthropic.APIStatusError("overloaded", response=response(529), body=None))
    assert _is_transient(errors.ServerError(503, {"error": {"code": 503, "message": "unavailable"}}))
    assert not _is_transient(openai.AuthenticationError("bad key", response=response(401), body=None))
    assert not _is_transient(errors.ClientError(400, {"error": {"code": 400, "message": "bad"}}))


@needs_ffmpeg
def test_studio_reports_real_progress_in_order(tmp_path):
    events = []
    studio = VideoStudio(FakeText(), CardImageProvider(), SilentVoiceProvider(), _settings(tmp_path))

    studio.produce("topic", progress=lambda stage, done, total: events.append((stage, done, total)))

    stages = [e[0] for e in events]
    assert stages[0] == "script" and stages[-1] == "render"
    asset_counts = [done for stage, done, total in events if stage == "assets"]
    assert asset_counts == list(range(0, 2 * len(STORYBOARD["scenes"]) + 1))

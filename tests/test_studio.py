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

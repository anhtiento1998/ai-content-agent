"""VideoStudio: topic -> storyboard -> voice + visual per scene -> captions -> final MP4.

Every run gets its own work folder (output/<slug>_<timestamp>/) holding
storyboard.json and every intermediate file, so a run can be inspected,
re-rendered, or exported to a desktop editor later.
"""

from __future__ import annotations

import json
import logging
import random
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ai_content_agent.media.ffmpeg import wav_duration
from ai_content_agent.providers.base import (
    ImageGenerator,
    TextGenerator,
    VideoGenerator,
    VideoResult,
    VoiceGenerator,
)
from ai_content_agent.studio import render
from ai_content_agent.studio.captions import Caption, build_ass, split_into_chunks, time_captions
from ai_content_agent.studio.storyboard import Storyboard, write_storyboard
from ai_content_agent.utils import slugify

logger = logging.getLogger(__name__)
_MUSIC_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
_TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504, 529}  # 529 = Anthropic "overloaded"
_TRANSIENT_NAMES = {"APIConnectionError", "APITimeoutError", "RateLimitError", "ServiceUnavailable"}
# Kept after a successful render: inputs a desktop editor needs to rebuild the
# edit (storyboard, per-scene visuals and voice, captions) plus the outputs.
_KEEP_PATTERNS = ("storyboard.json", "scene_*_visual.*", "scene_??_voice.wav", "subtitles.ass", "final.mp4", "thumbnail.jpg")


@dataclass
class StudioSettings:
    language: str = "vi"
    target_seconds: int = 40
    output_dir: str = "output"
    music_dir: str | None = "assets/music"
    logo_path: str | None = None
    font: str = "Arial"
    scene_padding: float = 0.35
    max_workers: int = 4
    retry_attempts: int = 3
    retry_base_delay: float = 4.0
    keep_intermediates: bool = False


Progress = Callable[[str, int, int], None]
"""progress(stage, done, total) — stage is script | assets | render; done/total count assets."""


def _no_progress(_stage: str, _done: int, _total: int) -> None:
    return None


class StudioStageError(RuntimeError):
    """A studio failure tagged with the stage it happened in (script/voice/visual/render)."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


def _is_transient(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return (
        (isinstance(status, int) and status in _TRANSIENT_STATUS)
        or isinstance(exc, (ConnectionError, TimeoutError))
        or type(exc).__name__ in _TRANSIENT_NAMES
    )


def _await(future: Future, stage: str, index: int):
    try:
        return future.result()
    except Exception as exc:
        raise StudioStageError(stage, f"scene {index}: {type(exc).__name__}: {exc}") from exc


class VideoStudio:
    def __init__(
        self,
        writer: TextGenerator,
        visuals: ImageGenerator | VideoGenerator,
        voice: VoiceGenerator,
        settings: StudioSettings | None = None,
    ) -> None:
        if not isinstance(visuals, (ImageGenerator, VideoGenerator)):
            raise TypeError(f"visual provider must be an ImageGenerator or VideoGenerator, got {visuals!r}")
        self._writer = writer
        self._visuals = visuals
        self._voice = voice
        self._settings = settings or StudioSettings()

    @property
    def engine_names(self) -> dict:
        return {"text": self._writer.name, "visual": self._visuals.name, "voice": self._voice.name}

    def _with_retries(self, fn, *args, **kwargs):
        """Retry rate limits, 5xx and connection errors with exponential backoff; fail fast otherwise."""

        attempts = max(1, self._settings.retry_attempts)
        for attempt in range(1, attempts + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                if attempt == attempts or not _is_transient(exc):
                    raise
                delay = self._settings.retry_base_delay * 2 ** (attempt - 1)
                logger.warning("Transient %s (attempt %d/%d), retrying in %.0fs", type(exc).__name__, attempt, attempts, delay)
                time.sleep(delay)

    def produce(
        self, topic: str, *, style: str = "", progress: Progress | None = None
    ) -> tuple[Storyboard, VideoResult]:
        report = progress or _no_progress
        report("script", 0, 0)
        storyboard = self.write_storyboard(topic, style=style)
        return storyboard, self.render(storyboard, progress=report)

    def write_storyboard(self, topic: str, *, style: str = "") -> Storyboard:
        logger.info("Writing storyboard for topic=%r via %s", topic, self._writer.name)
        try:
            return self._with_retries(
                write_storyboard,
                self._writer,
                topic,
                style=style,
                language=self._settings.language,
                target_seconds=self._settings.target_seconds,
            )
        except Exception as exc:
            raise StudioStageError("script", f"{type(exc).__name__}: {exc}") from exc

    def render(self, storyboard: Storyboard, *, progress: Progress | None = None) -> VideoResult:
        report = progress or _no_progress
        work = self._new_work_dir(storyboard.title)
        cwd = str(work)
        (work / "storyboard.json").write_text(
            json.dumps(storyboard.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        scenes = storyboard.scenes
        is_video = isinstance(self._visuals, VideoGenerator)
        visual_files = [f"scene_{i:02d}_visual.{'mp4' if is_video else 'png'}" for i in range(1, len(scenes) + 1)]
        logger.info("Rendering %d scenes in %s (visual=%s, voice=%s)", len(scenes), work, self._visuals.name, self._voice.name)

        voice_durations = self._generate_assets(scenes, visual_files, work, is_video, report)

        report("render", 0, 0)
        try:
            durations = [round((d + self._settings.scene_padding) * render.FPS) / render.FPS for d in voice_durations]
            clips, audios = [], []
            for i, duration in enumerate(durations, 1):
                clip, audio = f"scene_{i:02d}.mp4", f"scene_{i:02d}_audio.wav"
                if is_video:
                    render.video_to_clip(visual_files[i - 1], clip, duration, cwd=cwd)
                else:
                    render.image_to_clip(visual_files[i - 1], clip, duration, zoom_in=i % 2 == 1, cwd=cwd)
                render.pad_audio(f"scene_{i:02d}_voice.wav", audio, duration, cwd=cwd)
                clips.append(clip)
                audios.append(audio)
            render.concat(clips, "visuals.mp4", cwd=cwd)
            render.concat(audios, "voice.wav", cwd=cwd)

            captions, hooks, start = [], [], 0.0
            for scene, voice_duration, duration in zip(scenes, voice_durations, durations):
                captions += time_captions(split_into_chunks(scene.narration), start, voice_duration)
                if scene.on_screen_text:
                    hooks.append(Caption(start, start + duration, scene.on_screen_text))
                start += duration
            (work / "subtitles.ass").write_text(build_ass(captions, hooks, font=self._settings.font), encoding="utf-8")

            total = sum(durations)
            render.compose_final(
                "visuals.mp4",
                "voice.wav",
                "subtitles.ass",
                "final.mp4",
                total,
                cwd=cwd,
                music=self._pick_music(),
                logo=self._logo(),
            )
        except Exception as exc:
            raise StudioStageError("render", f"{type(exc).__name__}: {exc}") from exc

        if not self._settings.keep_intermediates:
            self._remove_intermediates(work)
        logger.info("Rendered %.1fs video: %s", total, work / "final.mp4")
        return VideoResult(
            file_path=str(work / "final.mp4"),
            duration_seconds=total,
            raw={"work_dir": str(work), "scenes": len(scenes), "engines": self.engine_names},
        )

    def _generate_assets(
        self, scenes, visual_files: list[str], work: Path, is_video: bool, report: Progress
    ) -> list[float]:
        """Voice and visual for every scene, concurrently — these are the slow API calls."""

        visual_slots = threading.Semaphore(self._visuals.max_concurrency or self._settings.max_workers)
        total, finished, counter_lock = 2 * len(scenes), [0], threading.Lock()
        report("assets", 0, total)

        def tick(_future: Future) -> None:
            with counter_lock:  # report under the lock so counts never arrive out of order
                finished[0] += 1
                report("assets", finished[0], total)

        def make_voice(i: int, text: str) -> float:
            raw, clean = f"scene_{i:02d}_voice_raw.wav", f"scene_{i:02d}_voice.wav"
            self._with_retries(self._voice.synthesize, text, str(work / raw))
            render.normalize_audio(raw, clean, cwd=str(work))
            return wav_duration(str(work / clean))

        def make_visual(prompt: str, name: str) -> None:
            generate = self._visuals.generate_clip if is_video else self._visuals.generate_image
            with visual_slots:
                self._with_retries(generate, prompt, str(work / name))

        pool = ThreadPoolExecutor(max_workers=self._settings.max_workers, thread_name_prefix="studio")
        try:
            voices = [pool.submit(make_voice, i, s.narration) for i, s in enumerate(scenes, 1)]
            visuals = [pool.submit(make_visual, s.visual_prompt, n) for s, n in zip(scenes, visual_files)]
            for future in (*voices, *visuals):
                future.add_done_callback(tick)
            durations = [_await(f, "voice", i) for i, f in enumerate(voices, 1)]
            for i, future in enumerate(visuals, 1):
                _await(future, "visual", i)
        except BaseException:
            pool.shutdown(wait=False, cancel_futures=True)
            raise
        pool.shutdown()
        return durations

    @staticmethod
    def _remove_intermediates(work: Path) -> None:
        keep = {path for pattern in _KEEP_PATTERNS for path in work.glob(pattern)}
        for path in work.iterdir():
            if path.is_file() and path not in keep:
                path.unlink()

    def _new_work_dir(self, title: str) -> Path:
        base = Path(self._settings.output_dir).resolve()
        stem = f"{slugify(title)}_{time.strftime('%Y%m%d-%H%M%S')}"
        work, n = base / stem, 1
        while work.exists():
            n += 1
            work = base / f"{stem}_{n}"
        work.mkdir(parents=True)
        return work

    def _pick_music(self) -> str | None:
        folder = Path(self._settings.music_dir) if self._settings.music_dir else None
        if not folder or not folder.is_dir():
            return None
        tracks = [p for p in folder.iterdir() if p.suffix.lower() in _MUSIC_EXTENSIONS]
        return str(random.choice(tracks).resolve()) if tracks else None

    def _logo(self) -> str | None:
        path = self._settings.logo_path
        return str(Path(path).resolve()) if path and Path(path).is_file() else None

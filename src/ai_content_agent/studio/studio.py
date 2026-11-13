"""VideoStudio: topic -> storyboard -> voice + visual per scene -> captions -> final MP4.

Every run gets its own work folder (output/<slug>_<timestamp>/) holding
storyboard.json, provenance.json and every intermediate file, so a run can be
inspected, re-rendered, or exported to a desktop editor later.

A Checkpoint (used by batch runs) remembers the storyboard and work folder:
a run resumed after a crash reuses the storyboard instead of paying for a new
one, and skips every scene voice/visual already on disk.
"""

from __future__ import annotations

import json
import logging
import random
import shutil
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ai_content_agent.costs import CostMeter, PriceBook
from ai_content_agent.media import encoders
from ai_content_agent.media.ffmpeg import probe_video, wav_duration
from ai_content_agent.providers.base import (
    AvatarGenerator,
    ImageGenerator,
    TextGenerator,
    VideoGenerator,
    VideoResult,
    VoiceGenerator,
)
from ai_content_agent.studio import render
from ai_content_agent.studio.align import _tokens
from ai_content_agent.studio.captions import (
    Caption,
    TimedWord,
    build_ass,
    build_srt,
    estimate_word_times,
    group_into_captions,
    split_into_chunks,
)
from ai_content_agent.studio.provenance import MusicLibrary, build_provenance, metadata_tags
from ai_content_agent.studio.storyboard import Storyboard, storyboard_from_dict, write_storyboard
from ai_content_agent.studio.variation import VariationPlan
from ai_content_agent.studio.vi_text import nfc, spoken_words
from ai_content_agent.utils import slugify

logger = logging.getLogger(__name__)
BUNDLED_FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
DEFAULT_FONT = "Be Vietnam Pro"  # bundled (SIL OFL); full Vietnamese coverage on every OS
_TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504, 529}  # 529 = Anthropic "overloaded"
_TRANSIENT_NAMES = {"APIConnectionError", "APITimeoutError", "RateLimitError", "ServiceUnavailable"}
# Kept after a successful render: inputs a desktop editor needs to rebuild the
# edit (storyboard, per-scene visuals and voice, captions) plus the outputs.
_KEEP_PATTERNS = (
    "storyboard.json", "timeline.json", "scene_*_visual.*", "scene_??_voice.wav",
    "subtitles.ass", "subtitles.srt", "final.mp4", "thumbnail.jpg", "provenance.json", "scene_??_avatar.mp4",
)
AVATAR_LAYOUTS = ("corner", "full")
LOW_PRONUNCIATION_SCORE = 0.6  # aligner recognised fewer than this share of a scene's words


@dataclass
class StudioSettings:
    language: str = "vi"
    target_seconds: int = 40
    output_dir: str = "output"
    music_dir: str | None = "assets/music"
    logo_path: str | None = None
    font: str = DEFAULT_FONT
    fonts_dir: str | None = str(BUNDLED_FONTS)
    caption_style: str = "karaoke"
    ai_label: str | None = None  # text kept in a corner of the video, e.g. "Video có sử dụng AI"
    require_music_license: bool = True
    video_encoder: str = "auto"  # auto | libx264 | h264_nvenc | h264_qsv | h264_amf
    pricing_file: str | None = None  # JSON overriding costs.DEFAULT_PRICES
    # With an avatar engine: "corner" = talking head in a circle over each scene's visual,
    # "full" = the avatar fills the frame and no scene visuals are generated.
    avatar_layout: str = "corner"
    avatar_position: str = "bottom-left"
    avatar_size_percent: int = 34
    scene_padding: float = 0.35
    max_workers: int = 4
    retry_attempts: int = 3
    retry_base_delay: float = 4.0
    keep_intermediates: bool = False


@dataclass
class Checkpoint:
    """Progress a resumed run can reuse. `save` is called whenever a field changes."""

    storyboard: dict | None = None
    work_dir: str | None = None
    save: Callable[["Checkpoint"], None] | None = field(default=None, repr=False)

    def commit(self) -> None:
        if self.save:
            self.save(self)


ScriptReview = Callable[[Storyboard], "str | None"]
"""review(storyboard) -> None to accept, or text of a too-similar earlier script to steer one rewrite."""


Progress = Callable[[str, int, int], None]
"""progress(stage, done, total) — stage is script | assets | render; done/total count assets."""


def _no_progress(_stage: str, _done: int, _total: int) -> None:
    return None


class StudioStageError(RuntimeError):
    """A studio failure tagged with the stage it happened in (script/voice/visual/render)."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage
        self.cost: dict | None = None  # what the failed run had already spent (set by produce)


def _is_transient(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return (
        (isinstance(status, int) and status in _TRANSIENT_STATUS)
        or isinstance(exc, (ConnectionError, TimeoutError))
        or type(exc).__name__ in _TRANSIENT_NAMES
    )


def _exists(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


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
        *,
        aligner=None,
        avatar: AvatarGenerator | None = None,
    ) -> None:
        if not isinstance(visuals, (ImageGenerator, VideoGenerator)):
            raise TypeError(f"visual provider must be an ImageGenerator or VideoGenerator, got {visuals!r}")
        settings = settings or StudioSettings()
        if avatar is not None:
            if settings.avatar_layout not in AVATAR_LAYOUTS:
                raise ValueError(f"AVATAR_LAYOUT must be one of {', '.join(AVATAR_LAYOUTS)}, "
                                 f"got {settings.avatar_layout!r}")
            render.avatar_box(settings.avatar_size_percent, settings.avatar_position)  # validates the position
        self._avatar = avatar
        self._writer = writer
        self._visuals = visuals
        self._voice = voice
        self._settings = settings
        self._aligner = aligner
        self._prices = PriceBook(self._settings.pricing_file)
        self.music = MusicLibrary(self._settings.music_dir, self._settings.require_music_license)

    @property
    def engine_names(self) -> dict:
        names = {"text": self._writer.name, "visual": self._visuals.name, "voice": self._voice.name}
        if self._avatar is not None:
            names["avatar"] = self._avatar.name
        return names

    @property
    def _avatar_full(self) -> bool:
        return self._avatar is not None and self._settings.avatar_layout == "full"

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
        self,
        topic: str,
        *,
        style: str = "",
        progress: Progress | None = None,
        plan: VariationPlan | None = None,
        checkpoint: Checkpoint | None = None,
        review: ScriptReview | None = None,
    ) -> tuple[Storyboard, VideoResult]:
        report = progress or _no_progress
        report("script", 0, 0)
        meter = CostMeter(self._prices)
        try:
            if checkpoint and checkpoint.storyboard:
                storyboard = storyboard_from_dict(checkpoint.storyboard)
                logger.info("Using the saved storyboard %r", storyboard.title)
            else:
                storyboard = self._write_reviewed(topic, style, plan, review, meter)
                if checkpoint:
                    checkpoint.storyboard = storyboard.to_dict()
                    checkpoint.commit()
            return storyboard, self.render(storyboard, progress=report, plan=plan, checkpoint=checkpoint, meter=meter)
        except StudioStageError as exc:
            exc.cost = meter.summary()  # money already spent on a run that failed
            raise

    def _write_reviewed(self, topic, style, plan, review, meter) -> Storyboard:
        hook = plan.hook_instruction if plan else ""
        storyboard = self.write_storyboard(topic, style=style, hook=hook, meter=meter)
        similar = review(storyboard) if review else None
        if similar:
            logger.info("Storyboard too similar to an earlier script — rewriting once with a different angle")
            storyboard = self.write_storyboard(topic, style=style, hook=hook, avoid=similar, meter=meter)
        return storyboard

    def draft(
        self, topic: str, *, style: str = "", plan: VariationPlan | None = None, review: ScriptReview | None = None
    ) -> tuple[Storyboard, dict]:
        """Write the storyboard only (for editing before rendering). Returns it with what it cost."""

        meter = CostMeter(self._prices)
        try:
            return self._write_reviewed(topic, style, plan, review, meter), meter.summary()
        except StudioStageError as exc:
            exc.cost = meter.summary()
            raise

    def write_storyboard(
        self, topic: str, *, style: str = "", hook: str = "", avoid: str = "", meter: CostMeter | None = None
    ) -> Storyboard:
        logger.info("Writing storyboard for topic=%r via %s", topic, self._writer.name)
        self._writer.last_usage = None
        try:
            return self._with_retries(
                write_storyboard,
                self._writer,
                topic,
                style=style,
                language=self._settings.language,
                target_seconds=self._settings.target_seconds,
                hook=hook,
                avoid=avoid,
            )
        except Exception as exc:
            raise StudioStageError("script", f"{type(exc).__name__}: {exc}") from exc
        finally:
            usage = self._writer.last_usage  # billed even when the reply could not be parsed
            if meter is not None and usage:
                meter.add_text(self._writer.name, usage.get("model") or getattr(self._writer, "_model", None),
                               usage.get("input_tokens", 0), usage.get("output_tokens", 0))

    def render(
        self,
        storyboard: Storyboard,
        *,
        progress: Progress | None = None,
        plan: VariationPlan | None = None,
        checkpoint: Checkpoint | None = None,
        meter: CostMeter | None = None,
    ) -> VideoResult:
        report = progress or _no_progress
        plan = plan or VariationPlan()
        meter = meter or CostMeter(self._prices)
        work = self._work_dir(storyboard.title, checkpoint)
        cwd = str(work)
        (work / "storyboard.json").write_text(
            json.dumps(storyboard.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        scenes = storyboard.scenes
        avatar_files = [f"scene_{i:02d}_avatar.mp4" for i in range(1, len(scenes) + 1)] if self._avatar else []
        # In the full layout the talking head *is* the visual: nothing else is generated.
        is_video = self._avatar_full or isinstance(self._visuals, VideoGenerator)
        visual_files = avatar_files if self._avatar_full else [
            f"scene_{i:02d}_visual.{'mp4' if is_video else 'png'}" for i in range(1, len(scenes) + 1)]
        language = self._settings.language
        caption_words = [nfc(scene.narration).split() for scene in scenes]
        spoken = [spoken_words(words, language) for words in caption_words]
        prompts = [f"{scene.visual_prompt}, {plan.visual_suffix}" if plan.visual_suffix else scene.visual_prompt
                   for scene in scenes]
        logger.info("Rendering %d scenes in %s (visual=%s, voice=%s)", len(scenes), work, self._visuals.name, self._voice.name)

        voice_durations = self._generate_assets(
            [" ".join(words) for words in spoken], prompts, visual_files, work, is_video, report, plan.voice, meter
        )
        word_times, scores = self._word_times(work, caption_words, spoken, voice_durations)

        report("render", 0, 0)
        try:
            encoder = encoders.detect(self._settings.video_encoder)
            durations = [round((d + self._settings.scene_padding) * render.FPS) / render.FPS for d in voice_durations]
            corner = self._avatar is not None and not self._avatar_full
            if corner:
                size, x, y = render.avatar_box(self._settings.avatar_size_percent, self._settings.avatar_position)
                render.write_avatar_mask(size, str(work / "avatar_mask.png"), str(work / "avatar_ring.png"))
            clips, audios = [], []
            for i, duration in enumerate(durations, 1):
                clip, audio = f"scene_{i:02d}.mp4", f"scene_{i:02d}_audio.wav"
                base = f"scene_{i:02d}_base.mp4" if corner else clip
                if is_video:
                    render.video_to_clip(visual_files[i - 1], base, duration, cwd=cwd, encoder=encoder)
                else:
                    render.image_to_clip(visual_files[i - 1], base, duration, zoom_in=i % 2 == 1, cwd=cwd,
                                         encoder=encoder)
                if corner:
                    render.overlay_avatar(base, avatar_files[i - 1], clip, duration, size=size, x=x, y=y,
                                          mask="avatar_mask.png", ring="avatar_ring.png", cwd=cwd, encoder=encoder)
                render.pad_audio(f"scene_{i:02d}_voice.wav", audio, duration, cwd=cwd)
                clips.append(clip)
                audios.append(audio)
            render.concat(clips, "visuals.mp4", cwd=cwd)
            render.concat(audios, "voice.wav", cwd=cwd)

            captions, hooks, start = [], [], 0.0
            for scene, words, timed, duration in zip(scenes, caption_words, word_times, durations):
                shifted = [TimedWord(w.text, start + w.start, start + w.end) for w in timed]
                captions += group_into_captions(split_into_chunks(" ".join(words)), shifted)
                if scene.on_screen_text:
                    hooks.append(Caption(start, start + duration, nfc(scene.on_screen_text)))
                start += duration
            total = sum(durations)
            settings = self._settings
            (work / "subtitles.ass").write_text(
                build_ass(captions, hooks, font=settings.font, style=settings.caption_style,
                          label=settings.ai_label, duration=total),
                encoding="utf-8",
            )
            (work / "subtitles.srt").write_text(build_srt(captions), encoding="utf-8")

            music_name = self._choose_music(plan)
            music, logo = (self.music.path(music_name) if music_name else None), self._logo()
            plan.music = music_name
            provenance = build_provenance(
                writer=self._writer, visuals=self._visuals, voice=self._voice, voice_name=plan.voice,
                music={"file": music_name, **(self.music.license_for(music_name) or {})} if music_name else None,
                plan=plan.to_dict(), language=language, disclosure=settings.ai_label,
                scenes=len(scenes), duration=total,
            )
            provenance["encoder"] = encoder.name
            if self._avatar is not None:
                provenance["engines"]["avatar"] = {
                    "provider": self._avatar.name, "model": getattr(self._avatar, "_model", None),
                    "layout": self._settings.avatar_layout,
                }
            provenance["cost"] = meter.summary()
            if scores:
                provenance["pronunciation"] = {"scene_scores": scores, "min": min(scores)}
            (work / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
            self._write_timeline(work, storyboard, visual_files, is_video, voice_durations, durations, music, logo,
                                 avatar=self._avatar_overlay(avatar_files) if corner else None)
            fonts = self._stage_fonts(work)
            render.compose_final(
                "visuals.mp4", "voice.wav", "subtitles.ass", "final.mp4", total, cwd=cwd, music=music, logo=logo,
                fontsdir=fonts, metadata=metadata_tags(provenance, storyboard.title), encoder=encoder,
            )
        except Exception as exc:
            raise StudioStageError("render", f"{type(exc).__name__}: {exc}") from exc

        if not self._settings.keep_intermediates:
            self._remove_intermediates(work)
        logger.info("Rendered %.1fs video: %s", total, work / "final.mp4")
        return VideoResult(
            file_path=str(work / "final.mp4"),
            duration_seconds=total,
            width=render.WIDTH,
            height=render.HEIGHT,
            raw={"work_dir": str(work), "scenes": len(scenes), "engines": self.engine_names,
                 "provenance": provenance, "variation": plan.to_dict(), "cost": provenance["cost"]},
        )

    def _word_times(self, work: Path, caption_words, spoken, voice_durations) -> tuple[list[list[TimedWord]], list[float]]:
        """Per scene, a time span for every caption word (relative to the scene start), plus the
        aligner's pronunciation score per scene when an aligner is configured."""

        result, scores = [], []
        for i, (words, said, duration) in enumerate(zip(caption_words, spoken, voice_durations), 1):
            timed = None
            if self._aligner is not None:
                try:
                    alignment = self._aligner.align(str(work / f"scene_{i:02d}_voice.wav"), " ".join(said))
                    scores.append(round(alignment.score, 3))
                    if alignment.score < LOW_PRONUNCIATION_SCORE:
                        logger.warning("Scene %d: the recogniser matched only %.0f%% of the narration — "
                                       "check pronunciation", i, alignment.score * 100)
                    if alignment.times:
                        timed = self._map_tokens(words, said, alignment.times, duration)
                except Exception:
                    logger.warning("Word alignment failed for scene %d — using estimated timing", i, exc_info=True)
            result.append(timed or estimate_word_times(words, said, 0.0, duration))
        return result, scores

    @staticmethod
    def _map_tokens(words, said, token_times, duration) -> list[TimedWord] | None:
        """Caption word i spans the aligned times of the tokens its spoken form contains."""

        counts = [len(_tokens(text)) for text in said]
        if sum(counts) != len(token_times):
            return None
        timed, index, previous_end = [], 0, 0.0
        for word, count in zip(words, counts):
            if count == 0:
                timed.append(TimedWord(word, previous_end, previous_end))
                continue
            start, end = token_times[index][0], token_times[index + count - 1][1]
            start = max(start, previous_end)
            end = min(max(end, start), duration)
            timed.append(TimedWord(word, start, end))
            previous_end, index = end, index + count
        return timed

    def _generate_assets(
        self, narrations: list[str], prompts: list[str], visual_files: list[str], work: Path, is_video: bool,
        report: Progress, voice_name: str | None = None, meter: CostMeter | None = None,
    ) -> list[float]:
        """Voice and visual for every scene, concurrently — these are the slow API calls.
        Files already in the work folder (a resumed run) are reused, not generated again."""

        visual_slots = threading.Semaphore(self._visuals.max_concurrency or self._settings.max_workers)
        scenes = len(narrations)
        steps = scenes * ((0 if self._avatar_full else 1) + 1 + (1 if self._avatar else 0))  # visual, voice, avatar
        total, finished, counter_lock = steps, [0], threading.Lock()
        report("assets", 0, total)

        def tick(_future: Future) -> None:
            with counter_lock:  # report under the lock so counts never arrive out of order
                finished[0] += 1
                report("assets", finished[0], total)

        meter = meter or CostMeter(self._prices)
        voice_model, visual_model = getattr(self._voice, "_model", None), getattr(self._visuals, "_model", None)

        def make_voice(i: int, text: str) -> float:
            raw, clean = f"scene_{i:02d}_voice_raw.wav", f"scene_{i:02d}_voice.wav"
            generated = not _exists(work / clean)
            if generated:
                if voice_name:
                    self._with_retries(self._voice.synthesize, text, str(work / raw), voice=voice_name)
                else:
                    self._with_retries(self._voice.synthesize, text, str(work / raw))
                render.normalize_audio(raw, clean, cwd=str(work))
            duration = wav_duration(str(work / clean))
            if generated:  # files reused from a checkpoint were paid for by the earlier attempt
                meter.add_voice(self._voice.name, voice_model, duration)
            return duration

        def make_visual(prompt: str, name: str) -> None:
            if _exists(work / name):
                return
            generate = self._visuals.generate_clip if is_video else self._visuals.generate_image
            with visual_slots:
                self._with_retries(generate, prompt, str(work / name))
            if not is_video:
                meter.add_images(self._visuals.name, visual_model)
                return
            try:
                seconds = probe_video(str(work / name))[2]
            except Exception:
                seconds = float(getattr(self._visuals, "clip_seconds", 8))
            meter.add_video(self._visuals.name, visual_model, seconds)

        pool = ThreadPoolExecutor(max_workers=self._settings.max_workers, thread_name_prefix="studio")
        try:
            voices = [pool.submit(make_voice, i, text) for i, text in enumerate(narrations, 1)]
            visuals = [] if self._avatar_full else [
                pool.submit(make_visual, prompt, n) for prompt, n in zip(prompts, visual_files)]
            for future in (*voices, *visuals):
                future.add_done_callback(tick)
            durations = [_await(f, "voice", i) for i, f in enumerate(voices, 1)]
            for i, future in enumerate(visuals, 1):
                _await(future, "visual", i)
        except BaseException:
            pool.shutdown(wait=False, cancel_futures=True)
            raise
        pool.shutdown()

        if self._avatar is not None:
            # One at a time, after the voices exist: lip-sync runs on the local GPU from each voice track.
            for i in range(1, scenes + 1):
                target = work / f"scene_{i:02d}_avatar.mp4"
                if not _exists(target):
                    try:
                        self._with_retries(self._avatar.animate, str(work / f"scene_{i:02d}_voice.wav"), str(target))
                    except Exception as exc:
                        raise StudioStageError("avatar", f"scene {i}: {type(exc).__name__}: {exc}") from exc
                    meter.add_video(f"{self._avatar.name}-avatar", getattr(self._avatar, "_model", None),
                                    durations[i - 1])
                tick(None)
        return durations

    def _avatar_overlay(self, avatar_files: list[str]) -> dict:
        """Where the corner avatar sits, for exporters that rebuild the edit."""

        size, x, y = render.avatar_box(self._settings.avatar_size_percent, self._settings.avatar_position)
        return {"files": avatar_files, "size": size, "x": x, "y": y, "position": self._settings.avatar_position}

    @staticmethod
    def _write_timeline(work, storyboard, visual_files, is_video, voice_durations, durations, music, logo,
                        avatar: dict | None = None) -> None:
        """timeline.json: the edit decision list — what plays when. Exporters (CapCut) rebuild the
        edit from this instead of re-deriving timings."""

        scenes, start = [], 0.0
        for i, (scene, visual, voice_duration, duration) in enumerate(
            zip(storyboard.scenes, visual_files, voice_durations, durations), 1
        ):
            scenes.append({
                "index": i,
                "start": round(start, 6),
                "duration": duration,
                "visual": visual,
                "visual_kind": "video" if is_video else "image",
                "zoom_in": i % 2 == 1,
                "voice": f"scene_{i:02d}_voice.wav",
                "voice_duration": voice_duration,
                "on_screen_text": scene.on_screen_text,
                "avatar": avatar["files"][i - 1] if avatar else None,
            })
            start += duration
        timeline = {
            "title": storyboard.title,
            "width": render.WIDTH,
            "height": render.HEIGHT,
            "fps": render.FPS,
            "duration": sum(durations),
            "captions": "subtitles.srt",
            "music": music,
            "logo": logo,
            "avatar": {key: value for key, value in avatar.items() if key != "files"} if avatar else None,
            "scenes": scenes,
        }
        (work / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _remove_intermediates(work: Path) -> None:
        keep = {path for pattern in _KEEP_PATTERNS for path in work.glob(pattern)}
        for path in work.iterdir():
            if path.is_file() and path not in keep:
                path.unlink()
        shutil.rmtree(work / "fonts", ignore_errors=True)

    def _stage_fonts(self, work: Path) -> str | None:
        """Copy the bundled fonts next to the subtitles so libass finds them through a relative
        `fontsdir` (absolute Windows paths need fragile escaping inside ffmpeg filters)."""

        source = Path(self._settings.fonts_dir) if self._settings.fonts_dir else None
        fonts = [p for p in source.iterdir() if p.suffix.lower() in (".ttf", ".otf")] if source and source.is_dir() else []
        if not fonts:
            return None
        target = work / "fonts"
        target.mkdir(exist_ok=True)
        for font in fonts:
            shutil.copy2(font, target / font.name)
        return "fonts"

    def _work_dir(self, title: str, checkpoint: Checkpoint | None) -> Path:
        if checkpoint and checkpoint.work_dir and Path(checkpoint.work_dir).is_dir():
            logger.info("Resuming in %s — scene files already there are reused", checkpoint.work_dir)
            return Path(checkpoint.work_dir)
        work = self._new_work_dir(title)
        if checkpoint:
            checkpoint.work_dir = str(work)
            checkpoint.commit()
        return work

    def _new_work_dir(self, title: str) -> Path:
        base = Path(self._settings.output_dir).resolve()
        stem = f"{slugify(title)}_{time.strftime('%Y%m%d-%H%M%S')}"
        work, n = base / stem, 1
        while work.exists():
            n += 1
            work = base / f"{stem}_{n}"
        work.mkdir(parents=True)
        return work

    def _choose_music(self, plan: VariationPlan) -> str | None:
        """The plan's track if it is still usable (licensed, present), else a random usable one."""

        tracks = self.music.usable_tracks()
        if plan.music in tracks:
            return plan.music
        return random.choice(tracks) if tracks else None

    def _logo(self) -> str | None:
        path = self._settings.logo_path
        return str(Path(path).resolve()) if path and Path(path).is_file() else None

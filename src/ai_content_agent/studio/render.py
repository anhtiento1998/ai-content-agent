"""ffmpeg building blocks: per-scene clips, concatenation and the final mix.

All functions take file names relative to `cwd` (the run's work folder).
Every scene clip is encoded with identical parameters so they can be
concatenated losslessly with `-c copy`.
"""

from __future__ import annotations

from pathlib import Path

from ai_content_agent.media.ffmpeg import run_ffmpeg

WIDTH, HEIGHT, FPS = 1080, 1920, 30
_ZOOM = 0.12
_X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS)]
_PCM = ["-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le"]


def image_to_clip(image: str, out: str, duration: float, *, zoom_in: bool, cwd: str) -> None:
    """Slow Ken Burns zoom over a still. Upscaling 2x first avoids zoompan's sub-pixel jitter."""

    frames = max(1, round(duration * FPS))
    step = _ZOOM / frames
    zoom = f"min(1+{step:.7f}*on,{1 + _ZOOM})" if zoom_in else f"max({1 + _ZOOM}-{step:.7f}*on,1)"
    vf = (
        f"scale={WIDTH * 2}:{HEIGHT * 2}:force_original_aspect_ratio=increase,crop={WIDTH * 2}:{HEIGHT * 2},"
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}"
    )
    run_ffmpeg(["-i", image, "-vf", vf, "-frames:v", str(frames), *_X264, "-an", out], cwd=cwd)


def video_to_clip(video: str, out: str, duration: float, *, cwd: str) -> None:
    """Cover-crop to 9:16, loop if shorter than the narration, trim if longer, drop its audio."""

    vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}"
    run_ffmpeg(
        ["-stream_loop", "-1", "-i", video, "-t", f"{duration:.3f}", "-vf", vf, *_X264, "-an", out], cwd=cwd
    )


def normalize_audio(src: str, out: str, *, cwd: str) -> None:
    run_ffmpeg(["-i", src, *_PCM, out], cwd=cwd)


def pad_audio(src: str, out: str, duration: float, *, cwd: str) -> None:
    run_ffmpeg(["-i", src, "-af", "apad", "-t", f"{duration:.3f}", *_PCM, out], cwd=cwd)


def concat(files: list[str], out: str, *, cwd: str) -> None:
    list_name = f"{Path(out).stem}_list.txt"
    (Path(cwd) / list_name).write_text("".join(f"file '{name}'\n" for name in files), encoding="utf-8")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", list_name, "-c", "copy", out], cwd=cwd)


def compose_final(
    visuals: str,
    voice: str,
    subtitles: str,
    out: str,
    duration: float,
    *,
    cwd: str,
    music: str | None = None,
    logo: str | None = None,
    fontsdir: str | None = None,
    metadata: dict[str, str] | None = None,
) -> None:
    inputs = ["-i", visuals, "-i", voice]
    next_index = 2
    ass = f"ass={subtitles}:fontsdir={fontsdir}" if fontsdir else f"ass={subtitles}"
    filters = [
        f"[0:v]{ass}[sub]",
        "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[voice]",
    ]
    video_label, audio_label = "sub", "voice"

    if music:
        music_index, next_index = next_index, next_index + 1
        inputs += ["-stream_loop", "-1", "-i", music]
        fade_start = max(0.0, duration - 1.5)
        filters += [
            f"[{music_index}:a]loudnorm=I=-30:TP=-2,aresample=48000,"
            f"afade=t=in:d=0.8,afade=t=out:st={fade_start:.2f}:d=1.5[bgm]",
            "[voice][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]",
        ]
        audio_label = "mix"

    if logo:
        logo_index = next_index
        inputs += ["-i", logo]
        filters += [f"[{logo_index}:v]scale=170:-1[logo]", "[sub][logo]overlay=W-w-48:72[branded]"]
        video_label = "branded"

    run_ffmpeg(
        [
            *inputs,
            "-filter_complex", ";".join(filters),
            "-map", f"[{video_label}]",
            "-map", f"[{audio_label}]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{duration:.3f}",
            *[arg for key, value in (metadata or {}).items() for arg in ("-metadata", f"{key}={value}")],
            "-movflags", "+faststart",
            out,
        ],
        cwd=cwd,
    )

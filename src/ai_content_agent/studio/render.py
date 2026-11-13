"""ffmpeg building blocks: per-scene clips, concatenation and the final mix.

All functions take file names relative to `cwd` (the run's work folder).
Every scene clip is encoded with identical parameters so they can be
concatenated losslessly with `-c copy`.
"""

from __future__ import annotations

from pathlib import Path

from ai_content_agent.media.encoders import ENCODERS, Encoder
from ai_content_agent.media.ffmpeg import run_ffmpeg

WIDTH, HEIGHT, FPS = 1080, 1920, 30
_ZOOM = 0.12
_PCM = ["-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le"]


def _video(encoder: Encoder | None, *, final: bool = False) -> list[str]:
    return [*(encoder or ENCODERS["libx264"]).args(final=final), "-r", str(FPS)]


def image_to_clip(
    image: str, out: str, duration: float, *, zoom_in: bool, cwd: str, encoder: Encoder | None = None
) -> None:
    """Slow Ken Burns zoom over a still. Upscaling 2x first avoids zoompan's sub-pixel jitter."""

    frames = max(1, round(duration * FPS))
    step = _ZOOM / frames
    zoom = f"min(1+{step:.7f}*on,{1 + _ZOOM})" if zoom_in else f"max({1 + _ZOOM}-{step:.7f}*on,1)"
    vf = (
        f"scale={WIDTH * 2}:{HEIGHT * 2}:force_original_aspect_ratio=increase,crop={WIDTH * 2}:{HEIGHT * 2},"
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}"
    )
    run_ffmpeg(["-i", image, "-vf", vf, "-frames:v", str(frames), *_video(encoder), "-an", out], cwd=cwd)


def video_to_clip(video: str, out: str, duration: float, *, cwd: str, encoder: Encoder | None = None) -> None:
    """Cover-crop to 9:16, loop if shorter than the narration, trim if longer, drop its audio."""

    vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}"
    run_ffmpeg(
        ["-stream_loop", "-1", "-i", video, "-t", f"{duration:.3f}", "-vf", vf, *_video(encoder), "-an", out],
        cwd=cwd,
    )


AVATAR_POSITIONS = ("bottom-left", "bottom-right", "top-left", "top-right")
_AVATAR_MARGIN = 48
_AVATAR_TOP = 260  # below the AI label and logo
_AVATAR_ABOVE_CAPTIONS = 590  # captions sit 440 px above the bottom edge; stay clear of them


def avatar_box(size_percent: int, position: str) -> tuple[int, int, int]:
    """(size, x, y) in pixels of the avatar circle for a corner position."""

    if position not in AVATAR_POSITIONS:
        raise ValueError(f"AVATAR_POSITION must be one of {', '.join(AVATAR_POSITIONS)}, got {position!r}")
    size = max(120, min(WIDTH - 2 * _AVATAR_MARGIN, round(WIDTH * size_percent / 100))) // 2 * 2
    x = _AVATAR_MARGIN if position.endswith("left") else WIDTH - size - _AVATAR_MARGIN
    y = _AVATAR_TOP if position.startswith("top") else HEIGHT - _AVATAR_ABOVE_CAPTIONS - size
    return size, x, y


def write_avatar_mask(size: int, mask_path: str, ring_path: str, *, ring_width: int = 8) -> None:
    """A circular alpha mask and a white ring to frame the avatar."""

    from PIL import Image, ImageDraw

    scale = 4  # draw large and shrink for smooth edges
    mask = Image.new("L", (size * scale, size * scale), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * scale - 1, size * scale - 1], fill=255)
    mask.resize((size, size), Image.LANCZOS).save(mask_path)
    ring = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([0, 0, size * scale - 1, size * scale - 1], outline=(255, 255, 255, 235),
                                 width=ring_width * scale)
    ring.resize((size, size), Image.LANCZOS).save(ring_path)


def overlay_avatar(
    base: str, avatar: str, out: str, duration: float, *, size: int, x: int, y: int, mask: str, ring: str,
    cwd: str, encoder: Encoder | None = None,
) -> None:
    """Put the talking head in a circle over a scene clip. The avatar is cropped to a square from
    its upper part (where the face is), looped if it is shorter than the scene, and muted."""

    filters = (
        f"[1:v]fps={FPS},scale={size}:{size}:force_original_aspect_ratio=increase,"
        f"crop={size}:{size}:(iw-{size})/2:(ih-{size})*0.2,format=yuva420p[head];"
        f"[2:v]format=gray[mask];[head][mask]alphamerge[cut];"
        f"[0:v][cut]overlay={x}:{y}[framed];[framed][3:v]overlay={x}:{y}[v]"
    )
    run_ffmpeg(
        ["-i", base, "-stream_loop", "-1", "-i", avatar, "-loop", "1", "-i", mask, "-loop", "1", "-i", ring,
         "-filter_complex", filters, "-map", "[v]", "-t", f"{duration:.3f}", *_video(encoder), "-an", out],
        cwd=cwd,
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
    encoder: Encoder | None = None,
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
            *_video(encoder, final=True),
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{duration:.3f}",
            *[arg for key, value in (metadata or {}).items() for arg in ("-metadata", f"{key}={value}")],
            "-movflags", "+faststart",
            out,
        ],
        cwd=cwd,
    )

"""Thin wrappers around the ffmpeg/ffprobe binaries.

Commands run with `cwd` set to the working folder and relative file names,
which sidesteps ffmpeg's filter-argument escaping of Windows drive letters
(`C:\\...`) in filters such as `ass=`.
"""

from __future__ import annotations

import json
import os
import subprocess
import wave


def ffmpeg_bin() -> str:
    return os.getenv("FFMPEG_PATH") or "ffmpeg"


def run_ffmpeg(args: list[str], *, cwd: str | None = None) -> None:
    proc = subprocess.run(
        [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {proc.stderr.strip()[-800:]}")


def ffprobe_bin() -> str:
    explicit = os.getenv("FFPROBE_PATH")
    if explicit:
        return explicit
    ffmpeg = os.getenv("FFMPEG_PATH")
    if ffmpeg:  # ffprobe ships next to ffmpeg in every standard build
        sibling = os.path.join(os.path.dirname(ffmpeg), "ffprobe" + (".exe" if ffmpeg.lower().endswith(".exe") else ""))
        if os.path.exists(sibling):
            return sibling
    return "ffprobe"


def probe_video(path: str) -> tuple[int, int, float]:
    """(width, height, duration_seconds) of the first video stream."""

    proc = subprocess.run(
        [ffprobe_bin(), "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:format=duration", "-of", "json", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {proc.stderr.strip()[-300:]}")
    data = json.loads(proc.stdout)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"]), float(data["format"]["duration"])


def wav_duration(path: str) -> float:
    with wave.open(path, "rb") as wav:
        return wav.getnframes() / float(wav.getframerate())

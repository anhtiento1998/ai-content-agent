"""Thin wrappers around the ffmpeg/ffprobe binaries.

Commands run with `cwd` set to the working folder and relative file names,
which sidesteps ffmpeg's filter-argument escaping of Windows drive letters
(`C:\\...`) in filters such as `ass=`.
"""

from __future__ import annotations

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


def wav_duration(path: str) -> float:
    with wave.open(path, "rb") as wav:
        return wav.getnframes() / float(wav.getframerate())

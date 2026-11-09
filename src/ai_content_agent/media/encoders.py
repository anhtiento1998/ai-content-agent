"""Pick the H.264 encoder: a GPU encoder when one actually works, else libx264.

VIDEO_ENCODER=auto (default) tries NVIDIA NVENC, Intel Quick Sync and AMD
AMF in that order. "Listed by `ffmpeg -encoders`" is not enough — an ffmpeg
build lists NVENC on machines without an NVIDIA GPU or with an old driver —
so each candidate must encode a few frames before it is chosen. The choice is
cached for the process. GeForce cards allow at most 8 concurrent NVENC
sessions (older drivers 3–5); the studio encodes one clip at a time, so a
single render never comes near that.
"""

from __future__ import annotations

import logging
import subprocess
import threading
from dataclasses import dataclass

from ai_content_agent.media.ffmpeg import ffmpeg_bin

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Encoder:
    name: str
    fast: tuple[str, ...]  # per-scene clips (re-encoded again in the final pass)
    final: tuple[str, ...]  # the published file
    pix_fmt: str = "yuv420p"  # 4:2:0 either way; Quick Sync wants it as nv12

    def args(self, *, final: bool) -> list[str]:
        return ["-c:v", self.name, *(self.final if final else self.fast), "-pix_fmt", self.pix_fmt]


ENCODERS = {
    "libx264": Encoder("libx264", ("-preset", "veryfast", "-crf", "20"), ("-preset", "medium", "-crf", "20")),
    "h264_nvenc": Encoder("h264_nvenc", ("-preset", "p2", "-cq", "21", "-b:v", "0"),
                          ("-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "20", "-b:v", "0")),
    "h264_qsv": Encoder("h264_qsv", ("-preset", "veryfast", "-global_quality", "22"),
                        ("-preset", "medium", "-global_quality", "20"), pix_fmt="nv12"),
    "h264_amf": Encoder("h264_amf", ("-quality", "speed", "-rc", "cqp", "-qp_i", "22", "-qp_p", "22"),
                        ("-quality", "quality", "-rc", "cqp", "-qp_i", "20", "-qp_p", "20")),
}
GPU_ORDER = ("h264_nvenc", "h264_qsv", "h264_amf")

_cache: dict[str, Encoder] = {}
_lock = threading.Lock()


def _listed() -> set[str]:
    try:
        proc = subprocess.run([ffmpeg_bin(), "-hide_banner", "-encoders"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.SubprocessError):
        return set()
    return {name for name in GPU_ORDER if f" {name} " in proc.stdout}


def works(name: str) -> bool:
    """Encode a few frames with `name` to prove the GPU, driver and ffmpeg build agree."""

    encoder = ENCODERS[name]
    try:
        proc = subprocess.run(
            [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-f", "lavfi",
             "-i", "color=c=black:s=320x568:r=30:d=0.2", *encoder.args(final=False), "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def detect(choice: str = "auto") -> Encoder:
    """The encoder to use for `choice` (auto | libx264 | h264_nvenc | h264_qsv | h264_amf)."""

    choice = (choice or "auto").strip().lower()
    if choice not in ("auto", *ENCODERS):
        raise ValueError(f"VIDEO_ENCODER must be auto or one of {', '.join(ENCODERS)}, got {choice!r}")
    with _lock:
        if choice in _cache:
            return _cache[choice]
        if choice == "libx264":
            encoder = ENCODERS["libx264"]
        elif choice != "auto":
            if not works(choice):
                logger.warning("VIDEO_ENCODER=%s does not work on this machine — falling back to libx264", choice)
                encoder = ENCODERS["libx264"]
            else:
                encoder = ENCODERS[choice]
        else:
            encoder = ENCODERS["libx264"]
            for name in (n for n in GPU_ORDER if n in _listed()):
                if works(name):
                    encoder = ENCODERS[name]
                    break
            logger.info("Video encoder: %s", encoder.name)
        _cache[choice] = encoder
        return encoder


def status(choice: str = "auto") -> dict:
    """Dashboard entry; runs detection (a second or two the first time)."""

    try:
        encoder = detect(choice)
    except ValueError as exc:
        return {"encoder": None, "gpu": False, "note": str(exc)}
    return {"encoder": encoder.name, "gpu": encoder.name != "libx264", "note": None}

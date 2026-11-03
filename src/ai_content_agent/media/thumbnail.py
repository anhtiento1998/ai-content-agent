"""Auto-generate a 1280x720 thumbnail: grab a frame from the rendered video
with ffmpeg, then overlay the title with Pillow.

Requires the `ffmpeg` binary on PATH (not a Python package) and Pillow.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

_SIZE = (1280, 720)
_BAR_HEIGHT = 200


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def extract_frame(video_path: str, *, at_seconds: float = 1.0) -> str:
    fd, frame_path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(at_seconds),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            frame_path,
        ],
        check=True,
        capture_output=True,
    )
    return frame_path


def generate_thumbnail(video_path: str, title: str, out_path: str) -> str:
    """Extract a frame from `video_path`, overlay `title`, write to `out_path`."""

    frame_path = extract_frame(video_path)
    try:
        image = ImageOps.fit(Image.open(frame_path).convert("RGB"), _SIZE)
    finally:
        Path(frame_path).unlink(missing_ok=True)

    overlay = Image.new("RGBA", _SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(
        [(0, _SIZE[1] - _BAR_HEIGHT), (_SIZE[0], _SIZE[1])],
        fill=(0, 0, 0, 160),
    )

    font = _load_font(64)
    text = title if len(title) <= 60 else title[:57] + "..."
    draw.text(
        (40, _SIZE[1] - _BAR_HEIGHT + 55),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )

    composed = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    composed.save(out_path, "JPEG", quality=90)
    return out_path

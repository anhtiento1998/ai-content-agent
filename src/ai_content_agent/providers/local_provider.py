"""Offline engines that need no API key — for previewing layout and for tests.

- CardImageProvider ("card"): a colored gradient background per scene.
- SilentVoiceProvider ("silent"): silence sized to the narration, so the
  video is captions + music only (a valid style on its own).
"""

from __future__ import annotations

import hashlib
import wave

from PIL import Image, ImageDraw, ImageFilter

from .base import ImageGenerator, VoiceGenerator

_PALETTES = [
    ((24, 32, 72), (120, 60, 160)),
    ((10, 60, 70), (30, 150, 130)),
    ((80, 20, 40), (220, 100, 60)),
    ((20, 20, 30), (70, 90, 140)),
    ((60, 30, 90), (230, 120, 170)),
]
_SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}


class CardImageProvider(ImageGenerator):
    name = "card"

    def generate_image(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        width, height = _SIZES.get(aspect_ratio, _SIZES["9:16"])
        seed = int(hashlib.sha256(prompt.encode()).hexdigest(), 16)
        top, bottom = _PALETTES[seed % len(_PALETTES)]

        image = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(image)
        for y in range(height):
            t = y / (height - 1)
            draw.line([(0, y), (width, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))

        glow = Image.new("L", (width, height), 0)
        glow_draw = ImageDraw.Draw(glow)
        cx, cy = width * (0.25 + (seed % 50) / 100), height * (0.3 + (seed // 50 % 40) / 100)
        radius = width * 0.45
        glow_draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=90)
        glow = glow.filter(ImageFilter.GaussianBlur(radius=width // 6))
        image = Image.composite(Image.new("RGB", (width, height), (255, 255, 255)), image, glow)
        image.save(out_path, "PNG")


class SilentVoiceProvider(VoiceGenerator):
    name = "silent"
    _WORDS_PER_SECOND = 2.6
    _RATE = 24000

    def synthesize(self, text: str, out_path: str) -> None:
        seconds = max(1.5, len(text.split()) / self._WORDS_PER_SECOND)
        with wave.open(out_path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self._RATE)
            wav.writeframes(b"\0\0" * int(seconds * self._RATE))

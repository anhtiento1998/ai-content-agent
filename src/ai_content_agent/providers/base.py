"""Abstract interfaces for every external AI service the studio uses.

Each kind of engine has one small interface: text (storyboards), image and
video (scene visuals), voice (narration). Adding a new engine means
implementing one of these and registering it in providers/__init__.py.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ScriptResult:
    """Text metadata publishers attach to a post."""

    title: str
    script: str
    hashtags: list[str] = field(default_factory=list)
    raw: dict | None = None


@dataclass
class VideoResult:
    file_path: str
    duration_seconds: float | None = None
    thumbnail_path: str | None = None
    raw: dict | None = None
    width: int | None = None
    height: int | None = None


def parse_json_object(text: str) -> dict:
    """Parse a model's JSON reply, tolerating ```json fences or stray prose around it."""

    if not text:
        raise ValueError("Model returned no text (the request may have been refused or safety-blocked)")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(f"Model reply contains no JSON object: {text[:200]!r}")
        candidate = text[start : end + 1]
    return json.loads(candidate)


class TextGenerator(ABC):
    """LLM used to write storyboards (GPT, Claude, Gemini, Muse Spark, ...)."""

    name: str

    @abstractmethod
    def complete(self, prompt: str) -> str:
        ...


class ImageGenerator(ABC):
    """Still image per scene; the studio animates it with a slow zoom."""

    name: str
    max_concurrency: int | None = None

    @abstractmethod
    def generate_image(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        ...


class VideoGenerator(ABC):
    """Short video clip per scene; the studio trims or loops it to the narration length."""

    name: str
    max_concurrency: int | None = None

    @abstractmethod
    def generate_clip(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        ...


class VoiceGenerator(ABC):
    """Text-to-speech for scene narration."""

    name: str

    @abstractmethod
    def synthesize(self, text: str, out_path: str) -> None:
        """Write speech for `text` to `out_path` as a WAV file."""

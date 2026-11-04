"""Abstract interfaces every AI provider plugs into.

Adding a new provider (another LLM, image or video engine) means
implementing one of these classes and registering it in providers/__init__.py
— nothing else in the pipeline needs to change.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ScriptResult:
    title: str
    script: str
    hashtags: list[str] = field(default_factory=list)
    raw: dict | None = None


def build_script_prompt(topic: str, style: str, max_words: int) -> str:
    return (
        f"Write a short-form video script about: {topic}\n"
        f"Style: {style or 'engaging, punchy, social-media friendly'}\n"
        f"Limit the spoken script to about {max_words} words.\n"
        "Respond with ONLY a JSON object, no prose: "
        '{"title": str, "script": str, "hashtags": [str, ...]}'
    )


def parse_script_json(text: str) -> ScriptResult:
    """Parse a model's JSON reply, tolerating ```json fences or stray prose around it."""

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(f"Model reply contains no JSON object: {text[:200]!r}")
        candidate = text[start : end + 1]

    data = json.loads(candidate)
    return ScriptResult(
        title=data["title"],
        script=data["script"],
        hashtags=[h.lstrip("#") for h in data.get("hashtags", [])],
        raw=data,
    )


@dataclass
class VideoResult:
    file_path: str
    duration_seconds: float | None = None
    thumbnail_path: str | None = None
    raw: dict | None = None


class TextGenerator(ABC):
    """Produces video ideas / scripts / captions (GPT, Claude, Gemini, ...)."""

    name: str

    @abstractmethod
    def generate_script(self, topic: str, *, style: str = "", max_words: int = 150) -> ScriptResult:
        ...


class VideoGenerator(ABC):
    """Turns a script/prompt into a rendered video file (Muse, Veo, ...)."""

    name: str

    @abstractmethod
    def generate_video(self, script: ScriptResult, *, aspect_ratio: str = "9:16") -> VideoResult:
        ...

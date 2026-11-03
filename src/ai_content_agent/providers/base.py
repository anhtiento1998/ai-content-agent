"""Abstract interfaces every AI provider plugs into.

Adding a new provider (another LLM, image or video engine) means
implementing one of these classes and registering it in providers/__init__.py
— nothing else in the pipeline needs to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ScriptResult:
    title: str
    script: str
    hashtags: list[str] = field(default_factory=list)
    raw: dict | None = None


@dataclass
class VideoResult:
    file_path: str
    duration_seconds: float | None = None
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

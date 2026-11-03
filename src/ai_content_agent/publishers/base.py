"""Abstract interface every publishing target implements.

Adding a new platform later (X, LinkedIn, Pinterest, ...) means writing one
class here and registering it in publishers/__init__.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ai_content_agent.providers.base import ScriptResult, VideoResult


@dataclass
class PublishResult:
    platform: str
    remote_id: str
    url: str | None = None
    raw: dict | None = None


class Publisher(ABC):
    name: str

    @abstractmethod
    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        ...

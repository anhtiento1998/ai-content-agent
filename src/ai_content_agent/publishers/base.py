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
    status: str | None = None  # e.g. "processing" when the platform finishes asynchronously
    raw: dict | None = None


@dataclass
class Disclosure:
    """AI-content disclosure applied on upload: platform flags where an API field exists,
    plus a visible line in the caption (Vietnam's Decree 142/2026 accepts title/description labels)."""

    enabled: bool = True
    text: str = "Video có sử dụng AI"

    def caption(self, body: str) -> str:
        return f"{body}\n\n{self.text}" if self.enabled and self.text else body


class Publisher(ABC):
    name: str

    @abstractmethod
    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        ...

    def delete(self, remote_id: str) -> None:
        """Take a published post down. Platforms without a delete API raise NotImplementedError."""

        raise NotImplementedError(f"{self.name} has no API to delete posts — remove it in the {self.name} app")

"""Abstract interface every publishing target implements.

Adding a new platform later (X, LinkedIn, Pinterest, ...) means writing one
class here and registering it in publishers/__init__.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

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


class PublishRejected(RuntimeError):
    """The platform refused the post before receiving it (bad privacy, too short, ...). Nothing was
    uploaded, so a retry never needs to look for a half-finished copy."""


# Hard posting limits per platform per rolling 24 h, applied on top of MAX_POSTS_PER_DAY:
# YouTube uploads 100/day per Cloud project (since 1 Jun 2026), TikTok ~15/day per creator,
# Facebook 30 API-published reels per Page.
PLATFORM_DAILY_LIMITS = {"youtube": 100, "tiktok": 15, "facebook": 30}


class Publisher(ABC):
    name: str

    @abstractmethod
    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        ...

    def find_existing(self, script: ScriptResult, since: datetime) -> PublishResult | None:
        """Look on the platform for a post of this script made since `since` — used before re-uploading
        after an attempt whose result was never recorded. Platforms that cannot search return None."""

        return None

    def stats(self, remote_ids: list[str]) -> dict[str, dict]:
        """{remote_id: {"views": int, "likes": int | None, "comments": int | None}} for the posts the
        platform can report on. Platforms without a statistics API return {}."""

        return {}

    def delete(self, remote_id: str) -> None:
        """Take a published post down. Platforms without a delete API raise NotImplementedError."""

        raise NotImplementedError(f"{self.name} has no API to delete posts — remove it in the {self.name} app")

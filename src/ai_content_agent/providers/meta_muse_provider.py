"""Meta Muse models via the official Meta Model API.

Status as of Oct 2026:
- Muse Spark (text): available through the Meta Model API (public preview,
  US developers only). The API is OpenAI-compatible, so MuseSparkProvider
  reuses the OpenAI SDK pointed at Meta's base URL.
- Muse Video: no official developer API yet. MetaMuseVideoProvider fails
  fast so a studio configured with it doesn't spend money writing a
  storyboard it can never render. Third-party wrappers that drive the
  consumer muse.ai subscription are intentionally not supported.
"""

from __future__ import annotations

from .base import VideoGenerator
from .openai_provider import OpenAIProvider


class MuseSparkProvider(OpenAIProvider):
    name = "muse"

    def __init__(self, api_key: str, base_url: str, model: str = "muse-spark-1.1") -> None:
        if not base_url:
            raise ValueError(
                "META_MODEL_API_BASE_URL is not set — copy the base URL from the "
                "Meta Model API docs (https://dev.meta.ai/docs) into .env"
            )
        super().__init__(api_key=api_key, model=model, base_url=base_url)


class MetaMuseVideoProvider(VideoGenerator):
    name = "muse"

    def __init__(self, *_args, **_kwargs) -> None:
        raise NotImplementedError(
            "Meta has not released a developer API for Muse Video yet. "
            "Use VISUAL_PROVIDER=imagen, gpt-image or veo for now; implement generate_clip() "
            "here once the Meta Model API lists a video model."
        )

    def generate_clip(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        raise NotImplementedError

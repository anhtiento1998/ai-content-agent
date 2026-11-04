"""Meta Muse models via the official Meta Model API.

Status as of Oct 2026:
- Muse Spark (text): available through the Meta Model API (public preview,
  US developers only). The API is OpenAI-compatible, so MuseSparkProvider
  reuses the OpenAI SDK pointed at Meta's base URL.
- Muse Video: no official developer API yet. MetaMuseVideoProvider fails
  fast so a pipeline configured with it doesn't spend money generating a
  script it can never render. Third-party wrappers that drive the consumer
  muse.ai subscription are intentionally not supported.
"""

from __future__ import annotations

from .base import ScriptResult, VideoGenerator, VideoResult
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
            "Use VIDEO_PROVIDER=veo for now; implement generate_video() here once "
            "the Meta Model API lists a video model."
        )

    def generate_video(self, script: ScriptResult, *, aspect_ratio: str = "9:16") -> VideoResult:
        raise NotImplementedError

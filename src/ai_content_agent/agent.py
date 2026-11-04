"""Top-level agent: wires config -> providers -> publishers -> pipeline.

This is the single object a caller (CLI, scheduler, future web dashboard)
needs to construct and run.
"""

from __future__ import annotations

from ai_content_agent.config import Config
from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.providers import TEXT_PROVIDERS, VIDEO_PROVIDERS
from ai_content_agent.publishers import FacebookPublisher, InstagramPublisher, TikTokPublisher, YouTubePublisher
from ai_content_agent.publishers.base import Publisher


class ContentAgent:
    def __init__(self, config: Config) -> None:
        self._config = config

    def _build_text_generator(self):
        provider = self._config.text_provider
        if provider == "gpt":
            return TEXT_PROVIDERS["gpt"](api_key=self._config.openai_api_key)
        if provider == "claude":
            return TEXT_PROVIDERS["claude"](api_key=self._config.anthropic_api_key)
        if provider == "gemini":
            return TEXT_PROVIDERS["gemini"](api_key=self._config.google_api_key)
        if provider == "muse":
            return TEXT_PROVIDERS["muse"](
                api_key=self._config.meta_model_api_key, base_url=self._config.meta_model_api_base_url
            )
        raise ValueError(f"Unknown text provider: {provider!r}")

    def _build_video_generator(self):
        provider = self._config.video_provider
        if provider == "veo":
            return VIDEO_PROVIDERS["veo"](api_key=self._config.google_api_key)
        if provider == "muse":
            return VIDEO_PROVIDERS["muse"]()
        raise ValueError(f"Unknown video provider: {provider!r}")

    def _build_publishers(self, platforms: list[str]) -> list[Publisher]:
        publishers: list[Publisher] = []
        for platform in platforms:
            if platform == "youtube":
                publishers.append(
                    YouTubePublisher(
                        token_file=self._config.youtube_token_file,
                        client_secret_file=self._config.youtube_client_secret_file,
                    )
                )
            elif platform == "tiktok":
                publishers.append(TikTokPublisher(access_token=self._config.tiktok_access_token))
            elif platform == "facebook":
                publishers.append(
                    FacebookPublisher(
                        page_id=self._config.facebook_page_id,
                        access_token=self._config.facebook_access_token,
                    )
                )
            elif platform == "instagram":
                publishers.append(
                    InstagramPublisher(
                        ig_user_id=self._config.instagram_user_id,
                        access_token=self._config.instagram_access_token,
                    )
                )
            else:
                raise ValueError(f"Unknown platform: {platform!r}")
        return publishers

    def build_pipeline(self, platforms: list[str]) -> ContentPipeline:
        return ContentPipeline(
            text_generator=self._build_text_generator(),
            video_generator=self._build_video_generator(),
            publishers=self._build_publishers(platforms),
            history=HistoryStore(self._config.history_db_path),
            dedup_window_days=self._config.dedup_window_days,
            make_thumbnails=self._config.make_thumbnails,
        )

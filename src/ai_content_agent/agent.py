"""Top-level agent: wires config -> engines -> studio -> publishers -> pipeline.

This is the single object a caller (CLI, scheduler, web dashboard) needs to
construct and run.
"""

from __future__ import annotations

from ai_content_agent.config import Config
from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.providers import (
    AnthropicProvider,
    CardImageProvider,
    GeminiProvider,
    GeminiVoiceProvider,
    ImagenProvider,
    MetaMuseVideoProvider,
    MuseSparkProvider,
    OpenAIImageProvider,
    OpenAIProvider,
    OpenAIVoiceProvider,
    SilentVoiceProvider,
    VeoProvider,
)
from ai_content_agent.publishers import FacebookPublisher, TikTokPublisher, YouTubePublisher
from ai_content_agent.publishers.base import Publisher
from ai_content_agent.studio import StudioSettings, VideoStudio


def _optional(**kwargs) -> dict:
    """Pass model/voice overrides only when set, so each provider keeps its own default."""

    return {key: value for key, value in kwargs.items() if value}


class ContentAgent:
    def __init__(self, config: Config) -> None:
        self._config = config

    def _build_text_generator(self):
        c = self._config
        extra = _optional(model=c.text_model)
        if c.text_provider == "gpt":
            return OpenAIProvider(api_key=c.openai_api_key, **extra)
        if c.text_provider == "claude":
            return AnthropicProvider(api_key=c.anthropic_api_key, **extra)
        if c.text_provider == "gemini":
            return GeminiProvider(api_key=c.google_api_key, **extra)
        if c.text_provider == "muse":
            return MuseSparkProvider(api_key=c.meta_model_api_key, base_url=c.meta_model_api_base_url, **extra)
        raise ValueError(f"Unknown TEXT_PROVIDER: {c.text_provider!r}")

    def _build_visual_generator(self):
        c = self._config
        extra = _optional(model=c.visual_model)
        if c.visual_provider == "card":
            return CardImageProvider()
        if c.visual_provider == "gpt-image":
            return OpenAIImageProvider(api_key=c.openai_api_key, **extra)
        if c.visual_provider == "imagen":
            return ImagenProvider(api_key=c.google_api_key, **extra)
        if c.visual_provider == "veo":
            return VeoProvider(api_key=c.google_api_key, **extra)
        if c.visual_provider == "muse":
            return MetaMuseVideoProvider()
        raise ValueError(f"Unknown VISUAL_PROVIDER: {c.visual_provider!r}")

    def _build_voice_generator(self):
        c = self._config
        extra = _optional(model=c.voice_model, voice=c.voice_name)
        if c.voice_provider == "gpt":
            return OpenAIVoiceProvider(api_key=c.openai_api_key, **extra)
        if c.voice_provider == "gemini":
            return GeminiVoiceProvider(api_key=c.google_api_key, **extra)
        if c.voice_provider == "silent":
            return SilentVoiceProvider()
        raise ValueError(f"Unknown VOICE_PROVIDER: {c.voice_provider!r}")

    def build_studio(self) -> VideoStudio:
        c = self._config
        return VideoStudio(
            writer=self._build_text_generator(),
            visuals=self._build_visual_generator(),
            voice=self._build_voice_generator(),
            settings=StudioSettings(
                language=c.content_language,
                target_seconds=c.target_seconds,
                output_dir=c.output_dir,
                music_dir=c.music_dir,
                logo_path=c.brand_logo_path,
                font=c.subtitle_font,
            ),
        )

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
                publishers.append(
                    TikTokPublisher(
                        access_token=self._config.tiktok_access_token,
                        privacy_level=self._config.tiktok_privacy_level,
                    )
                )
            elif platform == "facebook":
                publishers.append(
                    FacebookPublisher(
                        page_id=self._config.facebook_page_id,
                        access_token=self._config.facebook_access_token,
                    )
                )
            else:
                raise ValueError(f"Unknown platform: {platform!r}")
        return publishers

    def build_pipeline(self, platforms: list[str]) -> ContentPipeline:
        return ContentPipeline(
            studio=self.build_studio(),
            publishers=self._build_publishers(platforms),
            history=HistoryStore(self._config.history_db_path),
            dedup_window_days=self._config.dedup_window_days,
            make_thumbnails=self._config.make_thumbnails,
        )

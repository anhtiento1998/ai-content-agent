"""Top-level agent: wires config -> engines -> studio -> publishers -> pipeline.

This is the single object a caller (CLI, scheduler, web dashboard) needs to
construct and run. Engine classes come from the registries in
providers/__init__.py; this module only knows which credentials each needs.
"""

from __future__ import annotations

from ai_content_agent.config import Config
from ai_content_agent.export.capcut import CapCutExporter
from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.providers import TEXT_PROVIDERS, VISUAL_PROVIDERS, VOICE_PROVIDERS
from ai_content_agent.publishers import FacebookPublisher, TikTokPublisher, YouTubePublisher
from ai_content_agent.publishers.base import Publisher
from ai_content_agent.studio import StudioSettings, VideoStudio


def _build(kind: str, registry: dict, name: str, credentials: dict, overrides: dict):
    if name not in registry:
        raise ValueError(f"Unknown {kind}: {name!r} — choose one of {', '.join(registry)}")
    # Offline engines take no credentials, so model/voice overrides only apply to API engines.
    extra = {k: v for k, v in overrides.items() if v} if name in credentials else {}
    return registry[name](**credentials.get(name, {}), **extra)


class ContentAgent:
    def __init__(self, config: Config) -> None:
        self._config = config

    def _build_text_generator(self):
        c = self._config
        credentials = {
            "gpt": {"api_key": c.openai_api_key},
            "claude": {"api_key": c.anthropic_api_key},
            "gemini": {"api_key": c.google_api_key},
            "muse": {"api_key": c.meta_model_api_key, "base_url": c.meta_model_api_base_url},
        }
        return _build("TEXT_PROVIDER", TEXT_PROVIDERS, c.text_provider, credentials, {"model": c.text_model})

    def _build_visual_generator(self):
        c = self._config
        credentials = {
            "gpt-image": {"api_key": c.openai_api_key},
            "imagen": {"api_key": c.google_api_key},
            "veo": {"api_key": c.google_api_key},
        }
        return _build("VISUAL_PROVIDER", VISUAL_PROVIDERS, c.visual_provider, credentials, {"model": c.visual_model})

    def _build_voice_generator(self):
        c = self._config
        credentials = {"gpt": {"api_key": c.openai_api_key}, "gemini": {"api_key": c.google_api_key}}
        return _build(
            "VOICE_PROVIDER", VOICE_PROVIDERS, c.voice_provider, credentials,
            {"model": c.voice_model, "voice": c.voice_name},
        )

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
                keep_intermediates=c.keep_intermediates,
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
            capcut_exporter=self.capcut_exporter() if self._config.capcut_export else None,
        )

    def capcut_exporter(self) -> CapCutExporter:
        return CapCutExporter(self._config.capcut_drafts_dir)

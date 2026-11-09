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
from ai_content_agent.publishers import (
    Disclosure,
    FacebookPublisher,
    TikTokPublisher,
    TikTokTokens,
    UploadPostPublisher,
    YouTubePublisher,
)
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

    def build_publishers(self, platforms: list[str]) -> list[Publisher]:
        c = self._config
        disclosure = Disclosure(enabled=c.ai_disclosure, text=c.ai_disclosure_text)
        publishers: list[Publisher] = []
        for platform in platforms:
            if platform == "youtube":
                publishers.append(
                    YouTubePublisher(
                        token_file=c.youtube_token_file,
                        client_secret_file=c.youtube_client_secret_file,
                        privacy=c.youtube_privacy,
                        disclosure=disclosure,
                    )
                )
            elif platform == "tiktok" and c.tiktok_via == "upload-post":
                publishers.append(
                    UploadPostPublisher(
                        api_key=c.upload_post_api_key, user=c.upload_post_user, platform="tiktok",
                        privacy_level=c.tiktok_privacy_level, disclosure=disclosure,
                    )
                )
            elif platform == "tiktok":
                if c.tiktok_via != "api":
                    raise ValueError(f"TIKTOK_VIA must be api or upload-post, got {c.tiktok_via!r}")
                tokens = TikTokTokens(
                    access_token=c.tiktok_access_token,
                    client_key=c.tiktok_client_key,
                    client_secret=c.tiktok_client_secret,
                    refresh_token=c.tiktok_refresh_token,
                    token_file=c.tiktok_token_file,
                )
                publishers.append(
                    TikTokPublisher(tokens, c.tiktok_privacy_level, disclosure=disclosure, mode=c.tiktok_mode)
                )
            elif platform == "facebook":
                publishers.append(
                    FacebookPublisher(page_id=c.facebook_page_id, access_token=c.facebook_access_token,
                                      disclosure=disclosure)
                )
            else:
                raise ValueError(f"Unknown platform: {platform!r}")
        return publishers

    def build_pipeline(self, platforms: list[str], *, publish_only: bool = False) -> ContentPipeline:
        """`publish_only` skips building the AI engines — enough to approve, retry or take down runs."""

        c = self._config
        return ContentPipeline(
            studio=None if publish_only else self.build_studio(),
            publishers=self.build_publishers(platforms),
            history=HistoryStore(c.history_db_path),
            dedup_window_days=c.dedup_window_days,
            make_thumbnails=c.make_thumbnails,
            capcut_exporter=self.capcut_exporter() if c.capcut_export and not publish_only else None,
            require_approval=c.require_approval,
            max_posts_per_day=c.max_posts_per_day,
        )

    def capcut_exporter(self) -> CapCutExporter:
        return CapCutExporter(self._config.capcut_drafts_dir)

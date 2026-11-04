from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

from ai_content_agent.export.capcut import capcut_status


@dataclass
class Config:
    """Every field is read from the environment variable of the same name in upper case
    (e.g. `visual_provider` <- VISUAL_PROVIDER); unset or empty keeps the default below."""

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    meta_model_api_key: str | None = None
    meta_model_api_base_url: str | None = None

    text_provider: str = "claude"
    visual_provider: str = "imagen"
    voice_provider: str = "gemini"
    text_model: str | None = None
    visual_model: str | None = None
    voice_model: str | None = None
    voice_name: str | None = None

    content_language: str = "vi"
    target_seconds: int = 40
    output_dir: str = "output"
    music_dir: str = "assets/music"
    brand_logo_path: str | None = None
    subtitle_font: str = "Arial"
    keep_intermediates: bool = False

    capcut_export: bool = False
    capcut_drafts_dir: str | None = None

    youtube_token_file: str = "youtube_token.json"
    youtube_client_secret_file: str = "client_secret.json"
    tiktok_access_token: str | None = None
    tiktok_privacy_level: str = "SELF_ONLY"
    facebook_page_id: str | None = None
    facebook_access_token: str | None = None

    history_db_path: str = "data/history.db"
    dedup_window_days: int = 30
    make_thumbnails: bool = True

    dashboard_token: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        from dotenv import load_dotenv

        load_dotenv()
        values = {}
        for f in fields(cls):
            raw = os.getenv(f.name.upper())
            if raw is None or raw.strip() == "":
                continue
            raw = raw.strip()
            if f.type == "int":
                if not raw.lstrip("-").isdigit():
                    raise ValueError(f"{f.name.upper()} must be a whole number, got {raw!r}")
                values[f.name] = int(raw)
            elif f.type == "bool":
                values[f.name] = raw.lower() not in ("false", "0", "no", "off")
            else:
                values[f.name] = raw
        return cls(**values)

    def status(self) -> dict:
        """Readiness of each engine/platform for the dashboard — never includes secret values.
        Notes are user-facing (Vietnamese) because the dashboard shows them verbatim."""

        missing = "Chưa cấu hình trong .env"

        def entry(ready: bool, note: str | None = None) -> dict:
            return {"ready": ready, "note": None if ready else (note or missing)}

        openai, google = bool(self.openai_api_key), bool(self.google_api_key)
        return {
            "text_provider": self.text_provider,
            "visual_provider": self.visual_provider,
            "voice_provider": self.voice_provider,
            "text_providers": {
                "gpt": entry(openai),
                "claude": entry(bool(self.anthropic_api_key)),
                "gemini": entry(google),
                "muse": entry(bool(self.meta_model_api_key and self.meta_model_api_base_url)),
            },
            "visual_providers": {
                "card": entry(True),
                "gpt-image": entry(openai),
                "imagen": entry(google),
                "veo": entry(google),
                "muse": entry(False, "Meta chưa mở API cho Muse Video"),
            },
            "voice_providers": {
                "gpt": entry(openai),
                "gemini": entry(google),
                "silent": entry(True),
            },
            "capcut": capcut_status(),
            "platforms": {
                "youtube": entry(
                    Path(self.youtube_token_file).exists(),
                    "Chạy `ai-content-agent youtube-auth` một lần để đăng nhập YouTube"
                    if Path(self.youtube_client_secret_file).exists()
                    else None,
                ),
                "tiktok": entry(bool(self.tiktok_access_token)),
                "facebook": entry(bool(self.facebook_page_id and self.facebook_access_token)),
            },
        }

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

    require_approval: bool = True
    max_posts_per_day: int = 3
    ai_disclosure: bool = True
    ai_disclosure_text: str = "Video có sử dụng AI"
    schedule_timezone: str = "Asia/Ho_Chi_Minh"
    schedule_jitter_minutes: int = 15

    youtube_token_file: str = "youtube_token.json"
    youtube_client_secret_file: str = "client_secret.json"
    youtube_privacy: str = "public"
    tiktok_access_token: str | None = None
    tiktok_client_key: str | None = None
    tiktok_client_secret: str | None = None
    tiktok_refresh_token: str | None = None
    tiktok_token_file: str = "tiktok_token.json"
    tiktok_privacy_level: str = "SELF_ONLY"
    tiktok_mode: str = "direct"
    tiktok_via: str = "api"
    upload_post_api_key: str | None = None
    upload_post_user: str | None = None
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

        def entry(ready: bool, note: str | None = None, warning: str | None = None) -> dict:
            return {"ready": ready, "note": None if ready else (note or missing), "warning": warning if ready else None}

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
                    self._youtube_token_warning(),
                ),
                "tiktok": self._tiktok_status(entry),
                "facebook": entry(bool(self.facebook_page_id and self.facebook_access_token)),
            },
        }

    def _youtube_token_warning(self) -> str | None:
        from ai_content_agent.publishers.youtube_publisher import TESTING_TOKEN_DAYS, token_age_days

        age = token_age_days(self.youtube_token_file)
        # A token that survives past day 8 belongs to a published ("In production") app; stop warning.
        if age is not None and TESTING_TOKEN_DAYS - 2 <= age < TESTING_TOKEN_DAYS + 1:
            return (
                f"Đăng nhập YouTube từ {age:.0f} ngày trước — nếu dự án Google Cloud còn ở chế độ Testing, "
                f"token sẽ hết hạn sau {TESTING_TOKEN_DAYS} ngày. Chuyển sang In production hoặc chạy lại youtube-auth."
            )
        return None

    def _tiktok_status(self, entry) -> dict:
        if self.tiktok_via == "upload-post":
            return entry(bool(self.upload_post_api_key and self.upload_post_user),
                         "TIKTOK_VIA=upload-post cần UPLOAD_POST_API_KEY và UPLOAD_POST_USER")
        ready = bool(
            self.tiktok_access_token
            or (self.tiktok_client_key and self.tiktok_client_secret
                and (self.tiktok_refresh_token or Path(self.tiktok_token_file).exists()))
        )
        warning = None
        if self.tiktok_mode == "direct" and self.tiktok_privacy_level == "SELF_ONLY":
            warning = ("Đang đăng chế độ SELF_ONLY (chỉ mình bạn xem) — app chưa được TikTok duyệt chỉ đăng được "
                       "chế độ này. Dùng TIKTOK_MODE=inbox hoặc TIKTOK_VIA=upload-post để đăng công khai.")
        return entry(ready, None, warning)

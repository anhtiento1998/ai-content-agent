from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    openai_api_key: str | None
    anthropic_api_key: str | None
    google_api_key: str | None
    meta_model_api_key: str | None
    meta_model_api_base_url: str | None

    youtube_token_file: str
    youtube_client_secret_file: str
    tiktok_access_token: str | None
    facebook_page_id: str | None
    facebook_access_token: str | None
    instagram_user_id: str | None
    instagram_access_token: str | None

    text_provider: str
    video_provider: str

    history_db_path: str
    dedup_window_days: int
    make_thumbnails: bool

    dashboard_token: str | None

    @classmethod
    def from_env(cls) -> "Config":
        from dotenv import load_dotenv

        load_dotenv()
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            meta_model_api_key=os.getenv("META_MODEL_API_KEY"),
            meta_model_api_base_url=os.getenv("META_MODEL_API_BASE_URL"),
            youtube_token_file=os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.json"),
            youtube_client_secret_file=os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json"),
            tiktok_access_token=os.getenv("TIKTOK_ACCESS_TOKEN"),
            facebook_page_id=os.getenv("FACEBOOK_PAGE_ID"),
            facebook_access_token=os.getenv("FACEBOOK_ACCESS_TOKEN"),
            instagram_user_id=os.getenv("INSTAGRAM_USER_ID"),
            instagram_access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN"),
            text_provider=os.getenv("TEXT_PROVIDER", "claude"),
            video_provider=os.getenv("VIDEO_PROVIDER", "veo"),
            history_db_path=os.getenv("HISTORY_DB_PATH", "data/history.db"),
            dedup_window_days=int(os.getenv("DEDUP_WINDOW_DAYS", "30")),
            make_thumbnails=os.getenv("MAKE_THUMBNAILS", "true").lower() not in ("false", "0", ""),
            dashboard_token=os.getenv("DASHBOARD_TOKEN") or None,
        )

    def status(self) -> dict:
        """Readiness of each provider/platform for the dashboard — never includes secret values.
        Notes are user-facing (Vietnamese) because the dashboard shows them verbatim."""

        missing = "Chưa cấu hình trong .env"

        def entry(ready: bool, note: str | None = None) -> dict:
            return {"ready": ready, "note": None if ready else (note or missing)}

        return {
            "text_provider": self.text_provider,
            "video_provider": self.video_provider,
            "text_providers": {
                "gpt": entry(bool(self.openai_api_key)),
                "claude": entry(bool(self.anthropic_api_key)),
                "gemini": entry(bool(self.google_api_key)),
                "muse": entry(bool(self.meta_model_api_key and self.meta_model_api_base_url)),
            },
            "video_providers": {
                "veo": entry(bool(self.google_api_key)),
                "muse": entry(False, "Meta chưa mở API cho Muse Video"),
            },
            "platforms": {
                "youtube": entry(
                    Path(self.youtube_client_secret_file).exists() or Path(self.youtube_token_file).exists()
                ),
                "tiktok": entry(bool(self.tiktok_access_token)),
                "facebook": entry(bool(self.facebook_page_id and self.facebook_access_token)),
                "instagram": entry(False, "Cần video ở URL public — chưa hỗ trợ upload tự động"),
            },
        }

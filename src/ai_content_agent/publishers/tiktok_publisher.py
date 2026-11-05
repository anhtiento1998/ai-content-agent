"""Publish to TikTok via the Content Posting API (Direct Post).

Requires a TikTok developer app with the `video.publish` scope — see
README.md "TikTok setup". Until TikTok audits the app, posts can only be
SELF_ONLY (private); set TIKTOK_PRIVACY_LEVEL=PUBLIC_TO_EVERYONE after the
audit passes. Audited apps get roughly 15 posts/day per creator.

Access tokens are short-lived (TikTok's docs variously say 2 h or 24 h), so
TikTokTokens refreshes them with the refresh token, trusting each response's
`expires_in`, and persists the rotated refresh token to TIKTOK_TOKEN_FILE.

Flow: creator_info/query (required before posting) -> init -> PUT chunks ->
poll status/fetch until PUBLISH_COMPLETE / FAILED.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

from .base import Disclosure, Publisher, PublishResult
from ai_content_agent.providers.base import ScriptResult, VideoResult

_API_BASE = "https://open.tiktokapis.com/v2"
_MAX_SINGLE_CHUNK = 64 * 1024 * 1024
_CHUNK_SIZE = 10 * 1024 * 1024
_REFRESH_MARGIN = 300  # refresh this many seconds before expiry
_TOKEN_INVALID = {"access_token_invalid", "token_expired"}


def _chunk_plan(size: int) -> tuple[int, int]:
    """TikTok wants chunks of 5–64 MB; the last chunk absorbs the remainder."""

    if size <= _MAX_SINGLE_CHUNK:
        return size, 1
    return _CHUNK_SIZE, size // _CHUNK_SIZE


class TikTokTokens:
    """Supplies a valid access token: from the token file, by refreshing, or a static fallback."""

    def __init__(
        self,
        *,
        access_token: str | None = None,
        client_key: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        token_file: str | None = None,
    ) -> None:
        self._static = access_token
        self._client_key = client_key
        self._client_secret = client_secret
        self._initial_refresh = refresh_token
        self._file = Path(token_file) if token_file else None

    def _load(self) -> dict:
        if self._file and self._file.is_file():
            return json.loads(self._file.read_text(encoding="utf-8"))
        return {}

    def _save(self, data: dict) -> None:
        if not self._file:
            return
        tmp = self._file.with_suffix(self._file.suffix + ".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, self._file)

    @property
    def can_refresh(self) -> bool:
        return bool(self._client_key and self._client_secret and (self._load().get("refresh_token") or self._initial_refresh))

    def access_token(self) -> str:
        stored = self._load()
        if stored.get("access_token") and stored.get("expires_at", 0) - _REFRESH_MARGIN > time.time():
            return stored["access_token"]
        if self.can_refresh:
            return self.refresh()
        if self._static:
            return self._static
        raise RuntimeError(
            "No TikTok credentials — set TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET and TIKTOK_REFRESH_TOKEN "
            "(recommended) or a short-lived TIKTOK_ACCESS_TOKEN"
        )

    def refresh(self) -> str:
        if not self.can_refresh:
            if self._static:
                return self._static
            raise RuntimeError("TikTok token expired and no refresh credentials are configured")
        refresh_token = self._load().get("refresh_token") or self._initial_refresh
        resp = requests.post(
            f"{_API_BASE}/oauth/token/",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": self._client_key,
                "client_secret": self._client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=30,
        ).json()
        if "access_token" not in resp:
            raise RuntimeError(
                f"TikTok token refresh failed ({resp.get('error')}): {resp.get('error_description', resp)} — "
                "the refresh token may be expired or revoked; re-authorize the account"
            )
        now = time.time()
        self._save({
            "access_token": resp["access_token"],
            "expires_at": now + int(resp.get("expires_in", 3600)),
            # TikTok may rotate the refresh token; always keep the newest one.
            "refresh_token": resp.get("refresh_token", refresh_token),
            "refresh_expires_at": now + int(resp.get("refresh_expires_in", 0)) if resp.get("refresh_expires_in") else None,
            "open_id": resp.get("open_id"),
        })
        return resp["access_token"]


class TikTokPublisher(Publisher):
    name = "tiktok"

    def __init__(
        self,
        tokens: TikTokTokens | str,
        privacy_level: str = "SELF_ONLY",
        *,
        disclosure: Disclosure | None = None,
        poll_interval: float = 15.0,
        poll_timeout: float = 180.0,
    ) -> None:
        self._tokens = tokens if isinstance(tokens, TikTokTokens) else TikTokTokens(access_token=tokens)
        self._privacy_level = privacy_level
        self._disclosure = disclosure or Disclosure()
        self._poll_interval = poll_interval
        self._poll_timeout = poll_timeout

    def _call(self, path: str, body: dict, *, retry_auth: bool = True) -> dict:
        resp = requests.post(
            f"{_API_BASE}{path}",
            headers={
                "Authorization": f"Bearer {self._tokens.access_token()}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json=body,
            timeout=30,
        ).json()
        error = resp.get("error", {}) or {}
        code = error.get("code", "ok")
        if code in _TOKEN_INVALID and retry_auth:
            self._tokens.refresh()
            return self._call(path, body, retry_auth=False)
        if code != "ok":
            raise RuntimeError(f"TikTok {path} failed ({code}): {error.get('message', resp)}")
        return resp.get("data", {}) or {}

    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        creator = self._call("/post/publish/creator_info/query/", {})
        options = creator.get("privacy_level_options") or []
        if options and self._privacy_level not in options:
            raise RuntimeError(
                f"TikTok account does not allow privacy {self._privacy_level!r}; allowed: {', '.join(options)} "
                "(unaudited apps can only post SELF_ONLY)"
            )
        max_seconds = creator.get("max_video_post_duration_sec")
        if max_seconds and video.duration_seconds and video.duration_seconds > max_seconds:
            raise RuntimeError(f"Video is {video.duration_seconds:.0f}s; this TikTok account allows {max_seconds}s")

        size = os.path.getsize(video.file_path)
        chunk_size, chunk_count = _chunk_plan(size)
        caption = self._disclosure.caption(f"{script.title} " + " ".join(f"#{h}" for h in script.hashtags))
        init = self._call(
            "/post/publish/video/init/",
            {
                "post_info": {
                    "title": caption.strip()[:2200],
                    "privacy_level": self._privacy_level,
                    "is_aigc": self._disclosure.enabled,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": size,
                    "chunk_size": chunk_size,
                    "total_chunk_count": chunk_count,
                },
            },
        )
        publish_id, upload_url = init.get("publish_id"), init.get("upload_url")
        if not publish_id or not upload_url:
            raise RuntimeError(f"TikTok init returned no publish_id/upload_url: {init}")

        with open(video.file_path, "rb") as f:
            for index in range(chunk_count):
                start = index * chunk_size
                end = size - 1 if index == chunk_count - 1 else start + chunk_size - 1
                f.seek(start)
                resp = requests.put(
                    upload_url,
                    headers={"Content-Type": "video/mp4", "Content-Range": f"bytes {start}-{end}/{size}"},
                    data=f.read(end - start + 1),
                    timeout=300,
                )
                if resp.status_code not in (200, 201, 206):
                    raise RuntimeError(
                        f"TikTok upload of chunk {index + 1}/{chunk_count} failed: HTTP {resp.status_code} {resp.text[:200]}"
                    )

        status, post_id = self._wait_for_publish(publish_id)
        username = creator.get("creator_username")
        url = f"https://www.tiktok.com/@{username}/video/{post_id}" if post_id and username else None
        return PublishResult(platform=self.name, remote_id=post_id or publish_id, url=url, status=status, raw=init)

    def _wait_for_publish(self, publish_id: str) -> tuple[str, str | None]:
        """Poll until TikTok finishes; a timeout is not a failure — processing just takes longer."""

        deadline = time.monotonic() + self._poll_timeout
        while True:
            data = self._call("/post/publish/status/fetch/", {"publish_id": publish_id})
            status = data.get("status", "")
            if status == "PUBLISH_COMPLETE":
                ids = data.get("publicaly_available_post_id") or []  # sic — TikTok's field name
                return "published", str(ids[0]) if ids else None
            if status == "FAILED":
                raise RuntimeError(f"TikTok rejected the post: {data.get('fail_reason', 'unknown reason')}")
            if time.monotonic() >= deadline:
                return "processing", None
            time.sleep(self._poll_interval)

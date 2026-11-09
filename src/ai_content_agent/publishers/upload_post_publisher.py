"""Publish through Upload-Post (upload-post.com), a paid relay with an audited TikTok app.

TikTok only lets audited apps post publicly, and does not audit apps made for
one creator's own use — so most self-hosted tools post to TikTok through a
relay. Connect the TikTok account in the Upload-Post dashboard under a
profile name (UPLOAD_POST_USER), then set TIKTOK_VIA=upload-post.

The request follows Upload-Post's official Python SDK (upload-post-pip,
`upload_video`): multipart POST /api/upload with `Authorization: Apikey`,
`user`, `title`, `platform[]` and the TikTok fields `privacy_level` and
`is_aigc`. With async_upload the API answers with a request_id at once;
the post is then tracked as "processing". Not yet tested against a live
account — check the first posts in the Upload-Post dashboard.
"""

from __future__ import annotations

import logging

import requests

from .base import Disclosure, Publisher, PublishRejected, PublishResult
from ai_content_agent.providers.base import ScriptResult, VideoResult

logger = logging.getLogger(__name__)

API_BASE = "https://api.upload-post.com/api"


def _find(data, *keys):
    """First value under any of `keys`, searched depth-first through nested dicts/lists."""

    if isinstance(data, dict):
        for key in keys:
            if data.get(key):
                return data[key]
        values = data.values()
    elif isinstance(data, list):
        values = data
    else:
        return None
    for value in values:
        found = _find(value, *keys)
        if found:
            return found
    return None


class UploadPostPublisher(Publisher):
    """Posts to one platform (`platform`, default tiktok) of an Upload-Post profile. The publisher keeps
    that platform's name, so history, daily caps and retries treat it like the direct API publisher."""

    def __init__(
        self,
        api_key: str,
        user: str,
        *,
        platform: str = "tiktok",
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        disclosure: Disclosure | None = None,
        timeout: float = 600,
    ) -> None:
        self.name = platform
        self._api_key = api_key
        self._user = user
        self._privacy_level = privacy_level
        self._disclosure = disclosure or Disclosure()
        self._timeout = timeout

    def _headers(self) -> dict:
        return {"Authorization": f"Apikey {self._api_key}"}

    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        if not self._api_key or not self._user:
            raise PublishRejected("Upload-Post needs UPLOAD_POST_API_KEY and UPLOAD_POST_USER (the profile name)")
        caption = self._disclosure.caption(f"{script.title} " + " ".join(f"#{h}" for h in script.hashtags)).strip()
        data = [
            ("user", self._user),
            ("title", caption[:2200]),
            ("platform[]", self.name),
            ("async_upload", "true"),
        ]
        if self.name == "tiktok":
            data += [("privacy_level", self._privacy_level), ("is_aigc", str(self._disclosure.enabled).lower())]
        with open(video.file_path, "rb") as f:
            resp = requests.post(
                f"{API_BASE}/upload",
                headers=self._headers(),
                data=data,
                files=[("video", ("final.mp4", f, "video/mp4"))],
                timeout=self._timeout,
            )
        try:
            body = resp.json()
        except ValueError:
            body = {"message": resp.text[:300]}
        if resp.status_code >= 400 or body.get("success") is False:
            message = body.get("message") or body.get("detail") or body.get("error") or body
            raise RuntimeError(f"Upload-Post rejected the {self.name} upload (HTTP {resp.status_code}): {message}")

        request_id = _find(body, "request_id", "job_id")
        url = _find(body, "url", "post_url")
        post_id = _find(body, "platform_post_id", "post_id", "publish_id")
        remote_id = str(post_id or request_id or "")
        if not remote_id:
            raise RuntimeError(f"Upload-Post returned no request id: {body}")
        return PublishResult(
            platform=self.name,
            remote_id=remote_id,
            url=url if isinstance(url, str) else None,
            status="published" if url else "processing",
            raw=body,
        )

"""Publish to TikTok via the Content Posting API (Direct Post).

Requires a TikTok developer app with the `video.publish` scope and an access
token for the target account — see README.md "TikTok setup". Until TikTok
audits the app, posts can only be SELF_ONLY (private); set
TIKTOK_PRIVACY_LEVEL=PUBLIC_TO_EVERYONE after the audit passes.

Flow: init (get upload_url) -> PUT the file in chunks -> TikTok processes
and publishes asynchronously; `remote_id` is the publish_id.
"""

from __future__ import annotations

import os

import requests

from .base import Publisher, PublishResult
from ai_content_agent.providers.base import ScriptResult, VideoResult

_API_BASE = "https://open.tiktokapis.com/v2"
_MAX_SINGLE_CHUNK = 64 * 1024 * 1024
_CHUNK_SIZE = 10 * 1024 * 1024


def _chunk_plan(size: int) -> tuple[int, int]:
    """TikTok wants chunks of 5–64 MB; the last chunk absorbs the remainder."""

    if size <= _MAX_SINGLE_CHUNK:
        return size, 1
    return _CHUNK_SIZE, size // _CHUNK_SIZE


class TikTokPublisher(Publisher):
    name = "tiktok"

    def __init__(self, access_token: str, privacy_level: str = "SELF_ONLY") -> None:
        self._access_token = access_token
        self._privacy_level = privacy_level

    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        size = os.path.getsize(video.file_path)
        chunk_size, chunk_count = _chunk_plan(size)
        caption = f"{script.title} " + " ".join(f"#{h}" for h in script.hashtags)

        init_resp = requests.post(
            f"{_API_BASE}/post/publish/video/init/",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "post_info": {"title": caption.strip()[:2200], "privacy_level": self._privacy_level},
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": size,
                    "chunk_size": chunk_size,
                    "total_chunk_count": chunk_count,
                },
            },
            timeout=30,
        ).json()

        error = init_resp.get("error", {})
        if error.get("code", "ok") != "ok" or "publish_id" not in init_resp.get("data", {}):
            raise RuntimeError(f"TikTok init failed ({error.get('code')}): {error.get('message', init_resp)}")

        publish_id = init_resp["data"]["publish_id"]
        upload_url = init_resp["data"]["upload_url"]

        with open(video.file_path, "rb") as f:
            for index in range(chunk_count):
                start = index * chunk_size
                end = size - 1 if index == chunk_count - 1 else start + chunk_size - 1
                f.seek(start)
                resp = requests.put(
                    upload_url,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes {start}-{end}/{size}",
                    },
                    data=f.read(end - start + 1),
                    timeout=300,
                )
                if resp.status_code not in (200, 201, 206):
                    raise RuntimeError(
                        f"TikTok upload of chunk {index + 1}/{chunk_count} failed: HTTP {resp.status_code} {resp.text[:200]}"
                    )

        return PublishResult(platform=self.name, remote_id=publish_id, raw=init_resp)

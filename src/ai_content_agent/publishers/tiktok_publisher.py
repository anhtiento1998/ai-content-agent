"""Publish to TikTok via the Content Posting API (Business).

Requires a TikTok for Business developer app, approved content-posting
scope, and a long-lived access token for the target account — see
README.md "TikTok setup". The direct-post flow is: init -> upload chunk(s)
-> TikTok processes and publishes.
"""

from __future__ import annotations

import os

import requests

from .base import Publisher, PublishResult
from ai_content_agent.providers.base import ScriptResult, VideoResult

_API_BASE = "https://open.tiktokapis.com/v2"


class TikTokPublisher(Publisher):
    name = "tiktok"

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        size = os.path.getsize(video.file_path)
        init_resp = requests.post(
            f"{_API_BASE}/post/publish/video/init/",
            headers=self._headers(),
            json={
                "post_info": {
                    "title": script.title[:150],
                    "privacy_level": "SELF_ONLY",  # flip to PUBLIC_TO_EVERYONE once reviewed
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": size,
                    "chunk_size": size,
                    "total_chunk_count": 1,
                },
            },
            timeout=30,
        ).json()

        publish_id = init_resp["data"]["publish_id"]
        upload_url = init_resp["data"]["upload_url"]

        with open(video.file_path, "rb") as f:
            requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{size - 1}/{size}",
                },
                data=f,
                timeout=120,
            )

        return PublishResult(platform=self.name, remote_id=publish_id, raw=init_resp)

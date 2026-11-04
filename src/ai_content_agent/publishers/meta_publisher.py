"""Publish to a Facebook Page and/or Instagram Business account via the Meta Graph API.

Requires a Meta developer app, a long-lived Page access token, and (for
Instagram) the Page's linked IG Business account id — see README.md
"Meta setup". Instagram Reels publishing is a two-step container flow:
create a media container from a public video URL, then publish it.
"""

from __future__ import annotations

import time

import requests

from .base import Publisher, PublishResult
from ai_content_agent.providers.base import ScriptResult, VideoResult

_GRAPH = "https://graph.facebook.com/v19.0"


class FacebookPublisher(Publisher):
    name = "facebook"

    def __init__(self, page_id: str, access_token: str) -> None:
        self._page_id = page_id
        self._access_token = access_token

    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        with open(video.file_path, "rb") as f:
            resp = requests.post(
                f"{_GRAPH}/{self._page_id}/videos",
                params={"access_token": self._access_token},
                data={"description": script.script, "title": script.title[:100]},
                files={"source": f},
                timeout=120,
            ).json()
        return PublishResult(platform=self.name, remote_id=resp["id"], raw=resp)


class InstagramPublisher(Publisher):
    """Needs `video_public_url` — the rendered video must already be reachable
    at a public URL (e.g. uploaded to S3/GCS) before calling publish()."""

    name = "instagram"

    def __init__(self, ig_user_id: str, access_token: str) -> None:
        self._ig_user_id = ig_user_id
        self._access_token = access_token

    def publish(
        self, video: VideoResult, script: ScriptResult, *, video_public_url: str | None = None
    ) -> PublishResult:
        if not video_public_url:
            raise ValueError(
                "Instagram Reels needs the video at a public URL; automatic upload to "
                "S3/GCS is not implemented yet (see README roadmap)"
            )
        create_resp = requests.post(
            f"{_GRAPH}/{self._ig_user_id}/media",
            params={
                "access_token": self._access_token,
                "media_type": "REELS",
                "video_url": video_public_url,
                "caption": f"{script.title}\n\n{script.script}\n\n"
                + " ".join(f"#{h}" for h in script.hashtags),
            },
            timeout=30,
        ).json()
        container_id = create_resp["id"]

        for _ in range(30):
            status = requests.get(
                f"{_GRAPH}/{container_id}",
                params={"fields": "status_code", "access_token": self._access_token},
                timeout=15,
            ).json()
            if status.get("status_code") == "FINISHED":
                break
            time.sleep(10)

        publish_resp = requests.post(
            f"{_GRAPH}/{self._ig_user_id}/media_publish",
            params={"creation_id": container_id, "access_token": self._access_token},
            timeout=30,
        ).json()
        return PublishResult(platform=self.name, remote_id=publish_resp["id"], raw=publish_resp)

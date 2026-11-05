"""Publish to a Facebook Page via the Meta Graph API — as a Reel when possible.

Requires a Meta app (App Review + Business Verification for production) and a
long-lived Page access token with `pages_manage_posts`,
`pages_read_engagement` and `pages_show_list`; a Business System User token
avoids the 60-day re-login cycle — see README.md "Facebook Page".

Reels: /{page-id}/video_reels in three phases (start → upload to
rupload.facebook.com → finish), 3–90 s, at most 30 API-published reels per
rolling 24 h per Page. Longer videos fall back to a regular Page video.
"""

from __future__ import annotations

import os

import requests

from .base import Disclosure, Publisher, PublishResult
from ai_content_agent.providers.base import ScriptResult, VideoResult

_VERSION = "v23.0"
_GRAPH = f"https://graph.facebook.com/{_VERSION}"
_GRAPH_VIDEO = f"https://graph-video.facebook.com/{_VERSION}"
_RUPLOAD = f"https://rupload.facebook.com/video-upload/{_VERSION}"
_REEL_MAX_SECONDS = 90


def _check(resp: dict, step: str) -> dict:
    if "error" in resp:
        error = resp["error"]
        raise RuntimeError(f"Facebook {step} failed ({error.get('code', '?')}): {error.get('message', resp)}")
    return resp


class FacebookPublisher(Publisher):
    name = "facebook"

    def __init__(self, page_id: str, access_token: str, *, disclosure: Disclosure | None = None) -> None:
        self._page_id = page_id
        self._access_token = access_token
        self._disclosure = disclosure or Disclosure()

    def _description(self, script: ScriptResult) -> str:
        hashtags = " ".join(f"#{h}" for h in script.hashtags)
        # The Graph API has no AI-disclosure field, so the label goes in the caption.
        return self._disclosure.caption(f"{script.title}\n\n{script.script}\n\n{hashtags}".strip())

    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        if video.duration_seconds and video.duration_seconds > _REEL_MAX_SECONDS:
            return self._publish_page_video(video, script)
        return self._publish_reel(video, script)

    def _publish_reel(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        endpoint = f"{_GRAPH}/{self._page_id}/video_reels"
        start = _check(
            requests.post(endpoint, params={"upload_phase": "start", "access_token": self._access_token}, timeout=30).json(),
            "reel start",
        )
        video_id = start.get("video_id")
        if not video_id:
            raise RuntimeError(f"Facebook reel start returned no video_id: {start}")

        size = os.path.getsize(video.file_path)
        with open(video.file_path, "rb") as f:
            upload = requests.post(
                start.get("upload_url") or f"{_RUPLOAD}/{video_id}",
                headers={"Authorization": f"OAuth {self._access_token}", "offset": "0", "file_size": str(size)},
                data=f,
                timeout=600,
            ).json()
        if not _check(upload, "reel upload").get("success"):
            raise RuntimeError(f"Facebook reel upload was not accepted: {upload}")

        finish = _check(
            requests.post(
                endpoint,
                params={
                    "upload_phase": "finish",
                    "video_id": video_id,
                    "video_state": "PUBLISHED",
                    "description": self._description(script),
                    "access_token": self._access_token,
                },
                timeout=60,
            ).json(),
            "reel finish",
        )
        if not finish.get("success", True):
            raise RuntimeError(f"Facebook reel finish was not accepted: {finish}")
        return PublishResult(
            platform=self.name,
            remote_id=video_id,
            url=f"https://www.facebook.com/reel/{video_id}",
            status="processing",  # Meta encodes and publishes the reel asynchronously
            raw=finish,
        )

    def _publish_page_video(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        with open(video.file_path, "rb") as f:
            resp = requests.post(
                f"{_GRAPH_VIDEO}/{self._page_id}/videos",
                params={"access_token": self._access_token},
                data={"description": self._description(script), "title": script.title[:100]},
                files={"source": f},
                timeout=600,
            ).json()
        video_id = _check(resp, "video upload").get("id")
        if not video_id:
            raise RuntimeError(f"Facebook video upload returned no id: {resp}")
        return PublishResult(platform=self.name, remote_id=video_id, url=f"https://www.facebook.com/watch/?v={video_id}", raw=resp)

    def delete(self, remote_id: str) -> None:
        resp = requests.delete(f"{_GRAPH}/{remote_id}", params={"access_token": self._access_token}, timeout=30).json()
        if not _check(resp, "delete").get("success", False):
            raise RuntimeError(f"Facebook did not confirm deleting {remote_id}: {resp}")

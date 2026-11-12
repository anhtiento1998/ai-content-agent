"""Publish to a Facebook Page via the Meta Graph API — as a Reel when possible.

Requires a Meta app (App Review + Business Verification for production) and a
long-lived Page access token with `pages_manage_posts`,
`pages_read_engagement` and `pages_show_list`; a Business System User token
avoids the 60-day re-login cycle — see README.md "Facebook Page".

Reels: /{page-id}/video_reels in three phases (start → upload to
rupload.facebook.com → finish), 3–90 s, at least 540x960, at most 30
API-published reels per rolling 24 h per Page (the pipeline enforces the
cap). Longer videos fall back to a regular Page video; shorter or
low-resolution ones are refused before upload.

FACEBOOK_ACCESS_TOKEN may be a Page token, or a user / Business System User
token with access to the Page: the Page token is looked up from it once.
"""

from __future__ import annotations

import os

import requests

from . import http
from .base import Disclosure, Publisher, PublishRejected, PublishResult
from ai_content_agent.providers.base import ScriptResult, VideoResult

_VERSION = "v23.0"
_GRAPH = f"https://graph.facebook.com/{_VERSION}"
_GRAPH_VIDEO = f"https://graph-video.facebook.com/{_VERSION}"
_RUPLOAD = f"https://rupload.facebook.com/video-upload/{_VERSION}"
_REEL_MAX_SECONDS = 90
_REEL_MIN_SECONDS = 3
_REEL_MIN_SHORT_SIDE = 540


def _check(resp: dict, step: str) -> dict:
    if "error" in resp:
        error = resp["error"]
        raise RuntimeError(f"Facebook {step} failed ({error.get('code', '?')}): {error.get('message', resp)}")
    return resp


class FacebookPublisher(Publisher):
    name = "facebook"

    def __init__(self, page_id: str, access_token: str, *, disclosure: Disclosure | None = None,
                 retries: int = http.DEFAULT_ATTEMPTS) -> None:
        self._retries = retries
        self._page_id = page_id
        self._given_token = access_token
        self._page_token: str | None = None
        self._disclosure = disclosure or Disclosure()

    @property
    def _access_token(self) -> str:
        """The Page access token: derived once from a user/System User token, or the given one."""

        if not self._page_id or not self._given_token:
            raise RuntimeError("Facebook needs FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN in .env")
        if self._page_token is None:
            token = self._given_token
            try:
                resp = requests.get(
                    f"{_GRAPH}/{self._page_id}",
                    params={"fields": "access_token", "access_token": self._given_token},
                    timeout=30,
                ).json()
                token = resp.get("access_token") or self._given_token
            except Exception:  # network error or non-JSON reply
                pass  # use the token as given; the real call reports any auth problem
            self._page_token = token
        return self._page_token

    def _description(self, script: ScriptResult) -> str:
        hashtags = " ".join(f"#{h}" for h in script.hashtags)
        # The Graph API has no AI-disclosure field, so the label goes in the caption.
        return self._disclosure.caption(f"{script.title}\n\n{script.script}\n\n{hashtags}".strip())

    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        if video.duration_seconds and video.duration_seconds > _REEL_MAX_SECONDS:
            return self._publish_page_video(video, script)
        if video.duration_seconds is not None and video.duration_seconds < _REEL_MIN_SECONDS:
            raise PublishRejected(f"Facebook Reels must be at least {_REEL_MIN_SECONDS}s; video is "
                                  f"{video.duration_seconds:.1f}s")
        if video.width and video.height and min(video.width, video.height) < _REEL_MIN_SHORT_SIDE:
            raise PublishRejected(f"Facebook Reels need at least 540x960; video is {video.width}x{video.height}")
        return self._publish_reel(video, script)

    def _publish_reel(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        endpoint = f"{_GRAPH}/{self._page_id}/video_reels"
        token = self._access_token
        # Each phase can be repeated: "start" only reserves an id, the upload restarts at offset 0
        # for the same id, and "finish" publishes that one id.
        start = _check(
            http.send(lambda: requests.post(endpoint, params={"upload_phase": "start", "access_token": token},
                                            timeout=30),
                      "starting the Facebook reel", attempts=self._retries).json(),
            "reel start",
        )
        video_id = start.get("video_id")
        if not video_id:
            raise RuntimeError(f"Facebook reel start returned no video_id: {start}")

        size = os.path.getsize(video.file_path)

        def upload_file():
            with open(video.file_path, "rb") as f:
                return requests.post(
                    start.get("upload_url") or f"{_RUPLOAD}/{video_id}",
                    headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)},
                    data=f,
                    timeout=600,
                )

        upload = http.send(upload_file, "uploading the reel to Facebook", attempts=self._retries).json()
        if not _check(upload, "reel upload").get("success"):
            raise RuntimeError(f"Facebook reel upload was not accepted: {upload}")

        finish = _check(
            http.send(
                lambda: requests.post(
                    endpoint,
                    params={
                        "upload_phase": "finish",
                        "video_id": video_id,
                        "video_state": "PUBLISHED",
                        "description": self._description(script),
                        "access_token": token,
                    },
                    timeout=60,
                ),
                "publishing the Facebook reel", attempts=self._retries,
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
        token = self._access_token

        def upload_file():
            with open(video.file_path, "rb") as f:
                return requests.post(
                    f"{_GRAPH_VIDEO}/{self._page_id}/videos",
                    params={"access_token": token},
                    data={"description": self._description(script), "title": script.title[:100]},
                    files={"source": f},
                    timeout=600,
                )

        # One request uploads and publishes: if its reply is lost the video may be live, so it is
        # only repeated when the connection was never made.
        resp = http.send(upload_file, "uploading the video to Facebook", attempts=self._retries,
                         idempotent=False).json()
        video_id = _check(resp, "video upload").get("id")
        if not video_id:
            raise RuntimeError(f"Facebook video upload returned no id: {resp}")
        return PublishResult(platform=self.name, remote_id=video_id, url=f"https://www.facebook.com/watch/?v={video_id}", raw=resp)

    def delete(self, remote_id: str) -> None:
        token = self._access_token
        resp = http.send(lambda: requests.delete(f"{_GRAPH}/{remote_id}", params={"access_token": token}, timeout=30),
                         "deleting the Facebook post", attempts=self._retries).json()
        if not _check(resp, "delete").get("success", False):
            raise RuntimeError(f"Facebook did not confirm deleting {remote_id}: {resp}")

"""Publish to a Facebook Page via the Meta Graph API.

Requires a Meta developer app and a long-lived Page access token with the
`pages_manage_posts` and `pages_read_engagement` permissions — see README.md
"Facebook setup".
"""

from __future__ import annotations

import requests

from .base import Publisher, PublishResult
from ai_content_agent.providers.base import ScriptResult, VideoResult

# Video file uploads go to the graph-video host, per Meta's Page video publishing docs.
_GRAPH_VIDEO = "https://graph-video.facebook.com/v23.0"


class FacebookPublisher(Publisher):
    name = "facebook"

    def __init__(self, page_id: str, access_token: str) -> None:
        self._page_id = page_id
        self._access_token = access_token

    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        description = script.script + "\n\n" + " ".join(f"#{h}" for h in script.hashtags)
        with open(video.file_path, "rb") as f:
            resp = requests.post(
                f"{_GRAPH_VIDEO}/{self._page_id}/videos",
                params={"access_token": self._access_token},
                data={"description": description.strip(), "title": script.title[:100]},
                files={"source": f},
                timeout=300,
            ).json()

        if "error" in resp or "id" not in resp:
            error = resp.get("error", {})
            raise RuntimeError(f"Facebook Graph API error {error.get('code', '?')}: {error.get('message', resp)}")

        video_id = resp["id"]
        return PublishResult(
            platform=self.name,
            remote_id=video_id,
            url=f"https://www.facebook.com/watch/?v={video_id}",
            raw=resp,
        )

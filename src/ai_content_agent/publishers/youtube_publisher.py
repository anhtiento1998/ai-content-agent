"""Publish to YouTube (Shorts) via the YouTube Data API v3.

Requires a Google Cloud project with the YouTube Data API enabled, OAuth
client credentials (client_secret.json) and a one-time user consent flow
that produces a cached token — see README.md "YouTube setup".
"""

from __future__ import annotations

import logging

from .base import Publisher, PublishResult
from ai_content_agent.providers.base import ScriptResult, VideoResult

logger = logging.getLogger(__name__)


class YouTubePublisher(Publisher):
    name = "youtube"

    def __init__(self, token_file: str, client_secret_file: str) -> None:
        self._token_file = token_file
        self._client_secret_file = client_secret_file

    def _get_service(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        creds = None
        try:
            creds = Credentials.from_authorized_user_file(self._token_file, scopes)
        except FileNotFoundError:
            pass

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self._client_secret_file, scopes)
                creds = flow.run_local_server(port=0)
            with open(self._token_file, "w") as f:
                f.write(creds.to_json())

        return build("youtube", "v3", credentials=creds)

    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        from googleapiclient.http import MediaFileUpload

        service = self._get_service()
        body = {
            "snippet": {
                "title": script.title[:100],
                "description": script.script + "\n\n" + " ".join(f"#{h}" for h in script.hashtags),
                "tags": script.hashtags,
                "categoryId": "22",
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }
        media = MediaFileUpload(video.file_path, chunksize=-1, resumable=True)
        request = service.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        video_id = response["id"]

        if video.thumbnail_path:
            try:
                service.thumbnails().set(
                    videoId=video_id, media_body=MediaFileUpload(video.thumbnail_path)
                ).execute()
            except Exception:
                # Custom thumbnails require a phone-verified channel; not fatal.
                logger.warning("Setting custom thumbnail failed for video %s", video_id, exc_info=True)

        return PublishResult(
            platform=self.name,
            remote_id=video_id,
            url=f"https://youtube.com/shorts/{video_id}",
            raw=response,
        )

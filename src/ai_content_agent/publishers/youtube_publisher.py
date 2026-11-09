"""Publish to YouTube (Shorts) via the YouTube Data API v3.

Requires a Google Cloud project with the YouTube Data API enabled and OAuth
client credentials (client_secret.json). Consent is a one-time interactive
step (`ai-content-agent youtube-auth`, needs a browser); publishing itself
never opens a browser, so it cannot hang in a background job or on a server.

Keep the OAuth consent screen "In production": in "Testing" status Google
expires refresh tokens after 7 days, which silently breaks schedules — the
token file records when consent was given so the dashboard can warn, and a
refused refresh raises an error that says what to do.
Since 1 Jun 2026 uploads use their own quota bucket (default 100/day/project);
the pipeline caps YouTube at 100 posts per rolling 24 h.

If an upload's outcome was never recorded (the process died mid-upload, or the
response was lost), `find_existing` looks for the video in the channel's
uploads before the pipeline uploads it again (2 quota units, not 1,600).
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone

from .base import Disclosure, Publisher, PublishResult
from ai_content_agent.providers.base import ScriptResult, VideoResult

logger = logging.getLogger(__name__)

# youtube.upload to publish; youtube.force-ssl to read back status and delete (takedown).
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
_PRIVACY = {"public", "unlisted", "private"}
_TITLE_FORBIDDEN = str.maketrans("", "", "<>")  # YouTube rejects titles containing < or >
AUTHORIZED_AT = "authorized_at"  # extra key we keep in the token file; Google's loader ignores it
TESTING_TOKEN_DAYS = 7


def _title(script: ScriptResult) -> str:
    return script.title.translate(_TITLE_FORBIDDEN)[:100]


def _write_token(token_file: str, creds_json: str, authorized_at: float | None) -> None:
    data = json.loads(creds_json)
    data[AUTHORIZED_AT] = authorized_at or time.time()
    with open(token_file, "w", encoding="utf-8") as f:
        json.dump(data, f)


def token_age_days(token_file: str) -> float | None:
    """Days since `youtube-auth` consent, or None when unknown (token made by an older version)."""

    try:
        with open(token_file, encoding="utf-8") as f:
            authorized_at = json.load(f).get(AUTHORIZED_AT)
    except (OSError, ValueError):
        return None
    return (time.time() - authorized_at) / 86400 if authorized_at else None


def authorize(token_file: str, client_secret_file: str) -> None:
    """Interactive consent: opens a browser and caches the refreshable token in `token_file`."""

    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES).run_local_server(port=0)
    _write_token(token_file, creds.to_json(), time.time())


class YouTubePublisher(Publisher):
    name = "youtube"

    def __init__(
        self,
        token_file: str,
        client_secret_file: str,
        *,
        privacy: str = "public",
        disclosure: Disclosure | None = None,
    ) -> None:
        if privacy not in _PRIVACY:
            raise ValueError(f"YOUTUBE_PRIVACY must be one of {sorted(_PRIVACY)}, got {privacy!r}")
        self._token_file = token_file
        self._client_secret_file = client_secret_file
        self._privacy = privacy
        self._disclosure = disclosure or Disclosure()

    def _get_service(self):
        from google.auth.exceptions import RefreshError
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        try:
            creds = Credentials.from_authorized_user_file(self._token_file, SCOPES)
        except FileNotFoundError:
            creds = None

        if not creds or not creds.valid:
            if not (creds and creds.expired and creds.refresh_token):
                raise RuntimeError(
                    f"No valid YouTube token in {self._token_file} — run `ai-content-agent youtube-auth` "
                    "once on a machine with a browser, then copy the token file here if needed"
                )
            try:
                creds.refresh(Request())
            except RefreshError as exc:
                age = token_age_days(self._token_file)
                hint = (
                    f" The token is {age:.0f} days old: while the Google Cloud OAuth consent screen is in "
                    f"'Testing', Google revokes tokens after {TESTING_TOKEN_DAYS} days — publish the app "
                    "('In production') and run `ai-content-agent youtube-auth` again."
                    if age is not None and age >= TESTING_TOKEN_DAYS - 0.5
                    else " Run `ai-content-agent youtube-auth` again (access was revoked or the password changed)."
                )
                raise RuntimeError(f"YouTube refused to refresh the login token ({exc}).{hint}") from exc
            # Keep the original consent time so the 7-day Testing expiry can still be detected.
            authorized_at = None
            try:
                with open(self._token_file, encoding="utf-8") as f:
                    authorized_at = json.load(f).get(AUTHORIZED_AT)
            except (OSError, ValueError):
                pass
            _write_token(self._token_file, creds.to_json(), authorized_at)

        return build("youtube", "v3", credentials=creds)

    def publish(self, video: VideoResult, script: ScriptResult) -> PublishResult:
        from googleapiclient.http import MediaFileUpload

        service = self._get_service()
        hashtags = " ".join(f"#{h}" for h in script.hashtags)
        body = {
            "snippet": {
                "title": _title(script),
                "description": self._disclosure.caption(f"{script.script}\n\n{hashtags}".strip())[:5000],
                "tags": script.hashtags,
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": self._privacy,
                "selfDeclaredMadeForKids": False,
                "containsSyntheticMedia": self._disclosure.enabled,
            },
        }
        media = MediaFileUpload(video.file_path, chunksize=-1, resumable=True)
        response = service.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        video_id = response["id"]

        actual_privacy = response.get("status", {}).get("privacyStatus")
        if actual_privacy and actual_privacy != self._privacy:
            # Channel or account settings can override the requested visibility.
            logger.warning("YouTube video %s is %s (requested %s)", video_id, actual_privacy, self._privacy)

        if video.thumbnail_path:
            try:
                service.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(video.thumbnail_path)).execute()
            except Exception:
                # Custom thumbnails require a phone-verified channel; not fatal.
                logger.warning("Setting custom thumbnail failed for video %s", video_id, exc_info=True)

        return PublishResult(
            platform=self.name,
            remote_id=video_id,
            url=f"https://youtube.com/shorts/{video_id}",
            status=actual_privacy or self._privacy,
            raw=response,
        )

    def find_existing(self, script: ScriptResult, since: datetime) -> PublishResult | None:
        """Newest upload with this title made since `since` (channel uploads playlist: 2 quota units)."""

        service = self._get_service()
        channels = service.channels().list(part="contentDetails", mine=True).execute().get("items") or []
        if not channels:
            return None
        playlist = channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        items = service.playlistItems().list(part="snippet", playlistId=playlist, maxResults=25).execute()
        cutoff = since - timedelta(minutes=10)  # clock skew between this machine and YouTube
        title = _title(script)
        for item in items.get("items") or []:
            snippet = item.get("snippet", {})
            published = snippet.get("publishedAt", "")
            try:
                when = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                continue
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if snippet.get("title") == title and when >= cutoff:
                video_id = snippet["resourceId"]["videoId"]
                logger.info("Found earlier YouTube upload %s of %r — not uploading again", video_id, title)
                return PublishResult(platform=self.name, remote_id=video_id,
                                     url=f"https://youtube.com/shorts/{video_id}", status="recovered")
        return None

    def delete(self, remote_id: str) -> None:
        self._get_service().videos().delete(id=remote_id).execute()

"""YouTube/TikTok/Facebook publisher tests with the HTTP/SDK layer faked — no network."""

import json
import time

import pytest
from fakes import FakeText  # noqa: F401  (puts src/ on sys.path)

from ai_content_agent.providers.base import ScriptResult, VideoResult
from ai_content_agent.publishers import facebook_publisher, tiktok_publisher
from ai_content_agent.publishers.base import Disclosure
from ai_content_agent.publishers.facebook_publisher import FacebookPublisher
from ai_content_agent.publishers.tiktok_publisher import TikTokPublisher, TikTokTokens, _chunk_plan

SCRIPT = ScriptResult(title="Mẹo <hay>", script="Nội dung", hashtags=["meo", "hay"])
MB = 1024 * 1024


class FakeResponse:
    def __init__(self, payload=None, status_code=200, text=""):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload


class Router:
    """Answers requests by URL substring; a list of responses is consumed in order (last one repeats)."""

    def __init__(self, routes):
        self.routes = {key: (value if isinstance(value, list) else [value]) for key, value in routes.items()}
        self.calls = []

    def _answer(self, method, url, kwargs):
        self.calls.append((method, url, kwargs))
        for key, responses in self.routes.items():
            if key in url:
                response = responses.pop(0) if len(responses) > 1 else responses[0]
                return response if isinstance(response, FakeResponse) else FakeResponse(response)
        raise AssertionError(f"unexpected request {method} {url}")

    def post(self, url, **kwargs):
        return self._answer("POST", url, kwargs)

    def put(self, url, **kwargs):
        return self._answer("PUT", url, kwargs)

    def get(self, url, **kwargs):
        return self._answer("GET", url, kwargs)

    def delete(self, url, **kwargs):
        return self._answer("DELETE", url, kwargs)

    def bodies(self, fragment):
        return [kwargs.get("json") or kwargs.get("params") or kwargs.get("data") for _, url, kwargs in self.calls
                if fragment in url]


@pytest.fixture
def video(tmp_path):
    path = tmp_path / "v.mp4"
    path.write_bytes(b"\0" * 1000)
    return VideoResult(file_path=str(path), duration_seconds=40.0)


# ---------- TikTok ----------

OK = {"code": "ok"}
CREATOR = {"data": {"privacy_level_options": ["SELF_ONLY", "PUBLIC_TO_EVERYONE"], "creator_username": "kenhmeo",
                    "max_video_post_duration_sec": 600}, "error": OK}
INIT = {"data": {"publish_id": "p_123", "upload_url": "https://upload.example/x"}, "error": OK}
DONE = {"data": {"status": "PUBLISH_COMPLETE", "publicaly_available_post_id": [7300000001]}, "error": OK}


def _tiktok(**routes):
    base = {"creator_info": CREATOR, "video/init": INIT, "upload.example": FakeResponse(status_code=201),
            "status/fetch": DONE}
    return Router({**base, **routes})


def _publisher(**kwargs):
    return TikTokPublisher("token", kwargs.pop("privacy", "PUBLIC_TO_EVERYONE"), poll_interval=0, **kwargs)


def test_tiktok_posts_with_ai_flag_and_returns_public_url(monkeypatch, video):
    fake = _tiktok()
    monkeypatch.setattr(tiktok_publisher, "requests", fake)

    result = _publisher().publish(video, SCRIPT)

    assert (result.remote_id, result.status) == ("7300000001", "published")
    assert result.url == "https://www.tiktok.com/@kenhmeo/video/7300000001"
    [init] = fake.bodies("video/init")
    assert init["post_info"]["is_aigc"] is True
    assert init["post_info"]["privacy_level"] == "PUBLIC_TO_EVERYONE"
    assert init["post_info"]["title"].endswith("Video có sử dụng AI")
    assert [url for _, url, _ in fake.calls][0].endswith("/creator_info/query/")  # queried before posting
    [(_, _, put)] = [c for c in fake.calls if c[0] == "PUT"]
    assert put["headers"]["Content-Range"] == "bytes 0-999/1000"


def test_tiktok_disclosure_can_be_turned_off(monkeypatch, video):
    fake = _tiktok()
    monkeypatch.setattr(tiktok_publisher, "requests", fake)

    _publisher(disclosure=Disclosure(enabled=False)).publish(video, SCRIPT)

    [init] = fake.bodies("video/init")
    assert init["post_info"]["is_aigc"] is False and "AI" not in init["post_info"]["title"]


def test_tiktok_refuses_privacy_the_account_does_not_allow(monkeypatch, video):
    creator = {"data": {"privacy_level_options": ["SELF_ONLY"]}, "error": OK}
    fake = _tiktok(creator_info=creator)
    monkeypatch.setattr(tiktok_publisher, "requests", fake)

    with pytest.raises(RuntimeError, match="unaudited apps can only post SELF_ONLY"):
        _publisher().publish(video, SCRIPT)
    assert not fake.bodies("video/init")


def test_tiktok_reports_rejection_and_processing(monkeypatch, video):
    failed = {"data": {"status": "FAILED", "fail_reason": "video_pull_failed"}, "error": OK}
    monkeypatch.setattr(tiktok_publisher, "requests", _tiktok(**{"status/fetch": failed}))
    with pytest.raises(RuntimeError, match="video_pull_failed"):
        _publisher().publish(video, SCRIPT)

    slow = {"data": {"status": "PROCESSING_UPLOAD"}, "error": OK}
    monkeypatch.setattr(tiktok_publisher, "requests", _tiktok(**{"status/fetch": slow}))
    result = _publisher(poll_timeout=0).publish(video, SCRIPT)
    assert (result.status, result.remote_id) == ("processing", "p_123")


def test_tiktok_failed_upload_is_not_reported_as_success(monkeypatch, video):
    monkeypatch.setattr(tiktok_publisher, "requests", _tiktok(**{"upload.example": FakeResponse(status_code=500)}))
    with pytest.raises(RuntimeError, match="HTTP 500"):
        _publisher().publish(video, SCRIPT)


def test_tiktok_tokens_refresh_and_persist_rotated_refresh_token(monkeypatch, tmp_path):
    token_file = tmp_path / "tiktok_token.json"
    fake = Router({"oauth/token": {"access_token": "new-access", "expires_in": 7200, "refresh_token": "rotated",
                                   "refresh_expires_in": 15552000, "open_id": "u1"}})
    monkeypatch.setattr(tiktok_publisher, "requests", fake)
    tokens = TikTokTokens(client_key="ck", client_secret="cs", refresh_token="initial", token_file=str(token_file))

    assert tokens.access_token() == "new-access"
    assert fake.bodies("oauth/token")[0]["refresh_token"] == "initial"
    stored = json.loads(token_file.read_text())
    assert stored["refresh_token"] == "rotated" and stored["expires_at"] > time.time() + 7000

    assert tokens.access_token() == "new-access"  # cached, no second refresh
    assert len(fake.calls) == 1
    stored["expires_at"] = time.time()  # expired -> next refresh must use the rotated token
    token_file.write_text(json.dumps(stored))
    tokens.access_token()
    assert fake.bodies("oauth/token")[1]["refresh_token"] == "rotated"


def test_tiktok_retries_once_after_invalid_token(monkeypatch, tmp_path, video):
    expired = {"data": {}, "error": {"code": "access_token_invalid", "message": "expired"}}
    fake = _tiktok(creator_info=[expired, CREATOR],
                   **{"oauth/token": {"access_token": "fresh", "expires_in": 7200, "refresh_token": "r2"}})
    monkeypatch.setattr(tiktok_publisher, "requests", fake)
    tokens = TikTokTokens(client_key="ck", client_secret="cs", refresh_token="r1", token_file=str(tmp_path / "t.json"))

    result = TikTokPublisher(tokens, "PUBLIC_TO_EVERYONE", poll_interval=0).publish(video, SCRIPT)

    assert result.status == "published"
    assert len(fake.bodies("oauth/token")) == 2  # initial fetch + forced refresh after the 401-style error


def test_tiktok_refresh_failure_explains_reauthorization(monkeypatch, tmp_path):
    monkeypatch.setattr(tiktok_publisher, "requests",
                        Router({"oauth/token": {"error": "invalid_grant", "error_description": "refresh token expired"}}))
    tokens = TikTokTokens(client_key="ck", client_secret="cs", refresh_token="r", token_file=str(tmp_path / "t.json"))
    with pytest.raises(RuntimeError, match="re-authorize"):
        tokens.access_token()


@pytest.mark.parametrize(
    "size, expected",
    [(1000, (1000, 1)), (64 * MB, (64 * MB, 1)), (64 * MB + 1, (10 * MB, 6)), (105 * MB, (10 * MB, 10))],
)
def test_tiktok_chunk_plan(size, expected):
    chunk_size, count = _chunk_plan(size)
    assert (chunk_size, count) == expected
    assert size - chunk_size * (count - 1) <= 128 * MB


# ---------- Facebook ----------

REEL_START = {"video_id": "987", "upload_url": "https://rupload.facebook.com/video-upload/v23.0/987"}


def test_facebook_publishes_reels_in_three_phases_with_disclosure(monkeypatch, video):
    fake = Router({"video_reels": [REEL_START, {"success": True}], "rupload.facebook.com": {"success": True}})
    monkeypatch.setattr(facebook_publisher, "requests", fake)

    result = FacebookPublisher("page", "token").publish(video, SCRIPT)

    assert (result.remote_id, result.url) == ("987", "https://www.facebook.com/reel/987")
    start, finish = fake.bodies("video_reels")
    assert start["upload_phase"] == "start"
    assert finish["upload_phase"] == "finish" and finish["video_state"] == "PUBLISHED"
    assert finish["description"].endswith("Video có sử dụng AI")
    upload_headers = [kw for _, url, kw in fake.calls if "rupload" in url][0]["headers"]
    assert upload_headers["Authorization"] == "OAuth token" and upload_headers["file_size"] == "1000"


def test_facebook_long_video_falls_back_to_page_video(monkeypatch, video):
    fake = Router({"graph-video.facebook.com": {"id": "555"}})
    monkeypatch.setattr(facebook_publisher, "requests", fake)
    video.duration_seconds = 120

    result = FacebookPublisher("page", "token").publish(video, SCRIPT)

    assert result.url == "https://www.facebook.com/watch/?v=555"
    assert any("/page/videos" in url for method, url, _ in fake.calls if method == "POST")


def test_facebook_graph_error_raises_with_api_message(monkeypatch, video):
    fake = Router({"video_reels": {"error": {"code": 190, "message": "Error validating access token"}}})
    monkeypatch.setattr(facebook_publisher, "requests", fake)
    with pytest.raises(RuntimeError, match="190.*Error validating access token"):
        FacebookPublisher("page", "token").publish(video, SCRIPT)


def test_facebook_delete(monkeypatch):
    fake = Router({"graph.facebook.com": {"success": True}})
    monkeypatch.setattr(facebook_publisher, "requests", fake)
    FacebookPublisher("page", "token").delete("987")
    deletes = [url for method, url, _ in fake.calls if method == "DELETE"]
    assert len(deletes) == 1 and deletes[0].endswith("/987")


# ---------- YouTube ----------


class FakeYouTube:
    """Mimics the googleapiclient resource chain: service.videos().insert(...).execute()."""

    def __init__(self, response):
        self.response, self.inserted, self.deleted = response, None, None

    def videos(self):
        return self

    def thumbnails(self):
        return self

    def insert(self, part, body, media_body):
        self.inserted = body
        return self

    def set(self, videoId, media_body):
        return self

    def delete(self, id):
        self.deleted = id
        return self

    def execute(self):
        return self.response


def _youtube(monkeypatch, response, **kwargs):
    from ai_content_agent.publishers.youtube_publisher import YouTubePublisher

    service = FakeYouTube(response)
    publisher = YouTubePublisher("tok.json", "secret.json", **kwargs)
    monkeypatch.setattr(publisher, "_get_service", lambda: service)
    monkeypatch.setattr("googleapiclient.http.MediaFileUpload", lambda *a, **k: object())
    return publisher, service


def test_youtube_sets_privacy_and_synthetic_media_flag(monkeypatch, video):
    publisher, service = _youtube(monkeypatch, {"id": "abc", "status": {"privacyStatus": "private"}},
                                  privacy="private")

    result = publisher.publish(video, SCRIPT)

    status = service.inserted["status"]
    assert status["privacyStatus"] == "private" and status["containsSyntheticMedia"] is True
    assert service.inserted["snippet"]["title"] == "Mẹo hay"  # < and > are rejected by YouTube
    assert service.inserted["snippet"]["description"].endswith("Video có sử dụng AI")
    assert (result.remote_id, result.status) == ("abc", "private")


def test_youtube_reports_actual_privacy_when_account_overrides(monkeypatch, video):
    publisher, _ = _youtube(monkeypatch, {"id": "abc", "status": {"privacyStatus": "private"}})
    assert publisher.publish(video, SCRIPT).status == "private"


def test_youtube_rejects_unknown_privacy():
    from ai_content_agent.publishers.youtube_publisher import YouTubePublisher

    with pytest.raises(ValueError, match="YOUTUBE_PRIVACY"):
        YouTubePublisher("t", "s", privacy="friends")


def test_youtube_delete(monkeypatch):
    publisher, service = _youtube(monkeypatch, {})
    publisher.delete("abc")
    assert service.deleted == "abc"


def test_youtube_without_token_fails_fast_instead_of_opening_a_browser(tmp_path, video):
    from ai_content_agent.publishers.youtube_publisher import YouTubePublisher

    publisher = YouTubePublisher(str(tmp_path / "missing_token.json"), str(tmp_path / "client_secret.json"))
    with pytest.raises(RuntimeError, match="youtube-auth"):
        publisher.publish(video, SCRIPT)

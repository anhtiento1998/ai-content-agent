"""TikTok/Facebook publisher tests with the HTTP layer faked — no network."""

import pytest
from fakes import FakeText  # noqa: F401  (puts src/ on sys.path)

from ai_content_agent.providers.base import ScriptResult, VideoResult
from ai_content_agent.publishers import facebook_publisher, tiktok_publisher
from ai_content_agent.publishers.facebook_publisher import FacebookPublisher
from ai_content_agent.publishers.tiktok_publisher import TikTokPublisher, _chunk_plan

SCRIPT = ScriptResult(title="Mẹo hay", script="Nội dung", hashtags=["meo", "hay"])
MB = 1024 * 1024


class FakeResponse:
    def __init__(self, payload=None, status_code=200, text=""):
        self._payload = payload or {}
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload


class FakeRequests:
    def __init__(self, post_payload, put_status=200):
        self.post_payload = post_payload
        self.put_status = put_status
        self.posts = []
        self.puts = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse(self.post_payload)

    def put(self, url, **kwargs):
        self.puts.append((url, kwargs))
        return FakeResponse(status_code=self.put_status, text="upload error")


@pytest.fixture
def video(tmp_path):
    path = tmp_path / "v.mp4"
    path.write_bytes(b"\0" * 1000)
    return VideoResult(file_path=str(path))


TIKTOK_OK = {"data": {"publish_id": "p_123", "upload_url": "https://upload.example/x"}, "error": {"code": "ok"}}


def test_tiktok_success_uploads_and_returns_publish_id(monkeypatch, video):
    fake = FakeRequests(TIKTOK_OK)
    monkeypatch.setattr(tiktok_publisher, "requests", fake)

    result = TikTokPublisher("token", privacy_level="PUBLIC_TO_EVERYONE").publish(video, SCRIPT)

    assert result.remote_id == "p_123"
    post_info = fake.posts[0][1]["json"]["post_info"]
    assert post_info == {"title": "Mẹo hay #meo #hay", "privacy_level": "PUBLIC_TO_EVERYONE"}
    [(_, put)] = fake.puts
    assert put["headers"]["Content-Range"] == "bytes 0-999/1000"
    assert len(put["data"]) == 1000


def test_tiktok_init_error_raises_with_api_message(monkeypatch, video):
    fake = FakeRequests({"data": {}, "error": {"code": "access_token_invalid", "message": "token expired"}})
    monkeypatch.setattr(tiktok_publisher, "requests", fake)

    with pytest.raises(RuntimeError, match="token expired"):
        TikTokPublisher("token").publish(video, SCRIPT)
    assert fake.puts == []


def test_tiktok_failed_upload_is_not_reported_as_success(monkeypatch, video):
    monkeypatch.setattr(tiktok_publisher, "requests", FakeRequests(TIKTOK_OK, put_status=500))

    with pytest.raises(RuntimeError, match="HTTP 500"):
        TikTokPublisher("token").publish(video, SCRIPT)


@pytest.mark.parametrize(
    "size, expected",
    [
        (1000, (1000, 1)),
        (64 * MB, (64 * MB, 1)),
        (64 * MB + 1, (10 * MB, 6)),
        (105 * MB, (10 * MB, 10)),
    ],
)
def test_tiktok_chunk_plan(size, expected):
    chunk_size, count = _chunk_plan(size)
    assert (chunk_size, count) == expected
    last_chunk = size - chunk_size * (count - 1)
    assert last_chunk <= 128 * MB


def test_facebook_success_returns_watch_url(monkeypatch, video):
    monkeypatch.setattr(facebook_publisher, "requests", FakeRequests({"id": "987"}))

    result = FacebookPublisher("page", "token").publish(video, SCRIPT)

    assert (result.remote_id, result.url) == ("987", "https://www.facebook.com/watch/?v=987")


def test_facebook_graph_error_raises_with_api_message(monkeypatch, video):
    payload = {"error": {"code": 190, "message": "Error validating access token"}}
    monkeypatch.setattr(facebook_publisher, "requests", FakeRequests(payload))

    with pytest.raises(RuntimeError, match="190.*Error validating access token"):
        FacebookPublisher("page", "token").publish(video, SCRIPT)


def test_facebook_uploads_to_graph_video_host(monkeypatch, video):
    fake = FakeRequests({"id": "1"})
    monkeypatch.setattr(facebook_publisher, "requests", fake)

    FacebookPublisher("page", "token").publish(video, SCRIPT)

    assert fake.posts[0][0].startswith("https://graph-video.facebook.com/")


def test_youtube_without_token_fails_fast_instead_of_opening_a_browser(tmp_path, video):
    from ai_content_agent.publishers.youtube_publisher import YouTubePublisher

    publisher = YouTubePublisher(str(tmp_path / "missing_token.json"), str(tmp_path / "client_secret.json"))

    with pytest.raises(RuntimeError, match="youtube-auth"):
        publisher.publish(video, SCRIPT)

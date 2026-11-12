"""Leftover P0 items: idempotent uploads, platform limits, audit log, schedule catch-up,
TikTok inbox / Upload-Post, Facebook checks and YouTube token warnings."""

import json
import time
from datetime import datetime, timedelta, timezone

import pytest
from fakes import FakePublisher, FakeStudio
from fastapi.testclient import TestClient
from test_publishers import CREATOR, DONE, INIT, OK, SCRIPT, FakeResponse, Router

from ai_content_agent.config import Config
from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.providers.base import VideoResult
from ai_content_agent.publishers import facebook_publisher, tiktok_publisher, upload_post_publisher
from ai_content_agent.publishers.base import PublishRejected, PublishResult
from ai_content_agent.web.app import create_app
from ai_content_agent.web.jobs import JobManager

TOKEN = "t"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def video(tmp_path):
    path = tmp_path / "v.mp4"
    path.write_bytes(b"\0" * 1000)
    return VideoResult(file_path=str(path), duration_seconds=40.0)


class FlakyPublisher(FakePublisher):
    """First publish raises after "uploading" (like a lost response); find_existing finds that copy."""

    def __init__(self, name, error=RuntimeError("connection reset")):
        super().__init__(name=name)
        self.error, self.lookups = error, []

    def publish(self, video, script):
        if self.error:
            error, self.error = self.error, None
            raise error
        return super().publish(video, script)

    def find_existing(self, script, since):
        self.lookups.append(since)
        return PublishResult(platform=self.name, remote_id="already-there", url="https://example.com/x")


def _pipeline(tmp_path, publishers, history=None, **kwargs):
    history = history or HistoryStore(str(tmp_path / "h.db"))
    studio = FakeStudio(str(tmp_path / "run" / "final.mp4"))
    return ContentPipeline(studio, publishers, history=history, make_thumbnails=False, **kwargs), history


# ---------- idempotent uploads ----------


def test_retry_after_unrecorded_upload_adopts_the_existing_post(tmp_path):
    flaky = FlakyPublisher("youtube")
    pipeline, history = _pipeline(tmp_path, [flaky])

    outcome = pipeline.run("Chủ đề")
    assert outcome.published == [] and history.get_run(outcome.run_id).status == "failed"

    retry = pipeline.publish_run(outcome.run_id)

    assert [r.remote_id for r in retry.published] == ["already-there"]
    assert flaky.published == [] and len(flaky.lookups) == 1  # looked up, not uploaded again
    assert history.get_run(outcome.run_id).status == "published"


def test_refusal_before_upload_needs_no_lookup(tmp_path):
    flaky = FlakyPublisher("tiktok", error=PublishRejected("privacy not allowed"))
    pipeline, history = _pipeline(tmp_path, [flaky])
    run_id = pipeline.run("Chủ đề").run_id

    pipeline.publish_run(run_id)

    assert flaky.lookups == [] and len(flaky.published) == 1


def test_successful_attempts_are_not_looked_up_again(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    attempt = history.begin_attempt(1, "youtube")
    assert history.uncertain_attempt_since(1, "youtube") is not None  # unfinished = maybe uploaded
    history.finish_attempt(attempt, "ok")
    assert history.uncertain_attempt_since(1, "youtube") is None


# ---------- platform limits ----------


def test_platform_hard_limit_applies_even_without_user_cap(tmp_path, monkeypatch):
    from ai_content_agent.pipeline import content_pipeline

    monkeypatch.setitem(content_pipeline.PLATFORM_DAILY_LIMITS, "tiktok", 1)
    tiktok = FakePublisher("tiktok")
    pipeline, history = _pipeline(tmp_path, [tiktok], max_posts_per_day=0)

    pipeline.run("Một")
    pipeline.run("Hai")

    assert len(tiktok.published) == 1
    assert "at most 1 API posts" in history.recent_errors()[0].message


# ---------- reviewer audit log ----------


def test_api_records_who_approved_rejected_and_took_down(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    publishers = {"youtube": FakePublisher("youtube")}
    studio = FakeStudio(str(tmp_path / "run" / "final.mp4"))

    def factory(platforms, publish_only=False):
        return ContentPipeline(None if publish_only else studio, [publishers[p] for p in platforms],
                               history=history, make_thumbnails=False, require_approval=True)

    jobs = JobManager(factory, history=history)
    client = TestClient(create_app(history=history, jobs=jobs, token=TOKEN, config_status={},
                                   pipeline_factory=factory))
    try:
        for topic in ("A", "B"):
            job = client.post("/api/runs", json={"topic": topic, "platforms": ["youtube"]}, headers=AUTH).json()
            jobs.wait(job["id"], timeout=5)

        approve = client.post("/api/runs/1/approve", json={"reviewer": "  Lan  "}, headers=AUTH).json()
        jobs.wait(approve["id"], timeout=5)
        client.post("/api/runs/2/reject", json={"reviewer": "Minh", "reason": "Sai số liệu"}, headers=AUTH)
        client.post("/api/runs/1/takedown", json={"platform": "youtube", "reason": "Khiếu nại"}, headers=AUTH)

        first, second = history.get_run(1).reviews, history.get_run(2).reviews
        assert [(e.action, e.actor, e.platform) for e in first] == [
            ("approve", "dashboard:Lan", "youtube"), ("takedown", "dashboard", "youtube")]
        assert first[1].note == "Khiếu nại"
        assert [(e.action, e.actor, e.note) for e in second] == [("reject", "dashboard:Minh", "Sai số liệu")]
        assert client.get("/api/runs", headers=AUTH).json()[0]["reviews"][0]["action"] == "reject"
    finally:
        jobs.shutdown()


# ---------- schedule catch-up across restarts ----------


class MemoryState(dict):
    def get_meta(self, key):
        return self.get(key)

    def set_meta(self, key, value):
        self[key] = value


def test_missed_fire_time_finds_the_latest_due_run_within_grace():
    from ai_content_agent.pipeline.scheduler import missed_fire_time

    utc = timezone.utc
    now = datetime(2026, 11, 9, 4, 0, tzinfo=utc)  # 11:00 in Vietnam
    yesterday = datetime(2026, 11, 8, 3, 0, tzinfo=utc)
    # 09:00 Vietnam = 02:00 UTC today was missed (app closed since yesterday).
    due = missed_fire_time("0 9 * * *", "Asia/Ho_Chi_Minh", yesterday, now)
    assert due == datetime(2026, 11, 9, 2, 0, tzinfo=utc)
    assert missed_fire_time("0 9 * * *", "Asia/Ho_Chi_Minh", due, now) is None  # already ran
    assert missed_fire_time("0 9 * * *", "Asia/Ho_Chi_Minh", yesterday, now, grace_seconds=3600) is None
    assert missed_fire_time("0 9 * * *", "Asia/Ho_Chi_Minh", None, now) is None  # first start


def test_start_background_schedules_a_catch_up_run_and_records_fires():
    from ai_content_agent.pipeline.scheduler import LAST_FIRE_KEY, start_background

    state = MemoryState({LAST_FIRE_KEY: (datetime.now(timezone.utc) - timedelta(hours=26)).isoformat()})
    fired = []
    scheduler = start_background(lambda: fired.append(1), "*/30 * * * *", state=state, jitter_seconds=600)
    try:
        catch_up = scheduler.get_job("content-catch-up")
        assert catch_up is not None
        assert scheduler.get_job("content-run").trigger.jitter == 600
        catch_up.func()
        assert fired == [1]
        assert datetime.fromisoformat(state[LAST_FIRE_KEY]) > datetime.now(timezone.utc) - timedelta(minutes=1)
    finally:
        scheduler.shutdown(wait=False)


def test_first_start_only_records_a_baseline():
    from ai_content_agent.pipeline.scheduler import LAST_FIRE_KEY, start_background

    state = MemoryState()
    scheduler = start_background(lambda: None, "0 9 * * *", state=state)
    try:
        assert scheduler.get_job("content-catch-up") is None and LAST_FIRE_KEY in state
    finally:
        scheduler.shutdown(wait=False)


# ---------- TikTok inbox & Upload-Post ----------


def test_tiktok_inbox_mode_sends_a_draft_without_post_info(monkeypatch, video):
    inbox_done = {"data": {"status": "SEND_TO_USER_INBOX"}, "error": OK}
    fake = Router({"inbox/video/init": INIT, "upload.example": FakeResponse(status_code=201),
                   "status/fetch": inbox_done})
    monkeypatch.setattr(tiktok_publisher, "requests", fake)

    result = tiktok_publisher.TikTokPublisher("tok", "PUBLIC_TO_EVERYONE", mode="inbox").publish(video, SCRIPT)

    assert result.status == "inbox" and result.remote_id == "p_123"
    [init] = fake.bodies("inbox/video/init")
    assert "post_info" not in init and init["source_info"]["video_size"] == 1000
    assert not fake.bodies("creator_info")


def test_tiktok_privacy_refusal_is_a_publish_rejection(monkeypatch, video):
    creator = {"data": {**CREATOR["data"], "privacy_level_options": ["SELF_ONLY"]}, "error": OK}
    monkeypatch.setattr(tiktok_publisher, "requests", Router({"creator_info": creator, "video/init": INIT,
                                                              "status/fetch": DONE}))
    with pytest.raises(PublishRejected, match="TIKTOK_MODE=inbox"):
        tiktok_publisher.TikTokPublisher("tok", "PUBLIC_TO_EVERYONE").publish(video, SCRIPT)


def test_tiktok_rejects_unknown_mode():
    with pytest.raises(ValueError, match="TIKTOK_MODE"):
        tiktok_publisher.TikTokPublisher("tok", mode="sideways")


def test_upload_post_sends_tiktok_fields_with_apikey_auth(monkeypatch, video):
    fake = Router({"api.upload-post.com/api/upload": {"success": True, "request_id": "req-9"}})
    monkeypatch.setattr(upload_post_publisher, "requests", fake)

    publisher = upload_post_publisher.UploadPostPublisher("KEY", "kenh", privacy_level="PUBLIC_TO_EVERYONE")
    result = publisher.publish(video, SCRIPT)

    assert (publisher.name, result.remote_id, result.status) == ("tiktok", "req-9", "processing")
    _, _, kwargs = fake.calls[0]
    assert kwargs["headers"]["Authorization"] == "Apikey KEY"
    fields = dict(kwargs["data"])
    assert fields["user"] == "kenh" and fields["platform[]"] == "tiktok"
    assert fields["privacy_level"] == "PUBLIC_TO_EVERYONE" and fields["is_aigc"] == "true"
    assert fields["title"].endswith("Video có sử dụng AI")


def test_upload_post_error_and_missing_credentials(monkeypatch, video):
    fake = Router({"upload-post.com": FakeResponse({"success": False, "message": "No TikTok account"}, 400)})
    monkeypatch.setattr(upload_post_publisher, "requests", fake)
    with pytest.raises(RuntimeError, match="No TikTok account"):
        upload_post_publisher.UploadPostPublisher("KEY", "kenh").publish(video, SCRIPT)
    with pytest.raises(PublishRejected, match="UPLOAD_POST_API_KEY"):
        upload_post_publisher.UploadPostPublisher(None, None).publish(video, SCRIPT)


def test_agent_builds_upload_post_for_tiktok_when_configured(tmp_path):
    from ai_content_agent.agent import ContentAgent

    config = Config(history_db_path=str(tmp_path / "h.db"), tiktok_via="upload-post",
                    upload_post_api_key="k", upload_post_user="u")
    [publisher] = ContentAgent(config).build_publishers(["tiktok"])
    assert isinstance(publisher, upload_post_publisher.UploadPostPublisher) and publisher.name == "tiktok"
    assert config.status()["platforms"]["tiktok"]["ready"] is True


# ---------- Facebook ----------


def test_facebook_refuses_too_short_or_low_resolution_reels(video):
    publisher = facebook_publisher.FacebookPublisher("page", "token")
    video.duration_seconds = 2.0
    with pytest.raises(PublishRejected, match="at least 3s"):
        publisher.publish(video, SCRIPT)
    video.duration_seconds, video.width, video.height = 30.0, 360, 640
    with pytest.raises(PublishRejected, match="540x960"):
        publisher.publish(video, SCRIPT)


def test_facebook_derives_page_token_from_system_user_token(monkeypatch, video):
    fake = Router({  # first matching substring wins, so the bare Page URL goes last
        "video_reels": [{"video_id": "987", "upload_url": "https://rupload.facebook.com/x"}, {"success": True}],
        "rupload.facebook.com": {"success": True},
        "graph.facebook.com/v23.0/page": {"access_token": "PAGE-TOKEN"},
    })
    monkeypatch.setattr(facebook_publisher, "requests", fake)

    facebook_publisher.FacebookPublisher("page", "SYSTEM-USER-TOKEN").publish(video, SCRIPT)

    method, _, lookup = fake.calls[0]
    assert method == "GET" and lookup["params"]["access_token"] == "SYSTEM-USER-TOKEN"
    start, finish = fake.bodies("video_reels")
    assert start["access_token"] == finish["access_token"] == "PAGE-TOKEN"


# ---------- YouTube ----------


class FakeChannel:
    def __init__(self, items):
        self.items = items

    def channels(self):
        return self

    def playlistItems(self):
        return self

    def list(self, **kwargs):
        self.last = kwargs
        return self

    def execute(self, num_retries=0):
        if "mine" in self.last:
            return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]}
        return {"items": self.items}


def test_youtube_find_existing_matches_title_after_attempt_start(monkeypatch):
    from ai_content_agent.publishers.youtube_publisher import YouTubePublisher

    since = datetime(2026, 11, 9, 2, 0, tzinfo=timezone.utc)
    items = [
        {"snippet": {"title": "Mẹo hay", "publishedAt": "2026-11-01T02:00:00Z", "resourceId": {"videoId": "old"}}},
        {"snippet": {"title": "Khác", "publishedAt": "2026-11-09T02:01:00Z", "resourceId": {"videoId": "other"}}},
        {"snippet": {"title": "Mẹo hay", "publishedAt": "2026-11-09T02:03:00Z", "resourceId": {"videoId": "new"}}},
    ]
    publisher = YouTubePublisher("t", "s")
    monkeypatch.setattr(publisher, "_get_service", lambda: FakeChannel(items))

    found = publisher.find_existing(SCRIPT, since)  # SCRIPT title "Mẹo <hay>" is uploaded as "Mẹo hay"

    assert found.remote_id == "new" and found.url == "https://youtube.com/shorts/new"
    monkeypatch.setattr(publisher, "_get_service", lambda: FakeChannel(items[:2]))
    assert publisher.find_existing(SCRIPT, since) is None


def test_youtube_token_age_and_testing_mode_warning(tmp_path):
    from ai_content_agent.publishers.youtube_publisher import token_age_days

    token = tmp_path / "youtube_token.json"
    token.write_text(json.dumps({"refresh_token": "r", "authorized_at": time.time() - 6.2 * 86400}))
    assert 6 < token_age_days(str(token)) < 6.5

    warning = Config(youtube_token_file=str(token)).status()["platforms"]["youtube"]["warning"]
    assert "Testing" in warning and "7 ngày" in warning

    token.write_text(json.dumps({"refresh_token": "r", "authorized_at": time.time() - 30 * 86400}))
    assert Config(youtube_token_file=str(token)).status()["platforms"]["youtube"]["warning"] is None


def test_youtube_refresh_failure_explains_testing_expiry(tmp_path, monkeypatch, video):
    from google.auth.exceptions import RefreshError
    from google.oauth2.credentials import Credentials

    from ai_content_agent.publishers.youtube_publisher import YouTubePublisher

    token = tmp_path / "youtube_token.json"
    token.write_text(json.dumps({
        "token": "a", "refresh_token": "r", "client_id": "c", "client_secret": "s",
        "expiry": "2020-01-01T00:00:00Z", "authorized_at": time.time() - 8 * 86400,
    }))

    def refuse(self, request):
        raise RefreshError("invalid_grant: Token has been expired or revoked.")

    monkeypatch.setattr(Credentials, "refresh", refuse)
    with pytest.raises(RuntimeError, match="Testing.*7 days"):
        YouTubePublisher(str(token), "secret.json").publish(video, SCRIPT)

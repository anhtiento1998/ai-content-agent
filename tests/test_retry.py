"""Upload retries: per-request retry, resumable YouTube upload, and delayed auto-retry after an outage."""

import time

import pytest
import requests
from fakes import FakePublisher, FakeStudio
from test_publishers import CREATOR, DONE, INIT, OK, SCRIPT, FakeResponse, Router

from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.providers.base import VideoResult
from ai_content_agent.publishers import facebook_publisher, http, tiktok_publisher
from ai_content_agent.publishers.http import NetworkDown, send
from ai_content_agent.web.jobs import JobManager


def _reset():
    return requests.ConnectionError("('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))")


def _unreachable():
    return requests.ConnectionError("HTTPSConnectionPool: Max retries exceeded (Caused by NameResolutionError("
                                    "'Failed to resolve host'))")


class Flaky:
    """Callable that raises / returns the queued outcomes in order, then repeats the last one."""

    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes), 0

    def __call__(self):
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@pytest.fixture
def video(tmp_path):
    path = tmp_path / "v.mp4"
    path.write_bytes(b"\0" * 1000)
    return VideoResult(file_path=str(path), duration_seconds=40.0)


# ---------- the retry helper ----------


def test_send_retries_transient_failures_with_backoff(no_retry_sleep):
    ok = FakeResponse({"fine": True})
    busy = FakeResponse(status_code=503)
    busy.headers = {"Retry-After": "7"}
    request = Flaky(_reset(), busy, ok)

    assert send(request, "testing") is ok
    assert request.calls == 3 and no_retry_sleep == [2.0, 7.0]  # backoff, then the server's Retry-After


def test_send_gives_up_and_tells_outage_from_error(no_retry_sleep):
    always_busy = Flaky(FakeResponse(status_code=502))
    assert send(always_busy, "testing", attempts=3).status_code == 502 and always_busy.calls == 3

    offline = Flaky(_unreachable())
    with pytest.raises(NetworkDown, match="No network connection while testing"):
        send(offline, "testing")
    assert offline.calls == http.DEFAULT_ATTEMPTS

    mixed = Flaky(_unreachable(), _reset())  # it did connect once: not a clean "nothing was sent"
    with pytest.raises(requests.ConnectionError) as failure:
        send(mixed, "testing", attempts=2)
    assert not isinstance(failure.value, NetworkDown)


def test_non_idempotent_steps_only_retry_when_nothing_was_sent():
    lost_reply = Flaky(_reset(), FakeResponse())
    with pytest.raises(requests.ConnectionError):
        send(lost_reply, "uploading", idempotent=False)
    assert lost_reply.calls == 1  # the upload may have arrived: never send it twice

    not_connected = Flaky(requests.ConnectTimeout("timed out"), FakeResponse({"ok": 1}))
    assert send(not_connected, "uploading", idempotent=False).json() == {"ok": 1}
    assert send(Flaky(FakeResponse(status_code=503)), "uploading", idempotent=False).status_code == 503


# ---------- publishers ----------


class FlakyRouter(Router):
    """Router whose route values may contain exceptions to raise."""

    def _answer(self, method, url, kwargs):
        for key, responses in self.routes.items():
            if key in url and isinstance(responses[0], BaseException):
                self.calls.append((method, url, kwargs))
                error = responses.pop(0) if len(responses) > 1 else responses[0]
                raise error
        return super()._answer(method, url, kwargs)


def test_tiktok_resends_the_same_chunk_and_survives_a_drop_while_polling(monkeypatch, video):
    fake = FlakyRouter({"creator_info": CREATOR, "video/init": INIT,
                        "upload.example": [FakeResponse(status_code=503), _reset(), FakeResponse(status_code=201)],
                        "status/fetch": [_unreachable()]})
    monkeypatch.setattr(tiktok_publisher, "requests", fake)

    result = tiktok_publisher.TikTokPublisher("tok").publish(video, SCRIPT)

    puts = [kw["headers"]["Content-Range"] for method, _, kw in fake.calls if method == "PUT"]
    assert puts == ["bytes 0-999/1000"] * 3  # the same range, until it is accepted
    assert len(fake.bodies("video/init")) == 1  # never a second post
    assert (result.status, result.remote_id) == ("processing", "p_123")  # uploaded: not an error


def test_tiktok_failed_status_is_still_an_error(monkeypatch, video):
    failed = {"data": {"status": "FAILED", "fail_reason": "video_pull_failed"}, "error": OK}
    monkeypatch.setattr(tiktok_publisher, "requests", Router({
        "creator_info": CREATOR, "video/init": INIT, "upload.example": FakeResponse(status_code=201),
        "status/fetch": failed}))
    with pytest.raises(RuntimeError, match="video_pull_failed"):
        tiktok_publisher.TikTokPublisher("tok").publish(video, SCRIPT)
    assert DONE  # (imported fixture data stays in use by other modules)


def test_facebook_repeats_a_phase_not_the_whole_reel(monkeypatch, video):
    start = {"video_id": "987", "upload_url": "https://rupload.facebook.com/x"}
    fake = FlakyRouter({"upload_phase=finish": [], "rupload.facebook.com": [_reset(), {"success": True}],
                        "video_reels": [start, _reset(), {"success": True}],
                        "graph.facebook.com/v23.0/page": {"access_token": "PAGE"}})
    del fake.routes["upload_phase=finish"]
    monkeypatch.setattr(facebook_publisher, "requests", fake)

    result = facebook_publisher.FacebookPublisher("page", "token").publish(video, SCRIPT)

    phases = [kw["params"]["upload_phase"] for method, url, kw in fake.calls if "video_reels" in url]
    assert phases == ["start", "finish", "finish"] and result.remote_id == "987"
    assert sum("rupload" in url for _, url, _ in fake.calls) == 2


def test_facebook_single_shot_upload_is_not_repeated_after_a_lost_reply(monkeypatch, video):
    fake = FlakyRouter({"graph-video.facebook.com": [_reset()],
                        "graph.facebook.com/v23.0/page": {"access_token": "PAGE"}})
    monkeypatch.setattr(facebook_publisher, "requests", fake)
    video.duration_seconds = 120
    with pytest.raises(requests.ConnectionError):
        facebook_publisher.FacebookPublisher("page", "token").publish(video, SCRIPT)
    assert sum("graph-video" in url for _, url, _ in fake.calls) == 1


class ResumableRequest:
    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes), 0

    def next_chunk(self):
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _http_error(status):
    from googleapiclient.errors import HttpError

    return HttpError(type("Resp", (), {"status": status, "reason": "x"})(), b"{}")


def test_youtube_resumes_the_same_upload_after_drops(no_retry_sleep):
    from ai_content_agent.publishers.youtube_publisher import YouTubePublisher

    publisher = YouTubePublisher("t", "s", retries=3)
    request = ResumableRequest((None, None), ConnectionResetError("reset"), _http_error(503), (None, None),
                               TimeoutError("slow"), (None, {"id": "abc"}))
    assert publisher._upload(request) == {"id": "abc"}
    assert request.calls == 6 and len(no_retry_sleep) == 3  # progress resets the failure count

    with pytest.raises(Exception, match="403|x"):
        publisher._upload(ResumableRequest(_http_error(403)))  # a real refusal is not retried

    stuck = ResumableRequest((None, None), ConnectionResetError("reset"))
    with pytest.raises(ConnectionResetError):
        publisher._upload(stuck)
    assert stuck.calls == 4  # one chunk, then three failures in a row


def test_youtube_offline_from_the_start_is_network_down():
    import socket

    from ai_content_agent.publishers.youtube_publisher import YouTubePublisher

    request = ResumableRequest(socket.gaierror(-3, "Temporary failure in name resolution"))
    with pytest.raises(NetworkDown, match="YouTube"):
        YouTubePublisher("t", "s", retries=2)._upload(request)
    assert request.calls == 2


# ---------- pipeline & delayed auto-retry ----------


class OfflinePublisher(FakePublisher):
    def __init__(self, name, outages=1):
        super().__init__(name=name)
        self.outages, self.lookups = outages, 0

    def publish(self, video, script):
        if self.outages:
            self.outages -= 1
            raise NetworkDown("No network connection while uploading")
        return super().publish(video, script)

    def find_existing(self, script, since):
        self.lookups += 1
        return None


def test_outage_is_recorded_as_not_sent_and_offered_for_retry(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    youtube, facebook = OfflinePublisher("youtube"), FakePublisher("facebook")
    pipeline = ContentPipeline(FakeStudio(str(tmp_path / "run" / "final.mp4")), [youtube, facebook],
                               history=history, make_thumbnails=False)

    outcome = pipeline.run("Chủ đề")
    assert outcome.retry_later == ["youtube"] and [r.platform for r in outcome.published] == ["facebook"]
    assert history.get_run(outcome.run_id).status == "partial"
    assert history.uncertain_attempt_since(outcome.run_id, "youtube") is None  # nothing can be on YouTube

    retry = pipeline.publish_run(outcome.run_id)
    assert retry.retry_later == [] and youtube.lookups == 0 and len(youtube.published) == 1
    assert len(facebook.published) == 1 and history.get_run(outcome.run_id).status == "published"


def _wait_for(condition, seconds=5.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return False


def test_job_manager_retries_publishing_by_itself_after_an_outage(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    youtube = OfflinePublisher("youtube", outages=2)
    studio = FakeStudio(str(tmp_path / "run" / "final.mp4"))

    def factory(platforms, publish_only=False):
        return ContentPipeline(None if publish_only else studio, [youtube], history=history, make_thumbnails=False)

    jobs = JobManager(factory, history=history, auto_retry_minutes=0.0005)  # 30 ms, then 60 ms
    try:
        first = jobs.submit("Chủ đề", ["youtube"])
        jobs.wait(first.id, timeout=5)
        job = jobs.get(first.id)
        assert job["status"] == "failed" and job["retry_at"] and job["auto_retries"] == 0
        assert "tự thử lại" in history.recent_errors()[0].message

        assert _wait_for(lambda: len(youtube.published) == 1)
        retries = [j for j in jobs.list() if j["source"] == "auto-retry"]
        assert [j["auto_retries"] for j in reversed(retries)] == [1, 2]
        assert _wait_for(lambda: retries and jobs.get(retries[0]["id"])["status"] == "succeeded")
        assert history.get_run(job["run_id"]).status == "published" and studio.calls == 1  # never re-rendered
    finally:
        jobs.shutdown()


def test_auto_retry_stops_after_the_limit_and_can_be_disabled(tmp_path):
    from ai_content_agent.web import jobs as jobs_module

    history = HistoryStore(str(tmp_path / "h.db"))
    youtube = OfflinePublisher("youtube", outages=99)
    studio = FakeStudio(str(tmp_path / "run" / "final.mp4"))

    def factory(platforms, publish_only=False):
        return ContentPipeline(None if publish_only else studio, [youtube], history=history, make_thumbnails=False)

    jobs = JobManager(factory, history=history, auto_retry_minutes=0.0002)
    try:
        jobs.wait(jobs.submit("Chủ đề", ["youtube"]).id, timeout=5)
        limit = jobs_module.MAX_AUTO_RETRIES
        assert _wait_for(lambda: sum(j["source"] == "auto-retry" and j["status"] == "failed"
                                     for j in jobs.list()) == limit)
        time.sleep(0.3)
        assert sum(j["source"] == "auto-retry" for j in jobs.list()) == limit  # no fourth retry
    finally:
        jobs.shutdown()

    quiet = JobManager(factory, history=history)  # auto retry off by default for library use
    try:
        job = quiet.submit("Chủ đề khác", ["youtube"])
        quiet.wait(job.id, timeout=5)
        assert quiet.get(job.id)["retry_at"] is None
    finally:
        quiet.shutdown()

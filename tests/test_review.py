"""Review queue, approve/retry/takedown, daily caps, history migration and scheduler settings."""

import sqlite3

import pytest
from fakes import FakePublisher, FakeStudio
from fastapi.testclient import TestClient

from ai_content_agent.config import Config
from ai_content_agent.history import FAILED, PARTIAL, PENDING, PUBLISHED, REJECTED, HistoryStore
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.web.app import create_app
from ai_content_agent.web.jobs import JobManager

TOKEN = "test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def world(tmp_path):
    """A history plus a factory that hands out pipelines sharing one set of fake publishers."""

    history = HistoryStore(str(tmp_path / "h.db"))
    publishers = {name: FakePublisher(name=name) for name in ("youtube", "tiktok", "facebook")}
    studio = FakeStudio(str(tmp_path / "run" / "final.mp4"))

    def factory(platforms, publish_only=False, *, approval=True, cap=0):
        return ContentPipeline(None if publish_only else studio, [publishers[p] for p in platforms],
                               history=history, make_thumbnails=False, require_approval=approval,
                               max_posts_per_day=cap)

    return history, publishers, studio, factory


# ---------- pipeline ----------


def test_approval_holds_the_video_until_approved(world):
    history, publishers, _, factory = world

    outcome = factory(["youtube", "tiktok"]).run("Mẹo hay")

    assert outcome.pending_review and outcome.published == []
    assert publishers["youtube"].published == []
    [run] = history.pending_runs()
    assert (run.id, run.status, run.platforms) == (outcome.run_id, PENDING, ["youtube", "tiktok"])
    assert run.script["title"] == "Title for Mẹo hay"

    published = factory(["youtube", "tiktok"], publish_only=True).publish_run(run.id).published

    assert {r.platform for r in published} == {"youtube", "tiktok"}
    assert history.get_run(run.id).status == PUBLISHED
    assert history.pending_runs() == []


def test_pending_topic_counts_as_duplicate_but_rejected_does_not(world):
    history, _, studio, factory = world
    outcome = factory(["youtube"]).run("Same topic")

    assert factory(["youtube"]).run("same   TOPIC").skipped
    history.set_run_status(outcome.run_id, REJECTED)
    assert not factory(["youtube"]).run("Same topic").skipped
    assert studio.calls == 2


def test_retry_publishes_only_failed_platforms(world):
    history, publishers, _, factory = world
    publishers["tiktok"]._fail = True
    run_id = factory(["youtube", "tiktok"], approval=False).run("Topic").run_id

    assert history.get_run(run_id).status == PARTIAL
    publishers["tiktok"]._fail = False
    factory(["youtube", "tiktok"], publish_only=True).publish_run(run_id)

    assert len(publishers["youtube"].published) == 1  # not re-posted
    assert len(publishers["tiktok"].published) == 1
    assert history.get_run(run_id).status == PUBLISHED


def test_all_platforms_failing_marks_run_failed_and_allows_new_attempt(world):
    history, publishers, _, factory = world
    publishers["youtube"]._fail = True
    run_id = factory(["youtube"], approval=False).run("Topic").run_id

    assert history.get_run(run_id).status == FAILED
    assert not factory(["youtube"]).run("Topic").skipped


def test_daily_cap_blocks_extra_posts_and_logs_why(world):
    history, publishers, _, factory = world
    for topic in ("A", "B", "C"):
        factory(["youtube"], approval=False, cap=2).run(topic)

    assert len(publishers["youtube"].published) == 2
    assert any("Daily cap of 2" in e.message for e in history.recent_errors())


def test_takedown_deletes_post_and_frees_the_topic(world):
    history, publishers, _, factory = world
    run_id = factory(["youtube"], approval=False).run("Topic").run_id

    factory(["youtube"], publish_only=True).takedown(run_id, "youtube")

    assert publishers["youtube"].deleted == ["1"]
    assert history.live_publish(run_id, "youtube") is None
    assert not history.has_recent_topic("Topic")
    with pytest.raises(ValueError, match="not live"):
        factory(["youtube"], publish_only=True).takedown(run_id, "youtube")


def test_rejected_or_missing_video_cannot_be_published(world, tmp_path):
    history, _, _, factory = world
    run_id = factory(["youtube"]).run("Topic").run_id
    history.set_run_status(run_id, REJECTED)
    with pytest.raises(ValueError, match="rejected"):
        factory(["youtube"], publish_only=True).publish_run(run_id)

    run_id = factory(["youtube"]).run("Other").run_id
    (tmp_path / "run" / "final.mp4").unlink()
    with pytest.raises(FileNotFoundError):
        factory(["youtube"], publish_only=True).publish_run(run_id)


def test_publish_only_pipeline_cannot_produce(world):
    _, _, _, factory = world
    with pytest.raises(ValueError, match="publish-only"):
        factory(["youtube"], publish_only=True).run("Topic")


# ---------- history migration ----------


def test_old_database_is_migrated_in_place(tmp_path):
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE runs (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, title TEXT NOT NULL,
                           video_path TEXT, created_at TEXT NOT NULL);
        CREATE TABLE publishes (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, platform TEXT NOT NULL,
                                remote_id TEXT NOT NULL, url TEXT, created_at TEXT NOT NULL);
        INSERT INTO runs (topic, title, video_path, created_at) VALUES ('cũ', 'Old', '/v.mp4', '2026-11-01T00:00:00+00:00');
        INSERT INTO publishes (run_id, platform, remote_id, url, created_at)
            VALUES (1, 'youtube', 'x', 'u', '2026-11-01T00:00:00+00:00');
    """)
    conn.commit()
    conn.close()

    [run] = HistoryStore(str(db)).recent_runs()

    assert (run.title, run.status, run.platforms) == ("Old", PUBLISHED, [])
    assert run.publishes[0].deleted_at is None


# ---------- dashboard API ----------


@pytest.fixture
def api(world):
    history, publishers, _, factory = world
    jobs = JobManager(factory, history=history)
    client = TestClient(create_app(history=history, jobs=jobs, token=TOKEN,
                                   config_status=Config().status(), pipeline_factory=factory))
    yield client, jobs, history, publishers
    jobs.shutdown()


def _produce(client, jobs):
    res = client.post("/api/runs", json={"topic": "Chủ đề", "platforms": ["youtube", "facebook"]}, headers=AUTH)
    jobs.wait(res.json()["id"], timeout=5)
    return client.get(f"/api/jobs/{res.json()['id']}", headers=AUTH).json()


def test_api_review_flow(api):
    client, jobs, history, publishers = api

    job = _produce(client, jobs)
    assert (job["status"], job["run_id"]) == ("review", 1)
    [pending] = client.get("/api/reviews", headers=AUTH).json()
    assert pending["status"] == PENDING
    assert client.get("/api/runs/1/video", headers=AUTH).content == b"fake mp4"
    assert client.get("/api/runs/1/video").status_code == 401
    assert client.get("/api/stats", headers=AUTH).json()["pending_review"] == 1

    approve = client.post("/api/runs/1/approve", json={"platforms": ["youtube"]}, headers=AUTH)
    assert approve.status_code == 202
    jobs.wait(approve.json()["id"], timeout=5)
    assert client.get(f"/api/jobs/{approve.json()['id']}", headers=AUTH).json()["status"] == "succeeded"
    assert len(publishers["youtube"].published) == 1 and publishers["facebook"].published == []
    assert client.post("/api/runs/1/approve", headers=AUTH).status_code == 409

    retry = client.post("/api/runs/1/publish", json={"platforms": ["facebook"]}, headers=AUTH)
    jobs.wait(retry.json()["id"], timeout=5)
    assert len(publishers["facebook"].published) == 1 and len(publishers["youtube"].published) == 1

    down = client.post("/api/runs/1/takedown", json={"platform": "facebook"}, headers=AUTH)
    assert down.status_code == 200 and publishers["facebook"].deleted == ["1"]
    assert client.post("/api/runs/1/takedown", json={"platform": "facebook"}, headers=AUTH).status_code == 409


def test_api_reject(api):
    client, jobs, history, _ = api
    _produce(client, jobs)

    assert client.post("/api/runs/1/reject", headers=AUTH).json() == {"status": REJECTED}
    assert client.get("/api/reviews", headers=AUTH).json() == []
    assert client.post("/api/runs/1/publish", json={"platforms": []}, headers=AUTH).status_code == 409
    assert client.post("/api/runs/99/reject", headers=AUTH).status_code == 404


def test_csp_allows_blob_media_for_previews(api):
    client, *_ = api
    csp = client.get("/").headers["content-security-policy"]
    assert "media-src 'self' blob:" in csp


# ---------- scheduler & config ----------


def test_scheduler_catches_up_missed_runs_in_configured_timezone():
    from ai_content_agent.pipeline.scheduler import MISFIRE_GRACE_SECONDS, start_background

    scheduler = start_background(lambda: None, "0 9 * * *", timezone="Asia/Ho_Chi_Minh")
    try:
        job = scheduler.get_job("content-run")
        assert job.misfire_grace_time == MISFIRE_GRACE_SECONDS >= 3600
        assert job.coalesce is True
        assert str(job.trigger.timezone) == "Asia/Ho_Chi_Minh"
        assert job.next_run_time.utcoffset().total_seconds() == 7 * 3600
    finally:
        scheduler.shutdown(wait=False)


def test_agent_wires_safety_settings_into_pipeline_and_publishers(tmp_path):
    from ai_content_agent.agent import ContentAgent

    config = Config(history_db_path=str(tmp_path / "h.db"), max_posts_per_day=5, youtube_privacy="unlisted",
                    ai_disclosure_text="AI", tiktok_client_key="k", tiktok_client_secret="s",
                    tiktok_refresh_token="r")
    pipeline = ContentAgent(config).build_pipeline(["youtube", "tiktok", "facebook"], publish_only=True)

    assert pipeline._require_approval is True and pipeline._max_posts_per_day == 5
    youtube, tiktok, facebook = pipeline._publishers
    assert youtube._privacy == "unlisted" and youtube._disclosure.text == "AI"
    assert tiktok._tokens.can_refresh
    assert facebook._disclosure.enabled
    assert config.status()["platforms"]["tiktok"]["ready"] is True

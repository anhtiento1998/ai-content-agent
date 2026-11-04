"""Dashboard API tests — fake pipeline, FastAPI TestClient, no network calls."""

import pytest
from fakes import FakePublisher, FakeText, FakeVideo
from fastapi.testclient import TestClient

from ai_content_agent.config import Config
from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.web.app import create_app
from ai_content_agent.web.jobs import JobManager

TOKEN = "test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _config(**overrides):
    values = dict(
        openai_api_key=None,
        anthropic_api_key="sk-ant-SECRET-VALUE",
        google_api_key=None,
        meta_model_api_key=None,
        meta_model_api_base_url=None,
        youtube_token_file="missing_token.json",
        youtube_client_secret_file="missing_secret.json",
        tiktok_access_token="tiktok-SECRET-VALUE",
        facebook_page_id=None,
        facebook_access_token=None,
        instagram_user_id=None,
        instagram_access_token=None,
        text_provider="claude",
        video_provider="veo",
        history_db_path="unused.db",
        dedup_window_days=30,
        make_thumbnails=False,
        dashboard_token=None,
    )
    values.update(overrides)
    return Config(**values)


@pytest.fixture
def env(tmp_path):
    history = HistoryStore(str(tmp_path / "history.db"))
    state = {"failing": set(), "factory_error": None}

    def factory(platforms):
        if state["factory_error"]:
            raise state["factory_error"]
        return ContentPipeline(
            FakeText(),
            FakeVideo(str(tmp_path / "video.mp4")),
            [FakePublisher(name=p, fail=p in state["failing"]) for p in platforms],
            history=history,
            make_thumbnails=False,
        )

    jobs = JobManager(factory, history=history)
    app = create_app(history=history, jobs=jobs, token=TOKEN, config_status=_config().status())
    client = TestClient(app)
    yield client, jobs, state
    jobs.shutdown()


def _run(client, jobs, **body):
    res = client.post("/api/runs", json={"topic": "Chủ đề thử", "platforms": ["youtube"], **body}, headers=AUTH)
    assert res.status_code == 202, res.text
    job_id = res.json()["id"]
    jobs.wait(job_id, timeout=5)
    return client.get(f"/api/jobs/{job_id}", headers=AUTH).json()


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": TOKEN}])
def test_api_requires_valid_bearer_token(env, headers):
    client, _, _ = env
    for path in ("/api/stats", "/api/runs", "/api/errors", "/api/jobs", "/api/config", "/api/schedule"):
        assert client.get(path, headers=headers).status_code == 401
    assert client.post("/api/runs", json={"topic": "x", "dry_run": True}, headers=headers).status_code == 401


def test_index_is_public_with_security_headers(env):
    client, _, _ = env
    res = client.get("/")
    assert res.status_code == 200
    assert "AI Content Agent" in res.text
    assert "default-src 'self'" in res.headers["content-security-policy"]
    assert client.get("/static/app.js").status_code == 200


def test_run_job_succeeds_and_shows_in_history(env):
    client, jobs, _ = env

    job = _run(client, jobs, platforms=["youtube", "tiktok"])

    assert job["status"] == "succeeded"
    assert {r["platform"] for r in job["results"]} == {"youtube", "tiktok"}
    [run] = client.get("/api/runs", headers=AUTH).json()
    assert run["title"] == "Title for Chủ đề thử"
    assert {p["platform"] for p in run["publishes"]} == {"youtube", "tiktok"}
    assert client.get("/api/stats", headers=AUTH).json()["total_publishes"] == 2


def test_partial_failure_is_reported_and_logged(env):
    client, jobs, state = env
    state["failing"].add("tiktok")

    job = _run(client, jobs, platforms=["youtube", "tiktok"])

    assert job["status"] == "partial"
    [error] = client.get("/api/errors", headers=AUTH).json()
    assert (error["stage"], error["platform"]) == ("publish", "tiktok")


def test_all_publishes_failing_marks_job_failed(env):
    client, jobs, state = env
    state["failing"].add("youtube")

    assert _run(client, jobs)["status"] == "failed"


def test_duplicate_topic_is_skipped_unless_forced(env):
    client, jobs, _ = env
    _run(client, jobs)

    assert _run(client, jobs)["status"] == "skipped"
    assert _run(client, jobs, force=True)["status"] == "succeeded"


def test_dry_run_needs_no_platform_and_records_nothing(env):
    client, jobs, _ = env

    job = _run(client, jobs, platforms=[], dry_run=True)

    assert job["status"] == "succeeded"
    assert client.get("/api/runs", headers=AUTH).json() == []


def test_setup_failure_is_logged(env):
    client, jobs, state = env
    state["factory_error"] = ValueError("ANTHROPIC_API_KEY missing")

    job = _run(client, jobs)

    assert job["status"] == "failed"
    assert "ANTHROPIC_API_KEY missing" in job["error"]
    [error] = client.get("/api/errors", headers=AUTH).json()
    assert error["stage"] == "setup"


@pytest.mark.parametrize(
    "body",
    [
        {"topic": "x", "platforms": []},
        {"topic": "   ", "platforms": ["youtube"]},
        {"topic": "x", "platforms": ["myspace"]},
        {"topic": "x" * 301, "platforms": ["youtube"]},
    ],
)
def test_invalid_run_requests_are_rejected(env, body):
    client, _, _ = env
    assert client.post("/api/runs", json=body, headers=AUTH).status_code == 422


def test_config_endpoint_never_leaks_secrets(env):
    client, _, _ = env

    res = client.get("/api/config", headers=AUTH)

    assert "SECRET-VALUE" not in res.text
    cfg = res.json()
    assert cfg["text_providers"]["claude"]["ready"] is True
    assert cfg["platforms"]["tiktok"]["ready"] is True
    assert cfg["platforms"]["youtube"]["ready"] is False
    assert cfg["video_providers"]["muse"]["ready"] is False


def test_schedule_disabled_by_default(env):
    client, _, _ = env
    assert client.get("/api/schedule", headers=AUTH).json() == {"enabled": False}


def test_muse_spark_requires_base_url():
    from ai_content_agent.providers.meta_muse_provider import MuseSparkProvider

    with pytest.raises(ValueError, match="META_MODEL_API_BASE_URL"):
        MuseSparkProvider(api_key="k", base_url="")


def test_muse_video_fails_fast(tmp_path):
    from ai_content_agent.agent import ContentAgent

    config = _config(video_provider="muse", history_db_path=str(tmp_path / "h.db"))
    with pytest.raises(NotImplementedError):
        ContentAgent(config).build_pipeline(["youtube"])

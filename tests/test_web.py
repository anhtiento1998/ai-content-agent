"""Dashboard API tests — fake pipeline, FastAPI TestClient, no network calls."""

import pytest
from fakes import FakePublisher, FakeStudio
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
        anthropic_api_key="sk-ant-SECRET-VALUE",
        tiktok_access_token="tiktok-SECRET-VALUE",
        youtube_token_file="missing_token.json",
        youtube_client_secret_file="missing_secret.json",
        make_thumbnails=False,
    )
    values.update(overrides)
    return Config(**values)


@pytest.fixture
def env(tmp_path):
    history = HistoryStore(str(tmp_path / "history.db"))
    state = {"failing": set(), "factory_error": None, "studio_fail_stage": None}

    def factory(platforms, publish_only=False):
        if state["factory_error"]:
            raise state["factory_error"]
        return ContentPipeline(
            FakeStudio(str(tmp_path / "video.mp4"), fail_stage=state["studio_fail_stage"]),
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


def test_dry_run_needs_no_platform_and_records_nothing(env, tmp_path):
    client, jobs, _ = env

    job = _run(client, jobs, platforms=[], dry_run=True)

    assert job["status"] == "succeeded"
    assert job["video_path"] == str(tmp_path / "video.mp4")
    assert client.get("/api/runs", headers=AUTH).json() == []


def test_studio_failure_reports_the_failed_stage(env):
    client, jobs, state = env
    state["studio_fail_stage"] = "voice"

    job = _run(client, jobs)

    assert (job["status"], job["failed_stage"]) == ("failed", "voice")
    assert job["error"] == "scene 1: RuntimeError: voice broke"
    [error] = client.get("/api/errors", headers=AUTH).json()
    assert error["stage"] == "voice"


def test_setup_failure_is_logged(env):
    client, jobs, state = env
    state["factory_error"] = ValueError("ANTHROPIC_API_KEY missing")

    job = _run(client, jobs)

    assert (job["status"], job["failed_stage"]) == ("failed", "setup")
    assert "ANTHROPIC_API_KEY missing" in job["error"]
    [error] = client.get("/api/errors", headers=AUTH).json()
    assert error["stage"] == "setup"


@pytest.mark.parametrize(
    "body",
    [
        {"topic": "x", "platforms": []},
        {"topic": "   ", "platforms": ["youtube"]},
        {"topic": "x", "platforms": ["myspace"]},
        {"topic": "x", "platforms": ["instagram"]},
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
    assert cfg["visual_providers"]["muse"]["ready"] is False
    assert cfg["visual_providers"]["card"]["ready"] is True
    assert (cfg["text_provider"], cfg["visual_provider"], cfg["voice_provider"]) == ("claude", "imagen", "gemini")


def test_schedule_disabled_by_default(env):
    client, _, _ = env
    assert client.get("/api/schedule", headers=AUTH).json() == {"enabled": False}


def test_muse_spark_requires_base_url():
    from ai_content_agent.providers.meta_muse_provider import MuseSparkProvider

    with pytest.raises(ValueError, match="META_MODEL_API_BASE_URL"):
        MuseSparkProvider(api_key="k", base_url="")


def test_muse_video_fails_fast(tmp_path):
    from ai_content_agent.agent import ContentAgent

    config = _config(visual_provider="muse", history_db_path=str(tmp_path / "h.db"))
    with pytest.raises(NotImplementedError):
        ContentAgent(config).build_pipeline(["youtube"])


def test_config_from_env_maps_field_names_and_types(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no stray .env gets loaded
    monkeypatch.setenv("VISUAL_PROVIDER", "card")
    monkeypatch.setenv("TARGET_SECONDS", "25")
    monkeypatch.setenv("MAKE_THUMBNAILS", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    config = Config.from_env()

    assert (config.visual_provider, config.target_seconds, config.make_thumbnails) == ("card", 25, False)
    assert config.openai_api_key is None
    assert config.voice_provider == "gemini"


def test_job_exposes_stage_progress(env):
    client, jobs, _ = env

    job = _run(client, jobs, platforms=["youtube", "tiktok"])

    assert (job["stage"], job["stage_done"], job["stage_total"]) == ("publish", 2, 2)


class _StubCapCut:
    def __init__(self, fail=False):
        self.calls, self._fail = [], fail

    def export(self, work_dir):
        self.calls.append(str(work_dir))
        if self._fail:
            raise RuntimeError("format changed")
        return f"{work_dir}/draft"


def _app_with_capcut(tmp_path, exporter):
    history = HistoryStore(str(tmp_path / "h.db"))
    jobs = JobManager(
        lambda platforms, publish_only=False: ContentPipeline(FakeStudio(str(tmp_path / "run" / "final.mp4")), [], history=history,
                                          make_thumbnails=False),
        history=history,
    )
    app = create_app(history=history, jobs=jobs, token=TOKEN, config_status=_config().status(),
                     capcut_exporter=exporter)
    return TestClient(app), jobs


def test_capcut_export_uses_the_jobs_own_work_folder(tmp_path):
    exporter = _StubCapCut()
    client, jobs = _app_with_capcut(tmp_path, exporter)
    job = _run(client, jobs, platforms=[], dry_run=True)

    res = client.post(f"/api/jobs/{job['id']}/capcut", headers=AUTH)

    assert res.status_code == 200, res.text
    assert exporter.calls == [str(tmp_path / "run")]
    assert client.get(f"/api/jobs/{job['id']}", headers=AUTH).json()["capcut_draft"] == res.json()["draft"]
    jobs.shutdown()


def test_capcut_export_errors(tmp_path):
    client, jobs = _app_with_capcut(tmp_path, _StubCapCut(fail=True))
    job = _run(client, jobs, platforms=[], dry_run=True)

    assert client.post("/api/jobs/nope/capcut", headers=AUTH).status_code == 404
    assert client.post(f"/api/jobs/{job['id']}/capcut").status_code == 401
    res = client.post(f"/api/jobs/{job['id']}/capcut", headers=AUTH)
    assert res.status_code == 500 and "format changed" in res.json()["detail"]
    assert client.get("/api/errors", headers=AUTH).json()[0]["stage"] == "capcut"
    jobs.shutdown()


def test_capcut_export_unavailable_without_exporter(env):
    client, jobs, _ = env
    job = _run(client, jobs, platforms=[], dry_run=True)
    assert client.post(f"/api/jobs/{job['id']}/capcut", headers=AUTH).status_code == 501

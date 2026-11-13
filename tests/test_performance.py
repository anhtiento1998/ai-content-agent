"""View statistics and resting formats that earn few views."""

import json
import random
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest
from fakes import FakePublisher, FakeStudio
from fastapi.testclient import TestClient
from test_publishers import OK, FakeResponse, Router

from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.pipeline.performance import analyze, refresh_stats, weak_options
from ai_content_agent.providers.base import ScriptResult, VideoResult
from ai_content_agent.publishers import facebook_publisher, tiktok_publisher
from ai_content_agent.publishers.base import PublishResult
from ai_content_agent.studio.variation import Variator
from ai_content_agent.web.app import create_app
from ai_content_agent.web.jobs import JobManager

TOKEN = "t"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def history(tmp_path):
    return HistoryStore(str(tmp_path / "h.db"))


def _post(history, variation, views, *, platform="youtube", age_hours=100.0, run_id=None):
    """Record a run (or add a post to `run_id`) that is `age_hours` old with `views` views."""

    if run_id is None:
        run_id = history.record_run(f"topic {random.random()}", ScriptResult("T", "s"), VideoResult("/v.mp4"),
                                    status="published", platforms=[platform], variation=variation)
    history.record_publish(run_id, PublishResult(platform, f"{platform}-{run_id}"))
    when = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    with closing(history._connect()) as conn:
        conn.execute("UPDATE publishes SET views = ?, created_at = ?, stats_at = ? WHERE run_id = ? AND platform = ?",
                     (views, when, when, run_id, platform))
        conn.commit()
    return run_id


def _seed(history):
    """Ten scored runs: 'question' hooks do well, 'list' hooks poorly, 'story' has too few runs."""

    for views in (1000, 1200, 900, 1100):
        _post(history, {"hook": "question", "visual_style": "3d"}, views)
    for views in (100, 150, 120, 90):
        _post(history, {"hook": "list", "visual_style": "anime"}, views)
    for views in (5000, 30):
        _post(history, {"hook": "story", "visual_style": "3d"}, views)


def test_formats_are_scored_against_a_typical_post(history):
    _seed(history)
    report = analyze(history)

    assert report["scored_runs"] == 10 and report["enough_data"] is True
    hooks = {item["option"]: item for item in report["dimensions"]["hook"]}
    assert hooks["question"]["status"] == "ok" and hooks["question"]["score"] > 1.5
    assert hooks["list"]["status"] == "weak" and hooks["list"]["score"] < 0.5 and hooks["list"]["runs"] == 4
    assert hooks["story"]["status"] == "few"  # two runs: one viral video must not decide anything
    assert hooks["question"]["median_views"] == 1050
    assert weak_options(report)["hook"] == {"list"}
    # Two visual styles only: the weaker one is kept, a dimension is never rested down to one look.
    assert weak_options(report)["visual_style"] == set()
    assert report["dimensions"]["voice"] == [] and report["platform_median_views"] == {"youtube": 525}


def test_nothing_is_rested_without_enough_data_or_age(history):
    for views in (1000, 1100, 900):
        _post(history, {"hook": "question"}, views)
    for views in (10, 20, 15):
        _post(history, {"hook": "list"}, views)
    for views in (5, 5, 5):
        _post(history, {"hook": "myth"}, views, age_hours=3)  # too fresh to have views yet

    report = analyze(history)
    assert report["scored_runs"] == 6 and report["enough_data"] is False  # below MIN_RUNS
    assert weak_options(report)["hook"] == set()
    assert "myth" not in {item["option"] for item in report["dimensions"]["hook"]}
    # Even with a lower bar: only two hooks have data, and two always stay in rotation.
    assert weak_options(analyze(history, min_runs=6))["hook"] == set()

    for views in (500, 600, 550):
        _post(history, {"hook": "contrast"}, views)
    report = analyze(history)  # nine scored runs, three hooks with data
    assert report["enough_data"] and weak_options(report)["hook"] == {"list"}


def test_views_are_normalised_per_platform(history):
    # TikTok numbers are 100x YouTube's here; the same format must not look better just for being on TikTok.
    for views in (100, 110, 90, 105):
        run = _post(history, {"hook": "question"}, views)
        _post(history, {}, views * 100, platform="tiktok", run_id=run)
    for views in (20, 25, 15, 30):
        run = _post(history, {"hook": "list"}, views)
        _post(history, {}, views * 100, platform="tiktok", run_id=run)

    report = analyze(history)
    hooks = {item["option"]: item for item in report["dimensions"]["hook"]}
    assert report["scored_runs"] == 8 and hooks["list"]["score"] < 0.6 < 1.2 < hooks["question"]["score"]
    assert set(report["platform_median_views"]) == {"youtube", "tiktok"}


def test_variator_rests_weak_options_but_never_empties_a_dimension():
    variator = Variator(hooks=["question", "list", "story"], visual_styles=["3d"], rng=random.Random(1))
    picks = {variator.plan([], [], exclude={"hook": {"list"}}).hook for _ in range(30)}
    assert picks == {"question", "story"}
    assert variator.plan([], [], exclude={"visual_style": {"3d"}}).visual_style == "3d"


def test_pipeline_stops_using_a_weak_format(history, tmp_path):
    _seed(history)
    for _ in range(3):  # the newest videos used "question", so plain rotation would pick "list" next
        _post(history, {"hook": "question", "visual_style": "3d"}, 0, age_hours=1)
    studio = FakeStudio(str(tmp_path / "run" / "final.mp4"))
    variator = Variator(hooks=["question", "list"], rng=random.Random(2))

    def next_hook(prune):
        pipeline = ContentPipeline(studio, [], history=history, make_thumbnails=False, variator=variator,
                                   prune_formats=prune)
        return pipeline._new_plan().hook

    assert next_hook(prune=False) == "list"
    assert next_hook(prune=True) == "question"  # "list" earns a fraction of the views: rested


# ---------- reading numbers from the platforms ----------


class StatsPublisher(FakePublisher):
    def __init__(self, name, numbers=None, error=None):
        super().__init__(name=name)
        self.numbers, self.error, self.asked = numbers or {}, error, None

    def stats(self, remote_ids):
        self.asked = list(remote_ids)
        if self.error:
            raise self.error
        return self.numbers


def test_refresh_stats_saves_views_and_survives_a_failing_platform(history):
    run = _post(history, {"hook": "question"}, 1)
    _post(history, {}, 1, platform="tiktok", run_id=run)
    history.mark_taken_down(_post(history, {}, 1, platform="facebook"), "facebook")
    youtube = StatsPublisher("youtube", {f"youtube-{run}": {"views": 4321, "likes": 12, "comments": 3}})
    tiktok = StatsPublisher("tiktok", error=RuntimeError("scope_not_authorized"))
    facebook = StatsPublisher("facebook")

    summary = refresh_stats(history, [youtube, tiktok, facebook])

    assert summary == {"youtube": 1, "tiktok": "RuntimeError: scope_not_authorized"}  # no live facebook posts
    assert youtube.asked == [f"youtube-{run}"] and facebook.asked is None
    record = history.get_run(run).publishes[0]
    assert (record.views, record.likes, record.comments) == (4321, 12, 3) and record.stats_at


def test_youtube_stats(monkeypatch):
    from ai_content_agent.publishers.youtube_publisher import YouTubePublisher

    class Service:
        def videos(self):
            return self

        def list(self, part, id):
            self.asked = (part, id)
            return self

        def execute(self, num_retries=0):
            return {"items": [{"id": "abc", "statistics": {"viewCount": "1500", "likeCount": "40"}}]}

    service = Service()
    publisher = YouTubePublisher("t", "s")
    monkeypatch.setattr(publisher, "_get_service", lambda: service)
    assert publisher.stats(["abc", "gone"]) == {"abc": {"views": 1500, "likes": 40, "comments": None}}
    assert service.asked == ("statistics", "abc,gone")


def test_tiktok_stats_only_asks_for_real_video_ids(monkeypatch):
    videos = {"data": {"videos": [{"id": "7300000001", "view_count": 900, "like_count": 30, "comment_count": 2}]},
              "error": OK}
    fake = Router({"video/query": videos})
    monkeypatch.setattr(tiktok_publisher, "requests", fake)

    result = tiktok_publisher.TikTokPublisher("tok").stats(["7300000001", "v_pub_file~v2.123"])

    assert result == {"7300000001": {"views": 900, "likes": 30, "comments": 2}}
    assert fake.bodies("video/query") == [{"filters": {"video_ids": ["7300000001"]}}]


def test_facebook_stats_uses_insights_then_the_views_field(monkeypatch):
    fake = Router({
        "111/video_insights": {"data": [{"name": "fb_reels_total_plays", "values": [{"value": 800}]}]},
        "222/video_insights": {"error": {"code": 100, "message": "no insights for this video"}},
        "/222": {"views": 55},
        "graph.facebook.com/v23.0/page": {"access_token": "PAGE"},
    })
    monkeypatch.setattr(facebook_publisher, "requests", fake)
    stats = facebook_publisher.FacebookPublisher("page", "token").stats(["111", "222"])
    assert stats == {"111": {"views": 800, "likes": None, "comments": None},
                     "222": {"views": 55, "likes": None, "comments": None}}
    assert FakeResponse  # (shared fake kept imported for the Router)


# ---------- API & CLI ----------


def test_performance_api(history):
    _seed(history)
    calls = []

    def refresh():
        calls.append(1)
        return {"youtube": 3}

    client = TestClient(create_app(history=history, jobs=JobManager(lambda *a, **k: None), token=TOKEN,
                                   config_status={}, performance=lambda: analyze(history), refresh_stats=refresh))
    report = client.get("/api/performance", headers=AUTH).json()
    assert report["scored_runs"] == 10 and report["dimensions"]["hook"][-1]["status"] == "weak"
    refreshed = client.post("/api/performance/refresh", headers=AUTH).json()
    assert refreshed["updated"] == {"youtube": 3} and calls == [1] and refreshed["report"]["enough_data"]
    assert client.get("/api/performance").status_code == 401

    bare = TestClient(create_app(history=history, jobs=JobManager(lambda *a, **k: None), token=TOKEN,
                                 config_status={}))
    assert bare.get("/api/performance", headers=AUTH).status_code == 501
    # Runs returned to the dashboard carry the view counts.
    assert client.get("/api/runs", headers=AUTH).json()[0]["publishes"][0]["views"] is not None


def test_cli_stats_report(history, tmp_path, monkeypatch, capsys):
    from ai_content_agent import cli

    _seed(history)
    monkeypatch.setenv("HISTORY_DB_PATH", history._db_path)
    monkeypatch.setattr("sys.argv", ["ai-content-agent", "stats", "--no-refresh"])
    cli.main()
    out = capsys.readouterr().out
    assert "Scored runs: 10" in out and "rested (few views)" in out and "too few runs" in out
    assert json.dumps({}) == "{}"

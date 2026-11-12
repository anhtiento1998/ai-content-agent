"""Dashboard-managed schedule: stored settings, topic rotation, live re-arming and the API."""

import pytest
from fakes import FakeText  # noqa: F401  (puts src/ on sys.path)
from fastapi.testclient import TestClient

from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.scheduler import ScheduleManager, ScheduleStore, validate_cron
from ai_content_agent.web.app import create_app
from ai_content_agent.web.jobs import JobManager

TOKEN = "t"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def history(tmp_path):
    return HistoryStore(str(tmp_path / "h.db"))


def test_topics_are_deduplicated_and_rotate_least_recently_used(history):
    store = ScheduleStore(history)
    assert store.add_topics(["Mẹo tiết kiệm điện", "  mẹo  TIẾT kiệm điện ", "", "Chọn dưa hấu", "Ngủ ngon"]) == 3
    first, second, third = (t["id"] for t in store.topics())

    assert store.next_topic()["id"] == first  # never used: in the order added
    store.mark_used(first)
    assert store.next_topic()["id"] == second
    assert store.next_topic(skip=lambda topic: topic == "Chọn dưa hấu")["id"] == third  # dedup skips
    store.mark_used(second)
    store.mark_used(third)
    assert store.next_topic()["id"] == first  # everyone used once: oldest use comes round again
    assert store.topics()[0]["uses"] == 1

    assert store.remove_topic(second) and not store.remove_topic(second)
    assert [t["topic"] for t in store.topics()] == ["Mẹo tiết kiệm điện", "Ngủ ngon"]
    assert store.next_topic(skip=lambda _topic: True) is None


def test_settings_and_topics_survive_a_restart(tmp_path):
    path = str(tmp_path / "h.db")
    store = ScheduleStore(HistoryStore(path))
    store.add_topics(["Một"])
    store.save_settings(cron="30 8 * * mon,fri", platforms=["youtube"], enabled=True)

    reopened = ScheduleStore(HistoryStore(path))
    assert reopened.settings() == {"cron": "30 8 * * mon,fri", "platforms": ["youtube"], "enabled": True}
    assert [t["topic"] for t in reopened.topics()] == ["Một"]


def _manager(history, **kwargs):
    submitted, empties = [], []
    manager = ScheduleManager(ScheduleStore(history), lambda topic, platforms: submitted.append((topic, platforms)),
                              on_empty=empties.append, timezone="Asia/Ho_Chi_Minh", jitter_seconds=600, **kwargs)
    return manager, submitted, empties


def test_manager_arms_fires_and_rearms_without_restart(history):
    manager, submitted, empties = _manager(history, recently_done=lambda topic: topic == "Đã đăng")
    manager.start()
    try:
        assert manager.info()["enabled"] is False and manager.info()["next_run_at"] is None

        with pytest.raises(ValueError, match="platform"):
            manager.update(cron="0 9 * * *", platforms=[], enabled=True)
        with pytest.raises(ValueError, match="cron"):
            manager.update(cron="every day", platforms=["youtube"], enabled=True)

        info = manager.update(cron="0 9 * * *", platforms=["youtube", "youtube"], enabled=True)
        assert info["enabled"] and info["platforms"] == ["youtube"] and info["timezone"] == "Asia/Ho_Chi_Minh"
        job = manager._scheduler.get_job("content-run")
        assert job.trigger.jitter == 600 and job.next_run_time.utcoffset().total_seconds() == 7 * 3600

        manager.fire()  # no topics yet
        assert submitted == [] and "chưa có chủ đề" in empties[0]

        manager.store.add_topics(["Đã đăng", "Mới 1", "Mới 2"])
        info = manager.info()
        assert info["next_topic"] == "Mới 1" and [t["recently_done"] for t in info["topics"]] == [True, False, False]
        manager.fire()
        manager.fire()
        assert submitted == [("Mới 1", ["youtube"]), ("Mới 2", ["youtube"])]
        assert manager.info()["next_topic"] == "Mới 1"  # rotation continues, still skipping the duplicate

        before = manager._scheduler.get_job("content-run").next_run_time
        manager.update(cron="15 20 * * sat", platforms=["youtube"], enabled=True)
        after = manager._scheduler.get_job("content-run").next_run_time
        # Saturday 20:15 plus up to 10 minutes of jitter.
        assert after != before and after.weekday() == 5 and after.hour == 20 and 15 <= after.minute <= 25

        manager.update(cron="15 20 * * sat", platforms=["youtube"], enabled=False)
        assert manager._scheduler.get_job("content-run") is None and manager.info()["cron"] == "15 20 * * sat"
    finally:
        manager.shutdown()


def test_all_topics_recently_done_is_reported(history):
    manager, submitted, empties = _manager(history, recently_done=lambda _topic: True)
    manager.store.add_topics(["Một"])
    manager.fire()
    assert submitted == [] and "Mọi chủ đề" in empties[0]


def test_cron_validation_accepts_day_names():
    assert validate_cron("30 8 * * mon,wed,fri") == "30 8 * * mon,wed,fri"
    with pytest.raises(ValueError, match="5 fields"):
        validate_cron("9 * *")


def test_schedule_api(history):
    manager, submitted, _ = _manager(history)
    manager.start()
    jobs = JobManager(lambda *a, **k: None)
    client = TestClient(create_app(history=history, jobs=jobs, token=TOKEN, config_status={}, schedule=manager))
    try:
        assert client.get("/api/schedule", headers=AUTH).json()["editable"] is True

        added = client.post("/api/schedule/topics", json={"topics": ["Một", "Hai", "một"]}, headers=AUTH).json()
        assert added["added"] == 2 and [t["topic"] for t in added["topics"]] == ["Một", "Hai"]

        bad = client.put("/api/schedule", json={"cron": "nope", "platforms": ["youtube"], "enabled": True},
                         headers=AUTH)
        assert bad.status_code == 422 and "cron" in bad.json()["detail"]
        assert client.put("/api/schedule", json={"cron": "0 9 * * *", "platforms": ["myspace"], "enabled": True},
                          headers=AUTH).status_code == 422

        saved = client.put("/api/schedule", json={"cron": "0 9 * * *", "platforms": ["youtube"], "enabled": True},
                           headers=AUTH).json()
        assert saved["enabled"] and saved["next_run_at"] and saved["next_topic"] == "Một"

        topic_id = saved["topics"][0]["id"]
        after = client.delete(f"/api/schedule/topics/{topic_id}", headers=AUTH).json()
        assert [t["topic"] for t in after["topics"]] == ["Hai"]
        assert client.delete(f"/api/schedule/topics/{topic_id}", headers=AUTH).status_code == 404
        assert client.put("/api/schedule", json={"cron": "", "platforms": [], "enabled": False},
                          headers=AUTH).json()["enabled"] is False
    finally:
        manager.shutdown()
        jobs.shutdown()


def test_schedule_api_is_read_only_without_a_manager(history):
    client = TestClient(create_app(history=history, jobs=JobManager(lambda *a, **k: None), token=TOKEN,
                                   config_status={}))
    assert client.get("/api/schedule", headers=AUTH).json() == {"enabled": False}
    assert client.put("/api/schedule", json={"cron": "0 9 * * *", "platforms": ["youtube"], "enabled": True},
                      headers=AUTH).status_code == 501

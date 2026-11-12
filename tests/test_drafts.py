"""Script desk: write a storyboard, edit it scene by scene, then render exactly that text."""

import random

import pytest
from fakes import FakePublisher, FakeStudio
from fastapi.testclient import TestClient

from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.pipeline.drafts import OPEN, RENDERING, DraftStore, clean_storyboard, estimated_seconds
from ai_content_agent.studio.variation import Variator
from ai_content_agent.web.app import create_app
from ai_content_agent.web.jobs import JobManager

TOKEN = "t"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
EDITED = {
    "title": "  Mẹo  tiết kiệm điện (đã sửa) ",
    "description": "Mô tả mới",
    "hashtags": ["#tietkiemdien", "meo hay", ""],
    "scenes": [
        {"narration": "Câu mở đầu đã sửa.", "visual_prompt": "an electricity bill", "on_screen_text": "Giảm 30%"},
        {"narration": "Cảnh hai thêm mới.", "visual_prompt": "a fan next to an air conditioner"},
    ],
}


def test_clean_storyboard_normalises_and_rejects_bad_edits():
    board = clean_storyboard(EDITED)
    assert board.title == "Mẹo tiết kiệm điện (đã sửa)" and board.hashtags == ["tietkiemdien", "meohay"]
    assert [s.on_screen_text for s in board.scenes] == ["Giảm 30%", ""]
    assert estimated_seconds(board.to_dict()) == pytest.approx(9 / 2.5, abs=0.1)  # 9 words at 2.5 words/s

    for broken, message in [
        ({**EDITED, "scenes": []}, "at least one scene"),
        ({**EDITED, "scenes": [{"narration": " ", "visual_prompt": "x"}]}, "scene 1 narration must not be empty"),
        ({**EDITED, "scenes": [{"narration": "x" * 601, "visual_prompt": "x"}]}, "longer than 600"),
        ({**EDITED, "title": ""}, "title must not be empty"),
        ({**EDITED, "scenes": EDITED["scenes"] * 7}, "at most 12 scenes"),
    ]:
        with pytest.raises(ValueError, match=message):
            clean_storyboard(broken)


@pytest.fixture
def desk(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    drafts = DraftStore(str(tmp_path / "h.db"))
    studio = FakeStudio(str(tmp_path / "run" / "final.mp4"))
    youtube = FakePublisher("youtube")

    def factory(platforms, publish_only=False):
        return ContentPipeline(None if publish_only else studio, [youtube for _ in platforms], history=history,
                               make_thumbnails=False, require_approval=True, variator=Variator(rng=random.Random(3)))

    jobs = JobManager(factory, history=history, drafts=drafts)
    client = TestClient(create_app(history=history, jobs=jobs, token=TOKEN, config_status={},
                                   pipeline_factory=factory, drafts=drafts))
    yield client, jobs, history, drafts, studio
    jobs.shutdown()


def _job(client, jobs, response):
    assert response.status_code == 202, response.text
    jobs.wait(response.json()["id"], timeout=10)
    return client.get(f"/api/jobs/{response.json()['id']}", headers=AUTH).json()


def _write(client, jobs, topic="Tiết kiệm điện"):
    return _job(client, jobs, client.post("/api/runs", json={"topic": topic, "platforms": ["youtube"],
                                                             "script_only": True}, headers=AUTH))


def test_write_edit_render_uses_exactly_the_edited_script(desk):
    client, jobs, history, drafts, studio = desk

    job = _write(client, jobs)
    assert (job["status"], job["kind"], job["draft_id"]) == ("scripted", "script", 1)
    assert studio.calls == 0 and studio.drafts == 1  # only the script was written; nothing rendered yet
    [draft] = client.get("/api/drafts", headers=AUTH).json()
    assert draft["status"] == OPEN and draft["edited"] is False and draft["variation"]["hook"]
    assert draft["storyboard"]["scenes"][0]["narration"] == "Hello world" and draft["estimated_seconds"] > 0

    saved = client.put("/api/drafts/1", json=EDITED, headers=AUTH).json()
    assert saved["edited"] is True and saved["storyboard"]["title"] == "Mẹo tiết kiệm điện (đã sửa)"
    assert len(saved["storyboard"]["scenes"]) == 2

    render = _job(client, jobs, client.post("/api/drafts/1/render", json={}, headers=AUTH))
    assert (render["status"], render["source"], render["draft_id"]) == ("review", "script", 1)
    run = history.get_run(render["run_id"])
    assert run.title == "Mẹo tiết kiệm điện (đã sửa)" and "Câu mở đầu đã sửa." in run.script["script"]
    assert studio.drafts == 1  # the LLM was not asked again
    assert studio.last_plan.hook == draft["variation"]["hook"]  # same plan the script was written under
    assert client.get("/api/drafts", headers=AUTH).json() == []
    assert drafts.get(1).run_id == run.id
    assert client.put("/api/drafts/1", json=EDITED, headers=AUTH).status_code == 409


def test_dry_run_and_failed_renders_leave_the_draft_editable(desk):
    client, jobs, _, drafts, studio = desk
    _write(client, jobs)

    preview = _job(client, jobs, client.post("/api/drafts/1/render", json={"dry_run": True}, headers=AUTH))
    assert preview["status"] == "succeeded" and drafts.get(1).status == OPEN

    studio._fail_stage = "visual"
    failed = _job(client, jobs, client.post("/api/drafts/1/render", json={}, headers=AUTH))
    assert failed["status"] == "failed" and drafts.get(1).status == OPEN


def test_validation_discard_and_missing_drafts(desk):
    client, jobs, *_ = desk
    _write(client, jobs)

    bad = client.put("/api/drafts/1", json={**EDITED, "scenes": [{"narration": "  ", "visual_prompt": "x"}]},
                     headers=AUTH)
    assert bad.status_code == 422 and "scene 1 narration" in bad.json()["detail"]
    assert client.post("/api/drafts/1/render", json={"platforms": ["myspace"]}, headers=AUTH).status_code == 422
    assert client.put("/api/drafts/9", json=EDITED, headers=AUTH).status_code == 404

    assert client.delete("/api/drafts/1", headers=AUTH).json() == {"status": "discarded"}
    assert client.get("/api/drafts", headers=AUTH).json() == []
    assert client.post("/api/drafts/1/render", json={}, headers=AUTH).status_code == 404


def test_duplicate_topic_and_script_failure(desk):
    client, jobs, history, drafts, studio = desk
    _job(client, jobs, client.post("/api/runs", json={"topic": "Đã làm", "platforms": ["youtube"]}, headers=AUTH))
    assert _write(client, jobs, "Đã làm")["status"] == "skipped"

    studio._fail_stage = "script"
    failed = _write(client, jobs, "Chủ đề khác")
    assert (failed["status"], failed["failed_stage"]) == ("failed", "script")
    assert drafts.open_drafts() == [] and history.recent_errors()[0].stage == "script"


def test_interrupted_render_is_editable_again_after_restart(tmp_path):
    from ai_content_agent.studio import Scene, Storyboard

    path = str(tmp_path / "h.db")
    store = DraftStore(path)
    draft_id = store.create("t", "", ["youtube"], Storyboard("T", "", [], [Scene("a", "b")]))
    store.set_status(draft_id, RENDERING)
    assert DraftStore(path).get(draft_id).status == OPEN


def test_script_desk_is_absent_without_a_store(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    client = TestClient(create_app(history=history, jobs=JobManager(lambda *a, **k: None), token=TOKEN,
                                   config_status={}))
    assert client.get("/api/drafts", headers=AUTH).status_code == 501
    assert client.post("/api/runs", json={"topic": "x", "script_only": True}, headers=AUTH).status_code == 501

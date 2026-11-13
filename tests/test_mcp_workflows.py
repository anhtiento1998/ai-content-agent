"""MCP script desk and persistent dashboard schedule, including permission boundaries."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
from fakes import FakePublisher, FakeStudio

from ai_content_agent.config import Config
from ai_content_agent.history import HistoryStore
from ai_content_agent.mcp_server import AgentTools, build_server
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.pipeline.drafts import OPEN, RENDERING, DraftStore, clean_storyboard
from ai_content_agent.pipeline.scheduler import ScheduleManager, ScheduleStore

BOARD = {
    "title": "Kịch bản đã sửa",
    "description": "Mô tả",
    "hashtags": ["#meohay"],
    "scenes": [{"narration": "Đây là lời đọc đã sửa.", "visual_prompt": "a fan", "keywords": "ceiling fan"}],
}


@pytest.fixture
def factory(tmp_path):
    clients = []

    def create(**overrides):
        config = Config(history_db_path=str(tmp_path / "history.db"), **overrides)
        history = HistoryStore(config.history_db_path)
        studio = FakeStudio(str(tmp_path / "render" / "final.mp4"))
        publisher = FakePublisher("youtube")

        def pipeline(platforms, publish_only=False):
            return ContentPipeline(None if publish_only else studio, [publisher for _ in platforms],
                                   history=history, make_thumbnails=False, require_approval=config.require_approval)

        tools = AgentTools(config, pipeline_factory=pipeline, start_worker=False)
        clients.append(tools)
        return tools, studio, publisher

    yield create
    for tools in clients:
        tools.close()


def finish(tools, job):
    tools.jobs.wait(job["id"], timeout=10)
    return tools.job_status(job["id"])


def draft(tools):
    return finish(tools, tools.write_script("Mẹo tiết kiệm điện", platforms=["youtube"]))["draft_id"]


def test_script_edit_render_preserves_text_and_requires_human_review(factory):
    tools, studio, publisher = factory()
    draft_id = draft(tools)
    assert studio.calls == 0 and tools.list_drafts()[0]["id"] == draft_id
    saved = tools.update_draft(draft_id, BOARD)
    assert saved["edited"] and saved["storyboard"]["hashtags"] == ["meohay"]
    assert saved["storyboard"]["scenes"][0]["keywords"] == "ceiling fan"
    assert saved["platforms"] == ["youtube"]
    job = finish(tools, tools.render_draft(draft_id))
    assert job["status"] == "review" and studio.drafts == 1 and publisher.published == []
    run = tools.get_run(job["run_id"])
    assert run["title"] == BOARD["title"] and BOARD["scenes"][0]["narration"] in run["script"]
    assert tools.get_draft(draft_id)["run_id"] == run["run_id"]
    assert tools.list_drafts() == []
    for call in (lambda: tools.update_draft(draft_id, BOARD), lambda: tools.discard_draft(draft_id),
                 lambda: tools.render_draft(draft_id)):
        with pytest.raises(ValueError, match="no longer"):
            call()


def test_dry_render_keeps_draft_editable_and_does_not_publish(factory):
    tools, _, publisher = factory(require_approval=False)
    draft_id = draft(tools)  # writing alone is safe with approval disabled
    with pytest.raises(PermissionError, match="REQUIRE_APPROVAL"):
        tools.render_draft(draft_id)
    assert tools.get_draft(draft_id)["status"] == OPEN
    assert finish(tools, tools.render_draft(draft_id, platforms=[], dry_run=True))["status"] == "succeeded"
    assert tools.get_draft(draft_id)["status"] == OPEN and publisher.published == []
    tools.update_draft(draft_id, BOARD, platforms=[])
    with pytest.raises(ValueError, match="platform"):
        tools.render_draft(draft_id)


def test_owner_permission_allows_render_and_publish(factory):
    tools, _, publisher = factory(require_approval=False, mcp_allow_publish=True)
    assert finish(tools, tools.render_draft(draft(tools)))["status"] == "succeeded"
    assert len(publisher.published) == 1


def test_draft_validation_and_discard(factory):
    tools, _, _ = factory()
    for topic in (" ", "x" * 301):
        with pytest.raises(ValueError, match="topic"):
            tools.write_script(topic)
    with pytest.raises(ValueError, match="Unknown platform"):
        tools.write_script("test", platforms=["unknown"])
    draft_id = draft(tools)
    with pytest.raises(ValueError, match="at least one scene"):
        tools.update_draft(draft_id, {**BOARD, "scenes": []})
    with pytest.raises(ValueError, match="Unknown platform"):
        tools.update_draft(draft_id, BOARD, platforms=["unknown"])
    assert not tools.get_draft(draft_id)["edited"]
    assert tools.discard_draft(draft_id)["status"] == "discarded"
    with pytest.raises(ValueError, match="not found"):
        tools.get_draft(draft_id)
    assert tools.list_drafts() == []


def test_opening_mcp_does_not_reset_dashboard_render(factory):
    tools, _, _ = factory()
    draft_id = draft(tools)
    tools.drafts.claim_render(draft_id)
    other, _, _ = factory()
    assert other.get_draft(draft_id)["status"] == RENDERING
    with pytest.raises(ValueError, match="no longer"):
        other.update_draft(draft_id, BOARD)


def test_only_one_client_can_claim_render(factory):
    tools, _, _ = factory()
    draft_id = draft(tools)
    other = DraftStore(tools.config.history_db_path, recover=False)

    def claim(store):
        try:
            store.claim_render(draft_id)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(claim, [tools.drafts, other])) == [False, True]
    with pytest.raises(ValueError, match="not open"):
        other.update(draft_id, clean_storyboard(BOARD))
    with pytest.raises(ValueError, match="not open"):
        other.discard(draft_id)


def test_schedule_persists_and_dashboard_applies_external_changes(factory):
    tools, _, _ = factory()
    submitted = []
    dashboard = ScheduleManager(ScheduleStore(tools.history), lambda *args: submitted.append(args),
                                timezone=tools.config.schedule_timezone).start()
    try:
        assert dashboard._scheduler.get_job("content-settings-sync") is not None
        added = tools.add_schedule_topics(["Một", "Hai", "  MỘT  "])
        assert added["added"] == 2 and added["executor"] == "dashboard" and added["requires_dashboard"]
        saved = tools.update_schedule("0 9 * * mon,fri", ["youtube", "youtube"], True)
        assert saved["timezone"] == "Asia/Ho_Chi_Minh" and saved["platforms"] == ["youtube"]
        assert tools.schedule._scheduler is None  # no second schedule executor
        dashboard.sync()
        scheduled = dashboard._scheduler.get_job("content-run")
        assert scheduled and scheduled.next_run_time.hour == 9
        dashboard.fire()
        assert submitted == [("Một", ["youtube"])]
        assert tools.get_schedule()["topics"][0]["uses"] == 1
        reopened, _, _ = factory()
        assert reopened.get_schedule()["cron"] == saved["cron"]
        topic_id = saved["topics"][0]["id"]
        assert tools.remove_schedule_topic(topic_id)["next_topic"] == "Hai"
        with pytest.raises(ValueError, match="not found"):
            tools.remove_schedule_topic(topic_id)
        tools.update_schedule("", [], False)
        dashboard.fire()  # stale trigger cannot enqueue a run after MCP disabled it
        assert len(submitted) == 1 and dashboard._scheduler.get_job("content-run") is None
    finally:
        dashboard.shutdown()


def test_schedule_validation_does_not_overwrite_saved_settings(factory):
    tools, _, _ = factory()
    tools.update_schedule("0 9 * * *", ["youtube"], False)
    for cron, platforms in [("bad", ["youtube"]), ("0 9 * * *", []), ("0 9 * * *", ["unknown"])]:
        with pytest.raises(ValueError):
            tools.update_schedule(cron, platforms, True)
    for topics in ([], ["x"] * 501, ["x" * 301]):
        with pytest.raises(ValueError):
            tools.add_schedule_topics(topics)
    assert tools.get_schedule()["cron"] == "0 9 * * *" and not tools.get_schedule()["enabled"]
    assert tools.get_schedule()["topics"] == []


def test_schedule_cannot_bypass_publish_permission(factory):
    tools, _, _ = factory(require_approval=False)
    with pytest.raises(PermissionError, match="REQUIRE_APPROVAL"):
        tools.update_schedule("0 9 * * *", ["youtube"], True)
    tools.schedule.store.save_settings(cron="0 9 * * *", platforms=["youtube"], enabled=True)
    with pytest.raises(PermissionError, match="REQUIRE_APPROVAL"):
        tools.add_schedule_topics(["No unattended post"])
    assert tools.get_schedule()["topics"] == []
    assert not tools.update_schedule("", [], False)["enabled"]
    assert tools.add_schedule_topics(["Safe while paused"])["added"] == 1


def test_sdk_exposes_and_executes_new_tools(factory):
    pytest.importorskip("mcp")
    tools, _, _ = factory()
    server = build_server(tools)
    listed = {tool.name: tool for tool in asyncio.run(server.list_tools())}
    for name in ("write_script", "list_drafts", "get_draft", "update_draft", "discard_draft", "render_draft",
                 "get_schedule", "update_schedule", "add_schedule_topics", "remove_schedule_topic"):
        assert listed[name].description
        schema = getattr(listed[name], "input_schema", None) or getattr(listed[name], "inputSchema", None)
        assert schema and schema["type"] == "object"
    asyncio.run(server.call_tool("add_schedule_topics", {"topics": ["MCP transport"]}))
    assert tools.get_schedule()["next_topic"] == "MCP transport"
    draft_id = draft(tools)
    asyncio.run(server.call_tool("update_draft", {"draft_id": draft_id, "storyboard": BOARD}))
    assert tools.get_draft(draft_id)["edited"]
    with pytest.raises(Exception, match="not found"):
        asyncio.run(server.call_tool("get_draft", {"draft_id": 999}))

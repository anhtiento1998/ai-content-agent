"""P3: cost metering and budget, Claude response handling, ComfyUI engines, MCP tools."""

import asyncio
import json
import types
from pathlib import Path

import pytest
from fakes import FakePublisher, FakeStudio, FakeText

from ai_content_agent.config import Config
from ai_content_agent.costs import CostMeter, PriceBook
from ai_content_agent.history import PENDING, REJECTED, HistoryStore
from ai_content_agent.pipeline.batch import QUEUED, BatchRunner, BatchStore, parse_manifest
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.providers import comfyui_provider
from ai_content_agent.providers.comfyui_provider import ComfyUIImageProvider, ComfyUIVideoProvider, fill_workflow
from ai_content_agent.providers.local_provider import CardImageProvider, SilentVoiceProvider
from ai_content_agent.studio import StudioSettings, StudioStageError, VideoStudio

# ---------- costs ----------


def test_price_lookup_prefix_overrides_and_unknown(tmp_path):
    book = PriceBook()
    assert book.lookup("text", "claude-sonnet-5-5") == {"input": 2.0, "output": 10.0}
    assert book.lookup("text", "gpt-4.1-2026-04-14")["output"] == 8.0  # dated id -> longest known prefix
    assert book.lookup("text", "mystery-model") is None and book.lookup("image", None) is None

    override = tmp_path / "prices.json"
    override.write_text(json.dumps({"text": {"mystery-model": {"input": 1, "output": 2}}}))
    assert PriceBook(str(override)).lookup("text", "mystery-model") == {"input": 1, "output": 2}
    override.write_text(json.dumps({"sound": {}}))
    with pytest.raises(ValueError, match="unknown section"):
        PriceBook(str(override))
    with pytest.raises(FileNotFoundError):
        PriceBook(str(tmp_path / "missing.json"))


def test_meter_prices_merges_and_flags_unpriced():
    meter = CostMeter()
    meter.add_text("claude", "claude-sonnet-5-5", 1_000_000, 100_000)  # $2 + $1
    meter.add_images("imagen", "imagen-4.0-generate-001")
    meter.add_images("imagen", "imagen-4.0-generate-001", 4)  # 5 x $0.04
    meter.add_video("veo", "veo-3.0-generate-001", 8)  # 8 s x $0.40
    meter.add_voice("gemini", "gemini-2.5-flash-preview-tts", 120)  # 2 min x $0.015
    meter.add_images("card", None, 3)  # local engine: free, still priced
    summary = meter.summary()
    assert summary["usd"] == pytest.approx(3.0 + 0.20 + 3.20 + 0.03)
    assert summary["complete"] is True and summary["by_kind"]["image"] == pytest.approx(0.20)
    assert [i["quantity"] for i in summary["items"] if i["provider"] == "imagen"] == [5]

    meter.add_text("muse", "muse-spark-1.1", 500, 500)
    summary = meter.summary()
    assert summary["complete"] is False and summary["usd"] == pytest.approx(6.43)
    assert next(i for i in summary["items"] if i["provider"] == "muse")["usd"] is None


class MeteredText(FakeText):
    name = "gpt"
    _model = "gpt-4.1"

    def complete(self, prompt):
        self.last_usage = {"model": "gpt-4.1", "input_tokens": 1000, "output_tokens": 500}
        return super().complete(prompt)


def test_studio_reports_cost_of_a_render(tmp_path):
    studio = VideoStudio(MeteredText(), CardImageProvider(), SilentVoiceProvider(),
                         StudioSettings(output_dir=str(tmp_path / "out"), music_dir=None))
    _, video = studio.produce("x")

    cost = video.raw["cost"]
    assert cost["usd"] == pytest.approx(1000 * 2 / 1e6 + 500 * 8 / 1e6) and cost["complete"] is True
    kinds = {item["kind"]: item for item in cost["items"]}
    assert kinds["image"]["quantity"] == 2 and kinds["image"]["usd"] == 0.0  # two scenes, free engine
    assert kinds["voice"]["unit"] == "minutes"
    assert json.loads(next((tmp_path / "out").glob("*/provenance.json")).read_text())["cost"] == cost


def test_failed_script_still_reports_what_it_spent(tmp_path):
    class Garbage(MeteredText):
        def complete(self, prompt):
            super().complete(prompt)
            return "not json at all"

    studio = VideoStudio(Garbage(), CardImageProvider(), SilentVoiceProvider(),
                         StudioSettings(output_dir=str(tmp_path / "out"), music_dir=None))
    with pytest.raises(StudioStageError) as failure:
        studio.produce("x")
    assert failure.value.stage == "script" and failure.value.cost["usd"] > 0


class PricedStudio(FakeStudio):
    def __init__(self, video_path, usd=0.5, fail=False):
        super().__init__(video_path)
        self.usd, self.fail = usd, fail

    def _cost(self):
        return {"usd": self.usd, "complete": True, "by_kind": {"image": self.usd},
                "items": [{"kind": "image", "provider": "imagen", "model": "m", "quantity": 1, "unit": "images",
                           "usd": self.usd}]}

    def produce(self, topic, **kwargs):
        if self.fail:
            error = StudioStageError("visual", "scene 1: boom")
            error.cost = self._cost()
            raise error
        storyboard, video = super().produce(topic, **kwargs)
        video.raw = {"cost": self._cost()}
        return storyboard, video


def test_pipeline_records_costs_and_enforces_the_daily_budget(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    studio = PricedStudio(str(tmp_path / "run" / "final.mp4"), usd=0.6)
    pipeline = ContentPipeline(studio, [FakePublisher("youtube")], history=history, make_thumbnails=False,
                               require_approval=True, daily_budget_usd=1.0)

    first = pipeline.run("Một")
    assert first.cost["usd"] == 0.6 and history.get_run(first.run_id).cost_usd == 0.6
    pipeline.run("Hai", dry_run=True)  # dry runs cost money too
    assert history.cost_since(24) == pytest.approx(1.2)

    with pytest.raises(StudioStageError) as stopped:
        pipeline.run("Ba")
    assert stopped.value.stage == "budget" and "$1.00" in str(stopped.value)
    assert studio.calls == 2  # nothing was generated for the refused run
    stats = history.stats()
    assert stats["cost_24h_usd"] == pytest.approx(1.2) and stats["cost_30d_usd"] == pytest.approx(1.2)
    assert history.recent_errors()[0].stage == "budget"


def test_cost_of_a_failed_render_is_recorded(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    pipeline = ContentPipeline(PricedStudio(str(tmp_path / "final.mp4"), usd=0.3, fail=True), [], history=history)
    with pytest.raises(StudioStageError):
        pipeline.run("Một", dry_run=True)
    assert history.cost_since(24) == pytest.approx(0.3)


def test_batch_item_stopped_by_budget_waits_instead_of_failing(tmp_path):
    history = HistoryStore(str(tmp_path / "h.db"))
    store = BatchStore(str(tmp_path / "h.db"))
    studio = PricedStudio(str(tmp_path / "run" / "final.mp4"), usd=2.0)

    def factory(platforms, publish_only=False):
        return ContentPipeline(studio, [FakePublisher("youtube")], history=history, make_thumbnails=False,
                               require_approval=True, daily_budget_usd=1.0)

    runner = BatchRunner(store, factory)
    batch_id = store.create("Lô", ["youtube"], parse_manifest("Một\nHai"))
    runner.process(store.claim_next(batch_id))
    with pytest.raises(StudioStageError):
        runner.process(store.claim_next(batch_id))
    second = store.get(batch_id).items[1]
    assert second.status == QUEUED and second.not_before and "budget" in second.error.lower()


def test_budget_setting_is_validated():
    assert Config().budget() == 0.0 and Config(daily_budget_usd="2,5").budget() == 2.5
    with pytest.raises(ValueError, match="DAILY_BUDGET_USD"):
        Config(daily_budget_usd="nhiều").budget()


# ---------- Claude provider ----------


def _block(kind, **fields):
    return types.SimpleNamespace(type=kind, **fields)


def _message(content, stop_reason="end_turn", model="claude-sonnet-5-5"):
    usage = types.SimpleNamespace(input_tokens=900, output_tokens=300, cache_read_input_tokens=100,
                                  cache_creation_input_tokens=0)
    return types.SimpleNamespace(content=content, stop_reason=stop_reason, model=model, usage=usage,
                                 stop_details=types.SimpleNamespace(category="cyber"))


class FakeAnthropic:
    def __init__(self, reply, beta_error=None):
        self.calls = []
        outer = self

        class Messages:
            def __init__(self, beta):
                self.beta = beta

            def create(self, **kwargs):
                outer.calls.append(("beta" if self.beta else "plain", kwargs))
                if self.beta and beta_error:
                    raise beta_error
                return reply

        self.messages = Messages(False)
        self.beta = types.SimpleNamespace(messages=Messages(True))


def _claude(monkeypatch, client, model="claude-sonnet-5-5"):
    import anthropic

    from ai_content_agent.providers.anthropic_provider import AnthropicProvider

    monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: client)
    return AnthropicProvider("k", model)


def test_claude_reads_text_after_thinking_blocks_and_meters_usage(monkeypatch):
    client = FakeAnthropic(_message([_block("thinking", thinking=""), _block("text", text='{"a":'),
                                     _block("text", text=" 1}")]))
    provider = _claude(monkeypatch, client)

    assert provider.complete("prompt") == '{"a": 1}'
    kind, request = client.calls[0]
    assert kind == "beta" and request["fallbacks"] == "default"
    assert request["betas"] == ["server-side-fallback-2026-07-01"] and request["max_tokens"] == 16000
    assert provider.last_usage == {"model": "claude-sonnet-5-5", "input_tokens": 1000, "output_tokens": 300}


def test_claude_refusal_and_truncation_are_clear_errors(monkeypatch):
    with pytest.raises(RuntimeError, match="refusal: cyber"):
        _claude(monkeypatch, FakeAnthropic(_message([], stop_reason="refusal"))).complete("p")
    with pytest.raises(RuntimeError, match="max_tokens"):
        _claude(monkeypatch, FakeAnthropic(_message([_block("text", text="{")], stop_reason="max_tokens"))).complete("p")


def test_claude_without_fallback_support_uses_the_plain_endpoint(monkeypatch):
    import anthropic
    import httpx

    reply = _message([_block("text", text="ok")], model="claude-haiku-5-5")
    haiku = FakeAnthropic(reply)
    assert _claude(monkeypatch, haiku, "claude-haiku-5-5").complete("p") == "ok"
    assert [kind for kind, _ in haiku.calls] == ["plain"]

    response = httpx.Response(400, request=httpx.Request("POST", "https://example.invalid"))
    error = anthropic.BadRequestError("fallbacks: beta not enabled", response=response, body=None)
    client = FakeAnthropic(_message([_block("text", text="ok")]), beta_error=error)
    provider = _claude(monkeypatch, client)
    assert provider.complete("p") == "ok" and provider.complete("p") == "ok"
    assert [kind for kind, _ in client.calls] == ["beta", "plain", "plain"]  # stops retrying the beta


# ---------- ComfyUI ----------

WORKFLOW = {
    "3": {"class_type": "KSampler", "inputs": {"seed": "{{seed}}", "steps": 20}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": "{{width}}", "height": "{{height}}"}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "{{prompt}}, high quality"}},
}


def test_fill_workflow_keeps_types():
    filled = fill_workflow(WORKFLOW, {"prompt": "a cat", "seed": 7, "width": 720, "height": 1280})
    assert filled["3"]["inputs"]["seed"] == 7 and filled["5"]["inputs"] == {"width": 720, "height": 1280}
    assert filled["6"]["inputs"]["text"] == "a cat, high quality"
    assert WORKFLOW["3"]["inputs"]["seed"] == "{{seed}}"  # the template is not mutated


class FakeComfy:
    def __init__(self, outputs, status=None):
        self.posted, self.views, self.polls = [], [], 0
        self._outputs, self._status = outputs, status or {"status_str": "success", "completed": True}

    def post(self, url, json, timeout):
        self.posted.append(json)
        return types.SimpleNamespace(json=lambda: {"prompt_id": "p1"})

    def get(self, url, params=None, timeout=None):
        if "/history/" in url:
            self.polls += 1
            ready = self.polls > 1
            return types.SimpleNamespace(json=lambda: {"p1": {"status": self._status, "outputs": self._outputs}}
                                         if ready else {})
        self.views.append(params)
        return types.SimpleNamespace(status_code=200, content=b"MEDIA")

    ConnectionError = ConnectionError


def _workflow_file(tmp_path, workflow=WORKFLOW):
    path = tmp_path / "wan22.json"
    path.write_text(json.dumps(workflow))
    return str(path)


def test_comfyui_runs_the_workflow_and_downloads_the_right_output(tmp_path, monkeypatch):
    outputs = {"9": {"images": [{"filename": "preview.png", "subfolder": "", "type": "temp"}],
                     "gifs": [{"filename": "clip_0001.mp4", "subfolder": "video", "type": "output"}]}}
    fake = FakeComfy(outputs)
    monkeypatch.setattr(comfyui_provider, "requests", fake)
    provider = ComfyUIVideoProvider(_workflow_file(tmp_path), "http://gpu-box:8188/", poll_seconds=0)

    provider.generate_clip("a neon street", str(tmp_path / "scene.mp4"))

    sent = fake.posted[0]["prompt"]
    assert sent["6"]["inputs"]["text"] == "a neon street, high quality"
    assert isinstance(sent["3"]["inputs"]["seed"], int) and sent["5"]["inputs"] == {"width": 720, "height": 1280}
    assert fake.views == [{"filename": "clip_0001.mp4", "subfolder": "video", "type": "output"}]
    assert (tmp_path / "scene.mp4").read_bytes() == b"MEDIA"
    assert provider.max_concurrency == 1 and provider._model == "wan22"

    image = ComfyUIImageProvider(_workflow_file(tmp_path), poll_seconds=0)
    image.generate_image("a cat", str(tmp_path / "scene.png"))
    assert fake.views[-1]["filename"] == "preview.png"
    assert fake.posted[-1]["prompt"]["5"]["inputs"] == {"width": 1080, "height": 1920}


def test_comfyui_reports_workflow_problems(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="COMFYUI_WORKFLOW"):
        ComfyUIImageProvider(None)
    with pytest.raises(ValueError, match="prompt"):
        ComfyUIImageProvider(_workflow_file(tmp_path, {"1": {"class_type": "X", "inputs": {}}}))
    with pytest.raises(ValueError, match="API format"):
        ComfyUIImageProvider(_workflow_file(tmp_path, {"nodes": [], "note": "{{prompt}}"}))

    monkeypatch.setattr(comfyui_provider, "requests", FakeComfy({}, {"status_str": "error", "messages": ["OOM"]}))
    with pytest.raises(RuntimeError, match="OOM"):
        ComfyUIImageProvider(_workflow_file(tmp_path), poll_seconds=0).generate_image("x", str(tmp_path / "a.png"))
    monkeypatch.setattr(comfyui_provider, "requests", FakeComfy({"9": {"text": ["done"]}}))
    with pytest.raises(RuntimeError, match="Save Image"):
        ComfyUIImageProvider(_workflow_file(tmp_path), poll_seconds=0).generate_image("x", str(tmp_path / "a.png"))


def test_agent_builds_comfyui_from_config(tmp_path):
    from ai_content_agent.agent import ContentAgent

    config = Config(visual_provider="comfyui-video", comfyui_workflow=_workflow_file(tmp_path),
                    comfyui_url="http://box:8188", text_provider="gemini", google_api_key="k",
                    voice_provider="silent")
    visuals = ContentAgent(config).build_studio()._visuals
    assert isinstance(visuals, ComfyUIVideoProvider) and visuals._url == "http://box:8188"
    assert config.status()["visual_providers"]["comfyui-video"]["ready"] is True
    assert Config().status()["visual_providers"]["comfyui"]["ready"] is False


# ---------- MCP tools ----------


@pytest.fixture
def agent_tools(tmp_path):
    from ai_content_agent.mcp_server import AgentTools

    made = []

    def build(**overrides):
        config = Config(history_db_path=str(tmp_path / "h.db"), **overrides)
        history = HistoryStore(config.history_db_path)
        publishers = {name: FakePublisher(name) for name in ("youtube", "tiktok", "facebook")}
        studio = PricedStudio(str(tmp_path / "run" / "final.mp4"), usd=0.25)

        def factory(platforms, publish_only=False):
            return ContentPipeline(None if publish_only else studio, [publishers[p] for p in platforms],
                                   history=history, make_thumbnails=False,
                                   require_approval=config.require_approval)

        tools = AgentTools(config, pipeline_factory=factory, start_worker=False)
        made.append(tools)
        return tools, publishers

    yield build
    for tools in made:
        tools.close()


def _finish(tools, job):
    tools.jobs.wait(job["id"], timeout=10)
    return tools.job_status(job["id"])


def test_agent_can_produce_inspect_and_reject_but_not_publish(agent_tools):
    tools, publishers = agent_tools()

    with pytest.raises(ValueError, match="platform"):
        tools.produce_video("Chủ đề")
    with pytest.raises(ValueError, match="Unknown platform"):
        tools.produce_video("Chủ đề", platforms=["myspace"])
    job = _finish(tools, tools.produce_video("  Mẹo   tiết kiệm điện ", platforms=["youtube"]))
    assert (job["status"], job["source"], job["topic"], job["cost_usd"]) == ("review", "mcp", "Mẹo tiết kiệm điện", 0.25)

    [pending] = tools.review_queue()
    assert pending["status"] == PENDING and pending["cost_usd"] == 0.25
    assert tools.get_run(pending["run_id"])["script"]
    status = tools.status()
    assert status["pending_review"] == 1 and status["agent_may_publish"] is False
    assert status["cost_24h_usd"] == 0.25

    for call in (lambda: tools.approve_run(pending["run_id"]), lambda: tools.retry_publish(pending["run_id"]),
                 lambda: tools.takedown(pending["run_id"], "youtube")):
        with pytest.raises(PermissionError, match="MCP_ALLOW_PUBLISH"):
            call()
    assert publishers["youtube"].published == []

    assert tools.reject_run(pending["run_id"], reason="Sai chủ đề", reviewer="Claude")["status"] == REJECTED
    log = tools.get_run(pending["run_id"])["review_log"]
    assert (log[0]["actor"], log[0]["note"]) == ("mcp:Claude", "Sai chủ đề")


def test_agent_never_bypasses_the_review_gate(agent_tools):
    tools, publishers = agent_tools(require_approval=False)
    with pytest.raises(PermissionError, match="REQUIRE_APPROVAL"):
        tools.produce_video("Chủ đề", platforms=["youtube"])
    with pytest.raises(PermissionError, match="REQUIRE_APPROVAL"):
        tools.create_batch(["A"], ["youtube"])
    assert _finish(tools, tools.produce_video("Chủ đề", dry_run=True))["status"] == "succeeded"
    assert publishers["youtube"].published == []


def test_owner_can_let_the_agent_publish(agent_tools):
    tools, publishers = agent_tools(mcp_allow_publish=True)
    run_id = _finish(tools, tools.produce_video("Chủ đề", platforms=["youtube"]))["run_id"]

    assert _finish(tools, tools.approve_run(run_id, reviewer="Lan"))["status"] == "succeeded"
    assert len(publishers["youtube"].published) == 1
    assert tools.takedown(run_id, "youtube", reason="thử")["status"] == "taken_down"
    actions = [(e["action"], e["actor"]) for e in tools.get_run(run_id)["review_log"]]
    assert actions == [("approve", "mcp:Lan"), ("takedown", "mcp")]


def test_agent_batches_and_exports(agent_tools, tmp_path):
    tools, _ = agent_tools()
    batch = tools.create_batch(["Một", " ", "Hai"], ["youtube"], name="Tuần 46", style="vui")
    assert batch["total"] == 2 and batch["items"][0]["style"] == "vui"
    assert tools.batch_control(batch["id"], "pause")["status"] == "paused"
    assert tools.worker.step(timeout=10) is False
    tools.batch_control(batch["id"], "resume")
    assert tools.worker.step(timeout=10) and tools.worker.step(timeout=10)
    assert tools.list_batches()[0]["counts"] == {"review": 2}
    with pytest.raises(ValueError, match="not found"):
        tools.batch_control(99, "pause")
    with pytest.raises(FileNotFoundError):  # FakeStudio's run has no timeline.json to export
        tools.export_edit_bundle(tools.review_queue()[0]["run_id"])


def test_mcp_server_exposes_tools_and_readable_errors(agent_tools):
    pytest.importorskip("mcp")
    from ai_content_agent.mcp_server import TOOL_NAMES, build_server

    tools, _ = agent_tools()
    server = build_server(tools)
    listed = asyncio.run(server.list_tools())
    assert {tool.name for tool in listed} == set(TOOL_NAMES)
    assert all(tool.description for tool in listed)

    with pytest.raises(Exception, match="publishing needs a human"):
        asyncio.run(server.call_tool("approve_run", {"run_id": 1}))


def test_project_ships_mcp_config_and_skill():
    root = Path(__file__).resolve().parent.parent
    config = json.loads((root / ".mcp.json").read_text())
    assert config["mcpServers"]["ai-content-agent"] == {"command": "ai-content-agent", "args": ["mcp"]}
    skill = (root / ".claude" / "skills" / "video-factory" / "SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\nname: video-factory\n") and "Do not publish on your own" in skill

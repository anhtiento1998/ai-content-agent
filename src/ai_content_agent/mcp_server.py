"""MCP server: lets an AI agent (Claude Code, Claude Desktop, ...) run the video factory.

Start it with `ai-content-agent mcp` (stdio transport; needs `pip install -e ".[mcp]"`).
The agent can produce videos, run batches, inspect the review queue, read costs
and errors, reject videos and export edit bundles.

Publishing stays a human decision by default: approve / retry / takedown are
refused unless MCP_ALLOW_PUBLISH=true, and producing is refused when
REQUIRE_APPROVAL=false would let a video go live without review. An agent that
writes, renders *and* publishes with nobody looking is exactly the "automated
mass production" platforms penalise.

`AgentTools` holds the tool logic as plain methods (tested without the MCP
SDK); `build_server` registers them. Nothing here writes to stdout — the
stdio transport owns it; logs go to stderr.
"""

from __future__ import annotations

import functools
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Literal

from ai_content_agent.agent import ContentAgent
from ai_content_agent.config import Config
from ai_content_agent.export.capcut import CapCutRefused
from ai_content_agent.export.edit_bundle import EditBundleExporter
from ai_content_agent.history import PENDING, REJECTED, HistoryStore, RunRecord
from ai_content_agent.pipeline.batch import ACTIVE, PAUSED, BatchRunner, BatchStore, ItemSpec, batch_summary
from ai_content_agent.publishers import PUBLISHERS
from ai_content_agent.web.jobs import BatchWorker, JobManager

logger = logging.getLogger(__name__)

INSTRUCTIONS = """Vietnamese-first short-video factory (YouTube Shorts, TikTok, Facebook Reels).

Typical flow: call `status` first (which engines and platforms are ready, budget, queue size) ->
`produce_video` or `create_batch` (returns at once; rendering takes minutes) -> poll `job_status`
about every 30 s -> `review_queue` / `get_run` to inspect the result (script, similarity to earlier
scripts, cost, pronunciation) -> tell the user what is waiting; they approve in the dashboard.

Publishing tools (`approve_run`, `retry_publish`, `takedown`) work only when the owner set
MCP_ALLOW_PUBLISH=true; otherwise report what is ready and let the user approve. Never try to work
around that. `reject_run` is always available for videos that are clearly wrong.
Costs are list-price estimates in USD."""


def _run_summary(run: RunRecord, *, full: bool = False) -> dict:
    script = run.script or {}
    data = {
        "run_id": run.id,
        "title": run.title,
        "topic": run.topic,
        "status": run.status,
        "created_at": run.created_at,
        "platforms": run.platforms,
        "video_path": run.video_path,
        "cost_usd": run.cost_usd,
        "similar_to_run": run.similar_to,
        "similarity": run.similarity,
        "variation": run.variation,
        "published": [
            {"platform": p.platform, "url": p.url, "status": p.status, "taken_down": bool(p.deleted_at)}
            for p in run.publishes
        ],
    }
    if full:
        provenance = run.provenance or {}
        data.update({
            "script": script.get("script"),
            "hashtags": script.get("hashtags"),
            "engines": provenance.get("engines"),
            "music": provenance.get("music"),
            "pronunciation": provenance.get("pronunciation"),
            "cost": provenance.get("cost"),
            "review_log": [asdict(entry) for entry in run.reviews],
        })
    return data


class AgentTools:
    def __init__(
        self,
        config: Config,
        *,
        pipeline_factory: Callable | None = None,
        start_worker: bool = True,
    ) -> None:
        self.config = config
        self._factory = pipeline_factory or ContentAgent(config).build_pipeline
        self.history = HistoryStore(config.history_db_path)
        self.batches = BatchStore(config.history_db_path)
        runner = BatchRunner(self.batches, self._factory)
        self.jobs = JobManager(self._factory, history=self.history, batch_runner=runner)
        self.worker = BatchWorker(self.jobs, runner).start() if start_worker else BatchWorker(self.jobs, runner)

    # ---------- guards ----------

    def _require_publish_permission(self, action: str) -> None:
        if not self.config.mcp_allow_publish:
            raise PermissionError(
                f"{action} is disabled for agents: publishing needs a human. The owner can approve in the "
                "dashboard (`ai-content-agent dashboard`) or CLI, or set MCP_ALLOW_PUBLISH=true to allow it here."
            )

    def _require_review_gate(self, dry_run: bool) -> None:
        if not dry_run and not self.config.require_approval and not self.config.mcp_allow_publish:
            raise PermissionError(
                "REQUIRE_APPROVAL=false would publish this video with no human review. Use dry_run=true, "
                "or the owner must set REQUIRE_APPROVAL=true (recommended) or MCP_ALLOW_PUBLISH=true."
            )

    @staticmethod
    def _platforms(platforms: list[str] | None) -> list[str]:
        chosen = list(dict.fromkeys(platforms or []))
        unknown = [p for p in chosen if p not in PUBLISHERS]
        if unknown:
            raise ValueError(f"Unknown platform(s) {unknown}; choose from {list(PUBLISHERS)}")
        return chosen

    def _run(self, run_id: int) -> RunRecord:
        run = self.history.get_run(run_id)
        if run is None:
            raise ValueError(f"Run #{run_id} not found")
        return run

    # ---------- read ----------

    def status(self) -> dict:
        """Readiness of engines and platforms, queue sizes, spend and safety settings."""

        status = self.config.status()
        stats = self.history.stats()
        return {
            "engines": {"text": status["text_provider"], "visual": status["visual_provider"],
                        "voice": status["voice_provider"]},
            "platforms": {name: info["ready"] for name, info in status["platforms"].items()},
            "platform_notes": {name: info["note"] or info.get("warning") for name, info in status["platforms"].items()
                               if info["note"] or info.get("warning")},
            "require_approval": self.config.require_approval,
            "agent_may_publish": self.config.mcp_allow_publish,
            "max_posts_per_day": self.config.max_posts_per_day,
            "daily_budget_usd": self.config.budget(),
            "cost_24h_usd": stats["cost_24h_usd"],
            "cost_30d_usd": stats["cost_30d_usd"],
            "pending_review": stats["pending_review"],
            "total_runs": stats["total_runs"],
            "errors_last_7_days": stats["errors_last_7_days"],
            "encoder": status["encoder"],
            "music": status["music"],
        }

    def review_queue(self) -> list[dict]:
        """Rendered videos waiting for a human decision."""

        return [_run_summary(run) for run in self.history.pending_runs()]

    def get_run(self, run_id: int) -> dict:
        """Everything about one run: script, engines, cost breakdown, similarity, review log."""

        return _run_summary(self._run(run_id), full=True)

    def recent_runs(self, limit: int = 10) -> list[dict]:
        """Latest runs of any status (pending, published, partial, failed, rejected), newest first."""

        return [_run_summary(run) for run in self.history.recent_runs(limit=max(1, min(limit, 50)))]

    def recent_errors(self, limit: int = 10) -> list[dict]:
        """Latest failures with the stage they happened in (script, voice, visual, render, publish, budget...)."""

        return [asdict(err) for err in self.history.recent_errors(limit=max(1, min(limit, 50)))]

    def job_status(self, job_id: str) -> dict:
        """Progress of a produce / publish job: status, stage, counts, error, cost."""

        job = self.jobs.get(job_id)
        if job is None:
            raise ValueError(f"Job {job_id!r} not found (jobs are kept only while this server runs)")
        return job

    def list_jobs(self) -> list[dict]:
        """Jobs started since this server began, newest first (produce, publish and batch items)."""

        return self.jobs.list()

    # ---------- produce ----------

    def produce_video(self, topic: str, style: str = "", platforms: list[str] | None = None,
                      dry_run: bool = False, force: bool = False) -> dict:
        """Start producing one video. Returns the job at once; poll job_status."""

        topic = " ".join((topic or "").split())
        if not topic:
            raise ValueError("topic must not be empty")
        chosen = self._platforms(platforms)
        if not dry_run and not chosen:
            raise ValueError("choose at least one platform, or set dry_run=true to only render")
        self._require_review_gate(dry_run)
        job = self.jobs.submit(topic[:300], chosen, style=style[:300], dry_run=dry_run, force=force, source="mcp")
        return asdict(job)

    def create_batch(self, topics: list[str], platforms: list[str], name: str = "", style: str = "") -> dict:
        """Queue many topics as one durable batch (one video at a time; survives restarts)."""

        chosen = self._platforms(platforms)
        if not chosen:
            raise ValueError("choose at least one platform")
        self._require_review_gate(dry_run=False)
        items = [ItemSpec(topic=" ".join(str(t).split())[:300], style=style[:300]) for t in topics if str(t).strip()]
        batch_id = self.batches.create(name.strip(), chosen, items)
        return batch_summary(self.batches.get(batch_id))

    def list_batches(self, limit: int = 5) -> list[dict]:
        """Recent batches with per-status counts and each item's status, run id and error."""

        return [batch_summary(batch) for batch in self.batches.list(limit=max(1, min(limit, 20)))]

    def batch_control(self, batch_id: int, action: Literal["pause", "resume", "retry_failed"]) -> dict:
        """Pause or resume a batch, or put its failed items back in the queue."""

        batch = self.batches.get(batch_id, with_items=False)
        if batch is None:
            raise ValueError(f"Batch #{batch_id} not found")
        if action == "pause" and batch.status == ACTIVE:
            self.batches.set_status(batch_id, PAUSED)
        elif action == "resume" and batch.status == PAUSED:
            self.batches.set_status(batch_id, ACTIVE)
        elif action == "retry_failed":
            self.batches.retry_failed(batch_id)
        elif action not in ("pause", "resume"):
            raise ValueError("action must be pause, resume or retry_failed")
        return batch_summary(self.batches.get(batch_id))

    # ---------- review & publish ----------

    def reject_run(self, run_id: int, reason: str = "", reviewer: str = "") -> dict:
        """Reject a pending video so it is never published (always allowed)."""

        run = self._run(run_id)
        if run.status != PENDING:
            raise ValueError(f"Run #{run_id} is {run.status}, not waiting for review")
        self.history.set_run_status(run_id, REJECTED)
        self.history.log_review(run_id, "reject", self._actor(reviewer), note=reason.strip() or None)
        return {"run_id": run_id, "status": REJECTED}

    def approve_run(self, run_id: int, platforms: list[str] | None = None, reviewer: str = "") -> dict:
        """Approve a pending video and publish it. Needs MCP_ALLOW_PUBLISH=true."""

        self._require_publish_permission("approve_run")
        run = self._run(run_id)
        if run.status != PENDING:
            raise ValueError(f"Run #{run_id} is {run.status}, not waiting for review")
        chosen = self._platforms(platforms) or run.platforms
        if not chosen:
            raise ValueError("choose at least one platform")
        return asdict(self.jobs.submit_publish(run.id, run.topic, chosen, source="review",
                                               actor=self._actor(reviewer)))

    def retry_publish(self, run_id: int, platforms: list[str] | None = None, reviewer: str = "") -> dict:
        """Publish again to platforms that failed (live ones are skipped). Needs MCP_ALLOW_PUBLISH=true."""

        self._require_publish_permission("retry_publish")
        run = self._run(run_id)
        if run.status in (PENDING, REJECTED):
            raise ValueError(f"Run #{run_id} is {run.status}; it must be approved first")
        chosen = self._platforms(platforms) or run.platforms
        return asdict(self.jobs.submit_publish(run.id, run.topic, chosen, source="retry",
                                               actor=self._actor(reviewer)))

    def takedown(self, run_id: int, platform: str, reason: str = "", reviewer: str = "") -> dict:
        """Delete the run's post from a platform. Needs MCP_ALLOW_PUBLISH=true."""

        self._require_publish_permission("takedown")
        run = self._run(run_id)
        [chosen] = self._platforms([platform])
        self._factory([chosen], publish_only=True).takedown(
            run.id, chosen, actor=self._actor(reviewer), note=reason.strip() or None)
        return {"run_id": run_id, "platform": chosen, "status": "taken_down"}

    @staticmethod
    def _actor(reviewer: str) -> str:
        name = " ".join((reviewer or "").split())[:60]
        return f"mcp:{name}" if name else "mcp"

    # ---------- export ----------

    def _work_dir(self, run_id: int) -> Path:
        run = self._run(run_id)
        if not run.video_path or not Path(run.video_path).is_file():
            raise FileNotFoundError(f"Video for run #{run_id} is missing: {run.video_path}")
        return Path(run.video_path).parent

    def export_edit_bundle(self, run_id: int) -> dict:
        """FCPXML + SRT + media folder for DaVinci Resolve / Final Cut / any CapCut version."""

        return {"bundle": str(EditBundleExporter().export(self._work_dir(run_id)))}

    def export_capcut(self, run_id: int) -> dict:
        """Editable CapCut desktop draft (CapCut ≤ 9.x, closed). Falls back to an edit bundle if refused."""

        work = self._work_dir(run_id)
        try:
            return {"draft": str(ContentAgent(self.config).capcut_exporter().export(work))}
        except CapCutRefused as exc:
            return {"refused": str(exc), "bundle": str(EditBundleExporter().export(work))}

    def close(self) -> None:
        self.worker.stop()
        self.jobs.shutdown()


TOOL_NAMES = (
    "status", "produce_video", "job_status", "list_jobs", "create_batch", "list_batches", "batch_control",
    "review_queue", "get_run", "recent_runs", "recent_errors", "reject_run", "approve_run", "retry_publish",
    "takedown", "export_edit_bundle", "export_capcut",
)


# Failures the agent should read and react to; anything else is a crash the SDK hides from the model.
_EXPECTED_ERRORS = (ValueError, PermissionError, FileNotFoundError, NotImplementedError)


def build_server(tools: AgentTools):
    try:  # mcp 2.x
        from mcp.server.mcpserver import MCPServer
        from mcp.server.mcpserver.exceptions import ToolError
    except ImportError:
        try:  # mcp 1.x
            from mcp.server.fastmcp import FastMCP as MCPServer
            from mcp.server.fastmcp.exceptions import ToolError
        except ImportError as exc:
            raise RuntimeError('The MCP server needs the "mcp" package: pip install -e ".[mcp]"') from exc

    def readable(method):
        @functools.wraps(method)
        def call(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except _EXPECTED_ERRORS as exc:
                raise ToolError(str(exc)) from exc

        return call

    server = MCPServer("ai-content-agent", instructions=INSTRUCTIONS)
    for name in TOOL_NAMES:
        server.tool(name=name)(readable(getattr(tools, name)))
    return server


def main(config: Config) -> None:
    tools = AgentTools(config)
    try:
        build_server(tools).run("stdio")
    finally:
        tools.close()

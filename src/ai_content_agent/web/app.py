"""FastAPI app for the web dashboard: JSON API under /api plus a static page.

Every /api route requires `Authorization: Bearer <token>`. A token is always
enforced (even on localhost) because the dashboard can publish to real
accounts, and an unauthenticated localhost API is reachable from any web page
the user visits via CSRF / DNS rebinding.
"""

from __future__ import annotations

import secrets
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from ai_content_agent.export.capcut import CapCutExporter, CapCutRefused
from ai_content_agent.export.edit_bundle import EditBundleExporter
from ai_content_agent.history import PENDING, REJECTED, HistoryStore
from ai_content_agent.pipeline.batch import ACTIVE, PAUSED, BatchStore, batch_summary, parse_manifest
from ai_content_agent.pipeline.content_pipeline import ContentPipeline
from ai_content_agent.pipeline.drafts import DISCARDED, OPEN, DraftStore, clean_storyboard
from ai_content_agent.pipeline.scheduler import ScheduleManager
from ai_content_agent.publishers import PUBLISHERS
from ai_content_agent.web.jobs import JobManager

STATIC_DIR = Path(__file__).parent / "static"
Platform = Literal[tuple(PUBLISHERS)]  # type: ignore[valid-type]  # stays in sync with the registry

_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


class RunRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    platforms: list[Platform] = Field(default_factory=list)
    style: str = Field("", max_length=300)
    dry_run: bool = False
    force: bool = False
    script_only: bool = False  # write the storyboard and stop, so it can be edited before rendering

    @model_validator(mode="after")
    def _needs_platform_unless_dry_run(self) -> "RunRequest":
        self.topic = self.topic.strip()
        if not self.topic:
            raise ValueError("topic must not be blank")
        if not self.dry_run and not self.script_only and not self.platforms:
            raise ValueError("choose at least one platform, or enable dry_run")
        self.platforms = list(dict.fromkeys(self.platforms))
        return self


class SceneEdit(BaseModel):
    narration: str = Field(max_length=2000)
    visual_prompt: str = Field(max_length=2000)
    on_screen_text: str = Field("", max_length=300)


class DraftEdit(BaseModel):
    title: str = Field(max_length=300)
    description: str = Field("", max_length=1000)
    hashtags: list[str] = Field(default_factory=list, max_length=20)
    scenes: list[SceneEdit] = Field(min_length=1, max_length=20)


class RenderRequest(BaseModel):
    platforms: list[Platform] = Field(default_factory=list)
    dry_run: bool = False


class BatchRequest(BaseModel):
    name: str = Field("", max_length=120)
    manifest: str = Field(min_length=1, max_length=200_000)
    platforms: list[Platform] = Field(default_factory=list)
    style: str = Field("", max_length=300)


class ReviewerMixin(BaseModel):
    reviewer: str = Field("", max_length=60)

    def actor(self) -> str:
        name = " ".join(self.reviewer.split())
        return f"dashboard:{name}" if name else "dashboard"


class PublishRequest(ReviewerMixin):
    platforms: list[Platform] = Field(default_factory=list)


class RejectRequest(ReviewerMixin):
    reason: str = Field("", max_length=500)


class TakedownRequest(ReviewerMixin):
    platform: Platform
    reason: str = Field("", max_length=500)


class ScheduleUpdate(BaseModel):
    cron: str = Field("", max_length=120)
    platforms: list[Platform] = Field(default_factory=list)
    enabled: bool = False


class ScheduleTopics(BaseModel):
    topics: list[str] = Field(min_length=1, max_length=500)


def create_app(
    *,
    history: HistoryStore,
    jobs: JobManager,
    token: str,
    config_status: dict,
    schedule: ScheduleManager | None = None,
    capcut_exporter: CapCutExporter | None = None,
    pipeline_factory: Callable[..., ContentPipeline] | None = None,
    batches: BatchStore | None = None,
    drafts: DraftStore | None = None,
    performance: Callable[[], dict] | None = None,
    refresh_stats: Callable[[], dict] | None = None,
) -> FastAPI:
    app = FastAPI(title="AI Content Agent", docs_url=None, redoc_url=None, openapi_url=None)
    expected = token.encode()

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update(_SECURITY_HEADERS)
        return response

    def require_token(request: Request) -> None:
        scheme, _, value = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not secrets.compare_digest(value.encode(), expected):
            raise HTTPException(status_code=401, detail="Invalid or missing dashboard token")

    api = APIRouter(prefix="/api", dependencies=[Depends(require_token)])

    @api.get("/stats")
    def stats() -> dict:
        return history.stats()

    @api.get("/runs")
    def runs(limit: int = Query(20, ge=1, le=200)) -> list[dict]:
        return [asdict(run) for run in history.recent_runs(limit=limit)]

    @api.post("/runs", status_code=202)
    def create_run(body: RunRequest) -> dict:
        if body.script_only:
            _drafts()
            return asdict(jobs.submit_script(body.topic, body.platforms, style=body.style, force=body.force))
        job = jobs.submit(body.topic, body.platforms, style=body.style, dry_run=body.dry_run, force=body.force)
        return asdict(job)

    def _run_or_404(run_id: int):
        run = history.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    def _media(path: str | None, media_type: str) -> FileResponse:
        # Paths come from the server's own run record, never from the client.
        if not path or not Path(path).is_file():
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(path, media_type=media_type)

    @api.get("/reviews")
    def reviews() -> list[dict]:
        return [asdict(run) for run in history.pending_runs()]

    @api.get("/runs/{run_id}/video")
    def run_video(run_id: int) -> FileResponse:
        return _media(_run_or_404(run_id).video_path, "video/mp4")

    @api.get("/runs/{run_id}/thumbnail")
    def run_thumbnail(run_id: int) -> FileResponse:
        return _media(_run_or_404(run_id).thumbnail_path, "image/jpeg")

    @api.post("/runs/{run_id}/approve", status_code=202)
    def approve(run_id: int, body: PublishRequest | None = None) -> dict:
        run = _run_or_404(run_id)
        if run.status != PENDING:
            raise HTTPException(status_code=409, detail=f"Run is {run.status}, not waiting for review")
        body = body or PublishRequest()
        platforms = list(dict.fromkeys(body.platforms or run.platforms))
        if not platforms:
            raise HTTPException(status_code=422, detail="choose at least one platform")
        return asdict(jobs.submit_publish(run.id, run.topic, platforms, source="review", actor=body.actor()))

    @api.post("/runs/{run_id}/reject")
    def reject(run_id: int, body: RejectRequest | None = None) -> dict:
        body = body or RejectRequest()
        run = _run_or_404(run_id)
        if run.status != PENDING:
            raise HTTPException(status_code=409, detail=f"Run is {run.status}, not waiting for review")
        history.set_run_status(run.id, REJECTED)
        history.log_review(run.id, "reject", body.actor(), note=body.reason.strip() or None)
        return {"status": REJECTED}

    @api.post("/runs/{run_id}/publish", status_code=202)
    def republish(run_id: int, body: PublishRequest) -> dict:
        """Retry: publish a run to platforms it is not live on yet (live ones are skipped)."""

        run = _run_or_404(run_id)
        if run.status in (PENDING, REJECTED):
            raise HTTPException(status_code=409, detail=f"Run is {run.status}; approve or produce it instead")
        platforms = list(dict.fromkeys(body.platforms or run.platforms))
        if not platforms:
            raise HTTPException(status_code=422, detail="choose at least one platform")
        return asdict(jobs.submit_publish(run.id, run.topic, platforms, source="retry", actor=body.actor()))

    @api.post("/runs/{run_id}/takedown")
    def takedown(run_id: int, body: TakedownRequest) -> dict:
        run = _run_or_404(run_id)
        if pipeline_factory is None:
            raise HTTPException(status_code=501, detail="Takedown is not available on this server")
        try:
            pipeline_factory([body.platform], publish_only=True).takedown(
                run.id, body.platform, actor=body.actor(), note=body.reason.strip() or None
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except Exception as exc:
            history.record_error(run.topic, "takedown", f"{type(exc).__name__}: {exc}", run_id=run.id,
                                 platform=body.platform)
            raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}") from exc
        return {"status": "taken_down", "platform": body.platform}

    def _drafts() -> DraftStore:
        if drafts is None:
            raise HTTPException(status_code=501, detail="The script desk is not available on this server")
        return drafts

    def _open_draft(draft_id: int):
        draft = _drafts().get(draft_id)
        if draft is None or draft.status == DISCARDED:
            raise HTTPException(status_code=404, detail="Draft not found")
        if draft.status != OPEN:
            raise HTTPException(status_code=409, detail=f"Draft is {draft.status}; it can no longer be changed")
        return draft

    @api.get("/drafts")
    def list_drafts() -> list[dict]:
        return [draft.summary() for draft in _drafts().open_drafts()]

    @api.put("/drafts/{draft_id}")
    def save_draft(draft_id: int, body: DraftEdit) -> dict:
        _open_draft(draft_id)
        try:
            storyboard = clean_storyboard(body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        _drafts().update(draft_id, storyboard)
        return _drafts().get(draft_id).summary()

    @api.post("/drafts/{draft_id}/render", status_code=202)
    def render_draft(draft_id: int, body: RenderRequest) -> dict:
        draft = _open_draft(draft_id)
        platforms = list(dict.fromkeys(body.platforms or draft.platforms))
        if not body.dry_run and not platforms:
            raise HTTPException(status_code=422, detail="choose at least one platform, or enable dry_run")
        return asdict(jobs.submit_render(draft, platforms, dry_run=body.dry_run))

    @api.delete("/drafts/{draft_id}")
    def discard_draft(draft_id: int) -> dict:
        _open_draft(draft_id)
        _drafts().set_status(draft_id, DISCARDED)
        return {"status": DISCARDED}

    @api.get("/performance")
    def format_performance() -> dict:
        if performance is None:
            raise HTTPException(status_code=501, detail="Format performance is not available on this server")
        return performance()

    @api.post("/performance/refresh")
    def refresh_performance() -> dict:
        """Read view counts from the platforms now, then return the updated report."""

        if performance is None or refresh_stats is None:
            raise HTTPException(status_code=501, detail="Format performance is not available on this server")
        return {"updated": refresh_stats(), "report": performance()}

    def _batches() -> BatchStore:
        if batches is None:
            raise HTTPException(status_code=501, detail="Batch production is not available on this server")
        return batches

    @api.get("/batches")
    def list_batches(limit: int = Query(10, ge=1, le=50)) -> list[dict]:
        return [batch_summary(b) for b in _batches().list(limit=limit)]

    @api.post("/batches", status_code=201)
    def create_batch(body: BatchRequest) -> dict:
        store = _batches()
        try:
            items = parse_manifest(body.manifest)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Manifest: {exc}") from exc
        if not items:
            raise HTTPException(status_code=422, detail="Manifest has no topics")
        if not body.platforms and any(item.platforms is None for item in items):
            raise HTTPException(status_code=422, detail="choose at least one platform (or set platforms per item)")
        allowed = set(PUBLISHERS)
        for item in items:
            unknown = set(item.platforms or []) - allowed
            if unknown:
                raise HTTPException(status_code=422, detail=f"Unknown platform(s) {sorted(unknown)} for {item.topic!r}")
            if body.style and not item.style:
                item.style = body.style
        batch_id = store.create(body.name.strip(), list(dict.fromkeys(body.platforms)), items)
        return batch_summary(store.get(batch_id))

    def _batch_or_404(batch_id: int):
        batch = _batches().get(batch_id, with_items=False)
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        return batch

    @api.post("/batches/{batch_id}/pause")
    def pause_batch(batch_id: int) -> dict:
        batch = _batch_or_404(batch_id)
        if batch.status == ACTIVE:
            _batches().set_status(batch_id, PAUSED)
        return batch_summary(_batches().get(batch_id))

    @api.post("/batches/{batch_id}/resume")
    def resume_batch(batch_id: int) -> dict:
        batch = _batch_or_404(batch_id)
        if batch.status == PAUSED:
            _batches().set_status(batch_id, ACTIVE)
        return batch_summary(_batches().get(batch_id))

    @api.post("/batches/{batch_id}/retry")
    def retry_batch(batch_id: int) -> dict:
        _batch_or_404(batch_id)
        _batches().retry_failed(batch_id)
        return batch_summary(_batches().get(batch_id))

    @api.get("/errors")
    def errors(limit: int = Query(20, ge=1, le=200)) -> list[dict]:
        return [asdict(err) for err in history.recent_errors(limit=limit)]

    @api.get("/jobs")
    def list_jobs() -> list[dict]:
        return jobs.list()

    @api.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @api.post("/jobs/{job_id}/capcut")
    def export_capcut(job_id: str) -> dict:
        # The work folder comes from the server's own job record, never from the client.
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if not job["video_path"]:
            raise HTTPException(status_code=409, detail="This job has no rendered video to export")
        if capcut_exporter is None:
            raise HTTPException(status_code=501, detail="CapCut export is not available on this server")
        try:
            draft = str(capcut_exporter.export(Path(job["video_path"]).parent))
        except CapCutRefused as exc:
            raise HTTPException(status_code=409, detail=f"{exc} [bundle]") from exc
        except Exception as exc:
            history.record_error(job["topic"], "capcut", f"{type(exc).__name__}: {exc}")
            raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
        jobs.set_capcut_draft(job_id, draft)
        return {"draft": draft}

    @api.post("/jobs/{job_id}/bundle")
    def export_bundle(job_id: str) -> dict:
        """FCPXML + SRT + media folder: works for every editor and CapCut version."""

        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if not job["video_path"]:
            raise HTTPException(status_code=409, detail="This job has no rendered video to export")
        try:
            bundle = str(EditBundleExporter().export(Path(job["video_path"]).parent))
        except Exception as exc:
            history.record_error(job["topic"], "capcut", f"{type(exc).__name__}: {exc}")
            raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
        return {"bundle": bundle}

    @api.get("/config")
    def config() -> dict:
        return config_status

    def _schedule() -> ScheduleManager:
        if schedule is None:
            raise HTTPException(status_code=501, detail="The schedule is not available on this server")
        return schedule

    @api.get("/schedule")
    def schedule_info() -> dict:
        return schedule.info() if schedule is not None else {"enabled": False}

    @api.put("/schedule")
    def update_schedule(body: ScheduleUpdate) -> dict:
        try:
            return _schedule().update(cron=body.cron, platforms=body.platforms, enabled=body.enabled)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @api.post("/schedule/topics")
    def add_schedule_topics(body: ScheduleTopics) -> dict:
        manager = _schedule()
        added = manager.store.add_topics([topic for topic in body.topics if len(topic) <= 300])
        return {**manager.info(), "added": added}

    @api.delete("/schedule/topics/{topic_id}")
    def remove_schedule_topic(topic_id: int) -> dict:
        manager = _schedule()
        if not manager.store.remove_topic(topic_id):
            raise HTTPException(status_code=404, detail="Topic not found")
        return manager.info()

    app.include_router(api)

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app

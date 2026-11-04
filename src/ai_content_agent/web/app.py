"""FastAPI app for the web dashboard: JSON API under /api plus a static page.

Every /api route requires `Authorization: Bearer <token>`. A token is always
enforced (even on localhost) because the dashboard can publish to real
accounts, and an unauthenticated localhost API is reachable from any web page
the user visits via CSRF / DNS rebinding.
"""

from __future__ import annotations

import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.scheduler import TopicRotation
from ai_content_agent.web.jobs import JobManager

STATIC_DIR = Path(__file__).parent / "static"
Platform = Literal["youtube", "tiktok", "facebook", "instagram"]

_SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


class RunRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    platforms: list[Platform] = Field(default_factory=list)
    style: str = Field("", max_length=300)
    dry_run: bool = False
    force: bool = False

    @model_validator(mode="after")
    def _needs_platform_unless_dry_run(self) -> "RunRequest":
        self.topic = self.topic.strip()
        if not self.topic:
            raise ValueError("topic must not be blank")
        if not self.dry_run and not self.platforms:
            raise ValueError("choose at least one platform, or enable dry_run")
        self.platforms = list(dict.fromkeys(self.platforms))
        return self


@dataclass
class ScheduleInfo:
    cron: str
    platforms: list[str]
    rotation: TopicRotation
    scheduler: object


def create_app(
    *,
    history: HistoryStore,
    jobs: JobManager,
    token: str,
    config_status: dict,
    schedule: ScheduleInfo | None = None,
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
        job = jobs.submit(body.topic, body.platforms, style=body.style, dry_run=body.dry_run, force=body.force)
        return asdict(job)

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

    @api.get("/config")
    def config() -> dict:
        return config_status

    @api.get("/schedule")
    def schedule_info() -> dict:
        if schedule is None:
            return {"enabled": False}
        next_run = schedule.scheduler.get_job("content-run").next_run_time
        return {
            "enabled": True,
            "cron": schedule.cron,
            "platforms": schedule.platforms,
            "topics": schedule.rotation.topics,
            "next_topic": schedule.rotation.peek(),
            "next_run_at": next_run.isoformat() if next_run else None,
        }

    app.include_router(api)

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app

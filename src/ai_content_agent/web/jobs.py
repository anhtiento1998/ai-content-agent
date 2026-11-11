"""Background job runner for dashboard-triggered, scheduled and batch pipeline runs.

Three kinds of job share one worker thread: "produce" (render a topic, then
queue it for review or publish it), "publish" (approve or retry an
already-rendered run) and "batch" (one item of a durable batch, fed by
BatchWorker). Serialising keeps API spend and quota predictable. Job state
lives in memory only; durable results are in HistoryStore and BatchStore.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable

from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.batch import BatchItem, BatchRunner
from ai_content_agent.pipeline.content_pipeline import ContentPipeline, RunOutcome
from ai_content_agent.studio import StudioStageError

logger = logging.getLogger(__name__)

# factory(platforms, publish_only=False) -> ContentPipeline
PipelineFactory = Callable[..., ContentPipeline]
_TERMINAL = {"succeeded", "partial", "skipped", "failed", "review"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    id: str
    topic: str
    platforms: list[str]
    style: str
    dry_run: bool
    force: bool
    source: str
    kind: str = "produce"
    run_id: int | None = None
    status: str = "queued"
    created_at: str = field(default_factory=_now)
    started_at: str | None = None
    finished_at: str | None = None
    results: list[dict] = field(default_factory=list)
    video_path: str | None = None
    error: str | None = None
    failed_stage: str | None = None
    stage: str | None = None
    stage_done: int = 0
    stage_total: int = 0
    capcut_draft: str | None = None
    actor: str | None = None
    batch_id: int | None = None
    cost_usd: float | None = None
    cost_complete: bool = True


class JobManager:
    def __init__(
        self,
        pipeline_factory: PipelineFactory,
        *,
        history: HistoryStore | None = None,
        max_jobs: int = 100,
        batch_runner: BatchRunner | None = None,
    ) -> None:
        self._factory = pipeline_factory
        self._history = history
        self._batch_runner = batch_runner
        self._batch_items: dict[str, BatchItem] = {}
        self._max_jobs = max_jobs
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="content-job")
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._futures: dict[str, Future] = {}
        self._lock = threading.Lock()

    def _enqueue(self, job: Job) -> Job:
        with self._lock:
            self._jobs[job.id] = job
            self._evict_finished()
            self._futures[job.id] = self._executor.submit(self._run, job)
        return job

    def submit(
        self,
        topic: str,
        platforms: list[str],
        *,
        style: str = "",
        dry_run: bool = False,
        force: bool = False,
        source: str = "manual",
    ) -> Job:
        return self._enqueue(Job(
            id=uuid.uuid4().hex[:12], topic=topic, platforms=list(platforms), style=style,
            dry_run=dry_run, force=force, source=source,
        ))

    def submit_publish(
        self, run_id: int, topic: str, platforms: list[str], *, source: str = "review", actor: str | None = None
    ) -> Job:
        """Publish an already-rendered run (approve from the review queue, or retry failed platforms).
        `source` review|retry is logged with `actor` in the reviewer audit log."""

        return self._enqueue(Job(
            id=uuid.uuid4().hex[:12], topic=topic, platforms=list(platforms), style="", dry_run=False,
            force=False, source=source, kind="publish", run_id=run_id, actor=actor,
        ))

    def submit_batch_item(self, item: BatchItem) -> Job:
        if self._batch_runner is None:
            raise RuntimeError("This job manager has no batch runner")
        job = Job(
            id=uuid.uuid4().hex[:12], topic=item.topic, platforms=self._batch_runner.platforms_for(item),
            style=item.style, dry_run=False, force=item.force, source="batch", kind="batch", batch_id=item.batch_id,
        )
        self._batch_items[job.id] = item
        return self._enqueue(job)

    def busy(self) -> bool:
        with self._lock:
            return any(job.status in ("queued", "running") for job in self._jobs.values())

    def _evict_finished(self) -> None:
        for job_id in [j.id for j in self._jobs.values() if j.status in _TERMINAL]:
            if len(self._jobs) <= self._max_jobs:
                break
            del self._jobs[job_id]
            self._futures.pop(job_id, None)

    def _run(self, job: Job) -> None:
        job.status = "running"
        job.started_at = _now()

        def progress(stage: str, done: int, total: int) -> None:
            job.stage, job.stage_done, job.stage_total = stage, done, total

        try:
            if job.kind == "batch":
                self._finish(job, self._batch_runner.process(self._batch_items.pop(job.id), progress=progress))
                return
            try:
                pipeline = self._factory(job.platforms, publish_only=job.kind == "publish")
            except Exception as exc:
                job.failed_stage = "setup"
                if self._history:
                    self._history.record_error(job.topic, "setup", f"{type(exc).__name__}: {exc}")
                raise

            if job.kind == "publish":
                outcome = pipeline.publish_run(
                    job.run_id, progress=progress, actor=job.actor,
                    action="approve" if job.source == "review" else "retry",
                )
            else:
                outcome = pipeline.run(
                    job.topic, style=job.style, dry_run=job.dry_run, force=job.force, progress=progress
                )
            self._finish(job, outcome)
        except StudioStageError as exc:
            logger.exception("Job %s failed at stage %s", job.id, exc.stage)
            job.status = "failed"
            job.failed_stage = exc.stage
            job.error = str(exc)
            if exc.cost and exc.cost.get("items"):
                job.cost_usd, job.cost_complete = exc.cost["usd"], exc.cost["complete"]
        except Exception as exc:
            logger.exception("Job %s failed", job.id)
            job.status = "failed"
            job.failed_stage = job.failed_stage or ("publish" if job.kind == "publish" else None)
            job.error = f"{type(exc).__name__}: {exc}"
        finally:
            job.finished_at = _now()

    @staticmethod
    def _finish(job: Job, outcome: RunOutcome) -> None:
        if outcome.skipped:
            job.status = "skipped"
            job.error = "Topic này đã được đăng hoặc đang chờ duyệt — bật “Đăng lại” để bỏ qua kiểm tra trùng."
            return
        job.run_id = outcome.run_id or job.run_id
        if outcome.cost:
            job.cost_usd, job.cost_complete = outcome.cost["usd"], outcome.cost["complete"]
        job.video_path = outcome.video.file_path if outcome.video else None
        job.capcut_draft = outcome.capcut_draft
        job.results = [
            {"platform": r.platform, "remote_id": r.remote_id, "url": r.url, "status": r.status}
            for r in outcome.published
        ]
        if job.dry_run:
            job.status = "succeeded"
        elif outcome.pending_review:
            job.status = "review"
        elif not outcome.published:
            job.status = "failed"
            job.failed_stage = "publish"
            job.error = "Đăng thất bại trên mọi nền tảng — xem mục Lỗi gần đây."
        elif len(outcome.published) < len(job.platforms):
            job.status = "partial"
        else:
            job.status = "succeeded"

    def list(self) -> list[dict]:
        with self._lock:
            return [asdict(job) for job in reversed(self._jobs.values())]

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return asdict(job) if job else None

    def set_capcut_draft(self, job_id: str, path: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].capcut_draft = path

    def wait(self, job_id: str, timeout: float | None = None) -> None:
        self._futures[job_id].result(timeout=timeout)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


class BatchWorker:
    """Feeds runnable batch items to the job manager one at a time, while the dashboard runs.
    Manual and scheduled jobs queued meanwhile run between batch items."""

    def __init__(self, jobs: JobManager, runner: BatchRunner, *, poll_seconds: float = 3.0) -> None:
        self._jobs, self._runner, self._poll = jobs, runner, poll_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="batch-worker", daemon=True)

    def start(self) -> "BatchWorker":
        self._runner.store.recover()
        self._thread.start()
        return self

    def _loop(self) -> None:
        while not self._stop.wait(self._poll):
            try:
                self.step()
            except Exception:
                logger.exception("Batch worker step failed")

    def step(self, *, timeout: float | None = None) -> bool:
        """Run one batch item if one is runnable and no other job is waiting. True if one ran."""

        if self._jobs.busy() or not self._runner.store.has_runnable():
            return False
        item = self._runner.store.claim_next()
        if item is None:
            return False
        job = self._jobs.submit_batch_item(item)
        try:
            self._jobs.wait(job.id, timeout=timeout)
        except Exception:
            pass  # recorded on the job and the batch item
        return True

    def stop(self) -> None:
        self._stop.set()

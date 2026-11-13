"""Wire config -> agent -> job manager -> FastAPI app, then serve with uvicorn."""

from __future__ import annotations

import ipaddress
import logging
import secrets

from ai_content_agent.agent import ContentAgent
from ai_content_agent.config import Config
from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.batch import BatchRunner, BatchStore
from ai_content_agent.pipeline.drafts import DraftStore
from ai_content_agent.pipeline.performance import StatsRefresher
from ai_content_agent.pipeline.scheduler import ScheduleManager, ScheduleStore
from ai_content_agent.web.app import create_app
from ai_content_agent.web.jobs import BatchWorker, JobManager

logger = logging.getLogger(__name__)


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def serve(
    config: Config,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    cron: str | None = None,
    topics: list[str] | None = None,
    platforms: list[str] | None = None,
) -> None:
    import uvicorn

    agent = ContentAgent(config)
    history = HistoryStore(config.history_db_path)
    batches = BatchStore(config.history_db_path)
    runner = BatchRunner(batches, agent.build_pipeline)
    drafts = DraftStore(config.history_db_path)
    jobs = JobManager(agent.build_pipeline, history=history, batch_runner=runner, drafts=drafts,
                      auto_retry_minutes=config.auto_retry_minutes)
    batch_worker = BatchWorker(jobs, runner).start()

    def recently_published(topic: str) -> bool:
        return history.has_recent_topic(topic, within_days=config.dedup_window_days)

    store = ScheduleStore(history)
    if cron:  # command-line flags seed the stored schedule; after that it is edited in the dashboard
        store.add_topics(topics or [])
        store.save_settings(cron=cron, platforms=list(platforms or []), enabled=True)
    schedule = ScheduleManager(
        store,
        lambda topic, chosen: jobs.submit(topic, chosen, source="schedule"),
        recently_done=recently_published,
        on_empty=lambda message: history.record_error("(lịch tự động)", "schedule", message),
        timezone=config.schedule_timezone,
        jitter_seconds=max(0, config.schedule_jitter_minutes) * 60,
        dedup_window_days=config.dedup_window_days,
        state=history,
    ).start()

    stats_refresher = StatsRefresher(agent.refresh_stats, hours=max(0, config.stats_refresh_hours)).start()

    token = config.dashboard_token or secrets.token_urlsafe(24)
    app = create_app(
        history=history,
        jobs=jobs,
        token=token,
        config_status=config.status(),
        schedule=schedule,
        capcut_exporter=agent.capcut_exporter(),
        pipeline_factory=agent.build_pipeline,
        batches=batches,
        drafts=drafts,
        performance=agent.performance,
        refresh_stats=agent.refresh_stats,
    )

    if not _is_loopback(host):
        logger.warning(
            "Dashboard is listening on %s — anyone who can reach this port and has the token can publish. "
            "Put it behind HTTPS (reverse proxy) so the token is not sent in cleartext.",
            host,
        )
    shown_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    if config.dashboard_token:
        print(f"\n  Dashboard: http://{shown_host}:{port}/  (log in with DASHBOARD_TOKEN)\n", flush=True)
    else:
        print(f"\n  Dashboard: http://{shown_host}:{port}/#token={token}\n", flush=True)

    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    finally:
        batch_worker.stop()
        jobs.shutdown()
        schedule.shutdown()
        stats_refresher.stop()

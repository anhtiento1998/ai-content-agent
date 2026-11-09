"""Wire config -> agent -> job manager -> FastAPI app, then serve with uvicorn."""

from __future__ import annotations

import ipaddress
import logging
import secrets

from ai_content_agent.agent import ContentAgent
from ai_content_agent.config import Config
from ai_content_agent.history import HistoryStore
from ai_content_agent.pipeline.scheduler import ALL_TOPICS_USED, TopicRotation, start_background
from ai_content_agent.web.app import ScheduleInfo, create_app
from ai_content_agent.web.jobs import JobManager

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
    jobs = JobManager(agent.build_pipeline, history=history)

    schedule = None
    if cron:
        rotation = TopicRotation(topics or [])

        def recently_published(topic: str) -> bool:
            return history.has_recent_topic(topic, within_days=config.dedup_window_days)

        def _scheduled() -> None:
            topic = rotation.next(skip=recently_published)
            if topic is None:
                message = ALL_TOPICS_USED.format(days=config.dedup_window_days)
                logger.warning(message)
                history.record_error("(lịch tự động)", "schedule", message)
                return
            jobs.submit(topic, platforms or [], source="schedule")

        schedule = ScheduleInfo(
            cron=cron,
            platforms=list(platforms or []),
            rotation=rotation,
            scheduler=start_background(
                _scheduled, cron, timezone=config.schedule_timezone, state=history,
                jitter_seconds=max(0, config.schedule_jitter_minutes) * 60,
            ),
            skip=recently_published,
        )

    token = config.dashboard_token or secrets.token_urlsafe(24)
    app = create_app(
        history=history,
        jobs=jobs,
        token=token,
        config_status=config.status(),
        schedule=schedule,
        capcut_exporter=agent.capcut_exporter(),
        pipeline_factory=agent.build_pipeline,
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
        jobs.shutdown()
        if schedule:
            schedule.scheduler.shutdown(wait=False)

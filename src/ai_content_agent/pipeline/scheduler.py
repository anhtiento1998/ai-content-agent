"""Run the content pipeline on a recurring schedule.

`run_forever` is the standalone CLI mode (blocking). The web dashboard uses
`start_background` instead so the schedule runs inside the dashboard process
and its next run time can be displayed. For the simplest setup, cron a call
to `scripts/run_once.py` and skip this module entirely.
"""

from __future__ import annotations

import logging
import random
import threading
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Callable, Protocol

from ai_content_agent.pipeline.content_pipeline import ContentPipeline

logger = logging.getLogger(__name__)


class TopicRotation:
    def __init__(self, topics: list[str]) -> None:
        if not topics:
            raise ValueError("At least one topic is required")
        self._topics = list(topics)
        self._index = 0
        self._lock = threading.Lock()

    @property
    def topics(self) -> list[str]:
        return list(self._topics)

    def _find(self, skip: Callable[[str], bool], advance: bool) -> str | None:
        with self._lock:
            for offset in range(len(self._topics)):
                position = self._index + offset
                topic = self._topics[position % len(self._topics)]
                if not skip(topic):
                    if advance:
                        self._index = position + 1
                    return topic
            return None

    def peek(self, skip: Callable[[str], bool] = lambda _topic: False) -> str | None:
        return self._find(skip, advance=False)

    def next(self, skip: Callable[[str], bool] = lambda _topic: False) -> str | None:
        """Next topic in rotation that `skip` does not reject (e.g. recently published),
        or None when every topic is rejected."""

        return self._find(skip, advance=True)


ALL_TOPICS_USED = (
    "Mọi chủ đề trong lịch đã được đăng trong {days} ngày qua nên lần chạy này bị bỏ qua — "
    "thêm chủ đề mới hoặc giảm DEDUP_WINDOW_DAYS."
)


# A run missed because the machine slept or was busy still fires when it wakes, if within
# this window; several missed runs collapse into one (APScheduler's default grace is 1 s).
# Runs missed while the app was closed are caught up at the next start, within the same window,
# using the last fire time stored in the history database.
MISFIRE_GRACE_SECONDS = 6 * 3600
LAST_FIRE_KEY = "schedule.last_fire"


class ScheduleState(Protocol):
    def get_meta(self, key: str) -> str | None: ...
    def set_meta(self, key: str, value: str) -> None: ...


def _trigger(cron_expr: str, timezone: str | None, jitter_seconds: int = 0):
    from apscheduler.triggers.cron import CronTrigger

    trigger = CronTrigger.from_crontab(cron_expr, timezone=timezone) if timezone else CronTrigger.from_crontab(cron_expr)
    if jitter_seconds:
        # Posting at exactly the same minute every day is a bot signal; spread each run.
        trigger.jitter = jitter_seconds
    return trigger


def missed_fire_time(
    cron_expr: str, timezone: str | None, last_fire: datetime | None, now: datetime,
    grace_seconds: int = MISFIRE_GRACE_SECONDS,
) -> datetime | None:
    """The latest scheduled time in (last_fire, now] that is at most `grace_seconds` old, or None.
    Without a recorded last fire nothing counts as missed (first start)."""

    if last_fire is None:
        return None
    trigger = _trigger(cron_expr, timezone)
    start = max(last_fire, now - timedelta(seconds=grace_seconds))
    due, fire = None, trigger.get_next_fire_time(None, start)
    while fire is not None and fire <= now:
        if fire > last_fire:
            due = fire
        fire = trigger.get_next_fire_time(fire, fire + timedelta(seconds=1))
    return due


def _with_state(job: Callable[[], None], state: ScheduleState | None) -> Callable[[], None]:
    if state is None:
        return job

    def recorded() -> None:
        state.set_meta(LAST_FIRE_KEY, datetime.now(dt_timezone.utc).isoformat())
        job()

    return recorded


def _schedule(scheduler, job, cron_expr, timezone, state, jitter_seconds) -> None:
    wrapped = _with_state(job, state)
    scheduler.add_job(wrapped, _trigger(cron_expr, timezone, jitter_seconds), id="content-run",
                      misfire_grace_time=MISFIRE_GRACE_SECONDS, coalesce=True)
    if state is None:
        return
    now = datetime.now(dt_timezone.utc)
    stored = state.get_meta(LAST_FIRE_KEY)
    if stored is None:
        state.set_meta(LAST_FIRE_KEY, now.isoformat())  # baseline: later downtime can be detected
        return
    due = missed_fire_time(cron_expr, timezone, datetime.fromisoformat(stored), now)
    if due is not None:
        logger.warning("Scheduled run at %s was missed while the app was closed — running it now", due.isoformat())
        scheduler.add_job(wrapped, "date", run_date=now + timedelta(seconds=random.randint(5, 30)),
                          id="content-catch-up", misfire_grace_time=MISFIRE_GRACE_SECONDS)


def start_background(
    job: Callable[[], None],
    cron_expr: str,
    *,
    timezone: str | None = None,
    state: ScheduleState | None = None,
    jitter_seconds: int = 0,
):
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    _schedule(scheduler, job, cron_expr, timezone, state, jitter_seconds)
    scheduler.start()
    return scheduler


def run_forever(
    pipeline: ContentPipeline,
    topics: list[str],
    *,
    cron_expr: str = "0 9 * * *",
    timezone: str | None = None,
    state: ScheduleState | None = None,
    jitter_seconds: int = 0,
) -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler

    rotation = TopicRotation(topics)
    scheduler = BlockingScheduler()

    def _job() -> None:
        topic = rotation.next(skip=pipeline.is_duplicate)
        if topic is None:
            logger.warning(ALL_TOPICS_USED.format(days=pipeline.dedup_window_days))
            return
        logger.info("Scheduled run for topic=%r", topic)
        try:
            pipeline.run(topic)
        except Exception:
            logger.exception("Scheduled run for topic=%r failed", topic)

    _schedule(scheduler, _job, cron_expr, timezone, state, jitter_seconds)
    logger.info("Scheduler started with cron=%r (%s), %d topics queued", cron_expr, timezone or "local", len(topics))
    scheduler.start()

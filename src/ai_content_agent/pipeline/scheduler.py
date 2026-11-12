"""Run the content pipeline on a recurring schedule.

`run_forever` is the standalone CLI mode (blocking). The web dashboard uses
`start_background` instead so the schedule runs inside the dashboard process
and its next run time can be displayed. For the simplest setup, cron a call
to `scripts/run_once.py` and skip this module entirely.
"""

from __future__ import annotations

import json
import logging
import random
import threading
from contextlib import closing
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


# ---------- dashboard-managed schedule ----------

SETTINGS_KEY = "schedule.settings"
DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def validate_cron(cron_expr: str, timezone: str | None = None) -> str:
    """The expression, stripped, or ValueError. Use day names (mon..sun) for weekdays: APScheduler
    counts numeric weekdays from Monday = 0, unlike classic cron's Sunday = 0."""

    cron_expr = " ".join((cron_expr or "").split())
    if len(cron_expr.split(" ")) != 5:
        raise ValueError("cron needs 5 fields: minute hour day month weekday, e.g. 30 8 * * mon,wed,fri")
    try:
        _trigger(cron_expr, timezone)
    except ValueError as exc:
        raise ValueError(f"invalid cron expression {cron_expr!r}: {exc}") from exc
    return cron_expr


class ScheduleStore:
    """Schedule settings and the topic list, kept in the history database."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS schedule_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        topic_key TEXT NOT NULL UNIQUE,
        added_at TEXT NOT NULL,
        last_used_at TEXT,
        uses INTEGER NOT NULL DEFAULT 0
    );
    """

    def __init__(self, history) -> None:
        self._history = history
        with closing(self._connect()) as conn:
            conn.executescript(self._SCHEMA)

    def _connect(self):
        return self._history._connect()

    @staticmethod
    def _key(topic: str) -> str:
        return " ".join(topic.strip().lower().split())

    def settings(self) -> dict:
        raw = self._history.get_meta(SETTINGS_KEY)
        data = json.loads(raw) if raw else {}
        return {"cron": data.get("cron") or "", "platforms": list(data.get("platforms") or []),
                "enabled": bool(data.get("enabled", False))}

    def save_settings(self, *, cron: str, platforms: list[str], enabled: bool) -> None:
        self._history.set_meta(SETTINGS_KEY, json.dumps({"cron": cron, "platforms": platforms, "enabled": enabled}))

    def topics(self) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, topic, added_at, last_used_at, uses FROM schedule_topics ORDER BY id"
            ).fetchall()
        return [dict(zip(("id", "topic", "added_at", "last_used_at", "uses"), row)) for row in rows]

    def add_topics(self, topics: list[str]) -> int:
        """Add topics not on the list yet (compared ignoring case and spacing). Returns how many were new."""

        added = 0
        now = datetime.now(dt_timezone.utc).isoformat()
        with closing(self._connect()) as conn:
            for topic in topics:
                topic = " ".join(str(topic).split())[:300]
                if not topic:
                    continue
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO schedule_topics (topic, topic_key, added_at) VALUES (?, ?, ?)",
                    (topic, self._key(topic), now),
                )
                added += cursor.rowcount
            conn.commit()
        return added

    def remove_topic(self, topic_id: int) -> bool:
        with closing(self._connect()) as conn:
            removed = conn.execute("DELETE FROM schedule_topics WHERE id = ?", (topic_id,)).rowcount
            conn.commit()
        return bool(removed)

    def next_topic(self, skip: Callable[[str], bool] = lambda _topic: False) -> dict | None:
        """The topic used longest ago (never-used first, then in the order added) that `skip` accepts."""

        ordered = sorted(self.topics(), key=lambda t: (t["last_used_at"] is not None, t["last_used_at"] or "", t["id"]))
        return next((topic for topic in ordered if not skip(topic["topic"])), None)

    def mark_used(self, topic_id: int) -> None:
        with closing(self._connect()) as conn:
            conn.execute("UPDATE schedule_topics SET last_used_at = ?, uses = uses + 1 WHERE id = ?",
                         (datetime.now(dt_timezone.utc).isoformat(), topic_id))
            conn.commit()


class ScheduleManager:
    """The dashboard's schedule: edited at runtime, persisted, and re-armed without a restart.

    `submit(topic, platforms)` starts a run (the dashboard passes its job manager); `recently_done(topic)`
    is the dedup check, so the rotation skips topics published or waiting for review recently.
    """

    def __init__(
        self,
        store: ScheduleStore,
        submit: Callable[[str, list[str]], object],
        *,
        recently_done: Callable[[str], bool] = lambda _topic: False,
        on_empty: Callable[[str], None] = lambda _message: None,
        timezone: str | None = None,
        jitter_seconds: int = 0,
        dedup_window_days: int = 30,
        state: ScheduleState | None = None,
    ) -> None:
        self.store = store
        self._submit = submit
        self._recently_done = recently_done
        self._on_empty = on_empty
        self._timezone = timezone
        self._jitter = jitter_seconds
        self._dedup_days = dedup_window_days
        self._state = state
        self._scheduler = None
        self._lock = threading.Lock()

    def start(self) -> "ScheduleManager":
        from apscheduler.schedulers.background import BackgroundScheduler

        self._scheduler = BackgroundScheduler()
        self._scheduler.start()
        self._arm(catch_up=True)
        return self

    def shutdown(self) -> None:
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    def _arm(self, *, catch_up: bool = False) -> None:
        """(Re)create the cron job from the stored settings."""

        if self._scheduler is None:
            return
        with self._lock:
            for job_id in ("content-run", "content-catch-up"):
                if self._scheduler.get_job(job_id):
                    self._scheduler.remove_job(job_id)
            settings = self.store.settings()
            if not (settings["enabled"] and settings["cron"]):
                return
            if catch_up:
                _schedule(self._scheduler, self.fire, settings["cron"], self._timezone, self._state, self._jitter)
            else:
                self._scheduler.add_job(
                    _with_state(self.fire, self._state), _trigger(settings["cron"], self._timezone, self._jitter),
                    id="content-run", misfire_grace_time=MISFIRE_GRACE_SECONDS, coalesce=True)

    def fire(self) -> None:
        """One scheduled run: take the next topic in rotation and submit it."""

        settings = self.store.settings()
        topic = self.store.next_topic(skip=self._recently_done)
        if topic is None:
            message = (ALL_TOPICS_USED.format(days=self._dedup_days) if self.store.topics()
                       else "Lịch tự động chưa có chủ đề nào — thêm chủ đề ở mục Lịch tự động.")
            logger.warning(message)
            self._on_empty(message)
            return
        self.store.mark_used(topic["id"])
        logger.info("Scheduled run for topic=%r", topic["topic"])
        self._submit(topic["topic"], settings["platforms"])

    def update(self, *, cron: str, platforms: list[str], enabled: bool) -> dict:
        cron = validate_cron(cron, self._timezone) if cron.strip() or enabled else ""
        if enabled and not platforms:
            raise ValueError("choose at least one platform for the schedule")
        self.store.save_settings(cron=cron, platforms=list(dict.fromkeys(platforms)), enabled=enabled)
        self._arm()
        return self.info()

    def info(self) -> dict:
        settings = self.store.settings()
        topics = self.store.topics()
        for topic in topics:
            topic["recently_done"] = bool(self._recently_done(topic["topic"]))
        job = self._scheduler.get_job("content-run") if self._scheduler else None
        upcoming = self.store.next_topic(skip=self._recently_done)
        return {
            "editable": True,
            "enabled": bool(settings["enabled"] and settings["cron"]),
            "cron": settings["cron"],
            "platforms": settings["platforms"],
            "timezone": self._timezone or "local",
            "jitter_minutes": self._jitter // 60,
            "topics": topics,
            "next_topic": upcoming["topic"] if upcoming else None,
            "next_run_at": job.next_run_time.isoformat() if job and job.next_run_time else None,
        }

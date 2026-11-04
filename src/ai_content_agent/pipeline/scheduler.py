"""Run the content pipeline on a recurring schedule.

`run_forever` is the standalone CLI mode (blocking). The web dashboard uses
`start_background` instead so the schedule runs inside the dashboard process
and its next run time can be displayed. For the simplest setup, cron a call
to `scripts/run_once.py` and skip this module entirely.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

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


def start_background(job: Callable[[], None], cron_expr: str):
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler()
    scheduler.add_job(job, CronTrigger.from_crontab(cron_expr), id="content-run")
    scheduler.start()
    return scheduler


def run_forever(pipeline: ContentPipeline, topics: list[str], *, cron_expr: str = "0 9 * * *") -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

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

    scheduler.add_job(_job, CronTrigger.from_crontab(cron_expr))
    logger.info("Scheduler started with cron=%r, %d topics queued", cron_expr, len(topics))
    scheduler.start()

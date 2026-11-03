"""Run the content pipeline on a recurring schedule.

Uses APScheduler so this can run as a long-lived process (systemd service,
Docker container, etc). For a simpler setup, just cron a call to
`scripts/run_once.py` instead and skip this module entirely.
"""

from __future__ import annotations

import logging

from ai_content_agent.pipeline.content_pipeline import ContentPipeline

logger = logging.getLogger(__name__)


def run_forever(pipeline: ContentPipeline, topics: list[str], *, cron_expr: str = "0 9 * * *") -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BlockingScheduler()
    state = {"index": 0}

    def _job() -> None:
        topic = topics[state["index"] % len(topics)]
        state["index"] += 1
        logger.info("Scheduled run for topic=%r", topic)
        pipeline.run(topic)

    scheduler.add_job(_job, CronTrigger.from_crontab(cron_expr))
    logger.info("Scheduler started with cron=%r, %d topics queued", cron_expr, len(topics))
    scheduler.start()

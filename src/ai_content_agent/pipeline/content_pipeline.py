"""Idea -> script -> video -> thumbnail -> publish, end to end.

This is the one place that wires providers and publishers together. Swap
which text/video provider runs, or add another publisher, without touching
anything else in the pipeline.
"""

from __future__ import annotations

import logging
import re

from ai_content_agent.history import HistoryStore
from ai_content_agent.media.thumbnail import generate_thumbnail
from ai_content_agent.providers.base import TextGenerator, VideoGenerator
from ai_content_agent.publishers.base import Publisher, PublishResult

logger = logging.getLogger(__name__)


def _slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^\w]+", "_", text.strip().lower()).strip("_")
    return slug[:max_len] or "video"


class ContentPipeline:
    def __init__(
        self,
        text_generator: TextGenerator,
        video_generator: VideoGenerator,
        publishers: list[Publisher],
        *,
        history: HistoryStore | None = None,
        dedup_window_days: int = 30,
        make_thumbnails: bool = True,
        thumbnail_dir: str = "output/thumbnails",
    ) -> None:
        self._text_generator = text_generator
        self._video_generator = video_generator
        self._publishers = publishers
        self._history = history
        self._dedup_window_days = dedup_window_days
        self._make_thumbnails = make_thumbnails
        self._thumbnail_dir = thumbnail_dir

    def run(self, topic: str, *, style: str = "", dry_run: bool = False, force: bool = False) -> list[PublishResult]:
        if self._history and not force and self._history.has_recent_topic(topic, within_days=self._dedup_window_days):
            logger.warning(
                "Skipping topic=%r — already published within the last %d days (pass force=True to override)",
                topic,
                self._dedup_window_days,
            )
            return []

        logger.info("Generating script for topic=%r via %s", topic, self._text_generator.name)
        script = self._text_generator.generate_script(topic, style=style)

        logger.info("Generating video via %s", self._video_generator.name)
        video = self._video_generator.generate_video(script)

        if self._make_thumbnails:
            try:
                video.thumbnail_path = generate_thumbnail(
                    video.file_path, script.title, f"{self._thumbnail_dir}/{_slugify(script.title)}.jpg"
                )
            except Exception:
                logger.exception("Thumbnail generation failed — continuing without one")

        if dry_run:
            logger.info("Dry run — skipping publish. Script=%s Video=%s", script, video)
            return []

        run_id = self._history.record_run(topic, script, video) if self._history else None

        results = []
        for publisher in self._publishers:
            logger.info("Publishing to %s", publisher.name)
            try:
                result = publisher.publish(video, script)
                results.append(result)
                if self._history and run_id is not None:
                    self._history.record_publish(run_id, result)
            except Exception:
                logger.exception("Publish to %s failed", publisher.name)
        return results

"""Idea -> script -> video -> thumbnail -> publish, end to end.

This is the one place that wires providers and publishers together. Swap
which text/video provider runs, or add another publisher, without touching
anything else in the pipeline.
"""

from __future__ import annotations

import logging

from ai_content_agent.history import HistoryStore
from ai_content_agent.media.thumbnail import generate_thumbnail
from ai_content_agent.providers.base import TextGenerator, VideoGenerator
from ai_content_agent.publishers.base import Publisher, PublishResult
from ai_content_agent.utils import slugify

logger = logging.getLogger(__name__)


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

    @property
    def publisher_names(self) -> list[str]:
        return [p.name for p in self._publishers]

    def is_duplicate(self, topic: str) -> bool:
        return bool(self._history) and self._history.has_recent_topic(topic, within_days=self._dedup_window_days)

    def _record_error(self, topic: str, stage: str, exc: Exception, **kwargs) -> None:
        if self._history:
            self._history.record_error(topic, stage, f"{type(exc).__name__}: {exc}", **kwargs)

    def run(self, topic: str, *, style: str = "", dry_run: bool = False, force: bool = False) -> list[PublishResult]:
        if not force and self.is_duplicate(topic):
            logger.warning(
                "Skipping topic=%r — already published within the last %d days (pass force=True to override)",
                topic,
                self._dedup_window_days,
            )
            return []

        logger.info("Generating script for topic=%r via %s", topic, self._text_generator.name)
        try:
            script = self._text_generator.generate_script(topic, style=style)
        except Exception as exc:
            self._record_error(topic, "script", exc)
            raise

        logger.info("Generating video via %s", self._video_generator.name)
        try:
            video = self._video_generator.generate_video(script)
        except Exception as exc:
            self._record_error(topic, "video", exc)
            raise

        if self._make_thumbnails:
            try:
                video.thumbnail_path = generate_thumbnail(
                    video.file_path, script.title, f"{self._thumbnail_dir}/{slugify(script.title)}.jpg"
                )
            except Exception as exc:
                logger.exception("Thumbnail generation failed — continuing without one")
                self._record_error(topic, "thumbnail", exc)

        if dry_run:
            logger.info("Dry run — skipping publish. Script=%s Video=%s", script, video)
            return []

        run_id = self._history.record_run(topic, script, video) if self._history else None

        results = []
        for publisher in self._publishers:
            logger.info("Publishing to %s", publisher.name)
            try:
                result = publisher.publish(video, script)
            except Exception as exc:
                logger.exception("Publish to %s failed", publisher.name)
                self._record_error(topic, "publish", exc, run_id=run_id, platform=publisher.name)
                continue
            results.append(result)
            if self._history and run_id is not None:
                self._history.record_publish(run_id, result)
        return results

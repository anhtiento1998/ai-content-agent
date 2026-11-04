"""Topic -> studio (storyboard + rendered video) -> thumbnail -> publish.

This is the one place that wires the studio and publishers together. Swap
engines inside the studio, or add another publisher, without touching
anything else in the pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from ai_content_agent.history import HistoryStore
from ai_content_agent.media.thumbnail import generate_thumbnail
from ai_content_agent.providers.base import ScriptResult, VideoResult
from ai_content_agent.publishers.base import Publisher, PublishResult
from ai_content_agent.studio import StudioStageError, VideoStudio

logger = logging.getLogger(__name__)


@dataclass
class RunOutcome:
    skipped: bool = False
    script: ScriptResult | None = None
    video: VideoResult | None = None
    published: list[PublishResult] = field(default_factory=list)


class ContentPipeline:
    def __init__(
        self,
        studio: VideoStudio,
        publishers: list[Publisher],
        *,
        history: HistoryStore | None = None,
        dedup_window_days: int = 30,
        make_thumbnails: bool = True,
    ) -> None:
        self._studio = studio
        self._publishers = publishers
        self._history = history
        self._dedup_window_days = dedup_window_days
        self._make_thumbnails = make_thumbnails

    @property
    def publisher_names(self) -> list[str]:
        return [p.name for p in self._publishers]

    def is_duplicate(self, topic: str) -> bool:
        return bool(self._history) and self._history.has_recent_topic(topic, within_days=self._dedup_window_days)

    def _record_error(self, topic: str, stage: str, exc: Exception, **kwargs) -> None:
        if self._history:
            message = str(exc) if isinstance(exc, StudioStageError) else f"{type(exc).__name__}: {exc}"
            self._history.record_error(topic, stage, message, **kwargs)

    def run(self, topic: str, *, style: str = "", dry_run: bool = False, force: bool = False) -> RunOutcome:
        if not force and self.is_duplicate(topic):
            logger.warning(
                "Skipping topic=%r — already published within the last %d days (pass force=True to override)",
                topic,
                self._dedup_window_days,
            )
            return RunOutcome(skipped=True)

        try:
            storyboard, video = self._studio.produce(topic, style=style)
        except StudioStageError as exc:
            self._record_error(topic, exc.stage, exc)
            raise
        script = storyboard.to_script_result()

        if self._make_thumbnails:
            try:
                video.thumbnail_path = generate_thumbnail(
                    video.file_path, script.title, str(Path(video.file_path).with_name("thumbnail.jpg"))
                )
            except Exception as exc:
                logger.exception("Thumbnail generation failed — continuing without one")
                self._record_error(topic, "thumbnail", exc)

        if dry_run:
            logger.info("Dry run — skipping publish. Video at %s", video.file_path)
            return RunOutcome(script=script, video=video)

        run_id = self._history.record_run(topic, script, video) if self._history else None

        published = []
        for publisher in self._publishers:
            logger.info("Publishing to %s", publisher.name)
            try:
                result = publisher.publish(video, script)
            except Exception as exc:
                logger.exception("Publish to %s failed", publisher.name)
                self._record_error(topic, "publish", exc, run_id=run_id, platform=publisher.name)
                continue
            published.append(result)
            if self._history and run_id is not None:
                self._history.record_publish(run_id, result)
        return RunOutcome(script=script, video=video, published=published)

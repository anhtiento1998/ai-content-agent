"""Idea -> script -> video -> publish, end to end.

This is the one place that wires providers and publishers together. Swap
which text/video provider runs, or add another publisher, without touching
anything else in the pipeline.
"""

from __future__ import annotations

import logging

from ai_content_agent.providers.base import TextGenerator, VideoGenerator
from ai_content_agent.publishers.base import Publisher, PublishResult

logger = logging.getLogger(__name__)


class ContentPipeline:
    def __init__(
        self,
        text_generator: TextGenerator,
        video_generator: VideoGenerator,
        publishers: list[Publisher],
    ) -> None:
        self._text_generator = text_generator
        self._video_generator = video_generator
        self._publishers = publishers

    def run(self, topic: str, *, style: str = "", dry_run: bool = False) -> list[PublishResult]:
        logger.info("Generating script for topic=%r via %s", topic, self._text_generator.name)
        script = self._text_generator.generate_script(topic, style=style)

        logger.info("Generating video via %s", self._video_generator.name)
        video = self._video_generator.generate_video(script)

        if dry_run:
            logger.info("Dry run — skipping publish. Script=%s Video=%s", script, video)
            return []

        results = []
        for publisher in self._publishers:
            logger.info("Publishing to %s", publisher.name)
            try:
                results.append(publisher.publish(video, script))
            except Exception:
                logger.exception("Publish to %s failed", publisher.name)
        return results

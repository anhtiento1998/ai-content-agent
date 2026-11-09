"""Topic -> variation plan -> studio (storyboard + rendered video) -> thumbnail -> review -> publish.

This is the one place that wires the studio and publishers together. With
`require_approval` a rendered run waits in the review queue (status
pending_review) and is published later by `publish_run` — the same method
that retries only the platforms that failed, so a retry never re-renders
or double-posts.

Before rendering, each run gets a VariationPlan (hook, look, voice, music)
rotated against recent runs, and its storyboard is compared with recent
scripts: a near-copy is rewritten once, and the remaining similarity is
stored for the reviewer. A run whose provenance shows unlicensed music is
never published.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ai_content_agent.export.capcut import CapCutExporter
from ai_content_agent.history import FAILED, PARTIAL, PENDING, PUBLISHED, REJECTED, HistoryStore
from ai_content_agent.media.thumbnail import generate_thumbnail
from ai_content_agent.providers.base import ScriptResult, VideoResult
from ai_content_agent.publishers.base import PLATFORM_DAILY_LIMITS, Publisher, PublishRejected, PublishResult
from ai_content_agent.studio import StudioStageError, VideoStudio
from ai_content_agent.studio.provenance import publish_blocker
from ai_content_agent.studio.studio import Checkpoint, Progress
from ai_content_agent.studio.variation import SIMILARITY_THRESHOLD, Variator, most_similar

logger = logging.getLogger(__name__)


def _no_progress(_stage: str, _done: int, _total: int) -> None:
    return None


@dataclass
class RunOutcome:
    skipped: bool = False
    script: ScriptResult | None = None
    video: VideoResult | None = None
    published: list[PublishResult] = field(default_factory=list)
    capcut_draft: str | None = None
    run_id: int | None = None
    pending_review: bool = False
    similarity: float | None = None
    similar_to: int | None = None


class ContentPipeline:
    def __init__(
        self,
        studio: VideoStudio | None,
        publishers: list[Publisher],
        *,
        history: HistoryStore | None = None,
        dedup_window_days: int = 30,
        make_thumbnails: bool = True,
        capcut_exporter: CapCutExporter | None = None,
        require_approval: bool = False,
        max_posts_per_day: int = 0,
        variator: Variator | None = None,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        require_music_license: bool = True,
    ) -> None:
        if require_approval and history is None:
            raise ValueError("require_approval needs a HistoryStore to hold the review queue")
        self._studio = studio
        self._publishers = publishers
        self._history = history
        self._dedup_window_days = dedup_window_days
        self._make_thumbnails = make_thumbnails
        self._capcut_exporter = capcut_exporter
        self._require_approval = require_approval
        self._max_posts_per_day = max_posts_per_day
        self._variator = variator
        self._similarity_threshold = similarity_threshold
        self._require_music_license = require_music_license

    @property
    def history(self) -> HistoryStore | None:
        return self._history

    @property
    def publisher_names(self) -> list[str]:
        return [p.name for p in self._publishers]

    @property
    def dedup_window_days(self) -> int:
        return self._dedup_window_days

    def is_duplicate(self, topic: str) -> bool:
        return bool(self._history) and self._history.has_recent_topic(topic, within_days=self._dedup_window_days)

    def _record_error(self, topic: str, stage: str, exc: Exception, **kwargs) -> None:
        if self._history:
            message = str(exc) if isinstance(exc, StudioStageError) else f"{type(exc).__name__}: {exc}"
            self._history.record_error(topic, stage, message, **kwargs)

    def run(
        self,
        topic: str,
        *,
        style: str = "",
        dry_run: bool = False,
        force: bool = False,
        progress: Progress | None = None,
        checkpoint: Checkpoint | None = None,
    ) -> RunOutcome:
        """Produce a video for `topic`; then queue it for review, or publish it right away.
        `progress(stage, done, total)` reports script -> assets -> render -> publish.
        `checkpoint` lets a batch resume a crashed run without paying for finished steps."""

        report = progress or _no_progress
        if self._studio is None:
            raise ValueError("This pipeline was built publish-only; it cannot produce videos")
        if not force and self.is_duplicate(topic):
            logger.warning(
                "Skipping topic=%r — already published or awaiting review within the last %d days "
                "(pass force=True to override)",
                topic,
                self._dedup_window_days,
            )
            return RunOutcome(skipped=True)

        plan = None
        if self._variator:
            music = getattr(self._studio, "music", None)
            recent = self._history.recent_variations() if self._history else []
            plan = self._variator.plan(recent, music.usable_tracks() if music else [])
        corpus = self._history.recent_scripts() if self._history and self._similarity_threshold else []

        def review(candidate) -> str | None:
            run_id, score = most_similar(candidate.to_script_result().script, corpus)
            if run_id is not None and score >= self._similarity_threshold:
                logger.warning("Script is %.0f%% similar to run #%s", score * 100, run_id)
                return dict(corpus)[run_id]
            return None

        try:
            storyboard, video = self._studio.produce(
                topic, style=style, progress=report, plan=plan, checkpoint=checkpoint,
                review=review if corpus else None,
            )
        except StudioStageError as exc:
            self._record_error(topic, exc.stage, exc)
            raise
        script = storyboard.to_script_result()
        # Compared like for like with history.recent_scripts(): description + narration.
        similar_to, similarity = most_similar(script.script, corpus) if corpus else (None, 0.0)
        raw = video.raw or {}

        if self._make_thumbnails:
            try:
                video.thumbnail_path = generate_thumbnail(
                    video.file_path, script.title, str(Path(video.file_path).with_name("thumbnail.jpg"))
                )
            except Exception as exc:
                logger.exception("Thumbnail generation failed — continuing without one")
                self._record_error(topic, "thumbnail", exc)

        capcut_draft = None
        if self._capcut_exporter:
            try:
                capcut_draft = str(self._capcut_exporter.export(Path(video.file_path).parent))
                logger.info("CapCut draft written to %s", capcut_draft)
            except Exception as exc:
                logger.exception("CapCut export failed — continuing without a draft")
                self._record_error(topic, "capcut", exc)

        outcome = RunOutcome(script=script, video=video, capcut_draft=capcut_draft,
                             similarity=round(similarity, 3) if similar_to else None, similar_to=similar_to)
        if dry_run:
            logger.info("Dry run — skipping review and publish. Video at %s", video.file_path)
            return outcome

        if self._history:
            outcome.run_id = self._history.record_run(
                topic, script, video, status=PENDING, platforms=self.publisher_names,
                variation=raw.get("variation") or (plan.to_dict() if plan else None),
                provenance=raw.get("provenance"), similarity=outcome.similarity, similar_to=similar_to,
            )
        if self._require_approval:
            logger.info("Run #%s is waiting for review: %s", outcome.run_id, video.file_path)
            outcome.pending_review = True
            return outcome

        blocker = publish_blocker(raw.get("provenance"), require_license=self._require_music_license)
        if blocker:
            self._block(outcome.run_id, topic, blocker)
            return outcome
        outcome.published = self._publish(outcome.run_id, topic, script, video, report)
        return outcome

    def _block(self, run_id: int | None, topic: str, message: str) -> None:
        logger.error(message)
        if self._history:
            self._history.record_error(topic, "publish", message, run_id=run_id)
            if run_id is not None and self._history.get_run(run_id).status == PENDING:
                self._history.set_run_status(run_id, FAILED)

    def publish_run(
        self, run_id: int, *, progress: Progress | None = None, actor: str | None = None, action: str = "approve"
    ) -> RunOutcome:
        """Publish an already-rendered run to this pipeline's platforms (approve or retry).
        Platforms the run is already live on are skipped, never re-posted. With `actor`, the
        decision is written to the reviewer audit log."""

        if self._history is None:
            raise ValueError("publish_run needs a HistoryStore")
        run = self._history.get_run(run_id)
        if run is None:
            raise ValueError(f"Run #{run_id} not found")
        if run.status == REJECTED:
            raise ValueError(f"Run #{run_id} was rejected; produce the topic again instead")
        if not run.video_path or not Path(run.video_path).is_file():
            raise FileNotFoundError(f"Video for run #{run_id} is missing: {run.video_path}")
        blocker = publish_blocker(run.provenance, require_license=self._require_music_license)
        if blocker:
            self._history.record_error(run.topic, "publish", blocker, run_id=run_id)
            raise ValueError(blocker)

        script, video = run.script_result(), run.video_result()
        try:
            from ai_content_agent.media.ffmpeg import probe_video

            video.width, video.height, video.duration_seconds = probe_video(video.file_path)
        except Exception:
            logger.warning("Could not read duration of %s", video.file_path, exc_info=True)

        targets = sorted(set(run.platforms) | set(self.publisher_names))
        self._history.set_run_platforms(run_id, targets)
        if actor:
            for platform in self.publisher_names:
                self._history.log_review(run_id, action, actor, platform=platform)
        published = self._publish(run_id, run.topic, script, video, progress or _no_progress)
        return RunOutcome(script=script, video=video, published=published, run_id=run_id)

    def takedown(self, run_id: int, platform: str, *, actor: str | None = None, note: str | None = None) -> None:
        """Delete the run's live post on `platform` and mark it taken down."""

        if self._history is None:
            raise ValueError("takedown needs a HistoryStore")
        record = self._history.live_publish(run_id, platform)
        if record is None:
            raise ValueError(f"Run #{run_id} is not live on {platform}")
        publisher = next((p for p in self._publishers if p.name == platform), None)
        if publisher is None:
            raise ValueError(f"No {platform} publisher configured")
        publisher.delete(record.remote_id)
        self._history.mark_taken_down(run_id, platform)
        if actor:
            self._history.log_review(run_id, "takedown", actor, note=note, platform=platform)
        logger.info("Took down run #%s on %s (%s)", run_id, platform, record.remote_id)

    def _publish(
        self, run_id: int | None, topic: str, script: ScriptResult, video: VideoResult, report: Progress
    ) -> list[PublishResult]:
        results: list[PublishResult] = []
        total = len(self._publishers)
        report("publish", 0, total)
        for done, publisher in enumerate(self._publishers, 1):
            existing = self._history.live_publish(run_id, publisher.name) if self._history and run_id else None
            if existing:
                logger.info("Run #%s already live on %s — not re-posting", run_id, publisher.name)
                results.append(PublishResult(platform=existing.platform, remote_id=existing.remote_id,
                                             url=existing.url, status=existing.status))
                report("publish", done, total)
                continue
            cap_message = self._daily_cap_message(publisher.name)
            if cap_message:
                logger.warning(cap_message)
                if self._history:
                    self._history.record_error(topic, "publish", cap_message, run_id=run_id, platform=publisher.name)
                report("publish", done, total)
                continue

            tracked = self._history is not None and run_id is not None
            recovered = self._recover_unrecorded(run_id, publisher, script) if tracked else None
            if recovered:
                results.append(recovered)
                self._history.record_publish(run_id, recovered)
                report("publish", done, total)
                continue

            logger.info("Publishing to %s", publisher.name)
            attempt = self._history.begin_attempt(run_id, publisher.name) if tracked else None
            try:
                result = publisher.publish(video, script)
            except Exception as exc:
                logger.exception("Publish to %s failed", publisher.name)
                if attempt:
                    # A refusal before upload cannot have left a copy behind; anything else might have.
                    self._history.finish_attempt(attempt, "rejected" if isinstance(exc, PublishRejected) else "error")
                self._record_error(topic, "publish", exc, run_id=run_id, platform=publisher.name)
                report("publish", done, total)
                continue
            results.append(result)
            if tracked:
                self._history.record_publish(run_id, result)
                self._history.finish_attempt(attempt, "ok")
            report("publish", done, total)

        if self._history and run_id is not None:
            run = self._history.get_run(run_id)
            live = {p.platform for p in run.publishes if p.deleted_at is None}
            wanted = set(run.platforms) or set(self.publisher_names)
            status = PUBLISHED if wanted <= live else PARTIAL if live else FAILED
            self._history.set_run_status(run_id, status)
        return results

    def _recover_unrecorded(self, run_id: int, publisher: Publisher, script: ScriptResult) -> PublishResult | None:
        """After an attempt whose outcome is unknown, ask the platform whether the post exists already."""

        since = self._history.uncertain_attempt_since(run_id, publisher.name)
        if not since:
            return None
        try:
            found = publisher.find_existing(script, datetime.fromisoformat(since))
        except Exception:
            logger.warning("Could not check %s for an earlier upload of run #%s", publisher.name, run_id, exc_info=True)
            return None
        if found:
            logger.info("Run #%s was already uploaded to %s (%s) — recording it instead of re-posting",
                        run_id, publisher.name, found.remote_id)
        return found

    def _daily_cap_message(self, platform: str) -> str | None:
        """Why `platform` cannot take another post right now, or None. MAX_POSTS_PER_DAY applies
        on top of each platform's own hard limit."""

        if not self._history:
            return None
        used = self._history.publishes_in_last_day(platform)
        if self._max_posts_per_day and used >= self._max_posts_per_day:
            return f"Daily cap of {self._max_posts_per_day} posts on {platform} reached (MAX_POSTS_PER_DAY)"
        limit = PLATFORM_DAILY_LIMITS.get(platform)
        if limit and used >= limit:
            return f"{platform} allows at most {limit} API posts per 24 h — limit reached"
        return None

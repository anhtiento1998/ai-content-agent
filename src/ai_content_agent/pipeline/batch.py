"""Batch production: a manifest of topics -> a durable queue in the history database.

A manifest is JSON Lines, a JSON array, or plain text (one topic per line,
lines starting with # ignored). JSON items take:

    {"topic": "...", "style": "...", "platforms": ["youtube"], "force": false}

Every item is a row in SQLite, so nothing is lost when the app closes or
crashes: items left "running" go back to the queue at the next start and
resume from their checkpoint (saved storyboard and scene files are reused).
One item failing never stops the batch. Rate limits and other transient
errors re-queue the item with exponential backoff, up to MAX_ATTEMPTS.

The worker processes one item at a time — in the dashboard through the same
single job thread as every other job, so a batch never multiplies API spend
or provider concurrency.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from ai_content_agent.pipeline.content_pipeline import ContentPipeline, RunOutcome
from ai_content_agent.studio.studio import Checkpoint, StudioStageError, _is_transient

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 60
MAX_ITEMS = 500

QUEUED, RUNNING, DONE, REVIEW, SKIPPED, FAILED = "queued", "running", "done", "review", "skipped", "failed"
ACTIVE, PAUSED, FINISHED = "active", "paused", "finished"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    platforms TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS batch_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES batches(id),
    position INTEGER NOT NULL,
    topic TEXT NOT NULL,
    style TEXT NOT NULL DEFAULT '',
    platforms TEXT,
    force INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    not_before TEXT,
    run_id INTEGER,
    error TEXT,
    checkpoint TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_batch_items_batch ON batch_items (batch_id, status);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ItemSpec:
    topic: str
    style: str = ""
    platforms: list[str] | None = None
    force: bool = False


def parse_manifest(text: str) -> list[ItemSpec]:
    """Items from JSON Lines, a JSON array, or one topic per line."""

    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        entries = json.loads(stripped)
    else:
        entries = []
        for number, line in enumerate(stripped.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("{"):
                try:
                    entries.append(json.loads(line))
                except ValueError as exc:
                    raise ValueError(f"line {number}: invalid JSON ({exc})") from exc
            else:
                entries.append(line)

    items = []
    for index, entry in enumerate(entries, 1):
        if isinstance(entry, str):
            entry = {"topic": entry}
        if not isinstance(entry, dict) or not str(entry.get("topic", "")).strip():
            raise ValueError(f"item {index}: needs a non-empty \"topic\"")
        platforms = entry.get("platforms")
        if platforms is not None and not (isinstance(platforms, list) and all(isinstance(p, str) for p in platforms)):
            raise ValueError(f"item {index}: \"platforms\" must be a list of names")
        items.append(ItemSpec(
            topic=" ".join(str(entry["topic"]).split())[:300],
            style=str(entry.get("style") or "")[:300],
            platforms=platforms,
            force=bool(entry.get("force", False)),
        ))
    if len(items) > MAX_ITEMS:
        raise ValueError(f"a batch holds at most {MAX_ITEMS} items, got {len(items)}")
    return items


def load_manifest(path: str) -> list[ItemSpec]:
    return parse_manifest(Path(path).read_text(encoding="utf-8-sig"))


@dataclass
class BatchItem:
    id: int
    batch_id: int
    position: int
    topic: str
    style: str
    platforms: list[str] | None
    force: bool
    status: str
    attempts: int
    not_before: str | None
    run_id: int | None
    error: str | None
    checkpoint: dict | None
    updated_at: str


@dataclass
class Batch:
    id: int
    name: str
    platforms: list[str]
    status: str
    created_at: str
    counts: dict = field(default_factory=dict)
    items: list[BatchItem] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


_ITEM_COLUMNS = ("id, batch_id, position, topic, style, platforms, force, status, attempts, not_before, run_id,"
                 " error, checkpoint, updated_at")


def _item(row) -> BatchItem:
    (item_id, batch_id, position, topic, style, platforms, force, status, attempts, not_before, run_id, error,
     checkpoint, updated_at) = row
    return BatchItem(item_id, batch_id, position, topic, style, json.loads(platforms) if platforms else None,
                     bool(force), status, attempts, not_before, run_id, error,
                     json.loads(checkpoint) if checkpoint else None, updated_at)


class BatchStore:
    """Batch tables, kept in the same SQLite file as the run history."""

    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._lock = threading.Lock()
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, timeout=10)

    def create(self, name: str, platforms: list[str], items: list[ItemSpec]) -> int:
        if not items:
            raise ValueError("the manifest has no topics")
        now = _now()
        with closing(self._connect()) as conn:
            batch_id = conn.execute(
                "INSERT INTO batches (name, platforms, status, created_at) VALUES (?, ?, ?, ?)",
                (name[:120] or f"Lô {now[:16]}", json.dumps(platforms), ACTIVE, now),
            ).lastrowid
            conn.executemany(
                "INSERT INTO batch_items (batch_id, position, topic, style, platforms, force, status, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [(batch_id, i, spec.topic, spec.style, json.dumps(spec.platforms) if spec.platforms is not None else None,
                  int(spec.force), QUEUED, now) for i, spec in enumerate(items, 1)],
            )
            conn.commit()
        return batch_id

    def get(self, batch_id: int, *, with_items: bool = True) -> Batch | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT id, name, platforms, status, created_at FROM batches WHERE id = ?",
                               (batch_id,)).fetchone()
            if row is None:
                return None
            batch = Batch(row[0], row[1], json.loads(row[2]), row[3], row[4])
            batch.counts = dict(conn.execute(
                "SELECT status, COUNT(*) FROM batch_items WHERE batch_id = ? GROUP BY status", (batch_id,)
            ).fetchall())
            if with_items:
                batch.items = [_item(r) for r in conn.execute(
                    f"SELECT {_ITEM_COLUMNS} FROM batch_items WHERE batch_id = ? ORDER BY position", (batch_id,)
                ).fetchall()]
        return batch

    def list(self, limit: int = 20) -> list[Batch]:
        with closing(self._connect()) as conn:
            ids = [r[0] for r in conn.execute("SELECT id FROM batches ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
        return [self.get(batch_id) for batch_id in ids]

    def set_status(self, batch_id: int, status: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("UPDATE batches SET status = ? WHERE id = ?", (status, batch_id))
            conn.commit()

    def retry_failed(self, batch_id: int) -> int:
        with closing(self._connect()) as conn:
            count = conn.execute(
                "UPDATE batch_items SET status = ?, attempts = 0, not_before = NULL, error = NULL, updated_at = ?"
                " WHERE batch_id = ? AND status = ?", (QUEUED, _now(), batch_id, FAILED)
            ).rowcount
            if count:
                conn.execute("UPDATE batches SET status = ? WHERE id = ?", (ACTIVE, batch_id))
            conn.commit()
        return count

    def recover(self) -> int:
        """Items left running by a crash or shutdown go back to the queue (their checkpoint is kept)."""

        with closing(self._connect()) as conn:
            count = conn.execute("UPDATE batch_items SET status = ?, updated_at = ? WHERE status = ?",
                                 (QUEUED, _now(), RUNNING)).rowcount
            conn.commit()
        if count:
            logger.info("Re-queued %d batch item(s) interrupted by the last shutdown", count)
        return count

    def claim_next(self, batch_id: int | None = None) -> BatchItem | None:
        """Mark the next runnable item of an active batch as running and return it."""

        now = _now()
        where = "AND b.id = ?" if batch_id is not None else ""
        params = (ACTIVE, QUEUED, now, *([batch_id] if batch_id is not None else []))
        with self._lock, closing(self._connect()) as conn:
            row = conn.execute(
                f"SELECT {', '.join('i.' + c.strip() for c in _ITEM_COLUMNS.split(','))} FROM batch_items i"
                f" JOIN batches b ON b.id = i.batch_id"
                f" WHERE b.status = ? AND i.status = ? AND (i.not_before IS NULL OR i.not_before <= ?) {where}"
                f" ORDER BY b.id, i.position LIMIT 1",
                params,
            ).fetchone()
            if row is None:
                return None
            item = _item(row)
            conn.execute("UPDATE batch_items SET status = ?, attempts = attempts + 1, updated_at = ? WHERE id = ?",
                         (RUNNING, now, item.id))
            conn.commit()
        item.status, item.attempts = RUNNING, item.attempts + 1
        return item

    def has_runnable(self) -> bool:
        with closing(self._connect()) as conn:
            return conn.execute(
                "SELECT 1 FROM batch_items i JOIN batches b ON b.id = i.batch_id"
                " WHERE b.status = ? AND i.status = ? AND (i.not_before IS NULL OR i.not_before <= ?) LIMIT 1",
                (ACTIVE, QUEUED, _now()),
            ).fetchone() is not None

    def save_checkpoint(self, item_id: int, checkpoint: Checkpoint) -> None:
        data = json.dumps({"storyboard": checkpoint.storyboard, "work_dir": checkpoint.work_dir}, ensure_ascii=False)
        with closing(self._connect()) as conn:
            conn.execute("UPDATE batch_items SET checkpoint = ?, updated_at = ? WHERE id = ?", (data, _now(), item_id))
            conn.commit()

    def finish(self, item: BatchItem, status: str, *, run_id: int | None = None, error: str | None = None,
               retry_in: float | None = None) -> None:
        not_before = (datetime.now(timezone.utc) + timedelta(seconds=retry_in)).isoformat() if retry_in else None
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE batch_items SET status = ?, run_id = COALESCE(?, run_id), error = ?, not_before = ?,"
                " updated_at = ? WHERE id = ?",
                (status, run_id, (error or None) and error[:2000], not_before, _now(), item.id),
            )
            open_items = conn.execute("SELECT COUNT(*) FROM batch_items WHERE batch_id = ? AND status IN (?, ?)",
                                      (item.batch_id, QUEUED, RUNNING)).fetchone()[0]
            if not open_items:
                conn.execute("UPDATE batches SET status = ? WHERE id = ? AND status = ?",
                             (FINISHED, item.batch_id, ACTIVE))
            conn.commit()


PipelineFactory = Callable[..., ContentPipeline]


class BatchRunner:
    """Runs one claimed item through a pipeline and records the outcome on the item."""

    def __init__(self, store: BatchStore, pipeline_factory: PipelineFactory, *,
                 max_attempts: int = MAX_ATTEMPTS, backoff_seconds: float = BACKOFF_SECONDS) -> None:
        self.store = store
        self._factory = pipeline_factory
        self._max_attempts = max_attempts
        self._backoff = backoff_seconds

    def platforms_for(self, item: BatchItem) -> list[str]:
        if item.platforms is not None:
            return item.platforms
        batch = self.store.get(item.batch_id, with_items=False)
        return batch.platforms if batch else []

    def process(self, item: BatchItem, *, progress=None) -> RunOutcome | None:
        saved = item.checkpoint or {}
        checkpoint = Checkpoint(storyboard=saved.get("storyboard"), work_dir=saved.get("work_dir"),
                                save=lambda cp: self.store.save_checkpoint(item.id, cp))
        try:
            pipeline = self._factory(self.platforms_for(item))
            outcome = pipeline.run(item.topic, style=item.style, force=item.force, progress=progress,
                                   checkpoint=checkpoint)
        except Exception as exc:
            cause = exc.__cause__ if isinstance(exc, StudioStageError) and exc.__cause__ else exc
            message = str(exc) if isinstance(exc, StudioStageError) else f"{type(exc).__name__}: {exc}"
            if _is_transient(cause) and item.attempts < self._max_attempts:
                delay = self._backoff * 2 ** (item.attempts - 1)
                logger.warning("Batch item #%s hit a transient error (%s); retrying in %.0fs", item.id, message, delay)
                self.store.finish(item, QUEUED, error=message, retry_in=delay)
            else:
                logger.error("Batch item #%s failed: %s", item.id, message)
                self.store.finish(item, FAILED, error=message)
            raise
        if outcome.skipped:
            self.store.finish(item, SKIPPED, error="Chủ đề đã đăng hoặc đang chờ duyệt gần đây")
        elif outcome.pending_review:
            self.store.finish(item, REVIEW, run_id=outcome.run_id)
        else:
            self.store.finish(item, DONE, run_id=outcome.run_id)
        return outcome

    def run_all(self, batch_id: int | None = None, *, stop: threading.Event | None = None,
                on_item: Callable[[BatchItem, str], None] | None = None) -> None:
        """Process items until none are runnable (CLI). Items waiting on backoff are waited for."""

        while not (stop and stop.is_set()):
            item = self.store.claim_next(batch_id)
            if item is None:
                if not self._waiting(batch_id):
                    return
                time.sleep(2)
                continue
            try:
                self.process(item)
                status = "ok"
            except Exception:
                status = "error"
            if on_item:
                on_item(item, status)

    def _waiting(self, batch_id: int | None) -> bool:
        batches = [self.store.get(batch_id)] if batch_id is not None else self.store.list(limit=50)
        return any(b and b.status == ACTIVE and b.counts.get(QUEUED) for b in batches)


def batch_summary(batch: Batch) -> dict:
    data = asdict(batch)
    data["total"] = batch.total
    for item in data["items"]:
        item.pop("checkpoint", None)
    return data


__all__ = [
    "ACTIVE", "PAUSED", "FINISHED", "QUEUED", "RUNNING", "DONE", "REVIEW", "SKIPPED", "FAILED",
    "Batch", "BatchItem", "BatchRunner", "BatchStore", "ItemSpec", "batch_summary", "load_manifest",
    "parse_manifest",
]

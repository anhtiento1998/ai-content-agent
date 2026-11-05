"""SQLite-backed run history — the review queue, topic dedup, per-platform
publish log (with takedowns), stage error log, and dashboard statistics.

A run is recorded when its video is rendered (dry runs excepted), together
with the script and target platforms, so it can be approved, published,
retried on failed platforms or taken down later without re-rendering.
Run status: pending_review → (rejected | published | partial | failed).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ai_content_agent.providers.base import ScriptResult, VideoResult
from ai_content_agent.publishers.base import PublishResult

PENDING = "pending_review"
REJECTED = "rejected"
PUBLISHED = "published"
PARTIAL = "partial"
FAILED = "failed"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    title TEXT NOT NULL,
    video_path TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    platform TEXT NOT NULL,
    remote_id TEXT NOT NULL,
    url TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES runs(id),
    topic TEXT NOT NULL,
    stage TEXT NOT NULL,
    platform TEXT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_topic ON runs (topic);
CREATE INDEX IF NOT EXISTS idx_publishes_run ON publishes (run_id);
"""

# Columns added after the first release; ALTERed into existing databases.
# Older rows were only ever recorded when published, hence the 'published' default.
_MIGRATIONS = {
    "runs": {
        "status": "TEXT NOT NULL DEFAULT 'published'",
        "platforms": "TEXT NOT NULL DEFAULT '[]'",
        "script_json": "TEXT",
        "thumbnail_path": "TEXT",
        "decided_at": "TEXT",
    },
    "publishes": {
        "status": "TEXT",
        "deleted_at": "TEXT",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _since(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


@dataclass
class PublishRecord:
    platform: str
    remote_id: str
    url: str | None
    created_at: str
    status: str | None = None
    deleted_at: str | None = None


@dataclass
class RunRecord:
    id: int
    topic: str
    title: str
    video_path: str | None
    created_at: str
    status: str = PUBLISHED
    platforms: list[str] = field(default_factory=list)
    thumbnail_path: str | None = None
    script: dict | None = None
    publishes: list[PublishRecord] = field(default_factory=list)

    def script_result(self) -> ScriptResult:
        data = self.script or {}
        return ScriptResult(
            title=data.get("title", self.title), script=data.get("script", ""), hashtags=data.get("hashtags", [])
        )

    def video_result(self) -> VideoResult:
        return VideoResult(file_path=self.video_path or "", thumbnail_path=self.thumbnail_path)


@dataclass
class ErrorRecord:
    id: int
    run_id: int | None
    topic: str
    stage: str
    platform: str | None
    message: str
    created_at: str


_RUN_COLUMNS = "id, topic, title, video_path, created_at, status, platforms, thumbnail_path, script_json"
_PUBLISH_COLUMNS = "run_id, platform, remote_id, url, created_at, status, deleted_at"


def _run_from_row(row) -> RunRecord:
    *base, status, platforms, thumbnail, script_json = row
    return RunRecord(
        *base,
        status=status,
        platforms=json.loads(platforms or "[]"),
        thumbnail_path=thumbnail,
        script=json.loads(script_json) if script_json else None,
    )


class HistoryStore:
    def __init__(self, db_path: str = "data/history.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            for table, columns in _MIGRATIONS.items():
                existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
                for name, ddl in columns.items():
                    if name not in existing:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, timeout=10)

    @staticmethod
    def _normalize(topic: str) -> str:
        return " ".join(topic.strip().lower().split())

    # ---------- dedup ----------

    def has_recent_topic(self, topic: str, *, within_days: int = 30) -> bool:
        """True if the topic was published (and not taken down) or is awaiting review recently.
        Runs whose every publish failed, or that were rejected, can be produced again."""

        cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT 1 FROM runs r
                WHERE r.topic = ? AND r.created_at >= ?
                  AND (r.status = ? OR EXISTS (
                        SELECT 1 FROM publishes p WHERE p.run_id = r.id AND p.deleted_at IS NULL))
                LIMIT 1
                """,
                (self._normalize(topic), cutoff, PENDING),
            ).fetchone()
        return row is not None

    # ---------- runs ----------

    def record_run(
        self,
        topic: str,
        script: ScriptResult,
        video: VideoResult,
        *,
        status: str = PENDING,
        platforms: list[str] | None = None,
    ) -> int:
        script_json = json.dumps(
            {"title": script.title, "script": script.script, "hashtags": script.hashtags}, ensure_ascii=False
        )
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "INSERT INTO runs (topic, title, video_path, created_at, status, platforms, script_json, thumbnail_path)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self._normalize(topic), script.title, video.file_path, _now(), status,
                    json.dumps(list(platforms or [])), script_json, video.thumbnail_path,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_run(self, run_id: int) -> RunRecord | None:
        with closing(self._connect()) as conn:
            row = conn.execute(f"SELECT {_RUN_COLUMNS} FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            run = _run_from_row(row)
            run.publishes = self._publishes_for(conn, [run.id])[run.id]
        return run

    def set_run_status(self, run_id: int, status: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("UPDATE runs SET status = ?, decided_at = ? WHERE id = ?", (status, _now(), run_id))
            conn.commit()

    def set_run_platforms(self, run_id: int, platforms: list[str]) -> None:
        with closing(self._connect()) as conn:
            conn.execute("UPDATE runs SET platforms = ? WHERE id = ?", (json.dumps(platforms), run_id))
            conn.commit()

    def _runs_where(self, where: str, params: tuple, limit: int) -> list[RunRecord]:
        with closing(self._connect()) as conn:
            runs = [
                _run_from_row(row)
                for row in conn.execute(
                    f"SELECT {_RUN_COLUMNS} FROM runs {where} ORDER BY id DESC LIMIT ?", (*params, limit)
                ).fetchall()
            ]
            if runs:
                publishes = self._publishes_for(conn, [run.id for run in runs])
                for run in runs:
                    run.publishes = publishes[run.id]
        return runs

    def recent_runs(self, limit: int = 20) -> list[RunRecord]:
        return self._runs_where("", (), limit)

    def pending_runs(self, limit: int = 50) -> list[RunRecord]:
        return self._runs_where("WHERE status = ?", (PENDING,), limit)

    # ---------- publishes ----------

    @staticmethod
    def _publishes_for(conn, run_ids: list[int]) -> dict[int, list[PublishRecord]]:
        result: dict[int, list[PublishRecord]] = {run_id: [] for run_id in run_ids}
        if run_ids:
            placeholders = ",".join("?" * len(run_ids))
            for run_id, *publish in conn.execute(
                f"SELECT {_PUBLISH_COLUMNS} FROM publishes WHERE run_id IN ({placeholders}) ORDER BY id", run_ids
            ).fetchall():
                result[run_id].append(PublishRecord(*publish))
        return result

    def record_publish(self, run_id: int, result: PublishResult) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO publishes (run_id, platform, remote_id, url, created_at, status) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, result.platform, result.remote_id, result.url, _now(), result.status),
            )
            conn.commit()

    def live_publish(self, run_id: int, platform: str) -> PublishRecord | None:
        """The run's current (not taken down) publish on `platform`, if any."""

        with closing(self._connect()) as conn:
            row = conn.execute(
                f"SELECT {_PUBLISH_COLUMNS} FROM publishes WHERE run_id = ? AND platform = ? AND deleted_at IS NULL"
                " ORDER BY id DESC LIMIT 1",
                (run_id, platform),
            ).fetchone()
        return PublishRecord(*row[1:]) if row else None

    def mark_taken_down(self, run_id: int, platform: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE publishes SET deleted_at = ? WHERE run_id = ? AND platform = ? AND deleted_at IS NULL",
                (_now(), run_id, platform),
            )
            conn.commit()

    def publishes_in_last_day(self, platform: str) -> int:
        with closing(self._connect()) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM publishes WHERE platform = ? AND created_at >= ?", (platform, _since(24))
            ).fetchone()[0]

    # ---------- errors & stats ----------

    def record_error(
        self, topic: str, stage: str, message: str, *, run_id: int | None = None, platform: str | None = None
    ) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO errors (run_id, topic, stage, platform, message, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, self._normalize(topic), stage, platform, message[:2000], _now()),
            )
            conn.commit()

    def recent_errors(self, limit: int = 20) -> list[ErrorRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, run_id, topic, stage, platform, message, created_at FROM errors ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [ErrorRecord(*row) for row in rows]

    def stats(self) -> dict:
        with closing(self._connect()) as conn:
            total_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM runs WHERE status = ?", (PENDING,)).fetchone()[0]
            by_platform = dict(
                conn.execute(
                    "SELECT platform, COUNT(*) FROM publishes WHERE deleted_at IS NULL GROUP BY platform"
                ).fetchall()
            )
            errors_7d = conn.execute("SELECT COUNT(*) FROM errors WHERE created_at >= ?", (_since(24 * 7),)).fetchone()[0]
            last_run_at = conn.execute("SELECT MAX(created_at) FROM runs").fetchone()[0]
        return {
            "total_runs": total_runs,
            "pending_review": pending,
            "total_publishes": sum(by_platform.values()),
            "publishes_by_platform": by_platform,
            "errors_last_7_days": errors_7d,
            "last_run_at": last_run_at,
        }

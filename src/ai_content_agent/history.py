"""SQLite-backed run history — avoids posting the same topic twice, logs
failures per stage, and backs the CLI `history` command and web dashboard.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ai_content_agent.providers.base import ScriptResult, VideoResult
from ai_content_agent.publishers.base import PublishResult

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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PublishRecord:
    platform: str
    remote_id: str
    url: str | None
    created_at: str


@dataclass
class RunRecord:
    id: int
    topic: str
    title: str
    video_path: str | None
    created_at: str
    publishes: list[PublishRecord] = field(default_factory=list)


@dataclass
class ErrorRecord:
    id: int
    run_id: int | None
    topic: str
    stage: str
    platform: str | None
    message: str
    created_at: str


class HistoryStore:
    def __init__(self, db_path: str = "data/history.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    @staticmethod
    def _normalize(topic: str) -> str:
        return " ".join(topic.strip().lower().split())

    def has_recent_topic(self, topic: str, *, within_days: int = 30) -> bool:
        """True only if the topic was successfully published somewhere recently,
        so a run whose every publish failed can be retried without --force."""

        cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT 1 FROM runs r JOIN publishes p ON p.run_id = r.id
                WHERE r.topic = ? AND r.created_at >= ? LIMIT 1
                """,
                (self._normalize(topic), cutoff),
            ).fetchone()
        return row is not None

    def record_run(self, topic: str, script: ScriptResult, video: VideoResult) -> int:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "INSERT INTO runs (topic, title, video_path, created_at) VALUES (?, ?, ?, ?)",
                (self._normalize(topic), script.title, video.file_path, _now()),
            )
            conn.commit()
            return cursor.lastrowid

    def record_publish(self, run_id: int, result: PublishResult) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO publishes (run_id, platform, remote_id, url, created_at) VALUES (?, ?, ?, ?, ?)",
                (run_id, result.platform, result.remote_id, result.url, _now()),
            )
            conn.commit()

    def record_error(
        self, topic: str, stage: str, message: str, *, run_id: int | None = None, platform: str | None = None
    ) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO errors (run_id, topic, stage, platform, message, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, self._normalize(topic), stage, platform, message[:2000], _now()),
            )
            conn.commit()

    def recent_runs(self, limit: int = 20) -> list[RunRecord]:
        with closing(self._connect()) as conn:
            runs = [
                RunRecord(*row)
                for row in conn.execute(
                    "SELECT id, topic, title, video_path, created_at FROM runs ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            ]
            if runs:
                by_id = {run.id: run for run in runs}
                placeholders = ",".join("?" * len(by_id))
                for run_id, *publish in conn.execute(
                    f"SELECT run_id, platform, remote_id, url, created_at FROM publishes "
                    f"WHERE run_id IN ({placeholders}) ORDER BY id",
                    list(by_id),
                ).fetchall():
                    by_id[run_id].publishes.append(PublishRecord(*publish))
        return runs

    def recent_errors(self, limit: int = 20) -> list[ErrorRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, run_id, topic, stage, platform, message, created_at FROM errors ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [ErrorRecord(*row) for row in rows]

    def stats(self) -> dict:
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        with closing(self._connect()) as conn:
            total_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            by_platform = dict(
                conn.execute("SELECT platform, COUNT(*) FROM publishes GROUP BY platform").fetchall()
            )
            errors_7d = conn.execute("SELECT COUNT(*) FROM errors WHERE created_at >= ?", (week_ago,)).fetchone()[0]
            last_run_at = conn.execute("SELECT MAX(created_at) FROM runs").fetchone()[0]
        return {
            "total_runs": total_runs,
            "total_publishes": sum(by_platform.values()),
            "publishes_by_platform": by_platform,
            "errors_last_7_days": errors_7d,
            "last_run_at": last_run_at,
        }

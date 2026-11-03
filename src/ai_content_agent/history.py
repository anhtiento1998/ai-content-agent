"""SQLite-backed run history — avoids posting the same topic twice in a row
and gives a queryable log of what was generated/published and when.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
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

CREATE INDEX IF NOT EXISTS idx_runs_topic ON runs (topic);
"""


@dataclass
class RunRecord:
    id: int
    topic: str
    title: str
    video_path: str | None
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
        cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT 1 FROM runs WHERE topic = ? AND created_at >= ? LIMIT 1",
                (self._normalize(topic), cutoff),
            ).fetchone()
        return row is not None

    def record_run(self, topic: str, script: ScriptResult, video: VideoResult) -> int:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "INSERT INTO runs (topic, title, video_path, created_at) VALUES (?, ?, ?, ?)",
                (self._normalize(topic), script.title, video.file_path, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            return cursor.lastrowid

    def record_publish(self, run_id: int, result: PublishResult) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO publishes (run_id, platform, remote_id, url, created_at) VALUES (?, ?, ?, ?, ?)",
                (run_id, result.platform, result.remote_id, result.url, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def recent_runs(self, limit: int = 20) -> list[RunRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, topic, title, video_path, created_at FROM runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [RunRecord(*row) for row in rows]

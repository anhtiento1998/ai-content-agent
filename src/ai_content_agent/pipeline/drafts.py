"""Script desk: storyboards written but not rendered yet, kept for a human to edit.

The cheap step (one LLM call) happens first; the reviewer fixes wording,
facts, on-screen text or image prompts scene by scene; only then are voices
and visuals — the expensive steps — generated, from exactly the edited text.
Drafts live in the history database, so they survive restarts. Rendering a
draft reuses the variation plan it was written under (its hook is already in
the text) and links the draft to the run it became.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_content_agent.studio.storyboard import MAX_SCENES, WORDS_PER_SECOND, Scene, Storyboard
from ai_content_agent.studio.vi_text import nfc

OPEN, RENDERING, RENDERED, DISCARDED = "open", "rendering", "rendered", "discarded"
MAX_NARRATION, MAX_PROMPT, MAX_OVERLAY, MAX_TITLE = 600, 800, 60, 100

_SCHEMA = """
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    style TEXT NOT NULL DEFAULT '',
    platforms TEXT NOT NULL DEFAULT '[]',
    storyboard TEXT NOT NULL,
    variation TEXT,
    similarity REAL,
    similar_to INTEGER,
    cost_usd REAL,
    status TEXT NOT NULL,
    run_id INTEGER,
    edited INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""
_COLUMNS = ("id, topic, style, platforms, storyboard, variation, similarity, similar_to, cost_usd, status, run_id,"
            " edited, created_at, updated_at")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_storyboard(data: dict) -> Storyboard:
    """Validate an edited storyboard from the dashboard; raises ValueError naming the first problem."""

    def text(value, name: str, limit: int, *, required: bool = True) -> str:
        if value is None:
            value = ""
        if not isinstance(value, str):
            raise ValueError(f"{name} must be text")
        value = nfc(" ".join(value.split()))
        if required and not value:
            raise ValueError(f"{name} must not be empty")
        if len(value) > limit:
            raise ValueError(f"{name} is longer than {limit} characters")
        return value

    scenes_in = data.get("scenes")
    if not isinstance(scenes_in, list) or not scenes_in:
        raise ValueError("a script needs at least one scene")
    if len(scenes_in) > MAX_SCENES:
        raise ValueError(f"a script has at most {MAX_SCENES} scenes")
    scenes = []
    for number, scene in enumerate(scenes_in, 1):
        if not isinstance(scene, dict):
            raise ValueError(f"scene {number} is not an object")
        narration = text(scene.get("narration"), f"scene {number} narration", MAX_NARRATION)
        scenes.append(Scene(
            narration=narration,
            # A scene added by hand may have no image description: derive one from what is said.
            visual_prompt=text(scene.get("visual_prompt"), f"scene {number} visual prompt", MAX_PROMPT, required=False)
            or f"A vivid vertical shot illustrating: {narration}"[:MAX_PROMPT],
            on_screen_text=text(scene.get("on_screen_text"), f"scene {number} on-screen text", MAX_OVERLAY,
                                required=False),
            keywords=text(scene.get("keywords"), f"scene {number} keywords", 80, required=False),
        ))
    hashtags = data.get("hashtags") or []
    if isinstance(hashtags, str):
        hashtags = hashtags.replace(",", " ").split()
    if not isinstance(hashtags, list):
        raise ValueError("hashtags must be a list")
    tags = [nfc(str(tag)).strip().lstrip("#").replace(" ", "") for tag in hashtags]
    return Storyboard(
        title=text(data.get("title"), "title", MAX_TITLE),
        description=text(data.get("description"), "description", 500, required=False),
        hashtags=[tag for tag in tags if tag][:10],
        scenes=scenes,
    )


def estimated_seconds(storyboard: dict) -> float:
    words = sum(len(str(scene.get("narration", "")).split()) for scene in storyboard.get("scenes", []))
    return round(words / WORDS_PER_SECOND, 1)


@dataclass
class Draft:
    id: int
    topic: str
    style: str
    platforms: list[str]
    storyboard: dict
    variation: dict | None
    similarity: float | None
    similar_to: int | None
    cost_usd: float | None
    status: str
    run_id: int | None
    edited: bool
    created_at: str
    updated_at: str

    def summary(self) -> dict:
        return {**self.__dict__, "estimated_seconds": estimated_seconds(self.storyboard)}


def _draft(row) -> Draft:
    (draft_id, topic, style, platforms, storyboard, variation, similarity, similar_to, cost, status, run_id, edited,
     created_at, updated_at) = row
    return Draft(draft_id, topic, style, json.loads(platforms or "[]"), json.loads(storyboard),
                 json.loads(variation) if variation else None, similarity, similar_to, cost, status, run_id,
                 bool(edited), created_at, updated_at)


class DraftStore:
    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            # A render interrupted by a shutdown leaves its draft editable again.
            conn.execute("UPDATE drafts SET status = ? WHERE status = ?", (OPEN, RENDERING))
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, timeout=10)

    def create(self, topic: str, style: str, platforms: list[str], storyboard: Storyboard, *,
               variation: dict | None = None, similarity: float | None = None, similar_to: int | None = None,
               cost_usd: float | None = None) -> int:
        now = _now()
        with closing(self._connect()) as conn:
            draft_id = conn.execute(
                "INSERT INTO drafts (topic, style, platforms, storyboard, variation, similarity, similar_to, cost_usd,"
                " status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (topic, style, json.dumps(platforms), json.dumps(storyboard.to_dict(), ensure_ascii=False),
                 json.dumps(variation, ensure_ascii=False) if variation else None, similarity, similar_to, cost_usd,
                 OPEN, now, now),
            ).lastrowid
            conn.commit()
        return draft_id

    def get(self, draft_id: int) -> Draft | None:
        with closing(self._connect()) as conn:
            row = conn.execute(f"SELECT {_COLUMNS} FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        return _draft(row) if row else None

    def open_drafts(self, limit: int = 30) -> list[Draft]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM drafts WHERE status IN (?, ?) ORDER BY id DESC LIMIT ?",
                (OPEN, RENDERING, limit),
            ).fetchall()
        return [_draft(row) for row in rows]

    def update(self, draft_id: int, storyboard: Storyboard, platforms: list[str] | None = None) -> None:
        with closing(self._connect()) as conn:
            conn.execute("UPDATE drafts SET storyboard = ?, edited = 1, updated_at = ? WHERE id = ?",
                         (json.dumps(storyboard.to_dict(), ensure_ascii=False), _now(), draft_id))
            if platforms is not None:
                conn.execute("UPDATE drafts SET platforms = ? WHERE id = ?", (json.dumps(platforms), draft_id))
            conn.commit()

    def set_status(self, draft_id: int, status: str, *, run_id: int | None = None) -> None:
        with closing(self._connect()) as conn:
            conn.execute("UPDATE drafts SET status = ?, run_id = COALESCE(?, run_id), updated_at = ? WHERE id = ?",
                         (status, run_id, _now(), draft_id))
            conn.commit()

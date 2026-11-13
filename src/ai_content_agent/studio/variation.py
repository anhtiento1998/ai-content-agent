"""Variation engine: no two videos in a row share a hook, look, voice or music track.

YouTube's spam policy names "the same background music… AI-generated
script" repeated across uploads as mass-produced content. Each run gets a
VariationPlan whose every dimension is the least-recently-used option among
the last runs (ties broken at random), and the plan is stored with the run
so the rotation survives restarts.

Also here: a similarity check between a new script and the channel's recent
scripts (word 3-gram Jaccard). A near-copy is rewritten once with an
instruction to take a different angle; the remaining score is shown in the
review queue.
"""

from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass

from ai_content_agent.studio.vi_text import nfc

# Instructions appended to the storyboard prompt (English, like the rest of the prompt).
HOOKS = {
    "question": "Open with a provocative question the viewer wants answered.",
    "shock": "Open with a surprising fact or number.",
    "list": "Open by promising a short numbered list (e.g. '3 cách...') and deliver it.",
    "story": "Open with a one-sentence relatable mini-story.",
    "myth": "Open by stating a common myth, then debunk it.",
    "contrast": "Open with a before/after or wrong/right contrast.",
}

# Appended to every scene's visual prompt, so a whole video shares one look.
VISUAL_STYLES = {
    "cinematic": "cinematic photo, shallow depth of field, natural light",
    "documentary": "documentary photography, realistic, candid, handheld",
    "illustration": "flat vector illustration, bold colors, clean shapes",
    "3d": "3D render, soft studio lighting, clay-like materials",
    "anime": "anime style illustration, vibrant colors, expressive",
    "watercolor": "soft watercolor painting, textured paper",
}

SIMILARITY_THRESHOLD = 0.35
_TOKEN = re.compile(r"[^\W_]+")


@dataclass
class VariationPlan:
    hook: str | None = None
    visual_style: str | None = None
    voice: str | None = None
    music: str | None = None  # track file name inside MUSIC_DIR

    @property
    def hook_instruction(self) -> str:
        return HOOKS.get(self.hook or "", "")

    @property
    def visual_suffix(self) -> str:
        return VISUAL_STYLES.get(self.visual_style or "", "")

    def to_dict(self) -> dict:
        return asdict(self)


def _least_used(options: list[str], recent: list[str | None], rng: random.Random) -> str | None:
    """Option used least (and least recently) in `recent` (newest first); ties broken at random."""

    if not options:
        return None
    score = {option: 0.0 for option in options}
    for age, value in enumerate(recent):
        if value in score:
            score[value] += 1.0 / (age + 1)  # the last run's choice weighs most
    lowest = min(score.values())
    return rng.choice([option for option in options if score[option] == lowest])


class Variator:
    def __init__(
        self,
        *,
        hooks: list[str] | None = None,
        visual_styles: list[str] | None = None,
        voices: list[str] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._hooks = [h for h in (hooks or list(HOOKS)) if h in HOOKS]
        self._styles = [s for s in (visual_styles or list(VISUAL_STYLES)) if s in VISUAL_STYLES]
        self._voices = [v for v in (voices or []) if v]
        self._rng = rng or random.Random()

    def plan(self, recent: list[dict], tracks: list[str], *,
             exclude: dict[str, set[str]] | None = None) -> VariationPlan:
        """`recent`: plans of the latest runs, newest first. `tracks`: usable music files.
        `exclude`: options per dimension to rest (formats that earn few views); a dimension is
        never emptied by it."""

        def history(key: str) -> list[str | None]:
            return [(item or {}).get(key) for item in recent]

        def pick(key: str, options: list[str]) -> str | None:
            rested = (exclude or {}).get(key) or set()
            return _least_used([o for o in options if o not in rested] or options, history(key), self._rng)

        return VariationPlan(
            hook=pick("hook", self._hooks),
            visual_style=pick("visual_style", self._styles),
            voice=pick("voice", self._voices),
            music=pick("music", sorted(tracks)),
        )


def _shingles(text: str, n: int = 3) -> set[tuple[str, ...]]:
    tokens = _TOKEN.findall(nfc(text).lower())
    if len(tokens) < n:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def similarity(a: str, b: str) -> float:
    left, right = _shingles(a), _shingles(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def most_similar(text: str, corpus: list[tuple[int, str]]) -> tuple[int | None, float]:
    """(run_id, score) of the closest earlier script, or (None, 0.0)."""

    best: tuple[int | None, float] = (None, 0.0)
    for run_id, other in corpus:
        score = similarity(text, other)
        if score > best[1]:
            best = (run_id, score)
    return best

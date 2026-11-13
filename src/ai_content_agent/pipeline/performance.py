"""Which video formats earn views — and resting the ones that do not.

Every run records the variation it was made with (hook, visual style, voice,
music). `refresh_stats` reads view counts for live posts from the platforms;
`analyze` scores each option of each dimension, and options that clearly
under-perform are left out of the rotation (`weak_options`) until newer data
says otherwise.

How a format is judged, so one viral video or one platform's scale cannot
decide it:

- Only posts at least MIN_AGE_HOURS old count (a video posted an hour ago
  has no views yet), from the last WINDOW_DAYS days.
- A post's views are divided by the median views of all counted posts on the
  same platform, so "1.0" means a typical post there. A run's score is the
  average of its posts' ratios.
- An option's score is the *median* score of the runs that used it.
- An option is "weak" only with at least MIN_SAMPLES runs of its own, at least
  MIN_RUNS scored runs overall, and a score below WEAK_RATIO. At least two
  options per dimension always stay in rotation, and the worst is rested
  first. With small numbers this is a rule of thumb, not statistics — the
  dashboard shows the counts so a human can overrule it (AUTO_PRUNE_FORMATS).
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from statistics import median

from ai_content_agent.history import HistoryStore
from ai_content_agent.publishers.base import Publisher

logger = logging.getLogger(__name__)

DIMENSIONS = ("hook", "visual_style", "voice", "music")
WINDOW_DAYS = 60
MIN_AGE_HOURS = 48
MIN_SAMPLES = 3
MIN_RUNS = 8
WEAK_RATIO = 0.5
KEEP_AT_LEAST = 2


def refresh_stats(history: HistoryStore, publishers: list[Publisher], *, days: int = WINDOW_DAYS) -> dict:
    """Fetch view counts for live posts. Returns {platform: posts updated, or an error message}."""

    posts = history.live_posts(days=days)
    summary: dict[str, int | str] = {}
    for publisher in publishers:
        mine = [post for post in posts if post["platform"] == publisher.name]
        if not mine:
            continue
        try:
            numbers = publisher.stats([post["remote_id"] for post in mine])
        except Exception as exc:  # a platform without the scope or credentials must not stop the others
            logger.warning("Could not read %s statistics: %s", publisher.name, exc)
            summary[publisher.name] = f"{type(exc).__name__}: {exc}"[:300]
            continue
        updated = 0
        for post in mine:
            stats = numbers.get(post["remote_id"])
            if stats and stats.get("views") is not None:
                history.save_stats(post["id"], views=int(stats["views"]), likes=stats.get("likes"),
                                   comments=stats.get("comments"))
                updated += 1
        summary[publisher.name] = updated
    return summary


def analyze(
    history: HistoryStore,
    *,
    window_days: int = WINDOW_DAYS,
    min_age_hours: float = MIN_AGE_HOURS,
    min_samples: int = MIN_SAMPLES,
    min_runs: int = MIN_RUNS,
    weak_ratio: float = WEAK_RATIO,
) -> dict:
    """Score every option of every variation dimension. See the module docstring for the method."""

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=min_age_hours)).isoformat()
    rows = [row for row in history.performance_rows(days=window_days) if row["created_at"] <= cutoff]

    platform_median: dict[str, float] = {}
    for platform in {row["platform"] for row in rows}:
        platform_median[platform] = median(row["views"] for row in rows if row["platform"] == platform)

    runs: dict[int, dict] = {}
    for row in rows:
        typical = platform_median[row["platform"]]
        ratio = (row["views"] + 1) / (typical + 1)  # +1 keeps a platform of zero-view posts finite
        run = runs.setdefault(row["run_id"], {"ratios": [], "views": 0, "variation": row["variation"]})
        run["ratios"].append(ratio)
        run["views"] += row["views"]
    for run in runs.values():
        run["score"] = sum(run["ratios"]) / len(run["ratios"])

    enough = len(runs) >= min_runs
    dimensions: dict[str, list[dict]] = {}
    for dimension in DIMENSIONS:
        by_option: dict[str, list[dict]] = {}
        for run in runs.values():
            option = run["variation"].get(dimension)
            if option:
                by_option.setdefault(option, []).append(run)
        options = [{
            "option": option,
            "runs": len(used),
            "median_views": int(median(run["views"] for run in used)),
            "score": round(median(run["score"] for run in used), 2),
            "status": "ok" if len(used) >= min_samples else "few",
        } for option, used in by_option.items()]
        options.sort(key=lambda item: item["score"], reverse=True)

        if enough:
            candidates = [o for o in reversed(options) if o["status"] == "ok" and o["score"] < weak_ratio]
            droppable = max(0, len(options) - KEEP_AT_LEAST)
            for option in candidates[:droppable]:  # worst first; never rest a dimension down to one look
                option["status"] = "weak"
        dimensions[dimension] = options

    return {
        "scored_runs": len(runs),
        "enough_data": enough,
        "min_runs": min_runs,
        "min_samples": min_samples,
        "weak_ratio": weak_ratio,
        "window_days": window_days,
        "min_age_hours": min_age_hours,
        "platform_median_views": {platform: int(value) for platform, value in platform_median.items()},
        "stats_updated_at": history.last_stats_at(),
        "dimensions": dimensions,
    }


def weak_options(report: dict) -> dict[str, set[str]]:
    """{dimension: options to leave out of the rotation}."""

    return {dimension: {item["option"] for item in options if item["status"] == "weak"}
            for dimension, options in report["dimensions"].items()}


class StatsRefresher:
    """Background thread that refreshes view counts every `hours` while the dashboard runs."""

    def __init__(self, refresh, *, hours: float, first_delay_seconds: float = 90.0) -> None:
        self._refresh = refresh
        self._interval = hours * 3600
        self._first_delay = first_delay_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="stats-refresh", daemon=True)

    def start(self) -> "StatsRefresher":
        if self._interval > 0:
            self._thread.start()
        return self

    def _loop(self) -> None:
        delay = self._first_delay
        while not self._stop.wait(delay):
            try:
                self._refresh()
            except Exception:
                logger.exception("Refreshing view statistics failed")
            delay = self._interval

    def stop(self) -> None:
        self._stop.set()

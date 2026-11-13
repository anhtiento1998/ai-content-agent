"""Scene visuals from free stock libraries instead of AI generation.

VISUAL_PROVIDER=pexels        portrait video clips from Pexels   (PEXELS_API_KEY, free)
VISUAL_PROVIDER=pexels-photo  portrait photos from Pexels, animated with the usual slow zoom
VISUAL_PROVIDER=pixabay       video clips from Pixabay           (PIXABAY_API_KEY, free)

Stock search works on a few concrete words, not on the long prompt written
for an image model, so the storyboard carries a short `keywords` field per
scene and the studio passes that to these engines (`uses_keywords`). When a
search finds nothing the query is shortened word by word before giving up.

Clips already used are remembered in a small JSON file (most recent 600), so
one video does not show the same clip twice and neither do the next videos.
Where each clip came from (page URL, author) is kept in `sources` and written
to the run's provenance. Pexels and Pixabay content is free to use without
attribution under their licences — which also forbid selling it unaltered or
implying endorsement by people shown; read them before commercial use.
"""

from __future__ import annotations

import json
import os
import random
import threading
from pathlib import Path

import requests

from .base import ImageGenerator, VideoGenerator

_REMEMBER = 600
_MIN_CLIP_SECONDS = 3


class StockSearchError(RuntimeError):
    """HTTP error from a stock API; `status_code` lets the studio retry 429/5xx."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class _UsedClips:
    """Ids of clips already used, shared between runs through a JSON file."""

    def __init__(self, path: str | None) -> None:
        self._path = Path(path) if path else None
        self._lock = threading.Lock()
        self._ids: list[str] = []
        if self._path and self._path.is_file():
            try:
                self._ids = [str(item) for item in json.loads(self._path.read_text(encoding="utf-8"))]
            except (OSError, ValueError):
                self._ids = []

    def choose(self, candidates: list[dict]) -> dict:
        """A candidate not used before (random among the best few), else the least recently used."""

        with self._lock:
            fresh = [c for c in candidates if c["id"] not in self._ids]
            if fresh:
                chosen = random.choice(fresh[:5])
            else:
                chosen = min(candidates, key=lambda c: self._ids.index(c["id"]))
                self._ids.remove(chosen["id"])
            self._ids = (self._ids + [chosen["id"]])[-_REMEMBER:]
            if self._path:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self._path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self._ids), encoding="utf-8")
                os.replace(tmp, self._path)
            return chosen


class _Stock:
    uses_keywords = True  # the studio sends each scene's short keywords instead of its image prompt
    max_concurrency = 3
    site = ""

    def __init__(self, api_key: str | None, model: str | None = None, *, used_file: str | None = None,
                 timeout: float = 120) -> None:
        if not api_key:
            raise ValueError(f"VISUAL_PROVIDER={self.name} needs {self.key_setting} (free at {self.site})")
        self._api_key = api_key
        self._model = model or "stock"
        self._used = _UsedClips(used_file)
        self._timeout = timeout
        self.sources: list[dict] = []
        self._sources_lock = threading.Lock()

    def _get(self, url: str, **kwargs) -> dict:
        resp = requests.get(url, timeout=30, **kwargs)
        if resp.status_code != 200:
            raise StockSearchError(resp.status_code, f"{self.name} search failed (HTTP {resp.status_code}): "
                                                     f"{resp.text[:200]}")
        return resp.json()

    def _candidates(self, query: str, aspect_ratio: str) -> list[dict]:
        raise NotImplementedError

    def _fetch(self, query: str, out_path: str, aspect_ratio: str) -> None:
        words = " ".join(query.replace(",", " ").split()).split(" ")[:6]
        candidates: list[dict] = []
        while words and not candidates:  # too specific a query finds nothing: drop words from the end
            candidates = self._candidates(" ".join(words), aspect_ratio)
            words = words[:-1]
        if not candidates:
            raise RuntimeError(f"{self.name} has no result for {query!r} — edit the scene's keywords")
        chosen = self._used.choose(candidates)
        data = requests.get(chosen["download"], timeout=self._timeout)
        if data.status_code != 200 or not data.content:
            raise StockSearchError(data.status_code, f"Could not download the {self.name} file (HTTP {data.status_code})")
        Path(out_path).write_bytes(data.content)
        with self._sources_lock:
            self.sources.append({"file": Path(out_path).name, "provider": self.name, "id": chosen["id"],
                                 "url": chosen.get("page"), "author": chosen.get("author"), "query": query})


def _orientation(aspect_ratio: str) -> str:
    return {"9:16": "portrait", "16:9": "landscape"}.get(aspect_ratio, "square")


def _best_video_file(files: list[dict], portrait: bool) -> dict | None:
    """The rendition closest to full HD in the wanted orientation (4K files are needlessly large)."""

    usable = [f for f in files if f.get("link") or f.get("url")]
    if not usable:
        return None
    target = 1920 if portrait else 1080

    def score(item: dict) -> tuple:
        width, height = item.get("width") or 0, item.get("height") or 0
        right_way = (height >= width) == portrait
        return (not right_way, abs(height - target))

    return min(usable, key=score)


class PexelsVideoProvider(_Stock, VideoGenerator):
    name = "pexels"
    key_setting = "PEXELS_API_KEY"
    site = "pexels.com/api"

    def _candidates(self, query: str, aspect_ratio: str) -> list[dict]:
        data = self._get("https://api.pexels.com/videos/search", headers={"Authorization": self._api_key},
                         params={"query": query, "orientation": _orientation(aspect_ratio), "per_page": 15})
        results = []
        for video in data.get("videos") or []:
            best = _best_video_file(video.get("video_files") or [], aspect_ratio == "9:16")
            if best and (video.get("duration") or 0) >= _MIN_CLIP_SECONDS:
                results.append({"id": f"pexels-{video['id']}", "download": best["link"], "page": video.get("url"),
                                "author": (video.get("user") or {}).get("name")})
        return results

    def generate_clip(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        self._fetch(prompt, out_path, aspect_ratio)


class PexelsPhotoProvider(_Stock, ImageGenerator):
    name = "pexels-photo"
    key_setting = "PEXELS_API_KEY"
    site = "pexels.com/api"

    def _candidates(self, query: str, aspect_ratio: str) -> list[dict]:
        data = self._get("https://api.pexels.com/v1/search", headers={"Authorization": self._api_key},
                         params={"query": query, "orientation": _orientation(aspect_ratio), "per_page": 15})
        return [{"id": f"pexels-photo-{photo['id']}",
                 "download": (photo.get("src") or {}).get("large2x") or (photo.get("src") or {}).get("original"),
                 "page": photo.get("url"), "author": photo.get("photographer")}
                for photo in data.get("photos") or [] if (photo.get("src") or {}).get("original")]

    def generate_image(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        self._fetch(prompt, out_path, aspect_ratio)


class PixabayVideoProvider(_Stock, VideoGenerator):
    name = "pixabay"
    key_setting = "PIXABAY_API_KEY"
    site = "pixabay.com/api/docs"

    def _candidates(self, query: str, aspect_ratio: str) -> list[dict]:
        data = self._get("https://pixabay.com/api/videos/",
                         params={"key": self._api_key, "q": query, "per_page": 15, "safesearch": "true"})
        results = []
        for hit in data.get("hits") or []:
            renditions = [r for r in (hit.get("videos") or {}).values() if isinstance(r, dict)]
            best = _best_video_file(renditions, aspect_ratio == "9:16")
            if best and (hit.get("duration") or 0) >= _MIN_CLIP_SECONDS:
                results.append({"id": f"pixabay-{hit['id']}", "download": best["url"], "page": hit.get("pageURL"),
                                "author": hit.get("user")})
        return results

    def generate_clip(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        self._fetch(prompt, out_path, aspect_ratio)

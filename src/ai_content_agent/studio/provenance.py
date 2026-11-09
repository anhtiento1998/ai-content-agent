"""Licence registry for music and a provenance record for every video.

Music: list each track's licence in MUSIC_DIR/licenses.json —

    {
      "lofi-morning.mp3": {
        "license": "Pixabay Content License",
        "source": "https://pixabay.com/music/...",
        "attribution": ""
      }
    }

With REQUIRE_MUSIC_LICENSE=true (default) tracks without an entry are never
used, and a run whose provenance shows unlicensed music cannot be published.
Content ID claims and Suno/Udio terms make "royalty-free" folders a common
way to lose a channel's monetisation.

Provenance: every render writes provenance.json next to final.mp4 — which
engines and models wrote, drew and voiced it, the music and its licence,
the variation plan and the AI-disclosure label — and the same summary is
embedded in the MP4's metadata. This is not a signed C2PA manifest (that
needs a signing certificate); it is the record a reviewer, a platform
dispute or Decree 142/2026 labelling questions can be answered from.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MUSIC_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
LICENSES_FILE = "licenses.json"


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("ai-content-agent")
    except Exception:
        return "dev"


@dataclass
class MusicLibrary:
    folder: str | None
    require_license: bool = True

    def _licenses(self) -> dict:
        if not self.folder:
            return {}
        path = Path(self.folder) / LICENSES_FILE
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise RuntimeError(f"{path} is not valid JSON: {exc}") from exc
        return {name: entry for name, entry in data.items() if isinstance(entry, dict)}

    def all_tracks(self) -> list[str]:
        folder = Path(self.folder) if self.folder else None
        if not folder or not folder.is_dir():
            return []
        return sorted(p.name for p in folder.iterdir() if p.suffix.lower() in MUSIC_EXTENSIONS)

    def usable_tracks(self) -> list[str]:
        tracks = self.all_tracks()
        if not self.require_license:
            return tracks
        licensed = {name for name, entry in self._licenses().items() if entry.get("license")}
        skipped = [t for t in tracks if t not in licensed]
        if skipped:
            logger.warning("Skipping %d music track(s) without an entry in %s/%s: %s",
                           len(skipped), self.folder, LICENSES_FILE, ", ".join(skipped[:5]))
        return [t for t in tracks if t in licensed]

    def path(self, name: str) -> str:
        return str((Path(self.folder) / name).resolve())

    def license_for(self, name: str) -> dict | None:
        entry = self._licenses().get(name)
        return dict(entry) if entry and entry.get("license") else None

    def status(self) -> dict:
        tracks, licenses = self.all_tracks(), self._licenses()
        licensed = [t for t in tracks if (licenses.get(t) or {}).get("license")]
        return {"tracks": len(tracks), "licensed": len(licensed), "require_license": self.require_license}


def _model(engine) -> str | None:
    return getattr(engine, "_model", None) or getattr(engine, "model", None)


def build_provenance(*, writer, visuals, voice, voice_name: str | None, music: dict | None, plan: dict | None,
                     language: str, disclosure: str | None, scenes: int, duration: float) -> dict:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generator": f"ai-content-agent {_version()}",
        "ai_generated": True,
        "disclosure": disclosure,
        "language": language,
        "engines": {
            "text": {"provider": writer.name, "model": _model(writer)},
            "visual": {"provider": visuals.name, "model": _model(visuals)},
            "voice": {"provider": voice.name, "model": _model(voice),
                      "voice": voice_name or getattr(voice, "_voice", None)},
        },
        "music": music,
        "variation": plan,
        "scenes": scenes,
        "duration_seconds": round(duration, 3),
    }


def metadata_tags(provenance: dict, title: str) -> dict[str, str]:
    """MP4 tags (ffmpeg -metadata) summarising the provenance record."""

    engines = provenance.get("engines", {})
    parts = [f"{kind}={info.get('provider')}" + (f"/{info['model']}" if info.get("model") else "")
             for kind, info in engines.items()]
    music = provenance.get("music") or {}
    comment = "AI-generated content. " + (provenance.get("disclosure") or "") + " | engines: " + ", ".join(parts)
    if music:
        comment += f" | music: {music.get('file')} ({music.get('license') or 'no licence recorded'})"
    return {
        "title": title,
        "comment": comment[:900],
        "description": comment[:900],
        "encoder": provenance.get("generator", "ai-content-agent"),
    }


def publish_blocker(provenance: dict | None, *, require_license: bool) -> str | None:
    """Why a run must not be published, or None. Old runs without provenance are not blocked."""

    if not provenance or not require_license:
        return None
    music = provenance.get("music")
    if music and not music.get("license"):
        return (f"Music track {music.get('file')!r} has no licence in {LICENSES_FILE} "
                "(REQUIRE_MUSIC_LICENSE) — add one or re-render without it")
    return None

"""Export a studio run as an editable CapCut desktop draft.

CapCut has no official API or documented project format. This uses
`pycapcut` (community reverse-engineered writer for CapCut International
drafts; install with `pip install -e ".[capcut]"` — it has no licence file,
so it stays an optional extra the user installs) to rebuild the edit from
the run's timeline.json as separate, editable tracks:

  visuals (stills with a slow-zoom keyframe, or clips looped to length)
  logo · voice · music · hook text · captions (imported from subtitles.srt)

Hardening for CapCut 8.7–9.x, following the version matrix kept by
capcut-cli (MIT, github.com/renezander030/capcut-cli/docs/version-support.md):

- The installed version is detected (CAPCUT_VERSION, the Windows install
  folder, or version markers in drafts the app wrote). 10.x is refused —
  it reports tool-written drafts as corrupted — unless forced; use the edit
  bundle (export/edit_bundle.py) instead.
- Nothing is written while CapCut is running (it rewrites its store on exit).
- New drafts are seeded from a project the app itself created
  (CAPCUT_TEMPLATE: a project name, or "auto" = the newest app-made one):
  its version markers, file layout (draft_info.json / draft_content.json /
  template-2.tmp) and meta file are reused, so the app does not reject the
  draft for stale markers. Timelines/ is never copied — the app builds it
  from the root files on first open. Best: create one empty project in
  CapCut, quit, and name it in CAPCUT_TEMPLATE.
- Every draft gets a fresh draft_id (pycapcut's template reuses one ID).
- Text style ranges are counted in UTF-16 code units, as CapCut does.
- The store's root_meta_info.json is backed up before a draft is registered.

Media is referenced in place from the run folder, so keep that folder.
Close CapCut before exporting; it lists new drafts after it is reopened.
Verified only against a pycapcut stand-in — not yet in a real CapCut.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from ai_content_agent.media.ffmpeg import probe_video

logger = logging.getLogger(__name__)

_US = 1_000_000
_ZOOM = 0.12
_MUSIC_VOLUME = 0.15
_INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_INSTALL_HINT = 'CapCut export needs the optional "pycapcut" package: pip install -e ".[capcut]"'
MAX_TESTED_MAJOR = 9
TIMELINE_FILES = ("draft_info.json", "draft_content.json", "template-2.tmp")
META_FILE = "draft_meta_info.json"
ROOT_META = "root_meta_info.json"
OUR_MARKER = "ai_content_agent.json"


class CapCutRefused(RuntimeError):
    """Export was refused to protect the user's CapCut store (version beyond evidence, app running)."""


def _version_tuple(text) -> tuple[int, ...] | None:
    match = re.match(r"^\s*(\d+(?:\.\d+)*)", str(text or ""))
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def _read_json(path: Path):
    """Parsed JSON, or None when missing, encrypted or invalid (CapCut encrypts some mirrors)."""

    try:
        if not path.is_file() or path.stat().st_size > 200 * 1024 * 1024:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None


def _timeline_doc(project: Path) -> tuple[str, dict] | None:
    """(file name, document) of the first readable timeline file in a project folder."""

    for name in TIMELINE_FILES:
        data = _read_json(project / name)
        if isinstance(data, dict) and ("tracks" in data or "materials" in data or "platform" in data):
            return name, data
    return None


def _doc_versions(doc: dict) -> list[tuple[int, ...]]:
    versions = []
    for key in ("platform", "last_modified_platform"):
        marker = doc.get(key)
        if isinstance(marker, dict):
            version = _version_tuple(marker.get("app_version"))
            if version:
                versions.append(version)
    return versions


def _projects(store: Path) -> list[Path]:
    if not store or not store.is_dir():
        return []
    return sorted((p for p in store.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def _app_made(project: Path) -> bool:
    return not (project / OUR_MARKER).exists()


def detect_version(store: Path | None, override: str | None = None) -> tuple[str | None, str]:
    """(version, where it came from). Newest of: install folders (Windows), app-written drafts."""

    if override:
        return override, "CAPCUT_VERSION"
    found: list[tuple[tuple[int, ...], str]] = []
    if sys.platform == "win32" and os.getenv("LOCALAPPDATA"):
        apps = Path(os.environ["LOCALAPPDATA"]) / "CapCut" / "Apps"
        if apps.is_dir():
            found += [(v, "install folder") for v in (_version_tuple(p.name) for p in apps.iterdir()) if v]
    for project in _projects(store)[:30]:
        if not _app_made(project):
            continue
        doc = _timeline_doc(project)
        if doc:
            found += [(v, f"draft {project.name!r}") for v in _doc_versions(doc[1])]
    if not found:
        return None, "unknown"
    version, source = max(found)
    return ".".join(str(part) for part in version), source


def capcut_running() -> bool:
    try:
        if sys.platform == "win32":
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/NH"], capture_output=True,
                                 text=True, errors="replace", timeout=10).stdout
            return "capcut.exe" in out.lower()
        if sys.platform == "darwin":
            return subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
    return False


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def fix_text_ranges(content: dict) -> int:
    """NFC every text material and express style ranges in UTF-16 code units (CapCut's unit;
    differs from Python's code points for emoji and other astral characters). Returns fixes made."""

    fixes = 0
    for material in (content.get("materials") or {}).get("texts") or []:
        raw = material.get("content")
        if not isinstance(raw, str):
            continue
        try:
            inner = json.loads(raw)
        except ValueError:
            continue
        text = inner.get("text")
        if not isinstance(text, str):
            continue
        normalized = unicodedata.normalize("NFC", text)
        old_len, new_len = len(text), utf16_len(normalized)
        changed = normalized != text
        for style in inner.get("styles") or []:
            rng = style.get("range")
            if isinstance(rng, list) and len(rng) == 2 and rng[1] in (old_len, len(normalized)) and rng[1] != new_len:
                style["range"] = [rng[0], new_len]
                changed = True
        if changed:
            inner["text"] = normalized
            material["content"] = json.dumps(inner, ensure_ascii=False)
            fixes += 1
    return fixes


@dataclass
class Template:
    folder: Path
    timeline_files: list[str]  # readable timeline files the app keeps at the root
    doc: dict
    meta: dict | None

    @property
    def empty(self) -> bool:
        return not any((track.get("segments") or []) for track in self.doc.get("tracks") or [])


def find_template(store: Path | None, choice: str | None) -> Template | None:
    """The app-made project to seed from: by name, or "auto" = newest readable app-made project."""

    if not store or not choice or choice.lower() in ("off", "none", "false"):
        return None
    candidates = _projects(store)
    if choice.lower() != "auto":
        candidates = [p for p in candidates if p.name == choice]
        if not candidates:
            raise FileNotFoundError(
                f"CAPCUT_TEMPLATE={choice!r}: no such project in {store} — create an empty project with that "
                "name in CapCut, quit CapCut, and export again"
            )
    for project in candidates:
        if not _app_made(project):
            continue
        files = [name for name in TIMELINE_FILES if isinstance(_read_json(project / name), dict)]
        doc = _timeline_doc(project)
        if doc and doc[1].get("platform"):
            meta = _read_json(project / META_FILE)
            return Template(project, files, doc[1], meta if isinstance(meta, dict) else None)
    if choice.lower() != "auto":
        raise RuntimeError(f"CAPCUT_TEMPLATE={choice!r} has no readable timeline (encrypted or not a CapCut project)")
    return None


def default_drafts_dir() -> Path | None:
    """CapCut desktop's draft folder on this OS, or None where CapCut desktop does not run."""

    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA")
        return Path(base) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft" if base else None
    if sys.platform == "darwin":
        return Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    return None


def capcut_status(drafts_dir: str | Path | None = None, version: str | None = None) -> dict:
    """Dashboard readiness entry (Vietnamese notes are shown verbatim). The edit bundle
    (FCPXML + SRT + media) works whatever this says."""

    store = Path(drafts_dir) if drafts_dir else default_drafts_dir()
    detected, source = detect_version(store, version)
    parsed = _version_tuple(detected)
    supported = parsed is None or parsed[0] <= MAX_TESTED_MAJOR
    facts = {"version": detected, "version_source": source, "supported": supported}
    try:
        import pycapcut  # noqa: F401
    except ImportError:
        return {"ready": False, "note": 'Chưa cài pycapcut — chạy: pip install -e ".[capcut]"', **facts}
    if not supported:
        return {"ready": False, "note": f"CapCut {detected} chưa có bằng chứng nhận draft do công cụ tạo — "
                                        "dùng “Gói dựng” (FCPXML + SRT) thay thế", **facts}
    return {"ready": True, "note": None, **facts}


def _draft_name(title: str) -> str:
    clean = " ".join(_INVALID_NAME_CHARS.sub(" ", title).split()).strip(" .")[:60] or "video"
    return f"{clean} {time.strftime('%Y-%m-%d %H%M%S')}"


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp-write")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _cover_scale(media_w: int, media_h: int, canvas_w: int, canvas_h: int) -> float:
    """CapCut fits media inside the canvas by default; this scale makes it fill (crop) instead."""

    fit = min(canvas_w / media_w, canvas_h / media_h)
    cover = max(canvas_w / media_w, canvas_h / media_h)
    return cover / fit


class CapCutExporter:
    def __init__(
        self,
        drafts_dir: str | Path | None = None,
        *,
        template: str | None = "auto",
        version: str | None = None,
        force: bool = False,
    ) -> None:
        self._drafts_dir = Path(drafts_dir) if drafts_dir else default_drafts_dir()
        self._template = template
        self._version = version
        self._force = force

    def check(self) -> dict:
        """Version and safety facts for the dashboard / CLI, without writing anything."""

        store = self._drafts_dir
        version, source = detect_version(store, self._version)
        major = (_version_tuple(version) or (0,))[0]
        return {
            "store": str(store) if store else None,
            "version": version,
            "version_source": source,
            "supported": version is None or major <= MAX_TESTED_MAJOR,
            "running": capcut_running(),
        }

    def _guard(self, store: Path) -> str | None:
        version, source = detect_version(store, self._version)
        parsed = _version_tuple(version)
        if parsed and parsed[0] > MAX_TESTED_MAJOR:
            message = (f"CapCut {version} (from {source}) is newer than any version known to accept tool-written "
                       f"drafts (≤{MAX_TESTED_MAJOR}.x; 10.x reports them as corrupted). Export an edit bundle "
                       "(FCPXML + SRT + media) instead, or set CAPCUT_FORCE_WRITE=true to try anyway.")
            if not self._force:
                raise CapCutRefused(message)
            logger.warning("Forced write: %s", message)
        if self._drafts_dir is not None and capcut_running():
            message = "CapCut is running — quit it first, or it will overwrite the draft list when it closes."
            if not self._force:
                raise CapCutRefused(message)
            logger.warning("Forced write: %s", message)
        if version is None:
            logger.warning("Could not detect the CapCut version; writing a %s.x-style draft", MAX_TESTED_MAJOR)
        return version

    def export(self, work_dir: str | Path) -> Path:
        """Write a draft for the run in `work_dir`; returns the draft folder."""

        try:
            import pycapcut as cc
        except ImportError as exc:
            raise RuntimeError(_INSTALL_HINT) from exc

        work = Path(work_dir).resolve()
        timeline_path = work / "timeline.json"
        if not timeline_path.is_file():
            raise FileNotFoundError(f"{timeline_path} not found — only runs rendered by this version can be exported")
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))

        root = self._drafts_dir or (work / "capcut_draft")
        root.mkdir(parents=True, exist_ok=True)
        version = self._guard(root)
        template = find_template(self._drafts_dir, self._template)
        name = base = _draft_name(timeline["title"])
        suffix = 2
        while (root / name).exists():
            name, suffix = f"{base} ({suffix})", suffix + 1
        width, height = timeline["width"], timeline["height"]
        staging = Path(tempfile.mkdtemp(prefix="capcut_", dir=work))
        try:
            script = cc.DraftFolder(str(staging)).create_draft(name, width, height, fps=timeline["fps"])
            self._build(cc, script, work, timeline, width, height)
            script.save()
            return self._install(staging / name, root, name, work, version, template)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def _build(self, cc, script, work: Path, timeline: dict, width: int, height: int) -> None:

        script.add_track(cc.TrackType.video, "visuals")
        script.add_track(cc.TrackType.audio, "voice")
        if timeline.get("music"):
            script.add_track(cc.TrackType.audio, "music")
        avatar = timeline.get("avatar")
        if avatar:
            script.add_track(cc.TrackType.video, "avatar", relative_index=1)
        if timeline.get("logo"):
            script.add_track(cc.TrackType.video, "logo", relative_index=2 if avatar else 1)
        script.add_track(cc.TrackType.text, "hooks")

        # Integer microsecond boundaries derived from cumulative times, so adjacent
        # segments touch exactly and never overlap through rounding.
        bounds = [round(scene["start"] * _US) for scene in timeline["scenes"]] + [round(timeline["duration"] * _US)]
        for scene, start, end in zip(timeline["scenes"], bounds, bounds[1:]):
            self._add_visual(cc, script, work / scene["visual"], scene, start, end - start, width, height)
            if avatar and scene.get("avatar"):
                self._add_avatar(cc, script, work / scene["avatar"], avatar, start, end - start, width, height)
            voice = cc.AudioMaterial(str(work / scene["voice"]))
            voice_us = min(round(scene["voice_duration"] * _US), voice.duration, end - start)
            script.add_segment(cc.AudioSegment(voice, cc.Timerange(start, voice_us)), "voice")
            if scene.get("on_screen_text"):
                script.add_segment(
                    cc.TextSegment(
                        scene["on_screen_text"],
                        cc.Timerange(start, end - start),
                        style=cc.TextStyle(size=10, bold=True, color=(1.0, 0.9, 0.0), align=1, auto_wrapping=True),
                        border=cc.TextBorder(color=(0.0, 0.0, 0.0), width=60.0),
                        clip_settings=cc.ClipSettings(transform_y=0.72),
                    ),
                    "hooks",
                )

        total = bounds[-1]
        if timeline.get("music"):
            music = cc.AudioMaterial(timeline["music"])
            for offset, piece in self._loop_pieces(total, music.duration):
                script.add_segment(
                    cc.AudioSegment(music, cc.Timerange(offset, piece), source_timerange=cc.Timerange(0, piece),
                                    volume=_MUSIC_VOLUME),
                    "music",
                )
        if timeline.get("logo"):
            script.add_segment(
                cc.VideoSegment(
                    cc.VideoMaterial(timeline["logo"]),
                    cc.Timerange(0, total),
                    clip_settings=cc.ClipSettings(scale_x=0.18, scale_y=0.18, transform_x=0.74, transform_y=0.86),
                ),
                "logo",
            )

        captions = work / timeline["captions"]
        if captions.is_file() and captions.read_text(encoding="utf-8").strip():
            style = cc.TextSegment(
                "caption",
                cc.Timerange(0, _US),
                style=cc.TextStyle(size=7, bold=True, align=1, auto_wrapping=True, max_line_width=0.8),
                border=cc.TextBorder(color=(0.0, 0.0, 0.0), width=50.0),
            )
            script.import_srt(str(captions), "captions", style_reference=style,
                              clip_settings=cc.ClipSettings(transform_y=-0.52))

    def _install(self, built: Path, root: Path, name: str, work: Path, version: str | None,
                 template: Template | None) -> Path:
        """Move the pycapcut output into the store, seeded from `template` when there is one."""

        content = _read_json(built / "draft_content.json")
        if not isinstance(content, dict):
            raise RuntimeError("pycapcut did not write a readable draft_content.json")
        fix_text_ranges(content)
        draft_id = str(uuid.uuid4()).upper()
        content["id"] = draft_id

        if template:
            for key in ("platform", "last_modified_platform", "version", "new_version"):
                if key in template.doc:
                    content[key] = template.doc[key]
            if template.empty:  # settings of an empty app-made project are safe to inherit wholesale
                for key, value in template.doc.items():
                    content.setdefault(key, value)
                materials = content.setdefault("materials", {})
                for key, value in (template.doc.get("materials") or {}).items():
                    materials.setdefault(key, [] if isinstance(value, list) else value)
            timeline_files = template.timeline_files or ["draft_content.json"]
            meta = dict(template.meta or _read_json(built / META_FILE) or {})
        else:
            timeline_files = ["draft_content.json"]
            meta = dict(_read_json(built / META_FILE) or {})

        target = root / name
        target.mkdir(parents=True)
        for item in built.iterdir():  # anything else pycapcut ships with a draft
            if item.name not in (*TIMELINE_FILES, META_FILE) and item.is_file():
                shutil.copy2(item, target / item.name)
        data = json.dumps(content, ensure_ascii=False)
        for file_name in timeline_files:  # identical mirrors, never a lone extra file
            _atomic_write(target / file_name, data)

        now_us = int(time.time() * 1_000_000)
        cover = work / "thumbnail.jpg"
        if cover.is_file():
            shutil.copy2(cover, target / "draft_cover.jpg")
        meta.update({
            "draft_id": draft_id,
            "draft_name": name,
            "draft_fold_path": target.as_posix(),
            "draft_root_path": root.as_posix(),
            "tm_draft_create": now_us,
            "tm_draft_modified": now_us,
        })
        if cover.is_file():
            meta["draft_cover"] = "draft_cover.jpg"
        else:
            meta.pop("draft_cover", None)
        _atomic_write(target / META_FILE, json.dumps(meta, ensure_ascii=False))
        _atomic_write(target / OUR_MARKER, json.dumps({
            "source_run": str(work), "capcut_version": version,
            "template": template.folder.name if template else None, "created_at": time.time(),
        }, ensure_ascii=False))
        if template:
            self._register(root, template, target, meta)
        else:
            logger.warning("No app-made CapCut project to seed from — on CapCut 9.x create one empty project, quit "
                           "CapCut and export again (or set CAPCUT_TEMPLATE)")
        return target

    @staticmethod
    def _register(root: Path, template: Template, target: Path, meta: dict) -> None:
        """Add the draft to the store's root_meta_info.json, copying the template's entry (backed up first)."""

        path = root / ROOT_META
        data = _read_json(path)
        if not isinstance(data, dict) or not isinstance(data.get("all_draft_store"), list):
            return
        entry = next((e for e in data["all_draft_store"] if isinstance(e, dict) and (
            Path(str(e.get("draft_fold_path", ""))).name == template.folder.name)), None)
        if entry is None:
            return
        shutil.copy2(path, path.with_name(f"{ROOT_META}.bak-{time.strftime('%Y%m%d-%H%M%S')}"))
        new = dict(entry)
        json_file = Path(str(entry.get("draft_json_file", ""))).name or next(
            (n for n in TIMELINE_FILES if (target / n).exists()), "draft_content.json")
        new.update({
            "draft_id": meta["draft_id"], "draft_name": meta["draft_name"],
            "draft_fold_path": meta["draft_fold_path"], "draft_root_path": meta["draft_root_path"],
            "draft_json_file": (target / json_file).as_posix(),
            "draft_cover": (target / "draft_cover.jpg").as_posix() if meta.get("draft_cover") else "",
            "tm_draft_create": meta["tm_draft_create"], "tm_draft_modified": meta["tm_draft_modified"],
        })
        data["all_draft_store"].insert(0, new)
        if isinstance(data.get("draft_ids"), int):
            data["draft_ids"] += 1
        _atomic_write(path, json.dumps(data, ensure_ascii=False))

    def _add_avatar(self, cc, script, path: Path, box: dict, start: int, duration: int, width: int, height: int):
        """The corner talking head as its own track (a plain rectangle: CapCut drafts carry no circle
        mask here — add one in CapCut if wanted). CapCut positions by the clip centre, in half-canvas units."""

        material = cc.VideoMaterial(str(path))
        clip_w, clip_h, _ = probe_video(str(path))
        fit = min(width / clip_w, height / clip_h)  # CapCut first fits the clip inside the canvas
        scale = box["size"] / (min(clip_w, clip_h) * fit)
        centre_x = (box["x"] + box["size"] / 2) / width * 2 - 1
        centre_y = 1 - (box["y"] + box["size"] / 2) / height * 2
        for offset, piece in self._loop_pieces(duration, material.duration):
            script.add_segment(
                cc.VideoSegment(material, cc.Timerange(start + offset, piece), source_timerange=cc.Timerange(0, piece),
                                volume=0.0, clip_settings=cc.ClipSettings(scale_x=scale, scale_y=scale,
                                                                          transform_x=centre_x, transform_y=centre_y)),
                "avatar",
            )

    @staticmethod
    def _loop_pieces(total_us: int, source_us: int) -> list[tuple[int, int]]:
        """Consecutive (offset, length) pieces that tile `total_us` with a `source_us`-long source."""

        pieces, offset = [], 0
        while offset < total_us:
            piece = min(source_us, total_us - offset)
            pieces.append((offset, piece))
            offset += piece
        return pieces

    def _add_visual(self, cc, script, path: Path, scene: dict, start: int, duration: int, width: int, height: int):
        material = cc.VideoMaterial(str(path))
        if scene["visual_kind"] == "image":
            with Image.open(path) as image:
                scale = _cover_scale(image.width, image.height, width, height)
            segment = cc.VideoSegment(material, cc.Timerange(start, duration),
                                      clip_settings=cc.ClipSettings(scale_x=scale, scale_y=scale))
            first, last = (scale, scale * (1 + _ZOOM)) if scene["zoom_in"] else (scale * (1 + _ZOOM), scale)
            segment.add_keyframe(cc.KeyframeProperty.uniform_scale, 0, first)
            segment.add_keyframe(cc.KeyframeProperty.uniform_scale, duration, last)
            script.add_segment(segment, "visuals")
            return

        clip_w, clip_h, _ = probe_video(str(path))
        scale = _cover_scale(clip_w, clip_h, width, height)
        for offset, piece in self._loop_pieces(duration, material.duration):
            script.add_segment(
                cc.VideoSegment(material, cc.Timerange(start + offset, piece), source_timerange=cc.Timerange(0, piece),
                                volume=0.0, clip_settings=cc.ClipSettings(scale_x=scale, scale_y=scale)),
                "visuals",
            )

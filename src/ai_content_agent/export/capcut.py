"""Export a studio run as an editable CapCut desktop draft.

CapCut has no official API or documented project format. This uses
`pycapcut` (community reverse-engineered writer for CapCut International
drafts; install with `pip install -e ".[capcut]"`) to rebuild the edit from
the run's timeline.json as separate, editable tracks:

  visuals (stills with a slow-zoom keyframe, or clips looped to length)
  logo · voice · music · hook text · captions (imported from subtitles.srt)

Media is referenced in place from the run folder, so keep that folder.
Close CapCut before exporting; it lists new drafts after it is reopened.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

from PIL import Image

from ai_content_agent.media.ffmpeg import probe_video

_US = 1_000_000
_ZOOM = 0.12
_MUSIC_VOLUME = 0.15
_INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_INSTALL_HINT = 'CapCut export needs the optional "pycapcut" package: pip install -e ".[capcut]"'


def default_drafts_dir() -> Path | None:
    """CapCut desktop's draft folder on this OS, or None where CapCut desktop does not run."""

    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA")
        return Path(base) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft" if base else None
    if sys.platform == "darwin":
        return Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    return None


def capcut_status() -> dict:
    """Dashboard readiness entry (Vietnamese notes are shown verbatim)."""

    try:
        import pycapcut  # noqa: F401
    except ImportError:
        return {"ready": False, "note": 'Chưa cài pycapcut — chạy: pip install -e ".[capcut]"'}
    return {"ready": True, "note": None}


def _draft_name(title: str) -> str:
    clean = " ".join(_INVALID_NAME_CHARS.sub(" ", title).split()).strip(" .")[:60] or "video"
    return f"{clean} {time.strftime('%Y-%m-%d %H%M%S')}"


def _cover_scale(media_w: int, media_h: int, canvas_w: int, canvas_h: int) -> float:
    """CapCut fits media inside the canvas by default; this scale makes it fill (crop) instead."""

    fit = min(canvas_w / media_w, canvas_h / media_h)
    cover = max(canvas_w / media_w, canvas_h / media_h)
    return cover / fit


class CapCutExporter:
    def __init__(self, drafts_dir: str | Path | None = None) -> None:
        self._drafts_dir = Path(drafts_dir) if drafts_dir else default_drafts_dir()

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
        name = base = _draft_name(timeline["title"])
        suffix = 2
        while (root / name).exists():
            name, suffix = f"{base} ({suffix})", suffix + 1
        width, height = timeline["width"], timeline["height"]
        script = cc.DraftFolder(str(root)).create_draft(name, width, height, fps=timeline["fps"])

        script.add_track(cc.TrackType.video, "visuals")
        script.add_track(cc.TrackType.audio, "voice")
        if timeline.get("music"):
            script.add_track(cc.TrackType.audio, "music")
        if timeline.get("logo"):
            script.add_track(cc.TrackType.video, "logo", relative_index=1)
        script.add_track(cc.TrackType.text, "hooks")

        # Integer microsecond boundaries derived from cumulative times, so adjacent
        # segments touch exactly and never overlap through rounding.
        bounds = [round(scene["start"] * _US) for scene in timeline["scenes"]] + [round(timeline["duration"] * _US)]
        for scene, start, end in zip(timeline["scenes"], bounds, bounds[1:]):
            self._add_visual(cc, script, work / scene["visual"], scene, start, end - start, width, height)
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

        script.save()
        return root / name

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

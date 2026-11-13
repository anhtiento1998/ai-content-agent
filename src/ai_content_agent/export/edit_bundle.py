"""Version-independent edit bundle: FCPXML + SRT + the run's media in one folder.

The fallback when a CapCut draft cannot be written (CapCut 10.x, no
pycapcut) and the way into other editors. DaVinci Resolve and Final Cut Pro
import the FCPXML timeline directly: scene visuals on the main track, each
scene's voice and the music as connected audio, the logo as a connected
still. Captions come as SRT (Resolve: File > Import > Subtitle; CapCut:
Captions > Import), hooks and timings are listed in README.txt. Media is
copied into the bundle, so the folder can be moved to another machine.
"""

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

from ai_content_agent.export.capcut import _draft_name

FCPXML_VERSION = "1.10"


def _t(seconds: float, fps: int) -> str:
    """FCPXML rational time on the frame grid, e.g. 151/30s."""

    frames = round(seconds * fps)
    value = Fraction(frames, fps)
    return f"{value.numerator}/{value.denominator}s" if value.denominator != 1 else f"{value.numerator}s"


class EditBundleExporter:
    def export(self, work_dir: str | Path, out_dir: str | Path | None = None) -> Path:
        work = Path(work_dir).resolve()
        timeline_path = work / "timeline.json"
        if not timeline_path.is_file():
            raise FileNotFoundError(f"{timeline_path} not found — only runs rendered by this version can be exported")
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        bundle = Path(out_dir).resolve() if out_dir else work / "edit_bundle"
        media = bundle / "media"
        media.mkdir(parents=True, exist_ok=True)

        def stage(source: str | Path) -> Path:
            source = Path(source)
            source = source if source.is_absolute() else work / source
            target = media / source.name
            if not target.exists():
                shutil.copy2(source, target)
            return target

        fps, width, height = timeline["fps"], timeline["width"], timeline["height"]
        total = timeline["duration"]
        root = ET.Element("fcpxml", version=FCPXML_VERSION)
        resources = ET.SubElement(root, "resources")
        ET.SubElement(resources, "format", id="r0", name=f"FFVideoFormat{width}x{height}p{fps}",
                      frameDuration=f"1/{fps}s", width=str(width), height=str(height))
        counter = iter(range(1, 10_000))

        def asset(path: Path, *, video: bool, audio: bool, duration: float) -> str:
            ref = f"r{next(counter)}"
            attrs = {"id": ref, "name": path.stem, "start": "0s", "duration": _t(duration, fps),
                     "hasVideo": "1" if video else "0", "hasAudio": "1" if audio else "0"}
            if video:
                attrs["format"] = "r0"
            if audio:
                attrs.update(audioSources="1", audioChannels="2", audioRate="48000")
            element = ET.SubElement(resources, "asset", **attrs)
            ET.SubElement(element, "media-rep", kind="original-media", src=path.as_uri())
            return ref

        library = ET.SubElement(root, "library")
        event = ET.SubElement(library, "event", name="ai-content-agent")
        project = ET.SubElement(event, "project", name=timeline["title"])
        sequence = ET.SubElement(project, "sequence", format="r0", duration=_t(total, fps), tcStart="0s",
                                 tcFormat="NDF", audioLayout="stereo", audioRate="48k")
        spine = ET.SubElement(sequence, "spine")

        first_clip = None
        for scene in timeline["scenes"]:
            visual = stage(scene["visual"])
            is_image = scene["visual_kind"] == "image"
            ref = asset(visual, video=True, audio=False, duration=0 if is_image else scene["duration"])
            attrs = {"ref": ref, "name": f"Cảnh {scene['index']}", "offset": _t(scene["start"], fps),
                     "start": "0s", "duration": _t(scene["duration"], fps)}
            clip = ET.SubElement(spine, "video" if is_image else "asset-clip", **attrs)
            first_clip = first_clip if first_clip is not None else clip
            voice = stage(scene["voice"])
            voice_ref = asset(voice, video=False, audio=True, duration=scene["voice_duration"])
            # Connected clips: offset is in the parent's time, i.e. its own start.
            ET.SubElement(clip, "asset-clip", ref=voice_ref, lane="-1", name=f"Giọng {scene['index']}",
                          offset="0s", start="0s", duration=_t(scene["voice_duration"], fps))
            if scene.get("avatar"):  # corner talking head: a connected clip above the visual, to place by hand
                avatar_ref = asset(stage(scene["avatar"]), video=True, audio=False, duration=scene["duration"])
                ET.SubElement(clip, "asset-clip", ref=avatar_ref, lane="2", name=f"Avatar {scene['index']}",
                              offset="0s", start="0s", duration=_t(scene["duration"], fps))

        if first_clip is not None and timeline.get("music"):
            music = stage(timeline["music"])
            music_ref = asset(music, video=False, audio=True, duration=total)
            ET.SubElement(first_clip, "asset-clip", ref=music_ref, lane="-2", name="Nhạc nền", offset="0s",
                          start="0s", duration=_t(total, fps)).append(
                ET.Element("adjust-volume", amount="-16dB"))
        if first_clip is not None and timeline.get("logo"):
            logo = stage(timeline["logo"])
            logo_ref = asset(logo, video=True, audio=False, duration=0)
            ET.SubElement(first_clip, "video", ref=logo_ref, lane="1", name="Logo", offset="0s", start="0s",
                          duration=_t(total, fps))

        ET.indent(root)
        fcpxml = bundle / f"{_draft_name(timeline['title'])}.fcpxml"
        fcpxml.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n'
                          + ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")

        captions = work / timeline.get("captions", "subtitles.srt")
        if captions.is_file():
            shutil.copy2(captions, bundle / "captions.srt")
        final = work / "final.mp4"
        if final.is_file():
            shutil.copy2(final, bundle / "final.mp4")
        (bundle / "README.txt").write_text(self._readme(timeline, fcpxml.name), encoding="utf-8")
        return bundle

    @staticmethod
    def _readme(timeline: dict, fcpxml_name: str) -> str:
        lines = [
            f"{timeline['title']} — gói dựng từ ai-content-agent",
            "",
            f"{fcpxml_name}: timeline cho DaVinci Resolve (File > Import > Timeline) hoặc Final Cut Pro.",
            "captions.srt: phụ đề (Resolve: File > Import > Subtitle; CapCut: Phụ đề > Nhập file).",
            "media/: hình, clip, giọng đọc, nhạc, logo dùng trong timeline.",
            "final.mp4: bản đã dựng hoàn chỉnh để đối chiếu.",
            "",
            f"Khung hình {timeline['width']}x{timeline['height']}, {timeline['fps']} fps, "
            f"dài {timeline['duration']:.2f}s.",
            "",
            "Chữ hook từng cảnh (thêm bằng công cụ chữ của trình dựng):",
        ]
        for scene in timeline["scenes"]:
            if scene.get("on_screen_text"):
                end = scene["start"] + scene["duration"]
                lines.append(f"  {scene['start']:6.2f}s – {end:6.2f}s  {scene['on_screen_text']}")
        return "\n".join(lines) + "\n"

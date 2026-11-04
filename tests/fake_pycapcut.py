"""Stand-in for the `pycapcut` package, mirroring the signatures and the validation
the real library performs (track must exist and match type, segments must not
overlap, source ranges must fit the material). save() writes a JSON summary of
the edit so tests can assert on what would be sent to CapCut."""

import enum
import json
import os
import subprocess
import wave


class Timerange:
    def __init__(self, start, duration):
        self.start, self.duration = int(start), int(duration)

    @property
    def end(self):
        return self.start + self.duration


class TrackType(enum.Enum):
    video = "video"
    audio = "audio"
    text = "text"


class KeyframeProperty(enum.Enum):
    uniform_scale = "UNIFORM_SCALE"


def _media_duration_us(path):
    if path.endswith(".wav"):
        with wave.open(path) as w:
            return int(round(w.getnframes() / w.getframerate() * 1e6))
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return int(round(float(out) * 1e6))


class VideoMaterial:
    def __init__(self, path, material_name=None, crop_settings=None):
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        self.path = path
        self.material_type = "photo" if path.lower().endswith((".png", ".jpg", ".jpeg")) else "video"
        self.duration = 10800000000 if self.material_type == "photo" else _media_duration_us(path)


class AudioMaterial:
    def __init__(self, path, material_name=None):
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        self.path = path
        self.duration = _media_duration_us(path)


class ClipSettings:
    def __init__(self, *, alpha=1.0, flip_horizontal=False, flip_vertical=False, rotation=0.0,
                 scale_x=1.0, scale_y=1.0, transform_x=0.0, transform_y=0.0):
        self.scale_x, self.scale_y, self.transform_x, self.transform_y = scale_x, scale_y, transform_x, transform_y


class TextStyle:
    def __init__(self, *, size=8.0, bold=False, italic=False, underline=False, color=(1.0, 1.0, 1.0), alpha=1.0,
                 align=0, vertical=False, letter_spacing=0, line_spacing=0, auto_wrapping=False, max_line_width=0.82):
        self.size, self.bold, self.color = size, bold, color


class TextBorder:
    def __init__(self, *, alpha=1.0, color=(0.0, 0.0, 0.0), width=40.0):
        self.color, self.width = color, width


class _Segment:
    kind = None

    def __init__(self, material, target_timerange, source_timerange=None):
        self.material = material
        self.target_timerange = target_timerange
        if source_timerange is None:
            source_timerange = Timerange(0, target_timerange.duration)
        if material is not None and source_timerange.end > material.duration:
            raise ValueError(f"source range {source_timerange.end} exceeds material duration {material.duration}")
        self.source_timerange = source_timerange

    @property
    def end(self):
        return self.target_timerange.end


class VideoSegment(_Segment):
    kind = TrackType.video

    def __init__(self, material, target_timerange, *, source_timerange=None, speed=None, volume=1.0,
                 change_pitch=False, clip_settings=None):
        super().__init__(material, target_timerange, source_timerange)
        self.volume, self.clip_settings, self.keyframes = volume, clip_settings, []

    def add_keyframe(self, _property, time_offset, value):
        if not isinstance(time_offset, int) or not 0 <= time_offset <= self.target_timerange.duration:
            raise ValueError(f"keyframe offset {time_offset!r} outside the segment")
        self.keyframes.append((_property.value, time_offset, value))
        return self


class AudioSegment(_Segment):
    kind = TrackType.audio

    def __init__(self, material, target_timerange, *, source_timerange=None, speed=None, volume=1.0,
                 change_pitch=False):
        super().__init__(material, target_timerange, source_timerange)
        self.volume = volume


class TextSegment(_Segment):
    kind = TrackType.text

    def __init__(self, text, timerange, *, font=None, style=None, clip_settings=None, border=None,
                 background=None, shadow=None):
        super().__init__(None, timerange)
        self.text, self.style, self.clip_settings, self.border = text, style, clip_settings, border


class ScriptFile:
    def __init__(self, width, height, fps, save_path):
        self.width, self.height, self.fps, self.save_path = width, height, fps, save_path
        self.tracks = {}
        self.srt_imports = []
        self.duration = 0

    def add_track(self, track_type, track_name=None, *, mute=False, relative_index=0, absolute_index=None):
        if track_name in self.tracks:
            raise NameError(f"track {track_name} already exists")
        self.tracks[track_name] = {"type": track_type, "segments": []}
        return self

    def add_segment(self, segment, track_name=None):
        if track_name not in self.tracks:
            raise NameError(f"track {track_name!r} not found")
        track = self.tracks[track_name]
        if track["type"] is not segment.kind:
            raise TypeError(f"{type(segment).__name__} cannot go on a {track['type'].value} track")
        for other in track["segments"]:
            if segment.target_timerange.start < other.end and other.target_timerange.start < segment.end:
                raise ValueError(f"segment overlap on track {track_name}")
        track["segments"].append(segment)
        self.duration = max(self.duration, segment.end)
        return self

    def import_srt(self, srt_path, track_name, *, time_offset=0.0, style_reference=None, text_style=None,
                   clip_settings=None):
        if style_reference is None and clip_settings is None:
            raise ValueError("clip_settings required without a style reference")
        if not os.path.exists(srt_path):
            raise FileNotFoundError(srt_path)
        self.srt_imports.append({"path": srt_path, "track": track_name})
        return self

    def save(self):
        summary = {
            "canvas": [self.width, self.height, self.fps],
            "duration": self.duration,
            "srt": self.srt_imports,
            "tracks": {
                name: {
                    "type": track["type"].value,
                    "segments": [
                        {
                            "start": seg.target_timerange.start,
                            "duration": seg.target_timerange.duration,
                            "source_duration": seg.source_timerange.duration,
                            "path": getattr(seg.material, "path", None),
                            "text": getattr(seg, "text", None),
                            "volume": getattr(seg, "volume", None),
                            "scale": getattr(getattr(seg, "clip_settings", None), "scale_x", None),
                            "keyframes": getattr(seg, "keyframes", []),
                        }
                        for seg in track["segments"]
                    ],
                }
                for name, track in self.tracks.items()
            },
        }
        with open(self.save_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False)


class DraftFolder:
    def __init__(self, folder_path):
        if not os.path.isdir(folder_path):
            raise FileNotFoundError(folder_path)
        self.folder_path = folder_path

    def create_draft(self, draft_name, width, height, fps=30, *, maintrack_adsorb=True, allow_replace=False):
        path = os.path.join(self.folder_path, draft_name)
        if os.path.exists(path) and not allow_replace:
            raise FileExistsError(path)
        os.makedirs(path, exist_ok=True)
        return ScriptFile(width, height, fps, os.path.join(path, "draft_content.json"))

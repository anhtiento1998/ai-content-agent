"""Burned-in captions as an ASS subtitle file (rendered by ffmpeg's libass).

Timing is estimated: each scene's narration is split into short chunks and
the scene's measured voice duration is shared out by chunk length. It is
not word-level forced alignment, but stays in sync per scene because every
scene starts its captions exactly when its voice-over starts.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

_PHRASE_BREAK = re.compile(r"(?<=[.,!?;:…])\s+")
_SENTENCE_END = re.compile(r"[.!?…]$")


@dataclass
class Caption:
    start: float
    end: float
    text: str


def _fits(text: str, max_chars: int, max_words: int) -> bool:
    return len(text) <= max_chars and len(text.split()) <= max_words


def split_into_chunks(text: str, *, max_chars: int = 28, max_words: int = 7) -> list[str]:
    """Caption lines that never straddle a sentence: split at punctuation, merge short
    clauses of the same sentence when they fit one line, split long clauses evenly."""

    phrases: list[str] = []
    for phrase in _PHRASE_BREAK.split(" ".join(text.split())):
        if not phrase:
            continue
        if phrases and not _SENTENCE_END.search(phrases[-1]) and _fits(f"{phrases[-1]} {phrase}", max_chars, max_words):
            phrases[-1] = f"{phrases[-1]} {phrase}"
        else:
            phrases.append(phrase)

    chunks: list[str] = []
    for phrase in phrases:
        words = phrase.split()
        parts = max(math.ceil(len(phrase) / max_chars), math.ceil(len(words) / max_words), 1)
        bounds = [round(i * len(words) / parts) for i in range(parts + 1)]
        chunks += [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:]) if b > a]
    return chunks


def time_captions(chunks: list[str], start: float, duration: float) -> list[Caption]:
    weights = [len(chunk) + 2 for chunk in chunks]
    total = sum(weights) or 1
    captions, cursor = [], start
    for chunk, weight in zip(chunks, weights):
        end = cursor + duration * weight / total
        captions.append(Caption(cursor, end, chunk))
        cursor = end
    if captions:
        captions[-1].end = start + duration
    return captions


def _ass_time(seconds: float) -> str:
    centis = max(0, round(seconds * 100))
    hours, rest = divmod(centis, 360000)
    minutes, rest = divmod(rest, 6000)
    secs, cs = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _srt_time(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def build_srt(captions: list[Caption]) -> str:
    """SubRip captions — the format desktop editors such as CapCut import."""

    blocks = [
        f"{i}\n{_srt_time(cap.start)} --> {_srt_time(cap.end)}\n{' '.join(cap.text.split())}\n"
        for i, cap in enumerate(captions, 1)
    ]
    return "\n".join(blocks)


def _ass_escape(text: str) -> str:
    # Braces start override tags and backslashes start escapes in ASS.
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


def build_ass(
    captions: list[Caption], hooks: list[Caption], *, font: str = "Arial", width: int = 1080, height: int = 1920
) -> str:
    # Colours are &HAABBGGRR. Caption: white with black outline, low in frame but
    # above the TikTok/Shorts UI. Hook: yellow, top of frame.
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Caption,{font},70,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        "-1,0,0,0,100,100,0,0,1,6,0,2,90,90,440,1",
        f"Style: Hook,{font},86,&H0000E5FF,&H000000FF,&H00000000,&H64000000,"
        "-1,0,0,0,100,100,0,0,1,7,0,8,90,90,300,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for hook in hooks:
        lines.append(
            f"Dialogue: 1,{_ass_time(hook.start)},{_ass_time(hook.end)},Hook,,0,0,0,,"
            f"{{\\fad(200,150)}}{_ass_escape(hook.text)}"
        )
    for cap in captions:
        lines.append(
            f"Dialogue: 0,{_ass_time(cap.start)},{_ass_time(cap.end)},Caption,,0,0,0,,"
            f"{{\\fscx88\\fscy88\\t(0,110,\\fscx100\\fscy100)}}{_ass_escape(cap.text)}"
        )
    return "\n".join(lines) + "\n"

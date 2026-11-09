"""Word timing from the narration audio, and a pronunciation check — optional.

CAPTION_ALIGNER=whisper runs faster-whisper (`pip install -e ".[align]"`) on
each scene's voice track with word timestamps, then matches the recognised
words to the words the TTS was asked to say. That gives captions real word
timing, and the share of words recognised is a cheap pronunciation score: a
TTS that garbles Vietnamese tones scores low, and the run is flagged in the
review queue. Words the recogniser missed are interpolated between their
neighbours; a scene with too few matches falls back to estimated timing.

The model is downloaded from Hugging Face on first use (WHISPER_MODEL,
default "small"; "medium" is more accurate on Vietnamese but slower on CPU).
"""

from __future__ import annotations

import difflib
import logging
import re
import threading
from dataclasses import dataclass

from ai_content_agent.studio.vi_text import nfc

logger = logging.getLogger(__name__)
_TOKEN = re.compile(r"[^\W_]+")
MIN_MATCH_RATIO = 0.4  # below this the recognised words are too unreliable to time captions


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(nfc(text).lower())


@dataclass
class Alignment:
    """Per spoken token (start, end) relative to the start of the scene audio, and the match ratio."""

    times: list[tuple[float, float]] | None
    score: float


def align_tokens(expected: list[str], recognised: list[tuple[str, float, float]]) -> Alignment:
    """Match `expected` tokens to recogniser output (token, start, end); interpolate the gaps."""

    if not expected:
        return Alignment([], 1.0)
    heard = [(token, start, end) for text, start, end in recognised for token in _tokens(text) or [""]]
    matcher = difflib.SequenceMatcher(a=expected, b=[t for t, _, _ in heard], autojunk=False)
    times: list[tuple[float, float] | None] = [None] * len(expected)
    matched = 0
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            _, start, end = heard[block.b + k]
            times[block.a + k] = (start, end)
            matched += 1
    score = matched / len(expected)
    if score < MIN_MATCH_RATIO:
        return Alignment(None, score)

    # Fill unmatched tokens evenly between the surrounding matched ones.
    i = 0
    while i < len(times):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(times) and times[j] is None:
            j += 1
        left = times[i - 1][1] if i > 0 else (times[j][0] if j < len(times) else 0.0)
        right = times[j][0] if j < len(times) else max(left, heard[-1][2] if heard else left)
        step = max(right - left, 0.0) / (j - i)
        for k in range(i, j):
            times[k] = (left + step * (k - i), left + step * (k - i + 1))
        i = j
    return Alignment([t for t in times if t is not None], score)


class WhisperAligner:
    name = "whisper"

    def __init__(self, model: str = "small", *, language: str = "vi", device: str = "auto") -> None:
        try:
            import faster_whisper  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                'CAPTION_ALIGNER=whisper needs faster-whisper: pip install -e ".[align]"'
            ) from exc
        self._model_name, self._language, self._device = model, language, device
        self._model = None
        self._lock = threading.Lock()  # one model instance, scenes transcribed one at a time

    def _transcribe(self, wav_path: str) -> list[tuple[str, float, float]]:
        from faster_whisper import WhisperModel

        with self._lock:
            if self._model is None:
                logger.info("Loading Whisper model %r for caption alignment", self._model_name)
                self._model = WhisperModel(self._model_name, device=self._device, compute_type="int8")
            segments, _info = self._model.transcribe(wav_path, language=self._language, word_timestamps=True)
            return [(w.word, float(w.start), float(w.end)) for segment in segments for w in (segment.words or [])]

    def align(self, wav_path: str, spoken_text: str) -> Alignment:
        return align_tokens(_tokens(spoken_text), self._transcribe(wav_path))


def build_aligner(name: str | None, *, model: str = "small", language: str = "vi"):
    """None for "estimate" (default), else an aligner instance."""

    if not name or name == "estimate":
        return None
    if name == "whisper":
        return WhisperAligner(model, language=language)
    raise ValueError(f"CAPTION_ALIGNER must be estimate or whisper, got {name!r}")

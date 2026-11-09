"""Vietnamese TTS that runs on your own machine — no per-character bill, no account.

VieNeu-TTS v3 Turbo ("vieneu")
    Runs as a local server with an OpenAI-style endpoint, on CPU (ONNX, about
    0.5x real time on a 12th-gen Core i5) or an NVIDIA GPU. Start it once:

        pip install vieneu
        git clone https://github.com/pnnbao97/VieNeu-TTS && cd VieNeu-TTS
        uv run python -m apps.openai_speech        # serves http://localhost:8000/v1

    or with Docker (`--profile api-cpu`). 25 preset voices, e.g. "Hải Đăng"
    (default), "Mai Anh", "Ngọc Huyền", "Thùy Dung" (South), "Quang Sơn" (Central).
    We ask for raw 48 kHz PCM and write the WAV ourselves: its streaming WAV
    header has no length, which Python's wave reader rejects.
    Repo licence Apache-2.0; the weights' model card could not be checked from
    here — read it on Hugging Face before commercial use.

ZeroTTS ("zerotts")
    In-process ONNX model on CPU (`pip install zerotts`, ~900 MB of weights
    downloaded from Hugging Face on first use). Eight preset voices such as
    "maichi"; MIT licence for code and (per its README) weights.
"""

from __future__ import annotations

import threading
import wave

import requests

from .base import VoiceGenerator


class TTSServerError(RuntimeError):
    """HTTP error from a local TTS server; `status_code` lets the studio retry 429/5xx."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


def _write_wav(path: str, pcm: bytes, sample_rate: int) -> None:
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)


class VieNeuVoiceProvider(VoiceGenerator):
    name = "vieneu"
    SAMPLE_RATE = 48000

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000/v1",
        voice: str = "Hải Đăng",
        model: str = "vieneu-v3-turbo",
        api_key: str | None = None,
        timeout: float = 300,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._voice = voice
        self._model = model
        self._api_key = api_key
        self._timeout = timeout

    def synthesize(self, text: str, out_path: str, *, voice: str | None = None) -> None:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            resp = requests.post(
                f"{self._base_url}/audio/speech",
                headers=headers,
                json={"model": self._model, "input": text, "voice": voice or self._voice,
                      "response_format": "pcm", "sample_rate": self.SAMPLE_RATE},
                timeout=self._timeout,
            )
        except requests.ConnectionError as exc:
            raise ConnectionError(
                f"Cannot reach the VieNeu-TTS server at {self._base_url} — start it with "
                "`uv run python -m apps.openai_speech` in the VieNeu-TTS folder (see README \"Giọng đọc chạy trên máy\")"
            ) from exc
        if resp.status_code != 200:
            raise TTSServerError(resp.status_code, f"VieNeu-TTS HTTP {resp.status_code}: {resp.text[:300]}")
        if not resp.content:
            raise RuntimeError("VieNeu-TTS returned no audio")
        _write_wav(out_path, resp.content, self.SAMPLE_RATE)

    def voices(self) -> list[str]:
        """Preset and enrolled voice names from the server (GET /v1/voices)."""

        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        data = requests.get(f"{self._base_url}/voices", headers=headers, timeout=10).json()
        items = data.get("data", data) if isinstance(data, dict) else data
        return [item.get("name") or item.get("id") if isinstance(item, dict) else str(item) for item in items]


class ZeroTTSVoiceProvider(VoiceGenerator):
    name = "zerotts"

    def __init__(self, voice: str = "maichi", model: str = "zeroweight-ai/ZeroTTS") -> None:
        try:
            import zerotts  # noqa: F401
        except ImportError as exc:
            raise RuntimeError('VOICE_PROVIDER=zerotts needs the zerotts package: pip install -e ".[zerotts]"') from exc
        self._voice = voice
        self._model = model
        self._tts = None
        self._lock = threading.Lock()  # one ONNX session; the studio voices scenes in parallel threads

    def synthesize(self, text: str, out_path: str, *, voice: str | None = None) -> None:
        from zerotts import ZeroTTS

        with self._lock:
            if self._tts is None:
                self._tts = ZeroTTS.from_pretrained(self._model)
            audio = self._tts.synthesize(text, voice=voice or self._voice)
            # Whatever sample format it writes, the studio re-encodes it to 48 kHz PCM next.
            self._tts.save_audio(audio, out_path)

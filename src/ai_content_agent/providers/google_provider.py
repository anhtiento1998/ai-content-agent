"""Google AI: Gemini text, Imagen images, Veo clips and Gemini TTS.

Model names and parameters for Imagen/Veo/TTS change often — override them
with VISUAL_MODEL / VOICE_MODEL in .env when Google renames a model.
"""

from __future__ import annotations

import time
import wave
from pathlib import Path

from .base import ImageGenerator, TextGenerator, VideoGenerator, VoiceGenerator


class GeminiProvider(TextGenerator):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def complete(self, prompt: str) -> str:
        response = self._client.models.generate_content(model=self._model, contents=prompt)
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            self.last_usage = {
                "model": self._model,
                "input_tokens": getattr(usage, "prompt_token_count", 0) or 0,
                # Thinking tokens are billed as output.
                "output_tokens": (getattr(usage, "candidates_token_count", 0) or 0)
                + (getattr(usage, "thoughts_token_count", 0) or 0),
            }
        return response.text


class ImagenProvider(ImageGenerator):
    name = "imagen"

    def __init__(self, api_key: str, model: str = "imagen-4.0-generate-001") -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate_image(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        response = self._client.models.generate_images(
            model=self._model,
            prompt=prompt,
            config={"number_of_images": 1, "aspect_ratio": aspect_ratio},
        )
        if not response.generated_images:
            raise RuntimeError("Imagen returned no image (prompt may have been blocked by safety filters)")
        Path(out_path).write_bytes(response.generated_images[0].image.image_bytes)


class VeoProvider(VideoGenerator):
    """One Veo call per scene — the most expensive visual option; check your quota."""

    name = "veo"
    max_concurrency = 2  # Veo quotas allow few concurrent long-running generations

    def __init__(self, api_key: str, model: str = "veo-3.0-generate-001", poll_seconds: int = 10) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._poll_seconds = poll_seconds

    def generate_clip(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        operation = self._client.models.generate_videos(
            model=self._model, prompt=prompt, config={"aspect_ratio": aspect_ratio}
        )
        while not operation.done:
            time.sleep(self._poll_seconds)
            operation = self._client.operations.get(operation)

        if not operation.response or not operation.response.generated_videos:
            raise RuntimeError(f"Veo returned no video: {operation.error or 'unknown error'}")
        video = operation.response.generated_videos[0]
        self._client.files.download(file=video.video)
        video.video.save(out_path)


class GeminiVoiceProvider(VoiceGenerator):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-preview-tts", voice: str = "Kore") -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._voice = voice

    def synthesize(self, text: str, out_path: str, *, voice: str | None = None) -> None:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self._model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice or self._voice)
                    )
                ),
            ),
        )
        try:
            pcm = response.candidates[0].content.parts[0].inline_data.data
        except (AttributeError, IndexError, TypeError):
            pcm = None
        if not pcm:
            raise RuntimeError("Gemini TTS returned no audio (text may have been blocked or the model is unavailable)")
        # Gemini TTS returns raw 16-bit mono PCM at 24 kHz.
        with wave.open(out_path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(pcm)

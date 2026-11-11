"""OpenAI: GPT text, gpt-image visuals and TTS voice. Also any OpenAI-compatible text API."""

from __future__ import annotations

import base64
from pathlib import Path

from .base import ImageGenerator, TextGenerator, VoiceGenerator

_IMAGE_SIZES = {"9:16": "1024x1536", "16:9": "1536x1024", "1:1": "1024x1024"}


class OpenAIProvider(TextGenerator):
    name = "gpt"

    def __init__(self, api_key: str, model: str = "gpt-4.1", *, base_url: str | None = None) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def complete(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model, messages=[{"role": "user", "content": prompt}]
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.last_usage = {
                "model": getattr(response, "model", None) or self._model,
                "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            }
        return response.choices[0].message.content


class OpenAIImageProvider(ImageGenerator):
    name = "gpt-image"

    def __init__(self, api_key: str, model: str = "gpt-image-1") -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate_image(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        result = self._client.images.generate(
            model=self._model, prompt=prompt, size=_IMAGE_SIZES.get(aspect_ratio, "1024x1536")
        )
        Path(out_path).write_bytes(base64.b64decode(result.data[0].b64_json))


class OpenAIVoiceProvider(VoiceGenerator):
    name = "gpt"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini-tts",
        voice: str = "alloy",
        instructions: str = "Speak naturally and energetically, like a social media narrator.",
    ) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._voice = voice
        self._instructions = instructions

    def synthesize(self, text: str, out_path: str, *, voice: str | None = None) -> None:
        with self._client.audio.speech.with_streaming_response.create(
            model=self._model,
            voice=voice or self._voice,
            input=text,
            instructions=self._instructions,
            response_format="wav",
        ) as response:
            response.stream_to_file(out_path)

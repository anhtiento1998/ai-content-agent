"""Google AI (Gemini for scripts, Veo for video) — covered by a Google AI Pro plan."""

from __future__ import annotations

import time
from pathlib import Path

from ai_content_agent.utils import slugify

from .base import ScriptResult, TextGenerator, VideoGenerator, VideoResult, build_script_prompt, parse_script_json


class GeminiProvider(TextGenerator):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate_script(self, topic: str, *, style: str = "", max_words: int = 150) -> ScriptResult:
        response = self._client.models.generate_content(
            model=self._model, contents=build_script_prompt(topic, style, max_words)
        )
        return parse_script_json(response.text)


class VeoProvider(VideoGenerator):
    """Veo video generation via the Gemini API.

    NOTE: Veo access/quota and exact parameters depend on your Google AI Pro
    tier. Verify the current model name and polling contract against the
    live docs before relying on this in production — Google revises Veo's
    API surface frequently.
    """

    name = "veo"

    def __init__(self, api_key: str, model: str = "veo-3.0-generate-001") -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate_video(self, script: ScriptResult, *, aspect_ratio: str = "9:16") -> VideoResult:
        operation = self._client.models.generate_videos(
            model=self._model,
            prompt=script.script,
            config={"aspect_ratio": aspect_ratio},
        )
        while not operation.done:
            time.sleep(10)
            operation = self._client.operations.get(operation)

        video = operation.response.generated_videos[0]
        Path("output").mkdir(exist_ok=True)
        out_path = f"output/{slugify(script.title)}_{int(time.time())}.mp4"
        self._client.files.download(file=video.video)
        video.video.save(out_path)
        return VideoResult(file_path=out_path, raw={"operation_name": operation.name})

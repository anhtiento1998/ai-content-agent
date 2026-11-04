"""GPT (OpenAI) text/script generation, plus any OpenAI-compatible API."""

from __future__ import annotations

from .base import ScriptResult, TextGenerator, build_script_prompt, parse_script_json


class OpenAIProvider(TextGenerator):
    name = "gpt"

    def __init__(self, api_key: str, model: str = "gpt-4.1", *, base_url: str | None = None) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def generate_script(self, topic: str, *, style: str = "", max_words: int = 150) -> ScriptResult:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": build_script_prompt(topic, style, max_words)}],
        )
        return parse_script_json(response.choices[0].message.content)

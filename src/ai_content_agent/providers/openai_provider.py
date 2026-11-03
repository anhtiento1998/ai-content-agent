"""GPT (OpenAI) text/script generation."""

from __future__ import annotations

import json

from .base import ScriptResult, TextGenerator


class OpenAIProvider(TextGenerator):
    name = "gpt"

    def __init__(self, api_key: str, model: str = "gpt-4.1") -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate_script(self, topic: str, *, style: str = "", max_words: int = 150) -> ScriptResult:
        prompt = (
            f"Write a short-form video script about: {topic}\n"
            f"Style: {style or 'engaging, punchy, social-media friendly'}\n"
            f"Limit the spoken script to about {max_words} words.\n"
            'Respond as JSON: {"title": str, "script": str, "hashtags": [str, ...]}'
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        return ScriptResult(
            title=data["title"],
            script=data["script"],
            hashtags=data.get("hashtags", []),
            raw=data,
        )

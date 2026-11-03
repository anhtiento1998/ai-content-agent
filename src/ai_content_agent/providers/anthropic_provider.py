"""Claude (Anthropic) text/script generation."""

from __future__ import annotations

import json

from .base import ScriptResult, TextGenerator


class AnthropicProvider(TextGenerator):
    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-5-5") -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model

    def generate_script(self, topic: str, *, style: str = "", max_words: int = 150) -> ScriptResult:
        prompt = (
            f"Write a short-form video script about: {topic}\n"
            f"Style: {style or 'engaging, punchy, social-media friendly'}\n"
            f"Limit the spoken script to about {max_words} words.\n"
            "Respond with ONLY a JSON object, no prose: "
            '{"title": str, "script": str, "hashtags": [str, ...]}'
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(response.content[0].text)
        return ScriptResult(
            title=data["title"],
            script=data["script"],
            hashtags=data.get("hashtags", []),
            raw=data,
        )

"""Claude (Anthropic) text/script generation."""

from __future__ import annotations

from .base import ScriptResult, TextGenerator, build_script_prompt, parse_script_json


class AnthropicProvider(TextGenerator):
    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-5-5") -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model

    def generate_script(self, topic: str, *, style: str = "", max_words: int = 150) -> ScriptResult:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": build_script_prompt(topic, style, max_words)}],
        )
        return parse_script_json(response.content[0].text)

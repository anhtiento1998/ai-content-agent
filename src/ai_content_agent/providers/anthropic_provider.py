"""Claude (Anthropic) text generation.

Current Claude models think before answering, so a response's first content
block is usually a thinking block — the text is collected from the text blocks
only, and max_tokens leaves room for that thinking. Models with safety
classifiers can decline a request (stop_reason "refusal"); for those the
server-side fallback is enabled so the API retries on a fallback model inside
the same call instead of failing the video.
"""

from __future__ import annotations

import logging

from .base import TextGenerator

logger = logging.getLogger(__name__)

_FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Models that accept the server-side `fallbacks` parameter.
_FALLBACK_MODELS = ("claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5")


class AnthropicProvider(TextGenerator):
    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-5-5") -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model
        self._use_fallbacks = model in _FALLBACK_MODELS

    def _create(self, prompt: str):
        import anthropic

        request = {"model": self._model, "max_tokens": 16000, "messages": [{"role": "user", "content": prompt}]}
        if self._use_fallbacks:
            try:
                return self._client.beta.messages.create(**request, betas=[_FALLBACK_BETA], fallbacks="default")
            except anthropic.BadRequestError as exc:
                if "fallback" not in str(exc).lower():
                    raise
                # e.g. an account or gateway without the beta: carry on without the safety net.
                logger.warning("Server-side fallbacks are not available (%s) — continuing without them", exc)
                self._use_fallbacks = False
        return self._client.messages.create(**request)

    def complete(self, prompt: str) -> str:
        response = self._create(prompt)
        usage = response.usage
        self.last_usage = {
            "model": response.model,  # the model that actually answered (may be the fallback)
            "input_tokens": usage.input_tokens + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
            + (getattr(usage, "cache_read_input_tokens", 0) or 0),
            "output_tokens": usage.output_tokens,
        }
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) or "policy"
            raise RuntimeError(f"Claude declined to write this script (refusal: {category}) — rephrase the topic")
        text = "".join(block.text for block in response.content if block.type == "text")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("Claude's reply was cut off at max_tokens before the storyboard was complete")
        return text

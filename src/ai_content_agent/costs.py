"""What each video cost in API fees — metered from real usage where the API reports it.

Text is priced from the token counts each provider returns; images per image,
video clips per second of generated video, speech per minute of audio. Local
engines (card, silent, vieneu, zerotts, comfyui) cost nothing.

Prices are US dollars and go stale: the Claude rows are Anthropic's list
prices as of 2026-11-03; the OpenAI and Google rows are best-effort list
prices that could not be re-checked from the development environment. Put
corrections in a JSON file and point PRICING_FILE at it — same shape as
DEFAULT_PRICES, merged over it:

    {"text": {"gpt-4.1": {"input": 2.0, "output": 8.0}},
     "image": {"imagen-4.0-generate-001": {"per_image": 0.04}}}

A model with no price is reported as "unpriced" rather than guessed, and the
run's total is flagged incomplete. Batch and cache discounts are ignored, so
totals are an upper estimate of list price, not an invoice.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

# text: USD per million tokens. image: USD per image. video: USD per second. voice: USD per minute.
DEFAULT_PRICES: dict[str, dict[str, dict[str, float]]] = {
    "text": {
        "claude-fable-5-2": {"input": 8.0, "output": 40.0},
        "claude-fable-5-1": {"input": 10.0, "output": 50.0},
        "claude-opus-5-5": {"input": 4.0, "output": 20.0},
        "claude-opus-5": {"input": 5.0, "output": 25.0},
        "claude-opus-4-8": {"input": 5.0, "output": 25.0},
        "claude-sonnet-5-5": {"input": 2.0, "output": 10.0},
        "claude-sonnet-5": {"input": 2.0, "output": 10.0},
        "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
        "claude-haiku-5-5": {"input": 0.10, "output": 0.50},
        "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
        "gpt-4.1": {"input": 2.0, "output": 8.0},
        "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    },
    "image": {
        "imagen-4.0-generate-001": {"per_image": 0.04},
        "gpt-image-1": {"per_image": 0.063},
    },
    "video": {
        "veo-3.0-generate-001": {"per_second": 0.40},
    },
    "voice": {
        "gemini-2.5-flash-preview-tts": {"per_minute": 0.015},
        "gpt-4o-mini-tts": {"per_minute": 0.015},
    },
}
FREE_PROVIDERS = {"card", "silent", "vieneu", "zerotts", "comfyui", "comfyui-video", "comfyui-avatar"}


class PriceBook:
    def __init__(self, pricing_file: str | None = None) -> None:
        self._prices = {kind: dict(models) for kind, models in DEFAULT_PRICES.items()}
        if pricing_file:
            path = Path(pricing_file)
            if not path.is_file():
                raise FileNotFoundError(f"PRICING_FILE {pricing_file!r} not found")
            try:
                overrides = json.loads(path.read_text(encoding="utf-8"))
            except ValueError as exc:
                raise ValueError(f"PRICING_FILE {pricing_file!r} is not valid JSON: {exc}") from exc
            for kind, models in overrides.items():
                if kind not in self._prices or not isinstance(models, dict):
                    raise ValueError(f"PRICING_FILE: unknown section {kind!r} (use text, image, video, voice)")
                self._prices[kind].update(models)

    def lookup(self, kind: str, model: str | None) -> dict[str, float] | None:
        """Price row for `model`: exact id, else the longest known id it starts with
        (providers append date or revision suffixes)."""

        if not model:
            return None
        table = self._prices.get(kind, {})
        if model in table:
            return table[model]
        matches = [known for known in table if model.startswith(known)]
        return table[max(matches, key=len)] if matches else None


@dataclass
class CostItem:
    kind: str  # text | image | video | voice
    provider: str
    model: str | None
    quantity: float
    unit: str  # tokens | images | seconds | minutes
    usd: float | None  # None = no price known for this model


class CostMeter:
    """Collects one run's usage; safe to call from the studio's worker threads."""

    def __init__(self, prices: PriceBook | None = None) -> None:
        self._prices = prices or PriceBook()
        self._items: list[CostItem] = []
        self._lock = threading.Lock()

    def _add(self, item: CostItem) -> None:
        with self._lock:
            self._items.append(item)

    def _priced(self, kind: str, provider: str, model: str | None, compute) -> float | None:
        if provider in FREE_PROVIDERS:
            return 0.0
        row = self._prices.lookup(kind, model)
        return round(compute(row), 6) if row else None

    def add_text(self, provider: str, model: str | None, input_tokens: int, output_tokens: int) -> None:
        usd = self._priced("text", provider, model, lambda row: (
            input_tokens * row.get("input", 0.0) + output_tokens * row.get("output", 0.0)) / 1_000_000)
        self._add(CostItem("text", provider, model, input_tokens + output_tokens, "tokens", usd))

    def add_images(self, provider: str, model: str | None, count: int = 1) -> None:
        usd = self._priced("image", provider, model, lambda row: count * row.get("per_image", 0.0))
        self._add(CostItem("image", provider, model, count, "images", usd))

    def add_video(self, provider: str, model: str | None, seconds: float) -> None:
        usd = self._priced("video", provider, model, lambda row: seconds * row.get("per_second", 0.0))
        self._add(CostItem("video", provider, model, round(seconds, 2), "seconds", usd))

    def add_voice(self, provider: str, model: str | None, seconds: float) -> None:
        usd = self._priced("voice", provider, model, lambda row: seconds / 60 * row.get("per_minute", 0.0))
        self._add(CostItem("voice", provider, model, round(seconds / 60, 3), "minutes", usd))

    def summary(self) -> dict:
        """{"usd": total of priced items, "complete": every item had a price, "by_kind": {...}, "items": [...]}.
        Items of one kind/provider/model are merged."""

        with self._lock:
            items = list(self._items)
        merged: dict[tuple, CostItem] = {}
        for item in items:
            key = (item.kind, item.provider, item.model, item.unit)
            if key in merged:
                current = merged[key]
                current.quantity = round(current.quantity + item.quantity, 3)
                current.usd = None if current.usd is None or item.usd is None else round(current.usd + item.usd, 6)
            else:
                merged[key] = CostItem(**asdict(item))
        by_kind: dict[str, float] = {}
        for item in merged.values():
            if item.usd is not None:
                by_kind[item.kind] = round(by_kind.get(item.kind, 0.0) + item.usd, 6)
        return {
            "usd": round(sum(by_kind.values()), 4),
            "complete": all(item.usd is not None for item in merged.values()),
            "by_kind": by_kind,
            "items": [asdict(item) for item in merged.values()],
        }

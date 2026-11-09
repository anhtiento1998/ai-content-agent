"""Provider registry — the single place that knows which engines exist.

To add a new engine later: implement the matching interface from base.py in
a module here, then add one line to the right registry below.
"""

from .anthropic_provider import AnthropicProvider
from .base import (
    ImageGenerator,
    ScriptResult,
    TextGenerator,
    VideoGenerator,
    VideoResult,
    VoiceGenerator,
)
from .google_provider import GeminiProvider, GeminiVoiceProvider, ImagenProvider, VeoProvider
from .local_provider import CardImageProvider, SilentVoiceProvider
from .local_tts import VieNeuVoiceProvider, ZeroTTSVoiceProvider
from .meta_muse_provider import MetaMuseVideoProvider, MuseSparkProvider
from .openai_provider import OpenAIImageProvider, OpenAIProvider, OpenAIVoiceProvider

TEXT_PROVIDERS = {
    "gpt": OpenAIProvider,
    "claude": AnthropicProvider,
    "gemini": GeminiProvider,
    "muse": MuseSparkProvider,
}

# Image providers are animated with a slow zoom; video providers are trimmed/looped.
VISUAL_PROVIDERS = {
    "card": CardImageProvider,
    "gpt-image": OpenAIImageProvider,
    "imagen": ImagenProvider,
    "veo": VeoProvider,
    "muse": MetaMuseVideoProvider,
}

VOICE_PROVIDERS = {
    "gpt": OpenAIVoiceProvider,
    "gemini": GeminiVoiceProvider,
    "vieneu": VieNeuVoiceProvider,
    "zerotts": ZeroTTSVoiceProvider,
    "silent": SilentVoiceProvider,
}

__all__ = [
    "ScriptResult",
    "VideoResult",
    "TextGenerator",
    "ImageGenerator",
    "VideoGenerator",
    "VoiceGenerator",
    "OpenAIProvider",
    "OpenAIImageProvider",
    "OpenAIVoiceProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "GeminiVoiceProvider",
    "ImagenProvider",
    "VeoProvider",
    "MuseSparkProvider",
    "MetaMuseVideoProvider",
    "CardImageProvider",
    "SilentVoiceProvider",
    "VieNeuVoiceProvider",
    "ZeroTTSVoiceProvider",
    "TEXT_PROVIDERS",
    "VISUAL_PROVIDERS",
    "VOICE_PROVIDERS",
]

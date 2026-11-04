"""Provider registry — the single place that knows which classes exist.

To add a new text/video/image engine later: implement TextGenerator or
VideoGenerator in a new module here, then add one line below.
"""

from .anthropic_provider import AnthropicProvider
from .base import ScriptResult, TextGenerator, VideoGenerator, VideoResult
from .google_provider import GeminiProvider, VeoProvider
from .meta_muse_provider import MetaMuseVideoProvider, MuseSparkProvider
from .openai_provider import OpenAIProvider

TEXT_PROVIDERS = {
    "gpt": OpenAIProvider,
    "claude": AnthropicProvider,
    "gemini": GeminiProvider,
    "muse": MuseSparkProvider,
}

VIDEO_PROVIDERS = {
    "veo": VeoProvider,
    "muse": MetaMuseVideoProvider,
}

__all__ = [
    "ScriptResult",
    "TextGenerator",
    "VideoGenerator",
    "VideoResult",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "VeoProvider",
    "MuseSparkProvider",
    "MetaMuseVideoProvider",
    "TEXT_PROVIDERS",
    "VIDEO_PROVIDERS",
]

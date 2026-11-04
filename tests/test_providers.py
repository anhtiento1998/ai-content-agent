"""Registry/interface compliance and offline engines — no network calls, no API keys."""

import wave

from fakes import FakeText  # noqa: F401  (puts src/ on sys.path)
from PIL import Image

from ai_content_agent.providers import TEXT_PROVIDERS, VISUAL_PROVIDERS, VOICE_PROVIDERS
from ai_content_agent.providers.base import (
    ImageGenerator,
    TextGenerator,
    VideoGenerator,
    VoiceGenerator,
    parse_json_object,
)
from ai_content_agent.providers.local_provider import CardImageProvider, SilentVoiceProvider
from ai_content_agent.publishers import PUBLISHERS
from ai_content_agent.publishers.base import Publisher

import pytest


def test_registries_implement_their_interfaces():
    for registry, interfaces in (
        (TEXT_PROVIDERS, (TextGenerator,)),
        (VISUAL_PROVIDERS, (ImageGenerator, VideoGenerator)),
        (VOICE_PROVIDERS, (VoiceGenerator,)),
        (PUBLISHERS, (Publisher,)),
    ):
        for key, cls in registry.items():
            assert issubclass(cls, interfaces), key
            assert cls.name == key, key


@pytest.mark.parametrize(
    "reply",
    [
        '{"a": {"b": [1, 2]}}',
        'Sure! Here it is:\n```json\n{"a": {"b": [1, 2]}}\n```\nEnjoy.',
        'Here you go: {"a": {"b": [1, 2]}} Hope that helps!',
    ],
)
def test_parse_json_object_tolerates_fences_and_prose(reply):
    assert parse_json_object(reply) == {"a": {"b": [1, 2]}}


def test_parse_json_object_rejects_non_json():
    with pytest.raises(ValueError):
        parse_json_object("I cannot help with that.")


def test_card_images_are_vertical_and_vary_by_prompt(tmp_path):
    provider = CardImageProvider()
    provider.generate_image("a cat", str(tmp_path / "a.png"))
    provider.generate_image("a dog on a beach", str(tmp_path / "b.png"))

    with Image.open(tmp_path / "a.png") as a, Image.open(tmp_path / "b.png") as b:
        assert a.size == (1080, 1920)
        assert a.tobytes() != b.tobytes()


def test_silent_voice_length_tracks_word_count(tmp_path):
    voice = SilentVoiceProvider()
    voice.synthesize("một hai", str(tmp_path / "short.wav"))
    voice.synthesize(" ".join(["từ"] * 26), str(tmp_path / "long.wav"))

    def seconds(name):
        with wave.open(str(tmp_path / name)) as w:
            return w.getnframes() / w.getframerate()

    assert seconds("short.wav") == pytest.approx(1.5)
    assert seconds("long.wav") == pytest.approx(10.0)

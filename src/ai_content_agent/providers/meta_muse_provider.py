"""Meta Muse video generation.

Meta has not published a stable, public REST API for Muse at the time this
scaffold was written, so this is an interface stub rather than a working
client: fill in `_endpoint` and the request/response shape once you have
access (developer portal docs, or an internal API key) and it will slot
into the pipeline like any other VideoGenerator.
"""

from __future__ import annotations

import requests

from .base import ScriptResult, VideoGenerator, VideoResult


class MetaMuseProvider(VideoGenerator):
    name = "muse"

    def __init__(self, api_key: str, endpoint: str = "") -> None:
        self._api_key = api_key
        self._endpoint = endpoint or "https://graph.meta.com/v1/muse/generate"  # TODO: confirm real endpoint

    def generate_video(self, script: ScriptResult, *, aspect_ratio: str = "9:16") -> VideoResult:
        raise NotImplementedError(
            "MetaMuseProvider is a stub — set the real Muse API endpoint/payload "
            "once you have access, then implement the request below:\n"
            "  response = requests.post(self._endpoint, headers={'Authorization': "
            "f'Bearer {self._api_key}'}, json={'prompt': script.script, "
            "'aspect_ratio': aspect_ratio})"
        )
